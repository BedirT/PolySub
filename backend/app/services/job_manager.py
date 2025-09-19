from __future__ import annotations

import asyncio
import contextlib
import uuid
from datetime import datetime
from typing import Dict, Optional

import aiofiles
from fastapi import UploadFile

from app.config import settings
from app.models.job import Job, JobOptions, JobProgress, JobStatus
from app.services.pipeline import process_job
from app.services.progress import TERMINAL_STATUSES


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._queue: "asyncio.Queue[str]" = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._progress_task: Optional[asyncio.Task[None]] = None

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


job_manager = JobManager()
