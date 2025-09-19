from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.engines.base import BaseTranscriptionEngine, ProgressFn
from app.engines.types import Segment, TranscriptionResult
from app.models.job import Job

try:  # pragma: no cover
    from lightning_whisper_mlx import LightningWhisperMLX
    from lightning_whisper_mlx.lightning import models as AVAILABLE_MODELS
    from lightning_whisper_mlx.audio import HOP_LENGTH, SAMPLE_RATE
    from lightning_whisper_mlx import transcribe as mlx_transcribe
    import mlx.core as mx
    import numpy as np
except ImportError as err:  # pragma: no cover
    LightningWhisperMLX = None  # type: ignore[assignment]
    AVAILABLE_MODELS = {}
    IMPORT_ERROR = err
    FRAME_TO_SECONDS = 1.0
    mlx_transcribe = None  # type: ignore[assignment]
else:
    IMPORT_ERROR = None
    FRAME_TO_SECONDS = HOP_LENGTH / SAMPLE_RATE


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
    if 'mx' in globals() and mx is not None:
        if hasattr(mx, "gpu") and hasattr(mx, "set_default_device"):
            try:
                if mx.is_available(mx.gpu):  # type: ignore[attr-defined]
                    mx.set_default_device(mx.gpu)
            except Exception:  # pragma: no cover - best effort
                pass

    return LightningWhisperMLX(model=model_size, batch_size=batch_size, quant=quant)


def _transcribe_with_segments(
    model: LightningWhisperMLX,
    audio_path: Path,
    *,
    language: Optional[str] = None,
    lead_in: float,
    linger: float,
    min_gap: float,
    min_duration: float,
    max_chars_per_line: int,
    max_lines: int,
) -> dict[str, Any]:
    if mlx_transcribe is None or mx is None:
        raise IMPORT_ERROR  # type: ignore[misc]

    batch_size = max(1, getattr(model, "batch_size", 12))
    model_root = Path("./mlx_models") / model.name

    decode_options: dict[str, Any] = {"task": "transcribe"}
    if language:
        decode_options["language"] = language
    else:
        decode_options["language"] = None

    temperature: tuple[float, float] = (0.0, 1.0)
    compression_ratio_threshold = 2.4
    logprob_threshold = -1.0
    no_speech_threshold = 0.6
    condition_on_previous_text = True
    initial_prompt: Optional[str] = None
    clip_timestamps = "0"

    dtype = mx.float16
    mlx_model = mlx_transcribe.ModelHolder.get_model(str(model_root), dtype)

    mel = mlx_transcribe.log_mel_spectrogram(
        str(audio_path), n_mels=mlx_model.dims.n_mels, padding=mlx_transcribe.N_SAMPLES
    )
    content_frames = mel.shape[-2] - mlx_transcribe.N_FRAMES

    if decode_options.get("language") is None:
        if not mlx_model.is_multilingual:
            decode_options["language"] = "en"
        else:
            mel_segment = mlx_transcribe.pad_or_trim(
                mel, mlx_transcribe.N_FRAMES, axis=-2
            ).astype(dtype)
            _, probs = mlx_model.detect_language(mel_segment)
            decode_options["language"] = max(probs, key=probs.get)

    language_code = decode_options["language"] or "unknown"
    task = decode_options.get("task", "transcribe")
    tokenizer = mlx_transcribe.get_tokenizer(
        mlx_model.is_multilingual,
        num_languages=mlx_model.num_languages,
        language=language_code,
        task=task,
    )

    if isinstance(clip_timestamps, str):
        clip_values = [
            float(ts) for ts in (clip_timestamps.split(",") if clip_timestamps else [])
        ]
    else:
        clip_values = list(clip_timestamps)

    seek_points = [round(ts * mlx_transcribe.FRAMES_PER_SECOND) for ts in clip_values]
    if not seek_points:
        seek_points.append(0)
    if len(seek_points) % 2 == 1:
        seek_points.append(content_frames)
    seek_clips = list(zip(seek_points[::2], seek_points[1::2]))

    def decode_process(segment_batch: mx.array, temp: float) -> Any:
        kwargs = {
            k: v
            for k, v in decode_options.items()
            if k in {"task", "language", "prompt"}
        }
        options = mlx_transcribe.DecodingOptions(**kwargs, temperature=temp)
        return mlx_model.decode(segment_batch, options)

    def decode_with_fallback(segment_batch: mx.array) -> Any:
        decode_results = decode_process(segment_batch, temperature[0])
        final_decode = []
        for i, decode_result in enumerate(decode_results):
            segment = segment_batch[i : i + 1, :, :]
            needs_fallback = False
            if (
                compression_ratio_threshold is not None
                and decode_result.compression_ratio > compression_ratio_threshold
            ):
                needs_fallback = True
            if (
                logprob_threshold is not None
                and decode_result.avg_logprob < logprob_threshold
            ):
                needs_fallback = True
            if (
                no_speech_threshold is not None
                and decode_result.no_speech_prob > no_speech_threshold
            ):
                needs_fallback = False
            if needs_fallback:
                final_decode.append(decode_process(segment, temperature[1])[0])
            else:
                final_decode.append(decode_result)
        return final_decode

    clip_idx = 0
    seek = seek_clips[clip_idx][0]
    input_stride = mlx_transcribe.N_FRAMES // mlx_model.dims.n_audio_ctx
    time_precision = input_stride * mlx_transcribe.HOP_LENGTH / mlx_transcribe.SAMPLE_RATE
    all_tokens: list[int] = []
    prompt_reset_since = 0

    if initial_prompt is not None:
        initial_prompt_tokens = tokenizer.encode(" " + initial_prompt.strip())
        all_tokens.extend(initial_prompt_tokens)
    else:
        initial_prompt_tokens = []

    collected_segments: list[dict[str, Any]] = []

    def format_caption_text(raw: str) -> str:
        normalized = " ".join(raw.strip().split())
        if not normalized:
            return ""
        if max_chars_per_line <= 0 or max_lines <= 0:
            return normalized

        words = normalized.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip() if current else word
            if current and len(candidate) > max_chars_per_line and len(lines) + 1 < max_lines:
                lines.append(current)
                current = word
            elif not current:
                current = candidate
            elif len(candidate) <= max_chars_per_line or len(lines) + 1 >= max_lines:
                current = candidate
            else:
                lines.append(current)
                current = word

        if current:
            lines.append(current)

        if max_lines > 0:
            while len(lines) > max_lines:
                if len(lines) >= 2:
                    lines[-2] = f"{lines[-2]} {lines[-1]}".strip()
                    lines.pop()
                else:
                    break

        return "\n".join(lines)

    def new_segment(*, start: float, end: float, tokens: mx.array, result: Any) -> dict[str, Any]:
        token_list = tokens.tolist()
        text_tokens = [token for token in token_list if token < tokenizer.eot]
        return {
            "start": start,
            "end": end,
            "text": tokenizer.decode(text_tokens),
            "tokens": token_list,
            "temperature": result.temperature,
            "avg_logprob": result.avg_logprob,
            "compression_ratio": result.compression_ratio,
            "no_speech_prob": result.no_speech_prob,
        }

    def format_output(tokens: np.ndarray, result: Any, time_offset: float, segment_size: int) -> list[dict[str, Any]]:
        current_segments: list[dict[str, Any]] = []

        if no_speech_threshold is not None:
            should_skip = result.no_speech_prob > no_speech_threshold
            if logprob_threshold is not None and result.avg_logprob > logprob_threshold:
                should_skip = False
            if should_skip:
                return current_segments

        timestamp_tokens = tokens >= tokenizer.timestamp_begin
        single_timestamp_ending = timestamp_tokens[-2:].tolist() == [False, True]

        consecutive = np.where(np.logical_and(timestamp_tokens[:-1], timestamp_tokens[1:]))[0]
        consecutive += 1
        if len(consecutive) > 0:
            slices = consecutive.tolist()
            if single_timestamp_ending:
                slices.append(len(tokens))
            last_slice = 0
            for current_slice in slices:
                sliced = tokens[last_slice:current_slice]
                start_pos = sliced[0].item() - tokenizer.timestamp_begin
                end_pos = sliced[-1].item() - tokenizer.timestamp_begin
                current_segments.append(
                    new_segment(
                        start=time_offset + start_pos * time_precision,
                        end=time_offset + end_pos * time_precision,
                        tokens=sliced,
                        result=result,
                    )
                )
                last_slice = current_slice
        else:
            segment_duration = segment_size * mlx_transcribe.HOP_LENGTH / mlx_transcribe.SAMPLE_RATE
            timestamps = tokens[timestamp_tokens.nonzero()[0]]
            if len(timestamps) > 0 and timestamps[-1].item() != tokenizer.timestamp_begin:
                last_ts = timestamps[-1].item() - tokenizer.timestamp_begin
                segment_duration = last_ts * time_precision
            current_segments.append(
                new_segment(
                    start=time_offset,
                    end=time_offset + segment_duration,
                    tokens=tokens,
                    result=result,
                )
            )

        valid_segments: list[dict[str, Any]] = []
        for seg in current_segments:
            text = seg.get("text", "").strip()
            if not text:
                continue
            start_val = max(0.0, float(seg.get("start", 0.0)))
            end_val = max(start_val, float(seg.get("end", start_val)))
            seg["start"] = float(f"{start_val:.3f}")
            seg["end"] = float(f"{end_val:.3f}")
            seg["text"] = text
            valid_segments.append(seg)
        return valid_segments

    seek_clip_end = seek_clips[clip_idx][1]
    seek = -mlx_transcribe.N_FRAMES
    while seek < seek_clip_end:
        time_offset = float(seek * mlx_transcribe.HOP_LENGTH / mlx_transcribe.SAMPLE_RATE)

        mel_segments: list[mx.array] = []
        mel_timestamps: list[tuple[int, int]] = []

        for _ in range(batch_size):
            seek += mlx_transcribe.N_FRAMES
            if seek > seek_clip_end:
                break
            segment_size = min(
                mlx_transcribe.N_FRAMES,
                content_frames - seek,
                seek_clip_end - seek,
            )
            if segment_size <= 0:
                continue

            mel_segment = mel[seek : seek + segment_size]
            mel_segment = mlx_transcribe.pad_or_trim(
                mel_segment, mlx_transcribe.N_FRAMES, axis=-2
            ).astype(dtype)
            mel_segments.append(mel_segment)
            mel_timestamps.append((seek, seek + segment_size))

        if not mel_segments:
            break

        if condition_on_previous_text:
            decode_options["prompt"] = all_tokens[prompt_reset_since:]
        else:
            decode_options["prompt"] = []
        segment_batch = mx.array(mx.stack(mel_segments, axis=0))
        decode_results = decode_with_fallback(segment_batch)

        for idx, res in enumerate(decode_results):
            start_seek, end_seek = mel_timestamps[idx]
            tokens = np.array(res.tokens)
            segs = format_output(
                tokens,
                res,
                time_offset=float(start_seek * mlx_transcribe.HOP_LENGTH / mlx_transcribe.SAMPLE_RATE),
                segment_size=end_seek - start_seek,
            )
            if not segs:
                continue
            collected_segments.extend(segs)
            combined_tokens = [token for seg in segs for token in seg["tokens"]]
            all_tokens.extend(combined_tokens)

            if not condition_on_previous_text or res.temperature > 0.5:
                prompt_reset_since = len(all_tokens)

    transcript_text = tokenizer.decode(all_tokens[len(initial_prompt_tokens) :]).strip()

    cleaned_segments: list[dict[str, Any]] = []
    for idx, seg in enumerate(collected_segments):
        start = max(0.0, float(seg["start"]))
        end = max(start, float(seg["end"]))

        # allow subtitles to appear slightly early for readability
        start = max(0.0, start - lead_in)
        if cleaned_segments:
            prev_end = cleaned_segments[-1]["end"]
            start = max(start, prev_end + min_gap * 0.5)

        next_start = None
        if idx + 1 < len(collected_segments):
            next_start = float(collected_segments[idx + 1]["start"])

        if next_start is not None:
            latest_allowed = max(start, next_start - min_gap)
            desired_end = max(end, start) + linger
            end = min(desired_end, latest_allowed)
            if latest_allowed - start >= min_duration:
                end = max(end, start + min_duration)
            end = max(end, start)
        else:
            end = max(end, start) + linger
            end = max(end, start + min_duration)

        formatted = format_caption_text(seg["text"])
        if not formatted:
            continue

        cleaned_segments.append(
            {
                "start": float(f"{start:.3f}"),
                "end": float(f"{end:.3f}"),
                "text": formatted,
            }
        )

    return {"text": transcript_text, "segments": cleaned_segments, "language": language_code}


class LightningWhisperMLEngine(BaseTranscriptionEngine):
    name = "lightning-whisper-mlx"

    def __init__(
        self,
        model_size: str,
        batch_size: int = 12,
        quantization: Optional[str] = None,
        *,
        lead_in: Optional[float] = None,
        linger: Optional[float] = None,
        min_gap: Optional[float] = None,
        min_duration: Optional[float] = None,
        max_chars_per_line: Optional[int] = None,
        max_lines: Optional[int] = None,
    ) -> None:
        self.model_size = model_size
        self.batch_size = max(1, batch_size)
        self.quantization = quantization
        from app.config import settings

        self.lead_in = max(0.0, float(lead_in if lead_in is not None else settings.subtitle_lead_in))
        self.linger = max(0.0, float(linger if linger is not None else settings.subtitle_linger))
        self.min_gap = max(0.0, float(min_gap if min_gap is not None else settings.subtitle_min_gap))
        self.min_duration = max(
            0.0, float(min_duration if min_duration is not None else settings.subtitle_min_duration)
        )
        default_chars = settings.subtitle_max_chars_per_line
        default_lines = settings.subtitle_max_lines
        self.max_chars_per_line = int(
            max_chars_per_line if max_chars_per_line is not None else default_chars
        )
        self.max_lines = int(max_lines if max_lines is not None else default_lines)
        if self.max_chars_per_line < 0:
            self.max_chars_per_line = 0
        if self.max_lines < 0:
            self.max_lines = 0

    async def transcribe(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_sync, job, audio_path, update)

    def _run_sync(self, job: Job, audio_path: Path, update: ProgressFn) -> TranscriptionResult:
        model = _load_model(self.model_size, self.batch_size, self.quantization)
        update(10.0, f"Loaded {self.model_size} MLX model")

        try:
            raw_result = _transcribe_with_segments(
                model,
                audio_path,
                lead_in=self.lead_in,
                linger=self.linger,
                min_gap=self.min_gap,
                min_duration=self.min_duration,
                max_chars_per_line=self.max_chars_per_line,
                max_lines=self.max_lines,
            )
        except Exception:  # pragma: no cover - fall back to library output
            raw_result = model.transcribe(str(audio_path))

        if isinstance(raw_result, dict):
            segments_source = raw_result.get("segments") or []
            language = raw_result.get("language", "unknown")
            combined_text = raw_result.get("text", "")
        elif isinstance(raw_result, list):
            segments_source = raw_result
            language = "unknown"
            combined_text = ""
        else:  # pragma: no cover - unexpected response type
            raise RuntimeError(f"Unexpected MLX lightning output: {type(raw_result)!r}")

        frame_to_seconds = FRAME_TO_SECONDS or 1.0
        segments: list[Segment] = []
        texts: list[str] = []
        for idx, seg in enumerate(segments_source, start=1):
            text: str
            words: Optional[list] = None

            if isinstance(seg, dict):
                text = str(seg.get("text", "")).strip()
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", start))
                words = seg.get("words")
            elif isinstance(seg, (list, tuple)):
                text = str(seg[2] if len(seg) > 2 else "").strip()
                try:
                    start = float(seg[0] if len(seg) > 0 else 0.0) * frame_to_seconds
                    end = float(seg[1] if len(seg) > 1 else 0.0) * frame_to_seconds
                except (TypeError, ValueError):
                    start = 0.0
                    end = 0.0
            else:
                text = str(getattr(seg, "text", "")).strip()
                start = float(getattr(seg, "start", 0.0))
                end = float(getattr(seg, "end", start))
                words = getattr(seg, "words", None)

            if end < start:
                end = start

            start = float(f"{start:.3f}")
            end = float(f"{end:.3f}")

            segments.append(Segment(start=start, end=end, text=text, words=words))
            if text:
                texts.append(text)
            progress = 10.0 + min(idx * 0.5, 85.0)
            update(progress, f"Decoding segment {idx}")

        transcript_text = " ".join(texts).strip()
        if not transcript_text and combined_text:
            transcript_text = str(combined_text).strip()

        return TranscriptionResult(language=language, segments=segments, text=transcript_text)


__all__ = ["LightningWhisperMLEngine", "AVAILABLE_MODELS"]
