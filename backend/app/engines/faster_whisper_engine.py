from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, Optional, Tuple

from app.engines.base import BaseTranscriptionEngine, ProgressFn
from app.engines.types import Segment, TranscriptionResult
from app.models.job import Job

try:
    from faster_whisper import WhisperModel
except ImportError as err:  # pragma: no cover
    WhisperModel = None  # type: ignore[assignment]
    IMPORT_ERROR = err
else:  # pragma: no cover - executed in runtime environment
    IMPORT_ERROR = None

try:  # pragma: no cover - torch might be absent
    import torch
except Exception:  # pylint: disable=broad-except
    torch = None  # type: ignore[assignment]


LOGGER = logging.getLogger(__name__)

DEFAULT_PREFERENCES: Tuple[Tuple[str, str], ...] = (
    ("cuda", "float16"),
    ("mps", "float16"),
    ("metal", "float16"),
    ("cpu", "int8"),
)


def _torch_has_cuda() -> bool:
    if torch is None:
        return False
    try:  # pragma: no cover
        return torch.cuda.is_available()
    except Exception:
        return False


def _torch_has_mps() -> bool:
    if torch is None:
        return False
    try:  # pragma: no cover
        mps = getattr(torch.backends, "mps", None)
        return bool(mps and mps.is_available())
    except Exception:
        return False


def _candidate_profiles(preferred_device: Optional[str]) -> Iterable[Tuple[str, str]]:
    ordered: list[Tuple[str, str]] = []

    def add(device: str, compute_type: str) -> None:
        if (device, compute_type) not in ordered:
            ordered.append((device, compute_type))

    def add_if_supported(device: str, compute_type: str) -> None:
        if device == "cuda" and not _torch_has_cuda():
            return
        if device == "mps" and not _torch_has_mps():
            return
        add(device, compute_type)

    preference_map = {
        "cpu": [("cpu", "int8")],
        "cuda": [("cuda", "float16")],
        "gpu": [("cuda", "float16"), ("mps", "float16"), ("metal", "float16")],
        "mps": [("mps", "float16")],
        "metal": [("metal", "float16")],
    }

    preferred_list = preference_map.get(preferred_device or "auto")
    if preferred_list:
        for device, compute in preferred_list:
            if device in {"cuda", "mps"}:
                add_if_supported(device, compute)
            else:
                add(device, compute)

    for device, compute in DEFAULT_PREFERENCES:
        if device in {"cuda", "mps"}:
            add_if_supported(device, compute)
        else:
            add(device, compute)

    return ordered


@lru_cache(maxsize=6)
def _load_model(model_size: str, preferred_device: Optional[str]) -> WhisperModel:
    if WhisperModel is None:  # pragma: no cover
        raise IMPORT_ERROR  # type: ignore[misc]
    last_error: Exception | None = None
    for device, compute_type in _candidate_profiles(preferred_device):
        try:
            LOGGER.debug(
                "Loading faster-whisper model %s (device=%s, compute_type=%s)",
                model_size,
                device,
                compute_type,
            )
            return WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception as exc:  # pragma: no cover
            LOGGER.warning(
                "Failed to load faster-whisper on device=%s compute_type=%s: %s",
                device,
                compute_type,
                exc,
            )
            last_error = exc
            continue
    raise RuntimeError(
        f"Unable to load faster-whisper model '{model_size}'. Last error: {last_error}"
    )


class FasterWhisperEngine(BaseTranscriptionEngine):
    name = "faster-whisper"

    def __init__(self, model_size: str, preferred_device: Optional[str] = None) -> None:
        self.model_size = model_size
        self.preferred_device = preferred_device

    async def transcribe(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_sync, job, audio_path, update)

    def _run_sync(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        model = _load_model(self.model_size, self.preferred_device)
        update(10.0, f"Loaded {self.model_size} model")
        segments_iter, info = model.transcribe(
            audio=str(audio_path),
            beam_size=5,
            word_timestamps=True,
        )
        segments: list[Segment] = []
        all_text: list[str] = []
        for idx, seg in enumerate(segments_iter, start=1):
            words = None
            if getattr(seg, "words", None):
                words = [
                    {"word": w.word, "start": w.start, "end": w.end, "prob": getattr(w, "probability", None)}
                    for w in seg.words
                ]
            segments.append(
                Segment(
                    start=float(seg.start),
                    end=float(seg.end),
                    text=seg.text.strip(),
                    words=words,
                )
            )
            all_text.append(seg.text.strip())
            progress = 10.0 + (idx % 90)
            update(progress, f"Decoding segment {idx}")
        text = " ".join(all_text).strip()
        language = getattr(info, "language", "unknown")
        return TranscriptionResult(language=language, segments=segments, text=text)
