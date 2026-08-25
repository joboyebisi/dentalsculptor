"""
Nano3D Case 3 GPU path — scaffold for full TRELLIS FlowEdit inference.

Enable with Modal secret or env: NANO3D_GPU=1

When weights + CUDA image are ready, implement:
1. Encode source GLB → sparse structure + SLat (TRELLIS encoder)
2. Render reference views
3. Apply edited 2D reference (from Qwen-Image or user PNG)
4. FlowEdit merge in latent space
5. Decode → GLB

Until then this module raises a clear error so deploys fail fast instead of
silently falling back to CPU deform.
"""

from __future__ import annotations

import os
from typing import Any


def nano3d_gpu_enabled() -> bool:
    return os.environ.get("NANO3D_GPU", "").strip() in ("1", "true", "yes")


def run_nano3d_case3_gpu(
    source_model_url: str,
    operation: str,
    instruction: str,
    mask_bytes: bytes | None = None,
    reference_bytes: bytes | None = None,
    camera_json: str | None = None,
    region_marks_json: str | None = None,
) -> dict[str, Any]:
    """
    Full Nano3D Case 3 on GPU. Not yet implemented — see docs/NANO3D_IMPLEMENTATION.md.
    """
    raise NotImplementedError(
        "Nano3D GPU Case 3 is not implemented yet. "
        "Unset NANO3D_GPU or deploy CPU v1 (default). "
        "Track progress in docs/SPRINT_ROADMAP.md §3.4."
    )
