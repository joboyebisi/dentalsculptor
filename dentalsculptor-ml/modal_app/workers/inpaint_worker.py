"""
Self-hosted SDXL inpainting on Modal GPU — replaces fal.ai for 2D edit preview.

Model: diffusers/stable-diffusion-xl-1.0-inpainting-0.1 (HF, open license).
VRAM: ~8–12 GB — runs on L4 / T4 / L40S.

Enable: deploy with TRELLIS GPU image or set INPAINT_GPU=1 on Modal.
"""

from __future__ import annotations

import io
import os
from typing import Any

MASK_THRESHOLD = 128


def inpaint_gpu_enabled() -> bool:
    return os.environ.get("INPAINT_GPU", "").strip() in ("1", "true", "yes")


def _build_prompt(instruction: str, operation: str) -> str:
    base = "clinical dental tooth photograph, realistic enamel and dentin texture"
    if operation == "remove":
        return f"{base}, {instruction}, remove tissue in masked area, preserve anatomy outside mask"
    if operation == "add":
        return f"{base}, {instruction}, add detail only within masked region"
    return f"{base}, {instruction}, replace masked region with anatomically correct tooth structure"


def run_sdxl_inpaint(
    reference_bytes: bytes,
    mask_bytes: bytes,
    instruction: str,
    operation: str = "replace",
    num_inference_steps: int = 28,
    guidance_scale: float = 7.5,
) -> dict[str, Any]:
    """Run SDXL inpainting — requires CUDA."""
    import torch
    from diffusers import AutoPipelineForInpainting
    from PIL import Image

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    pipe = AutoPipelineForInpainting.from_pretrained(
        "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        torch_dtype=dtype,
        variant="fp16" if dtype == torch.float16 else None,
    )
    pipe = pipe.to(device)
    pipe.enable_attention_slicing()

    ref = Image.open(io.BytesIO(reference_bytes)).convert("RGB")
    mask = Image.open(io.BytesIO(mask_bytes)).convert("L")
    if mask.size != ref.size:
        mask = mask.resize(ref.size, Image.Resampling.NEAREST)

    prompt = _build_prompt(instruction, operation)
    result = pipe(
        prompt=prompt,
        image=ref,
        mask_image=mask,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        strength=0.99,
    ).images[0]

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return {
        "pngBytes": buf.getvalue(),
        "provider": "modal-sdxl-inpaint",
        "prompt": prompt,
    }
