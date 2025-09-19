from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.services.job_manager import job_manager
from app.utils.media import ensure_ffmpeg_available

app = FastAPI(title="PolySub Backend", version="0.1.0")
app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    ensure_ffmpeg_available()
    await job_manager.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await job_manager.shutdown()
