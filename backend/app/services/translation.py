from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from pydantic import BaseModel, ConfigDict, Field, create_model

from app.config import settings
from app.engines.types import Segment, TranslationResult
from app.models.job import TranslationModel

try:  # pragma: no cover
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


MAX_SEGMENTS_PER_REQUEST = 500


class _SubtitleModelBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

@dataclass
class SubtitleChunk:
    language: str
    chunk_index: int
    items: Sequence[tuple[int, Segment]]


class TranslationService:
    def __init__(self, api_key: str | None = None) -> None:
        if OpenAI is None:  # pragma: no cover
            raise RuntimeError("openai package not installed")
        key = api_key or settings.openai_api_key
        if not key:
            raise RuntimeError("OpenAI API key required for translation")
        self.client = OpenAI(api_key=key)

    async def translate(
        self,
        segments: Iterable[Segment],
        source_language: str,
        target_languages: List[str],
        model: TranslationModel,
    ) -> dict[str, TranslationResult]:
        segments_list = list(segments)
        if not target_languages or not segments_list:
            return {}

        loop = asyncio.get_running_loop()
        tasks: List[asyncio.Future] = []
        for language in target_languages:
            for chunk_index, chunk in enumerate(_chunk_with_index(segments_list, MAX_SEGMENTS_PER_REQUEST)):
                subtitle_chunk = SubtitleChunk(language=language, chunk_index=chunk_index, items=chunk)
                tasks.append(
                    asyncio.to_thread(
                        self._translate_chunk,
                        subtitle_chunk,
                        source_language,
                        model.value,
                    )
                )

        chunk_results = await asyncio.gather(*tasks)

        aggregated: Dict[str, Dict[int, str]] = {lang: {} for lang in target_languages}
        for language, chunk_index, entries in chunk_results:
            language_store = aggregated.setdefault(language, {})
            for global_index, translated_text in entries:
                language_store[global_index] = translated_text

        outputs: dict[str, TranslationResult] = {}
        for language, translations in aggregated.items():
            ordered_texts: List[str] = []
            translated_segments: List[Segment] = []
            for idx, segment in enumerate(segments_list):
                if idx not in translations:
                    raise RuntimeError(
                        f"Translation for language '{language}' missing segment index {idx}"
                    )
                text = translations[idx]
                ordered_texts.append(text)
                translated_segments.append(
                    Segment(start=segment.start, end=segment.end, text=text)
                )
            outputs[language] = TranslationResult(
                language=language,
                segments=translated_segments,
                text=" ".join(ordered_texts),
            )

        return outputs

    def _translate_chunk(
        self,
        chunk: SubtitleChunk,
        source_language: str,
        model: str,
    ) -> tuple[str, int, List[tuple[int, str]]]:
        payload_segments: List[dict] = []
        timestamp_lookup: Dict[str, int] = {}
        for global_index, segment in chunk.items:
            timestamp = _format_timestamp(segment.start, segment.end)
            payload_segments.append(
                {
                    "timestamp": timestamp,
                    "text": segment.text,
                }
            )
            timestamp_lookup[timestamp] = global_index

        instructions = (
            "You are a professional subtitle translator. Translate the subtitle text from "
            f"{source_language} into {chunk.language}. Maintain the meaning, tone, and any inline markup. "
            "Never add or remove entries. Return each translation in the same order using the exact timestamp keys provided."
        )

        request_payload = {
            "source_language": source_language,
            "target_language": chunk.language,
            "segments": payload_segments,
        }

        timestamps = [segment["timestamp"] for segment in payload_segments]
        SubtitleTranslations = _build_subtitle_model(timestamps)

        response = self.client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": instructions},
                {
                    "role": "user",
                    "content": json.dumps(request_payload, ensure_ascii=False),
                },
            ],
            reasoning={"effort": "minimal"},
            text={"verbosity": "low"},
            text_format=SubtitleTranslations,
        )

        parsed: SubtitleTranslations = response.output_parsed

        translated_entries: List[tuple[int, str]] = []
        for timestamp, translated_text in parsed.translations.items():
            if timestamp not in timestamp_lookup:
                raise RuntimeError(
                    f"Model returned unexpected timestamp key '{timestamp}' for language {chunk.language}"
                )
            translated_entries.append((timestamp_lookup[timestamp], translated_text.strip()))

        translated_entries.sort(key=lambda item: item[0])
        return chunk.language, chunk.chunk_index, translated_entries


def _chunk_with_index(segments: Sequence[Segment], size: int) -> Iterable[Sequence[tuple[int, Segment]]]:
    chunk: List[tuple[int, Segment]] = []
    for idx, segment in enumerate(segments):
        chunk.append((idx, segment))
        if len(chunk) == size:
            yield tuple(chunk)
            chunk = []
    if chunk:
        yield tuple(chunk)


def _format_timestamp(start_seconds: float, end_seconds: float) -> str:
    return f"{_format_single_timestamp(start_seconds)} --> {_format_single_timestamp(end_seconds)}"


def _format_single_timestamp(seconds: float) -> str:
    total_millis = int(round(seconds * 1000))
    hours, remainder = divmod(total_millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def _timestamp_to_field_name(timestamp: str) -> str:
    sanitized = re.sub(r"[^0-9a-zA-Z]+", "_", timestamp).strip("_")
    return f"ts_{sanitized.lower()}"


def _build_subtitle_model(timestamps: Sequence[str]) -> type[BaseModel]:
    fields: Dict[str, tuple[type, Field]] = {}
    mapping: Dict[str, str] = {}
    for ts in timestamps:
        base_name = _timestamp_to_field_name(ts)
        candidate = base_name
        suffix = 1
        while candidate in fields:
            suffix += 1
            candidate = f"{base_name}_{suffix}"
        mapping[candidate] = ts
        fields[candidate] = (str, Field(..., alias=ts, description="Translated subtitle text"))

    model = create_model(
        "SubtitleTranslations",
        __base__=_SubtitleModelBase,
        **fields,
    )

    def _translations(self) -> Dict[str, str]:
        return {alias: getattr(self, field) for field, alias in mapping.items()}

    setattr(model, "translations", property(_translations))
    return model
