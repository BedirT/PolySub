from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.config import settings


def _ffmpeg_binary() -> str:
    if settings.ffmpeg_path and settings.ffmpeg_path.exists():
        return str(settings.ffmpeg_path)
    resolved = shutil.which("ffmpeg")
    if resolved:
        return resolved
    raise RuntimeError(
        "ffmpeg executable not found. Install ffmpeg or set FFMPEG_PATH to its location."
    )


def extract_audio(source: Path, target: Path) -> None:
    ffmpeg = _ffmpeg_binary()
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(target),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def ensure_ffmpeg_available() -> str:
    """Return the ffmpeg binary path or raise if unavailable."""
    return _ffmpeg_binary()
