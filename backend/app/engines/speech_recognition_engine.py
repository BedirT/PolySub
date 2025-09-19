from __future__ import annotations

import asyncio
from pathlib import Path

from app.engines.base import BaseTranscriptionEngine, ProgressFn
from app.engines.types import Segment, TranscriptionResult
from app.models.job import Job

try:  # pragma: no cover
    import speech_recognition as sr
except ImportError as err:  # pragma: no cover
    sr = None
    IMPORT_ERROR = err
else:
    IMPORT_ERROR = None


class SpeechRecognitionEngine(BaseTranscriptionEngine):
    name = "speech-recognition"

    def __init__(self, model: str | None = None) -> None:
        if sr is None:  # pragma: no cover
            raise IMPORT_ERROR  # type: ignore[misc]
        self.recognizer = sr.Recognizer()
        self.model = model or "base"

    async def transcribe(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_sync, audio_path, update)

    def _run_sync(self, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        update(30.0, "Loading audio into SpeechRecognition")
        with sr.AudioFile(str(audio_path)) as source:
            audio = self.recognizer.record(source)
        update(60.0, "Running Whisper backend")
        text = self.recognizer.recognize_whisper(audio, model=self.model)
        update(95.0, "SpeechRecognition complete")
        segment = Segment(start=0.0, end=0.0, text=text)
        return TranscriptionResult(language="unknown", segments=[segment], text=text)
