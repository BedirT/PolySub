from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.engines.types import Segment


def _format_timestamp(seconds: float, sep: str = ",") -> str:
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}{sep}{millis:03}"


def write_srt(path: Path, segments: Iterable[Segment]) -> None:
    lines: list[str] = []
    for idx, segment in enumerate(segments, start=1):
        start = _format_timestamp(segment.start)
        end = _format_timestamp(segment.end)
        speaker = f"{segment.speaker}: " if segment.speaker else ""
        lines.extend([str(idx), f"{start} --> {end}", f"{speaker}{segment.text}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_vtt(path: Path, segments: Iterable[Segment]) -> None:
    lines = ["WEBVTT", ""]
    for segment in segments:
        start = _format_timestamp(segment.start, ".")
        end = _format_timestamp(segment.end, ".")
        speaker = f"<v {segment.speaker}>" if segment.speaker else ""
        text = f"{speaker}{segment.text}"
        lines.extend([f"{start} --> {end}", text, ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
