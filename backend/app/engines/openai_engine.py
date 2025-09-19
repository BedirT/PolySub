from __future__ import annotations

import asyncio
from pathlib import Path

from app.config import settings
from app.engines.base import BaseTranscriptionEngine, ProgressFn
from app.engines.types import Segment, TranscriptionResult
from app.models.job import Job

try:  # pragma: no cover
    from openai import OpenAI
except ImportError as err:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]
    IMPORT_ERROR = err
else:
    IMPORT_ERROR = None


class OpenAITranscriptionEngine(BaseTranscriptionEngine):
    name = "openai"

    def __init__(self, model: str, api_key: str | None = None) -> None:
        if OpenAI is None:  # pragma: no cover
            raise IMPORT_ERROR  # type: ignore[misc]
        key = api_key or settings.openai_api_key
        if not key:
            raise RuntimeError("OpenAI API key required for OpenAI engines")
        self.model = model
        self.client = OpenAI(api_key=key)

    async def transcribe(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_sync, audio_path, update)

    def _run_sync(self, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        update(20.0, "Uploading to OpenAI")
        with audio_path.open("rb") as handle:
            response = self.client.audio.transcriptions.create(
                model=self.model,
                file=handle,
                response_format="verbose_json",
            )
        update(80.0, "Parsing response")
        segments = []
        texts = []
        for item in response.segments or []:
            segments.append(
                Segment(
                    start=float(item.start),
                    end=float(item.end),
                    text=item.text.strip(),
                )
            )
            texts.append(item.text.strip())
        language = getattr(response, "language", "unknown")
        update(95.0, "OpenAI transcription complete")
        return TranscriptionResult(language=language, segments=segments, text=" ".join(texts))
