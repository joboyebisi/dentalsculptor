"""Validated TRELLIS.2 deployment and inference configuration."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any


def _env_int(name: str, default: int, *, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}.") from exc
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")
    return value


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


DEPLOYMENT_ENV = os.getenv("TRELLIS_DEPLOYMENT_ENV", "development").strip().lower()
IS_PRODUCTION = DEPLOYMENT_ENV == "production"
# Research pilot: keep one warm GPU even when DEPLOYMENT_ENV=development.
RESEARCH_WARM_POOL = _env_bool("TRELLIS_RESEARCH_WARM_POOL", False)

# Modal capacity is resolved when the app is deployed. Development scales to zero
# unless TRELLIS_RESEARCH_WARM_POOL or TRELLIS_DEPLOYMENT_ENV=production.
GPU_TYPE = os.getenv("TRELLIS_MODAL_GPU", "A100")
MIN_CONTAINERS = _env_int(
    "TRELLIS_MIN_CONTAINERS",
    1 if (IS_PRODUCTION or RESEARCH_WARM_POOL) else 0,
)
BUFFER_CONTAINERS = _env_int("TRELLIS_BUFFER_CONTAINERS", 0)
SCALEDOWN_WINDOW = _env_int(
    "TRELLIS_SCALEDOWN_WINDOW",
    3600 if RESEARCH_WARM_POOL else 1200,
    minimum=60,
)
MAX_CONTAINERS = _env_int("TRELLIS_MAX_CONTAINERS", 1, minimum=1)
if MIN_CONTAINERS > MAX_CONTAINERS:
    raise ValueError("TRELLIS_MIN_CONTAINERS cannot exceed TRELLIS_MAX_CONTAINERS.")

ENABLE_TF32 = _env_bool("TRELLIS_ENABLE_TF32", True)
# Warm CUDA kernels on every new container (scale-to-zero or warm pool).
ENABLE_WARMUP = _env_bool("TRELLIS_ENABLE_WARMUP", True)
HF_HUB_OFFLINE = _env_bool("TRELLIS_HF_HUB_OFFLINE", False)
ASYNC_S3_ENABLED = _env_bool("TRELLIS_ASYNC_S3_ENABLED", True)
BASE64_COMPAT_ENABLED = _env_bool("TRELLIS_BASE64_COMPAT_ENABLED", True)

HF_CACHE_PATH = "/cache/huggingface"
TRELLIS2_PATH = "/opt/TRELLIS.2"
BASE_MODEL_NAME = "microsoft/TRELLIS.2-4B"
BASE_MODEL_REVISION = "af44b45f2e35a493886929c6d786e563ec68364d"
# A candidate is deployed alongside the base model and promoted only by changing
# these two environment values. Rolling back never mutates or deletes weights.
MODEL_NAME = os.getenv("TRELLIS_MODEL_NAME", BASE_MODEL_NAME).strip()
MODEL_REVISION = os.getenv("TRELLIS_MODEL_REVISION", BASE_MODEL_REVISION).strip()
TRELLIS_COMMIT = "1762f493fe7731a3b7cc6b79ad5da7b015b516c1"

HF_REPOSITORIES = {
    MODEL_NAME: MODEL_REVISION,
    "facebook/dinov3-vitl16-pretrain-lvd1689m": "ea8dc2863c51be0a264bab82070e3e8836b02d51",
    "briaai/RMBG-2.0": "5df4c9c76d8170882c34f6986e848ee07fd0ba43",
}

MAX_INPUT_BYTES = _env_int("TRELLIS_MAX_INPUT_BYTES", 15 * 1024 * 1024, minimum=1)
MAX_INPUT_PIXELS = _env_int("TRELLIS_MAX_INPUT_PIXELS", 25_000_000, minimum=4096)
ALLOWED_IMAGE_MIME_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)

# Match the higher-quality TRELLIS.2 Space preset used for dental evaluation.
DEFAULT_PIPELINE_TYPE = "1024_cascade"
DEFAULT_SEED = 0
# Dental reconstruction is repeatable by default. The web application derives a
# stable seed from the prepared image; direct callers without a seed fall back
# to DEFAULT_SEED. Variants must opt in by supplying another seed explicitly.
DEFAULT_RANDOMIZE_SEED = False

# Preserve anatomy for editing; simulator export performs target-specific reduction.
DEFAULT_DECIMATION_TARGET = 300_000
DEFAULT_TEXTURE_SIZE = 2048

# Official Space advanced defaults.
SS_SAMPLER_PARAMS = {
    "steps": 12,
    "guidance_strength": 7.5,
    "guidance_rescale": 0.7,
    "rescale_t": 5.0,
}
SHAPE_SAMPLER_PARAMS = {
    "steps": 12,
    "guidance_strength": 7.5,
    "guidance_rescale": 0.5,
    "rescale_t": 3.0,
}
TEXTURE_SAMPLER_PARAMS = {
    "steps": 12,
    "guidance_strength": 1.0,
    "guidance_rescale": 0.0,
    "rescale_t": 3.0,
}

QUALITY_PRESETS: dict[str, dict[str, int | str]] = {
    "preview": {
        "pipeline_type": "512",
        "steps": 8,
        "decimation_target": 100_000,
        "texture_size": 1024,
    },
    "standard": {
        "pipeline_type": "1024_cascade",
        "steps": 12,
        "decimation_target": 300_000,
        "texture_size": 2048,
    },
    "final": {
        "pipeline_type": "1024_cascade",
        "steps": 12,
        "decimation_target": 1_000_000,
        "texture_size": 4096,
    },
}
DEFAULT_QUALITY = os.getenv("TRELLIS_DEFAULT_QUALITY", "standard").strip().lower()
if DEFAULT_QUALITY not in QUALITY_PRESETS:
    raise ValueError(
        f"TRELLIS_DEFAULT_QUALITY must be one of {sorted(QUALITY_PRESETS)}."
    )


def _bool_env(value: bool) -> str:
    return "true" if value else "false"


def modal_runtime_env() -> dict[str, str]:
    """Env vars baked into Modal images at deploy time (local shell env is not inherited)."""
    return {
        "TRELLIS_ASYNC_S3_ENABLED": _bool_env(ASYNC_S3_ENABLED),
        "TRELLIS_ENABLE_WARMUP": _bool_env(ENABLE_WARMUP),
        "TRELLIS_ENABLE_TF32": _bool_env(ENABLE_TF32),
        "TRELLIS_HF_HUB_OFFLINE": _bool_env(HF_HUB_OFFLINE),
        "TRELLIS_BASE64_COMPAT_ENABLED": _bool_env(BASE64_COMPAT_ENABLED),
        "TRELLIS_DEPLOYMENT_ENV": DEPLOYMENT_ENV,
        "TRELLIS_MODAL_GPU": GPU_TYPE,
        "TRELLIS_MODEL_NAME": MODEL_NAME,
        "TRELLIS_MODEL_REVISION": MODEL_REVISION,
    }


def get_quality_preset(quality: str | None) -> dict[str, int | str]:
    """Return a defensive copy of a server-controlled quality preset."""
    resolved = (quality or DEFAULT_QUALITY).strip().lower()
    try:
        return deepcopy(QUALITY_PRESETS[resolved])
    except KeyError as exc:
        raise ValueError(
            f"Unsupported quality {quality!r}; expected one of {sorted(QUALITY_PRESETS)}."
        ) from exc


def sampler_params_for_steps(steps: int) -> dict[str, dict[str, Any]]:
    """Apply a preset's step count without exposing arbitrary sampler controls."""
    params = {
        "sparse_structure": deepcopy(SS_SAMPLER_PARAMS),
        "shape": deepcopy(SHAPE_SAMPLER_PARAMS),
        "texture": deepcopy(TEXTURE_SAMPLER_PARAMS),
    }
    for stage in params.values():
        stage["steps"] = steps
    return params
