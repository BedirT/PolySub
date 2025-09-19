from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from app.engines.types import TranscriptionResult
from app.models.job import Job

ProgressFn = Callable[[float, str], None]


class BaseTranscriptionEngine(ABC):
    name: str

    @abstractmethod
    async def transcribe(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        ...
