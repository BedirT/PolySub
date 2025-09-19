from __future__ import annotations

import asyncio
import contextlib
import uuid
from datetime import datetime
from typing import Dict, Optional

import aiofiles
from fastapi import UploadFile

from app.config import settings
from app.models.job import Job, JobOptions, JobProgress, JobStatus, TranslationModel
from app.services.pipeline import perform_translation, process_job, write_translation_artifacts
from app.services.progress import TERMINAL_STATUSES, finalize_stage, update_stage_progress


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._queue: "asyncio.Queue[str]" = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._progress_task: Optional[asyncio.Task[None]] = None
        self._translation_tasks: Dict[str, asyncio.Task[None]] = {}

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker_loop())
        if self._progress_task is None:
            self._progress_task = asyncio.create_task(self._progress_daemon())

    async def shutdown(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None
        if self._progress_task:
            self._progress_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._progress_task
            self._progress_task = None
        for task in list(self._translation_tasks.values()):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._translation_tasks.clear()

    async def _worker_loop(self) -> None:
        while True:
            job_id = await self._queue.get()
            job = self._jobs.get(job_id)
            if not job:
                self._queue.task_done()
                continue
            if job.status == JobStatus.cancelled:
                self._queue.task_done()
                continue
            job.mark(JobStatus.processing, "Starting pipeline", 5.0)
            try:
                await process_job(job)
            except Exception as exc:  # pragma: no cover
                job.fail(str(exc))
            finally:
                self._queue.task_done()

    async def _progress_daemon(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            now = datetime.utcnow()
            for job in list(self._jobs.values()):
                if job.status in TERMINAL_STATUSES:
                    continue
                target = job.progress_end_bound - 1.0
                if job.progress.percent >= target:
                    continue
                expected = max(job.progress_expected_seconds, 5.0)
                elapsed = (now - job.progress_last_tick).total_seconds()
                if elapsed <= 0:
                    continue
                fraction = min(elapsed / expected, 0.2)
                remaining = max(0.0, target - job.progress.percent)
                if remaining <= 0:
                    continue
                increment = max(remaining * fraction, 0.2)
                percent = min(target, job.progress.percent + increment)
                if percent <= job.progress.percent:
                    continue
                job.progress = JobProgress(percent=percent, stage=job.progress.stage, message=job.progress.message)
                job.progress_last_tick = now
                job.updated_at = now

    async def create_job(self, file: UploadFile, options: JobOptions) -> Job:
        job_id = str(uuid.uuid4())
        job_dir = settings.storage_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        source_path = job_dir / file.filename
        async with aiofiles.open(source_path, "wb") as dest:
            while chunk := await file.read(1024 * 1024):
                await dest.write(chunk)
        await file.close()
        job = Job(id=job_id, source_path=source_path, options=options)
        job.mark(JobStatus.queued, "Queued", 0.0)
        async with self._lock:
            self._jobs[job_id] = job
            await self._queue.put(job_id)
        return job

    def list_jobs(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        if job.status in {JobStatus.completed, JobStatus.failed, JobStatus.cancelled}:
            return False
        job.status = JobStatus.cancelled
        job.progress.message = "Cancelled"
        return True

    async def start_translation(
        self,
        job_id: str,
        *,
        languages: list[str],
        model: TranslationModel,
        openai_api_key: str | None = None,
    ) -> Job:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ValueError("Job not found")
            if job.status not in {JobStatus.completed, JobStatus.exporting}:
                raise ValueError("Job must be completed before translating")
            if job_id in self._translation_tasks:
                raise ValueError("Translation already in progress for this job")
            if not job.transcript_json or not job.transcript_json.exists():
                raise ValueError("Transcript not available for translation")

            normalized_languages = sorted({lang.lower() for lang in languages if lang})
            if not normalized_languages:
                raise ValueError("No translation languages provided")
            if model == TranslationModel.none:
                raise ValueError("Translation model must be specified")

            job.options.translation_languages = normalized_languages
            job.options.translation_model = model
            if openai_api_key:
                job.options.openai_api_key = openai_api_key

            update_stage_progress(job, JobStatus.translating, "Translating subtitles", local_progress=0.0)
            job.error = None

            task = asyncio.create_task(
                self._run_translation(job_id, normalized_languages, model, openai_api_key)
            )
            self._translation_tasks[job_id] = task
            return job

    async def _run_translation(
        self,
        job_id: str,
        languages: list[str],
        model: TranslationModel,
        openai_api_key: str | None,
    ) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return

        try:
            translations = await perform_translation(job, languages, model, openai_api_key)
            finalize_stage(job, JobStatus.translating, "Translation complete")

            update_stage_progress(job, JobStatus.exporting, "Updating caption artifacts", local_progress=0.0)

            new_artifacts = write_translation_artifacts(job, translations)
            if new_artifacts:
                existing_paths = {artifact.path for artifact in new_artifacts}
                job.artifacts = [
                    artifact for artifact in job.artifacts if artifact.path not in existing_paths
                ] + new_artifacts

            finalize_stage(job, JobStatus.exporting, "Artifacts updated")
            finalize_stage(job, JobStatus.completed, "Job complete")
        except Exception as exc:  # pragma: no cover - translation failure
            message = str(exc)
            job.error = message
            update_stage_progress(
                job,
                JobStatus.translating,
                f"Translation failed: {message}",
                local_progress=100.0,
            )
            finalize_stage(job, JobStatus.translating, "Translation stage skipped")
            finalize_stage(job, JobStatus.completed, "Job complete")
        finally:
            self._translation_tasks.pop(job_id, None)


job_manager = JobManager()
