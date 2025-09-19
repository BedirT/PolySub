from __future__ import annotations

import importlib.util
import os
import platform
from typing import Dict

from app.config import settings

try:  # pragma: no cover
    import torch
except Exception:  # pylint: disable=broad-except
    torch = None  # type: ignore[assignment]



def _torch_cuda_available() -> bool:
    if torch is None:
        return False
    try:
        return torch.cuda.is_available()
    except Exception:  # pragma: no cover
        return False


def _torch_mps_available() -> bool:
    if torch is None:
        return False
    try:
        mps = getattr(torch.backends, "mps", None)
        return bool(mps and mps.is_available())
    except Exception:  # pragma: no cover
        return False


def _has_lightning_mlx() -> bool:
    return importlib.util.find_spec("lightning_whisper_mlx") is not None


def detect_system_specs() -> Dict:
    os_name = platform.system()
    arch = platform.machine()
    cpu_count = os.cpu_count()

    has_cuda = _torch_cuda_available()
    has_mps = _torch_mps_available()
    has_mlx = _has_lightning_mlx()

    def device_option(device_id: str, label: str, available: bool) -> Dict[str, object]:
        return {"id": device_id, "label": label, "available": available}

    engines: Dict[str, Dict[str, object]] = {}

    engines["faster-whisper"] = {
        "device_options": [
            device_option("auto", "Auto", True),
            device_option("cpu", "CPU only", True),
            device_option("gpu", "GPU (CUDA/MPS)", has_cuda or has_mps),
        ],
        "model_options": {
            "default": "large-v3" if (has_cuda or has_mps) else "small",
            "choices": [
                "tiny",
                "base",
                "small",
                "medium",
                "large-v3",
                "distil-large-v2",
            ],
        },
        "batch_sizes": [],
    }

    engines["whisperx"] = {
        "device_options": [
            device_option("auto", "Auto", True),
            device_option("cpu", "CPU only", True),
            device_option("gpu", "GPU (CUDA/MPS)", has_cuda or has_mps),
        ],
        "model_options": {
            "default": "large-v2",
            "choices": [
                "base",
                "small",
                "medium",
                "large-v2",
                "large-v3",
            ],
        },
        "batch_sizes": [1, 2, 4],
    }

    if has_mlx:
        try:
            from lightning_whisper_mlx.lightning import models as mlx_models
            mlx_model_choices = list(mlx_models.keys())
        except Exception:  # pragma: no cover
            mlx_model_choices = [
                "tiny",
                "small",
                "base",
                "medium",
                "large",
                "large-v2",
                "large-v3",
            ]
    else:
        mlx_model_choices = []

    preferred_mlx_default = None
    if mlx_model_choices:
        if "small" in mlx_model_choices:
            preferred_mlx_default = "small"
        elif "base" in mlx_model_choices:
            preferred_mlx_default = "base"
        else:
            preferred_mlx_default = mlx_model_choices[0]

    engines["lightning-whisper-mlx"] = {
        "device_options": [
            device_option("mlx", "Apple MLX GPU", has_mlx),
        ],
        "model_options": {
            "default": preferred_mlx_default,
            "choices": mlx_model_choices,
        },
        "batch_sizes": [4, 8, 12, 16],
        "quantizations": [
            {"id": "base", "label": "Full precision"},
            {"id": "4bit", "label": "4-bit"},
            {"id": "8bit", "label": "8-bit"},
        ],
        "available": has_mlx,
    }

    engines["openai"] = {
        "device_options": [device_option("cloud", "Cloud", True)],
        "model_options": {
            "default": "gpt-4o-transcribe",
            "choices": ["gpt-4o-transcribe", "gpt-4o-mini-transcribe"],
        },
        "batch_sizes": [],
    }
    engines["assemblyai"] = {
        "device_options": [device_option("cloud", "Cloud", True)],
        "model_options": {"default": None, "choices": []},
        "batch_sizes": [],
    }

    return {
        "os": os_name,
        "arch": arch,
        "cpu_count": cpu_count,
        "capabilities": {
            "cuda": has_cuda,
            "mps": has_mps,
            "mlx": has_mlx,
        },
        "engines": engines,
        "subtitle_defaults": {
            "lead_in": settings.subtitle_lead_in,
            "linger": settings.subtitle_linger,
            "min_gap": settings.subtitle_min_gap,
            "min_duration": settings.subtitle_min_duration,
            "max_chars_per_line": settings.subtitle_max_chars_per_line,
            "max_lines": settings.subtitle_max_lines,
        },
    }
