from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

from app.engines.base import BaseTranscriptionEngine, ProgressFn
from app.engines.types import Segment, TranscriptionResult
from app.models.job import Job

try:  # pragma: no cover
    from lightning_whisper_mlx import LightningWhisperMLX
    from lightning_whisper_mlx.lightning import models as AVAILABLE_MODELS
except ImportError as err:  # pragma: no cover
    LightningWhisperMLX = None  # type: ignore[assignment]
    AVAILABLE_MODELS = {}
    IMPORT_ERROR = err
else:
    IMPORT_ERROR = None


def _validate_model(model_size: str) -> None:
    if model_size not in AVAILABLE_MODELS:
        valid = ", ".join(sorted(AVAILABLE_MODELS.keys()))
        raise ValueError(f"Unsupported MLX Whisper model '{model_size}'. Valid options: {valid}")


def _validate_quant(model_size: str, quantization: Optional[str]) -> Optional[str]:
    if not quantization:
        return None
    if quantization not in {"4bit", "8bit"}:
        raise ValueError("Quantization must be '4bit' or '8bit'.")
    if "distil" in model_size:
        # LightningWhisperMLX appends suffix automatically, quant still allowed
        return quantization
    return quantization


@lru_cache(maxsize=2)
def _load_model(model_size: str, batch_size: int, quantization: Optional[str]) -> LightningWhisperMLX:
    if LightningWhisperMLX is None:  # pragma: no cover
        raise IMPORT_ERROR  # type: ignore[misc]
    _validate_model(model_size)
    quant = _validate_quant(model_size, quantization)
    return LightningWhisperMLX(model=model_size, batch_size=batch_size, quant=quant)


class LightningWhisperMLEngine(BaseTranscriptionEngine):
    name = "lightning-whisper-mlx"

    def __init__(self, model_size: str, batch_size: int = 12, quantization: Optional[str] = None) -> None:
        self.model_size = model_size
        self.batch_size = max(1, batch_size)
        self.quantization = quantization

    async def transcribe(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_sync, job, audio_path, update)

    def _run_sync(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        model = _load_model(self.model_size, self.batch_size, self.quantization)
        update(10.0, f"Loaded {self.model_size} MLX model")
        result = model.transcribe(str(audio_path))
        segments: list[Segment] = []
        texts: list[str] = []
        for idx, seg in enumerate(result.get("segments", []), start=1):
            text = seg.get("text", "").strip()
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start))
            segments.append(
                Segment(start=start, end=end, text=text)
            )
            texts.append(text)
            progress = 10.0 + min(idx * 0.5, 85.0)
            update(progress, f"Decoding segment {idx}")
        language = result.get("language", "unknown")
        return TranscriptionResult(language=language, segments=segments, text=" ".join(texts).strip())


__all__ = ["LightningWhisperMLEngine", "AVAILABLE_MODELS"]
