from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    transcribing = "transcribing"
    aligning = "aligning"
    translating = "translating"
    exporting = "exporting"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TranscriptionEngine(str, Enum):
    faster_whisper = "faster-whisper"
    whisperx = "whisperx"
    lightning_mlx = "lightning-whisper-mlx"
    mlx_whisper = "mlx-whisper"
    openai_gpt4o = "gpt-4o-transcribe"
    openai_gpt4omini = "gpt-4o-mini-transcribe"
    assemblyai = "assemblyai"
    speech_recognition = "speech-recognition"


class TranslationModel(str, Enum):
    gpt5_nano = "gpt-5-nano"
    gpt5_mini = "gpt-5-mini"
    none = "none"


class JobOptions(BaseModel):
    engine: TranscriptionEngine = Field(default=TranscriptionEngine.faster_whisper)
    local_model_size: Optional[str] = Field(default=None)
    translation_languages: List[str] = Field(default_factory=list)
    translation_model: TranslationModel = Field(default=TranslationModel.gpt5_nano)
    enable_alignment: bool = Field(default=True)
    enable_diarization: bool = Field(default=False)
    output_formats: List[str] = Field(default_factory=lambda: ["srt", "vtt"])
    burn_subtitles: bool = Field(default=False)
    openai_api_key: Optional[str] = Field(default=None)
    assemblyai_api_key: Optional[str] = Field(default=None)
    preferred_device: Optional[str] = Field(default=None)
    batch_size: Optional[int] = Field(default=None)
    quantization: Optional[str] = Field(default=None)
    subtitle_lead_in: Optional[float] = Field(default=None)
    subtitle_linger: Optional[float] = Field(default=None)
    subtitle_min_gap: Optional[float] = Field(default=None)
    subtitle_min_duration: Optional[float] = Field(default=None)
    subtitle_max_chars_per_line: Optional[int] = Field(default=None)
    subtitle_max_lines: Optional[int] = Field(default=None)


class JobProgress(BaseModel):
    percent: float = Field(default=0.0)
    stage: JobStatus = Field(default=JobStatus.queued)
    message: str = Field(default="Queued")


class Artifact(BaseModel):
    kind: str
    path: Path
    label: str


class Job(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: JobStatus = Field(default=JobStatus.queued)
    options: JobOptions = Field(default_factory=JobOptions)
    source_path: Path
    audio_path: Optional[Path] = None
    transcript_json: Optional[Path] = None
    summary: Optional[str] = None
    artifacts: List[Artifact] = Field(default_factory=list)
    progress: JobProgress = Field(default_factory=JobProgress)
    error: Optional[str] = None
    progress_start_bound: float = Field(default=0.0, exclude=True)
    progress_end_bound: float = Field(default=100.0, exclude=True)
    progress_expected_seconds: float = Field(default=30.0, exclude=True)
    progress_last_tick: datetime = Field(default_factory=datetime.utcnow, exclude=True)

    def mark(self, status: JobStatus, message: str, percent: float) -> None:
        self.status = status
        self.updated_at = datetime.utcnow()
        self.progress = JobProgress(percent=percent, stage=status, message=message)

    def fail(self, message: str) -> None:
        self.status = JobStatus.failed
        self.error = message
        self.updated_at = datetime.utcnow()
        self.progress = JobProgress(percent=self.progress.percent, stage=JobStatus.failed, message=message)
