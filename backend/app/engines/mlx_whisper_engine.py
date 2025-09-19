from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

from app.engines.base import BaseTranscriptionEngine, ProgressFn
from app.engines.types import Segment, TranscriptionResult
from app.models.job import Job

try:  # pragma: no cover
    from lightning_whisper_mlx.transcribe import transcribe_audio
except ImportError as err:  # pragma: no cover
    transcribe_audio = None
    IMPORT_ERROR = err
else:
    IMPORT_ERROR = None


@lru_cache(maxsize=2)
def _model_repo(model_size: str) -> str:
    presets = {
        "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
        "large-v3": "mlx-community/whisper-large-v3",
        "large": "mlx-community/whisper-large",
    }
    if model_size in presets:
        return presets[model_size]
    return model_size


class MLXWhisperEngine(BaseTranscriptionEngine):
    name = "mlx-whisper"

    def __init__(self, model_size: str, batch_size: int | None = None) -> None:
        if transcribe_audio is None:  # pragma: no cover
            raise IMPORT_ERROR  # type: ignore[misc]
        self.model_size = model_size
        self.batch_size = batch_size or 8

    async def transcribe(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_sync, job, audio_path, update)

    def _run_sync(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        repo = _model_repo(self.model_size)
        update(10.0, f"Using MLX whisper model {repo}")
        try:
            raw_result = transcribe_audio(
                str(audio_path),
                path_or_hf_repo=repo,
                batch_size=self.batch_size,
                word_timestamps=True,
            )
        except RuntimeError as exc:
            msg = str(exc)
            if "load_npz" in msg:
                raise RuntimeError(
                    f"Failed to load MLX whisper weights from {repo}. Ensure this repository contains MLX-converted .npz weights or choose a compatible mlx-community model."
                ) from exc
            raise

        segments: list[Segment] = []
        texts: list[str] = []
        if isinstance(raw_result, dict):
            segments_source = raw_result.get("segments") or []
            language = raw_result.get("language", "unknown")
        elif isinstance(raw_result, list):
            segments_source = raw_result
            language = "unknown"
        else:
            raise RuntimeError(f"Unexpected MLX whisper output type: {type(raw_result)!r}")

        for idx, seg in enumerate(segments_source, start=1):
            if isinstance(seg, dict):
                text = seg.get("text", "").strip()
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", start))
                words = seg.get("words")
            else:
                text = getattr(seg, "text", "").strip()
                start = float(getattr(seg, "start", 0.0))
                end = float(getattr(seg, "end", start))
                words = getattr(seg, "words", None)
            segments.append(Segment(start=start, end=end, text=text, words=words))
            texts.append(text)
            progress = 10.0 + min(idx * 0.5, 85.0)
            update(progress, f"Decoding segment {idx}")

        return TranscriptionResult(language=language, segments=segments, text=" ".join(texts).strip())


__all__ = ["MLXWhisperEngine"]
