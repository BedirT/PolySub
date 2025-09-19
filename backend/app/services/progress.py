from __future__ import annotations

from datetime import datetime

from app.models.job import Job, JobProgress, JobStatus

STAGE_RANGES: dict[JobStatus, tuple[float, float]] = {
    JobStatus.processing: (0.0, 5.0),
    JobStatus.transcribing: (5.0, 80.0),
    JobStatus.translating: (80.0, 95.0),
    JobStatus.exporting: (95.0, 100.0),
}

STAGE_EXPECTED_SECONDS: dict[JobStatus, float] = {
    JobStatus.processing: 6.0,
    JobStatus.transcribing: 120.0,
    JobStatus.translating: 45.0,
    JobStatus.exporting: 15.0,
}

TERMINAL_STATUSES = {
    JobStatus.completed,
    JobStatus.failed,
    JobStatus.cancelled,
}


def stage_bounds(status: JobStatus) -> tuple[float, float]:
    return STAGE_RANGES.get(status, (0.0, 100.0))


def stage_expected_seconds(status: JobStatus) -> float:
    return STAGE_EXPECTED_SECONDS.get(status, 30.0)


def update_stage_progress(
    job: Job,
    status: JobStatus,
    message: str,
    local_progress: float | None = None,
) -> None:
    start, end = stage_bounds(status)
    job.status = status
    job.progress_start_bound = start
    job.progress_end_bound = end
    job.progress_expected_seconds = stage_expected_seconds(status)
    job.progress_last_tick = datetime.utcnow()

    percent = job.progress.percent
    if local_progress is not None:
        clamped = max(0.0, min(100.0, local_progress))
        span = max(end - start, 0.1)
        percent = start + (clamped / 100.0) * span
        if clamped >= 100.0:
            percent = end
        else:
            percent = min(percent, end - 0.5)
        percent = max(job.progress.percent, percent)
    else:
        if percent < start:
            percent = start
        percent = min(percent, end - 1.0)

    job.progress = JobProgress(percent=percent, stage=status, message=message)
    job.updated_at = datetime.utcnow()


def finalize_stage(job: Job, status: JobStatus, message: str) -> None:
    start, end = stage_bounds(status)
    job.status = status
    job.progress = JobProgress(percent=end, stage=status, message=message)
    job.progress_start_bound = end
    job.progress_end_bound = end
    job.progress_last_tick = datetime.utcnow()
    job.updated_at = datetime.utcnow()
