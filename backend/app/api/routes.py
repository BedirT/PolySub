from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.models.job import JobOptions, TranslationModel
from app.services.job_manager import job_manager
from app.services.system_info import detect_system_specs

router = APIRouter(prefix="/api")


def _serialize(job):  # pragma: no cover - simple serialization
    data = job.model_dump(mode="json")
    if "openai_api_key" in data.get("options", {}):
        data["options"].pop("openai_api_key", None)
    if "assemblyai_api_key" in data.get("options", {}):
        data["options"].pop("assemblyai_api_key", None)
    data["source_path"] = str(job.source_path)
    if job.audio_path:
        data["audio_path"] = str(job.audio_path)
    data["artifacts"] = [
        {
            "kind": artifact.kind,
            "path": str(artifact.path),
            "label": artifact.label,
        }
        for artifact in job.artifacts
    ]
    return data


class TranslationPayload(BaseModel):
    languages: list[str]
    model: TranslationModel
    openai_api_key: str | None = None


@router.post("/jobs")
async def create_job(file: UploadFile = File(...), options: str = Form("{}")):
    try:
        parsed = JobOptions.model_validate_json(options)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job = await job_manager.create_job(file, parsed)
    return _serialize(job)


@router.get("/jobs")
async def list_jobs():
    return [_serialize(job) for job in job_manager.list_jobs()]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize(job)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    cancelled = await job_manager.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Unable to cancel job")
    return {"status": "cancelled"}


@router.get("/jobs/{job_id}/artifacts/{filename}")
async def download_artifact(job_id: str, filename: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    for artifact in job.artifacts:
        if Path(artifact.path).name == filename:
            return FileResponse(path=artifact.path, filename=filename)
    raise HTTPException(status_code=404, detail="Artifact not found")


@router.get("/system/specs")
async def system_specs():
    return detect_system_specs()


@router.post("/jobs/{job_id}/translate")
async def translate_job(job_id: str, payload: TranslationPayload):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        updated = await job_manager.start_translation(
            job_id,
            languages=payload.languages,
            model=payload.model,
            openai_api_key=payload.openai_api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize(updated)
