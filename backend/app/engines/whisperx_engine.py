from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.engines.base import BaseTranscriptionEngine, ProgressFn
from app.engines.types import Segment, TranscriptionResult
from app.models.job import Job

try:
    import whisperx
except ImportError as err:  # pragma: no cover
    whisperx = None
    IMPORT_ERROR = err
else:
    IMPORT_ERROR = None

try:  # pragma: no cover
    import torch
except Exception:  # pylint: disable=broad-except
    torch = None  # type: ignore[assignment]


def _device() -> tuple[str, str]:
    if torch is not None:
        try:
            if torch.cuda.is_available():
                return "cuda", "float16"
        except Exception:
            pass
    return "cpu", "int8"


class WhisperXEngine(BaseTranscriptionEngine):
    name = "whisperx"

    def __init__(
        self,
        model_size: str,
        enable_alignment: bool,
        enable_diarization: bool,
        batch_size: int | None = None,
    ) -> None:
        self.model_size = model_size
        self.enable_alignment = enable_alignment
        self.enable_diarization = enable_diarization
        self.batch_size = batch_size

    async def transcribe(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_sync, job, audio_path, update)

    def _run_sync(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        if whisperx is None:  # pragma: no cover
            raise IMPORT_ERROR  # type: ignore[misc]
        device, compute_type = _device()
        update(10.0, f"Loading {self.model_size} model")
        model = whisperx.load_model(self.model_size, device=device, compute_type=compute_type)
        audio = whisperx.load_audio(str(audio_path))
        batch_size = self.batch_size or (16 if device == "cuda" else 4)
        update(15.0, "Running transcription")
        result = model.transcribe(audio, batch_size=batch_size)
        segments = result.get("segments", [])
        language = result.get("language", "unknown")

        if self.enable_alignment:
            update(35.0, "Loading alignment model")
            align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
            result = whisperx.align(
                segments,
                align_model,
                metadata,
                audio,
                device,
                return_char_alignments=False,
            )
            segments = result.get("segments", segments)

        diarize_segments = None
        if self.enable_diarization:
            hf_token = os.getenv("HUGGINGFACE_TOKEN")
            update(55.0, "Running diarization")
            diarize_pipeline = whisperx.diarize.DiarizationPipeline(use_auth_token=hf_token, device=device)
            diarize_segments = diarize_pipeline(audio)
            segments = whisperx.assign_word_speakers(diarize_segments, result)

        update(75.0, "Compiling segments")
        compiled: list[Segment] = []
        texts: list[str] = []
        for seg in segments:
            compiled.append(
                Segment(
                    start=float(seg["start"]),
                    end=float(seg["end"]),
                    text=seg["text"].strip(),
                    speaker=seg.get("speaker"),
                    words=seg.get("words"),
                )
            )
            texts.append(seg["text"].strip())
        update(90.0, "WhisperX complete")
        return TranscriptionResult(language=language, segments=compiled, text=" ".join(texts))
