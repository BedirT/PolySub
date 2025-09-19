from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Segment:
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    words: Optional[list[dict]] = None


@dataclass
class TranscriptionResult:
    language: str
    segments: List[Segment] = field(default_factory=list)
    text: str = ""


@dataclass
class TranslationResult:
    language: str
    segments: List[Segment]
    text: str
