from __future__ import annotations

import asyncio
from pathlib import Path

from app.config import settings
from app.engines.base import BaseTranscriptionEngine, ProgressFn
from app.engines.types import Segment, TranscriptionResult
from app.models.job import Job

try:  # pragma: no cover
    import assemblyai as aai
except ImportError as err:  # pragma: no cover
    aai = None
    IMPORT_ERROR = err
else:
    IMPORT_ERROR = None


class AssemblyAIEngine(BaseTranscriptionEngine):
    name = "assemblyai"

    def __init__(self, api_key: str | None = None) -> None:
        if aai is None:  # pragma: no cover
            raise IMPORT_ERROR  # type: ignore[misc]
        key = api_key or settings.assemblyai_api_key
        if not key:
            raise RuntimeError("AssemblyAI API key required for AssemblyAI engine")
        aai.settings.api_key = key
        self.transcriber = aai.Transcriber()

    async def transcribe(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_sync, audio_path, update)

    def _run_sync(self, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        update(20.0, "Uploading to AssemblyAI")
        transcript = self.transcriber.transcribe(str(audio_path))
        update(80.0, "Compiling segments")
        segments: list[Segment] = []
        texts: list[str] = []

        utterances = getattr(transcript, "utterances", None) or []
        for utt in utterances:
            segments.append(
                Segment(
                    start=float(utt.start) / 1000.0,
                    end=float(utt.end) / 1000.0,
                    text=utt.text.strip(),
                    speaker=utt.speaker,
                )
            )
            texts.append(utt.text.strip())

        if not segments and getattr(transcript, "text", None):
            segments.append(
                Segment(start=0.0, end=0.0, text=transcript.text.strip())
            )
            texts.append(transcript.text.strip())

        language = getattr(transcript, "language", None) or "unknown"
        update(95.0, "AssemblyAI transcription complete")
        return TranscriptionResult(language=language, segments=segments, text=" ".join(texts))
