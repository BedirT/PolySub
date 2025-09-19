from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.engines.assemblyai_engine import AssemblyAIEngine
from app.engines.base import BaseTranscriptionEngine
from app.engines.faster_whisper_engine import FasterWhisperEngine
from app.engines.openai_engine import OpenAITranscriptionEngine
from app.engines.mlx_whisper_engine import MLXWhisperEngine
from app.engines.speech_recognition_engine import SpeechRecognitionEngine
from app.engines.types import Segment, TranscriptionResult, TranslationResult
from app.engines.whisperx_engine import WhisperXEngine
from app.engines.lightning_mlx_engine import LightningWhisperMLEngine, AVAILABLE_MODELS as MLX_MODELS
from app.models.job import Artifact, Job, JobOptions, JobStatus, TranscriptionEngine, TranslationModel
from app.services.progress import finalize_stage, stage_bounds, update_stage_progress
from app.services.translation import TranslationService
from app.utils.media import extract_audio
from app.utils.subtitles import write_json, write_srt, write_vtt


async def process_job(job: Job) -> None:
    options = job.options
    job_dir = job.source_path.parent

    audio_path = job_dir / "audio.wav"
    update_stage_progress(job, JobStatus.processing, "Extracting audio", local_progress=5.0)
    extract_audio(job.source_path, audio_path)
    job.audio_path = audio_path
    finalize_stage(job, JobStatus.processing, "Audio extracted")

    engine = _select_engine(options)
    update_stage_progress(job, JobStatus.transcribing, f"Transcribing via {options.engine.value}", local_progress=0.0)

    def progress_callback(percent: float, message: str) -> None:
        start, end = stage_bounds(JobStatus.transcribing)
        span = max(end - start, 1.0)
        local = (percent - start) / span * 100.0
        update_stage_progress(job, JobStatus.transcribing, message, local_progress=local)

    transcription = await engine.transcribe(job, audio_path, progress_callback)
    finalize_stage(job, JobStatus.transcribing, "Transcription complete")

    transcript_data = _serialize_transcription(transcription)
    transcript_path = job_dir / "transcript.json"
    write_json(transcript_path, transcript_data)
    job.transcript_json = transcript_path
    job.summary = transcription.text[:400]

    artifacts = [Artifact(kind="transcript-json", path=transcript_path, label="Transcript JSON")]

    translations: dict[str, TranslationResult] = {}

    update_stage_progress(job, JobStatus.exporting, "Exporting captions", local_progress=0.0)
    base_output_dir = job_dir / "outputs"
    base_output_dir.mkdir(exist_ok=True)

    if "srt" in options.output_formats:
        srt_path = base_output_dir / "captions.srt"
        write_srt(srt_path, transcription.segments)
        artifacts.append(Artifact(kind="srt", path=srt_path, label="Primary SRT"))
    if "vtt" in options.output_formats:
        vtt_path = base_output_dir / "captions.vtt"
        write_vtt(vtt_path, transcription.segments)
        artifacts.append(Artifact(kind="vtt", path=vtt_path, label="Primary VTT"))

    source_language = (transcription.language or "source").replace(" ", "_").lower()
    if source_language:
        if "srt" in options.output_formats:
            source_srt = base_output_dir / f"captions.{source_language}.srt"
            write_srt(source_srt, transcription.segments)
            artifacts.append(Artifact(kind="srt", path=source_srt, label=f"{source_language.upper()} SRT"))
        if "vtt" in options.output_formats:
            source_vtt = base_output_dir / f"captions.{source_language}.vtt"
            write_vtt(source_vtt, transcription.segments)
            artifacts.append(Artifact(kind="vtt", path=source_vtt, label=f"{source_language.upper()} VTT"))

    for lang, result in translations.items():
        if "srt" in options.output_formats:
            srt_path = base_output_dir / f"captions.{lang}.srt"
            write_srt(srt_path, result.segments)
            artifacts.append(Artifact(kind="srt", path=srt_path, label=f"{lang.upper()} SRT"))
        if "vtt" in options.output_formats:
            vtt_path = base_output_dir / f"captions.{lang}.vtt"
            write_vtt(vtt_path, result.segments)
            artifacts.append(Artifact(kind="vtt", path=vtt_path, label=f"{lang.upper()} VTT"))

    job.artifacts = artifacts
    finalize_stage(job, JobStatus.exporting, "Artifacts ready")
    finalize_stage(job, JobStatus.completed, "Job complete")


def _select_engine(options: JobOptions) -> BaseTranscriptionEngine:
    model_size = options.local_model_size or settings.default_local_model
    if options.engine == TranscriptionEngine.faster_whisper:
        return FasterWhisperEngine(model_size=model_size, preferred_device=options.preferred_device)
    if options.engine == TranscriptionEngine.whisperx:
        return WhisperXEngine(
            model_size=model_size,
            enable_alignment=options.enable_alignment,
            enable_diarization=options.enable_diarization,
            batch_size=options.batch_size,
        )
    if options.engine == TranscriptionEngine.lightning_mlx:
        if not MLX_MODELS:
            raise RuntimeError(
                "lightning-whisper-mlx not installed. Install optional extra with `pip install polysub-backend[mlx]`."
            )
        chosen_model = model_size if model_size in MLX_MODELS else "small"
        batch_size = options.batch_size or 12
        quant = options.quantization
        lead_in = options.subtitle_lead_in if options.subtitle_lead_in is not None else settings.subtitle_lead_in
        linger = options.subtitle_linger if options.subtitle_linger is not None else settings.subtitle_linger
        min_gap = options.subtitle_min_gap if options.subtitle_min_gap is not None else settings.subtitle_min_gap
        min_duration = (
            options.subtitle_min_duration
            if options.subtitle_min_duration is not None
            else settings.subtitle_min_duration
        )
        max_chars_per_line = (
            options.subtitle_max_chars_per_line
            if options.subtitle_max_chars_per_line is not None
            else settings.subtitle_max_chars_per_line
        )
        max_lines = (
            options.subtitle_max_lines
            if options.subtitle_max_lines is not None
            else settings.subtitle_max_lines
        )
        return LightningWhisperMLEngine(
            model_size=chosen_model,
            batch_size=batch_size,
            quantization=quant,
            lead_in=lead_in,
            linger=linger,
            min_gap=min_gap,
            min_duration=min_duration,
            max_chars_per_line=max_chars_per_line,
            max_lines=max_lines,
        )
    if options.engine == TranscriptionEngine.mlx_whisper:
        repo = options.local_model_size or "mlx-community/whisper-large-v3-turbo"
        batch = options.batch_size or 8
        return MLXWhisperEngine(model_size=repo, batch_size=batch)
    if options.engine == TranscriptionEngine.openai_gpt4o:
        return OpenAITranscriptionEngine("gpt-4o-transcribe", api_key=options.openai_api_key)
    if options.engine == TranscriptionEngine.openai_gpt4omini:
        return OpenAITranscriptionEngine("gpt-4o-mini-transcribe", api_key=options.openai_api_key)
    if options.engine == TranscriptionEngine.assemblyai:
        return AssemblyAIEngine(api_key=options.assemblyai_api_key)
    if options.engine == TranscriptionEngine.speech_recognition:
        return SpeechRecognitionEngine(model=model_size)
    raise ValueError(f"Unsupported engine {options.engine}")


def _serialize_transcription(result: TranscriptionResult) -> dict:
    return {
        "language": result.language,
        "text": result.text,
        "segments": [
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "speaker": segment.speaker,
                "words": segment.words,
            }
            for segment in result.segments
        ],
    }


def _load_transcript_segments(job: Job) -> tuple[str, list[Segment]]:
    if not job.transcript_json:
        raise RuntimeError("Transcript not found for job")
    data = json.loads(job.transcript_json.read_text())
    language = data.get("language", "unknown")
    segments: list[Segment] = []
    for item in data.get("segments", []):
        segments.append(
            Segment(
                start=float(item.get("start", 0.0)),
                end=float(item.get("end", 0.0)),
                text=str(item.get("text", "")),
                speaker=item.get("speaker"),
                words=item.get("words"),
            )
        )
    if not segments:
        raise RuntimeError("Transcript has no segments")
    return language, segments


async def perform_translation(
    job: Job,
    target_languages: list[str],
    translation_model: TranslationModel,
    openai_api_key: str | None,
) -> dict[str, TranslationResult]:
    if translation_model == TranslationModel.none:
        raise RuntimeError("Translation model must be specified")
    if not target_languages:
        raise RuntimeError("At least one target language is required")

    source_language, segments = _load_transcript_segments(job)
    translator = TranslationService(api_key=openai_api_key or job.options.openai_api_key)
    return await translator.translate(
        segments,
        source_language,
        target_languages,
        translation_model,
    )


def write_translation_artifacts(
    job: Job,
    translations: dict[str, TranslationResult],
) -> list[Artifact]:
    if not translations:
        return []
    options = job.options
    base_output_dir = job.source_path.parent / "outputs"
    base_output_dir.mkdir(exist_ok=True)

    new_artifacts: list[Artifact] = []
    for lang, result in translations.items():
        if "srt" in options.output_formats:
            srt_path = base_output_dir / f"captions.{lang}.srt"
            write_srt(srt_path, result.segments)
            new_artifacts.append(Artifact(kind="srt", path=srt_path, label=f"{lang.upper()} SRT"))
        if "vtt" in options.output_formats:
            vtt_path = base_output_dir / f"captions.{lang}.vtt"
            write_vtt(vtt_path, result.segments)
            new_artifacts.append(Artifact(kind="vtt", path=vtt_path, label=f"{lang.upper()} VTT"))
    return new_artifacts


__all__ = [
    "process_job",
    "perform_translation",
    "write_translation_artifacts",
]
