# PolySub

Local-first subtitle studio combining modern open-source speech models with optional cloud APIs.

## Structure

- `backend/`: FastAPI service handling media ingestion, transcription engines, translation, and artifact export.
- `frontend/`: Next.js dashboard with live progress, engine selection, and artifact downloads.
- `images/`: design assets.

## Quick Start

```bash
make setup        # installs backend virtualenv + frontend deps
make backend      # runs uvicorn with autoreload
make frontend     # starts Next.js dev server
```

Prefer scripts? `./setup.sh` performs the same dependency bootstrap as `make setup`.

Once both servers are running, open <http://localhost:3000> to access the dashboard (it proxies to the backend at `http://localhost:8000`).

Ensure `ffmpeg` is installed locally for audio extraction (for example, `brew install ffmpeg` on macOS or `sudo apt install ffmpeg` on Debian/Ubuntu). If `ffmpeg` lives in a non-standard location, set `FFMPEG_PATH=/full/path/to/ffmpeg` before starting the backend. GPU acceleration for Faster Whisper/WhisperX remains optional but recommended when available.
Running `make setup`/`./setup.sh` attempts to install `ffmpeg` automatically when Homebrew or `apt-get` is available. If that step fails, install `ffmpeg` manually (for example `brew install ffmpeg --build-from-source`) or set `FFMPEG_PATH` to the binary before rerunning the backend.

### Hardware-aware presets

The dashboard calls `/api/system/specs` on load to detect CPU/GPU capabilities (CUDA, MPS, MLX). Engine pickers light up when acceleration is available and auto-fill sensible defaults for model size, device target, batch size, and (for MLX) quantization. You can still override any of the guided options.

To enable the Lightning Whisper MLX engine on Apple Silicon:

```bash
cd backend
pip install -e .[mlx]
```

## Project Commands

Common targets (run with `make <target>`):

| target       | description                                            |
|--------------|--------------------------------------------------------|
| `setup`      | install Python + Node dependencies                     |
| `backend`    | launch FastAPI server via uvicorn (auto reload)        |
| `frontend`   | launch Next.js dev server                              |
| `docker-up`  | build & start docker-compose stack                     |
| `docker-down`| stop compose stack                                     |


## Docker Compose

For an isolated environment:

```bash
docker compose up --build
```

Export `OPENAI_API_KEY` / `ASSEMBLYAI_API_KEY` beforehand to pass them into the backend container. Captions and transcripts persist under `./storage` on the host. Tear down with `docker compose down`.

## Features

- **Local models**: Faster Whisper, WhisperX, and Lightning Whisper (MLX) with guided hardware-aware presets.
- **Cloud options**: OpenAI `gpt-4o-transcribe` / `gpt-4o-mini-transcribe`, AssemblyAI (leveraging their free credits), and legacy SpeechRecognition pipeline.
- **Translations**: OpenAI `gpt-5-nano` by default with `gpt-5-mini` fallback for batch subtitle translation; toggle per target language.
- **Artifacts**: Generates SRT and VTT tracks per language plus raw transcript JSON. Files stay on disk under `storage/<job-id>/`.
- **UX**: Animated dashboard built with TailwindCSS + Framer Motion, progress indicators for each pipeline stage, quick artifact downloads, and job cancellation.

## Configuration & API keys

The backend reads API credentials from `backend/.env`:

```
OPENAI_API_KEY=
ASSEMBLYAI_API_KEY=
STORAGE_ROOT=../storage
```

When these values are absent you can still provide keys per job directly in the UI. Toggle **API keys** inside the job creator panel, paste the desired key(s), and they will be stored only in your browser's local storage before being sent with the job request. This enables entirely key-less `.env` files for local-only pipelines while still allowing cloud runs on demand.

## Roadmap

- Timeline editor for manual subtitle adjustments.
- Inline media player preview with subtitle switching.
- Optional Electron shell for a packaged desktop experience.
- Hardware-aware benchmarking to suggest optimal local model sizes.
