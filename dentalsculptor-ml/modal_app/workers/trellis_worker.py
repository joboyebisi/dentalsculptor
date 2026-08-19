"""TRELLIS.2 generation worker — GPU path when weights exist, else CPU placeholder."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from modal_app.workers.mesh_utils import generate_response_from_image


def trellis_weights_ready(weights_dir: str = "/weights") -> bool:
    """True when HF/TRELLIS weights are present on the Modal volume."""
    hf = Path(weights_dir) / "huggingface"
    if not hf.exists():
        return False
    # Any checkpoint file indicates a successful pre-download spike.
    for pattern in ("**/*.safetensors", "**/*.ckpt", "**/*.bin"):
        if any(hf.glob(pattern)):
            return True
    return False


def generate_mesh_trellis(image_bytes: bytes, weights_dir: str = "/weights") -> dict[str, Any]:
    """
    Try TRELLIS.2 inference when weights are mounted; otherwise CPU silhouette placeholder.
    Full TRELLIS integration: see modal_app/images/trellis.py and docs/MODAL_SETUP_GUIDE.md.
    """
    if os.environ.get("TRELLIS_FORCE_CPU", "").lower() in ("1", "true", "yes"):
        return generate_response_from_image(image_bytes)

    if not trellis_weights_ready(weights_dir):
        result = generate_response_from_image(image_bytes)
        result["message"] = (
            "TRELLIS weights not on volume — CPU silhouette placeholder. "
            "Pre-download weights to trellis-weights-v1 (see MODAL_SETUP_GUIDE.md)."
        )
        return result

    # GPU spike hook — replace body after TRELLIS.2 build validates on A100/H100.
    try:
        # from trellis import infer  # future
        raise NotImplementedError("TRELLIS.2 infer not wired yet")
    except Exception as exc:
        result = generate_response_from_image(image_bytes)
        result["message"] = f"TRELLIS GPU path pending ({exc}) — CPU placeholder returned."
        result["source"] = "modal-trellis-fallback-v0"
        return result
