# PolySub Backend

FastAPI service that orchestrates local and cloud transcription/translation pipelines.

## Features

- Local engines: faster-whisper, WhisperX (alignment + diarization), SpeechRecognition wrappers.
- Cloud engines: OpenAI gpt-4o-transcribe / gpt-4o-mini-transcribe, AssemblyAI.
- Translation via OpenAI gpt-5-nano with optional gpt-5-mini.
- Job orchestration with progress updates and artifact management on local disk.

## Development

```bash
# create virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

Configure environment variables in `.env`:

```
OPENAI_API_KEY=...
ASSEMBLYAI_API_KEY=...
STORAGE_ROOT=../storage
FFMPEG_PATH=
```

Providing keys is optional—users can supply them from the dashboard on a per-job basis if they prefer not to store secrets in this file.

### Optional MLX acceleration

To enable the Lightning Whisper MLX engine on Apple Silicon, install the optional extras:

```bash
pip install -e .[mlx]
```

The dashboard will detect MLX support automatically and expose the hardware-specific engine with batch/quantization controls.

Set `FFMPEG_PATH` if the `ffmpeg` binary isn't on `PATH`.

Artifacts stored under `../storage` relative to repo root.
