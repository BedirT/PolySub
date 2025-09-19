#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

info() {
  printf "\033[1;34m[polysetup]\033[0m %s\n" "$1"
}

warn() {
  printf "\033[1;33m[polysetup]\033[0m %s\n" "$1"
}

error_exit() {
  printf "\033[1;31m[polysetup]\033[0m %s\n" "$1" >&2
  exit 1
}

PYTHON_BIN=${PYTHON_BIN:-python3}
NODE_BIN=${NODE_BIN:-node}
NPM_BIN=${NPM_BIN:-npm}
UNAME=$(uname -s)
ARCH=$(uname -m)

info "Checking runtime versions"
$PYTHON_BIN --version >/dev/null 2>&1 || error_exit "Python 3.10+ required"
$NODE_BIN --version >/dev/null 2>&1 || error_exit "Node.js 18+ required"

ensure_ffmpeg() {
  if [ -n "${FFMPEG_PATH:-}" ] && [ -x "$FFMPEG_PATH" ]; then
    info "Using ffmpeg from FFMPEG_PATH=$FFMPEG_PATH"
    return
  fi
  if command -v ffmpeg >/dev/null 2>&1; then
    return
  fi

  info "ffmpeg not detected, attempting installation"
  if [ "$UNAME" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    if brew install ffmpeg; then
      info "ffmpeg installed via Homebrew"
    elif brew install ffmpeg --build-from-source; then
      info "ffmpeg built from source via Homebrew"
    else
      warn "Homebrew installation failed. Install ffmpeg manually (e.g. 'brew install ffmpeg --build-from-source') or set FFMPEG_PATH."
    fi
  elif command -v apt-get >/dev/null 2>&1; then
    if sudo apt-get update && sudo apt-get install -y ffmpeg; then
      info "ffmpeg installed via apt-get"
    else
      warn "apt-get installation failed. Install ffmpeg manually and re-run setup or set FFMPEG_PATH."
    fi
  else
    warn "Automatic ffmpeg install unsupported on this platform. Install ffmpeg manually or set FFMPEG_PATH before running the backend."
  fi

  if ! command -v ffmpeg >/dev/null 2>&1 && [ -z "${FFMPEG_PATH:-}" ]; then
    warn "ffmpeg still not detected. Continue setup, but backend jobs will fail without it."
  fi
}

ensure_ffmpeg

info "Creating Python virtual environment"
if [ ! -d "$BACKEND_DIR/.venv" ]; then
  $PYTHON_BIN -m venv "$BACKEND_DIR/.venv"
fi

source "$BACKEND_DIR/.venv/bin/activate"

info "Installing backend dependencies"
pip install --upgrade pip
install_backend() {
  local target="$BACKEND_DIR"
  if [ "$UNAME" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
    info "Detected Apple Silicon; installing backend with MLX extras"
    target="${BACKEND_DIR}[mlx]"
  fi
  if ! pip install -e "$target"; then
    warn "Backend install failed for $target. Retrying without optional extras."
    pip install -e "$BACKEND_DIR" || error_exit "Failed to install backend dependencies"
  fi
}

install_backend

deactivate

info "Installing frontend dependencies"
cd "$FRONTEND_DIR"
$NPM_BIN install
cd "$SCRIPT_DIR"

info "Setup complete!"
printf "Next steps:\n"
printf "  1. (optional) populate backend/.env with API keys.\n"
printf "  2. Start backend: source backend/.venv/bin/activate && uvicorn app.main:app --reload\n"
printf "  3. Start frontend: cd frontend && npm run dev\n"
