"""
Nano3D edit worker — Case 3 path (v1).

Pipeline stages:
1. Load source GLB + optional reference PNG + mask PNG + camera JSON.
2. Apply masked 2D reference edit (stub inpaint until Qwen-Image worker ships).
3. Deform mesh vertices in masked screen regions (stand-in until full TRELLIS FlowEdit).
4. Export edited GLB.

Full Nano3D Case 3 replaces steps 2–3 with latent FlowEdit on Modal GPU.
"""

from __future__ import annotations

import io
import json
import urllib.request
from typing import Any

from modal_app.workers.nano3d_gpu import nano3d_gpu_enabled, run_nano3d_case3_gpu

import numpy as np

MASK_THRESHOLD = 128
VERTEX_DISPLACE = {
    "remove": -0.04,
    "add": 0.05,
    "replace": 0.03,
}


def _load_mesh_from_url(url: str):
    import trimesh

    with urllib.request.urlopen(url, timeout=120) as resp:
        data = resp.read()
    return trimesh.load(io.BytesIO(data), file_type="glb", force="mesh")


def _load_image_bytes(data: bytes):
    from PIL import Image

    return Image.open(io.BytesIO(data)).convert("RGBA")


def _mask_array(mask_bytes: bytes | None, width: int, height: int) -> np.ndarray | None:
    if not mask_bytes:
        return None
    from PIL import Image

    mask = Image.open(io.BytesIO(mask_bytes)).convert("L")
    mask = mask.resize((width, height), Image.Resampling.NEAREST)
    return np.array(mask) >= MASK_THRESHOLD


def _apply_masked_2d_edit(
    reference_bytes: bytes | None,
    mask_bytes: bytes | None,
    operation: str,
    instruction: str,
    width: int,
    height: int,
) -> bytes | None:
    """Stub 2D inpaint — darkens/lightens masked pixels by operation."""
    if not reference_bytes:
        return None
    from PIL import Image, ImageDraw, ImageFont

    img = _load_image_bytes(reference_bytes).resize((width, height))
    mask = _mask_array(mask_bytes, width, height)
    if mask is None:
        return None

    pixels = np.array(img)
    alpha = pixels[:, :, 3]
    editable = mask & (alpha > 0)

    if operation == "remove":
        pixels[editable, :3] = (pixels[editable, :3] * 0.72).astype(np.uint8)
    elif operation == "add":
        pixels[editable, :3] = np.clip(pixels[editable, :3] * 1.12 + 18, 0, 255).astype(np.uint8)
    else:
        pixels[editable, :3] = np.clip(pixels[editable, :3] * 0.95 + 12, 0, 255).astype(np.uint8)

    out = Image.fromarray(pixels, "RGBA")
    draw = ImageDraw.Draw(out)
    snippet = (instruction or operation)[:48]
    draw.text((8, height - 20), snippet, fill=(255, 255, 255, 200))

    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def _project_vertex_weights(
    vertices: np.ndarray,
    camera: dict[str, Any] | None,
    mask: np.ndarray | None,
) -> np.ndarray:
    """Map vertices to mask coverage using captured camera matrices."""
    n = len(vertices)
    weights = np.zeros(n, dtype=np.float32)
    if mask is None or not camera:
        return weights

    width = int(camera.get("width") or mask.shape[1])
    height = int(camera.get("height") or mask.shape[0])
    view = np.array(camera.get("viewMatrix"), dtype=np.float64)
    proj = np.array(camera.get("projectionMatrix"), dtype=np.float64)

    if view.size != 16 or proj.size != 16:
        return weights

    view = view.reshape(4, 4)
    proj = proj.reshape(4, 4)

    ones = np.ones((n, 1), dtype=np.float64)
    v4 = np.hstack([vertices.astype(np.float64), ones])
    clip = (proj @ view @ v4.T).T

    w = np.clip(clip[:, 3], 1e-8, None)
    ndc_x = clip[:, 0] / w
    ndc_y = clip[:, 1] / w
    ndc_z = clip[:, 2] / w

    visible = (ndc_z >= -1) & (ndc_z <= 1)
    px = ((ndc_x * 0.5 + 0.5) * width).astype(int)
    py = ((1 - (ndc_y * 0.5 + 0.5)) * height).astype(int)

    for i in range(n):
        if not visible[i]:
            continue
        x, y = px[i], py[i]
        if 0 <= x < width and 0 <= y < height and mask[y, x]:
            weights[i] = 1.0
    return weights


def _apply_masked_mesh_deform(mesh, weights: np.ndarray, operation: str):
    import trimesh

    vertices = np.array(mesh.vertices, copy=True)
    if weights.max() <= 0:
        return _apply_fallback_operation(mesh, operation)

    delta = VERTEX_DISPLACE.get(operation, VERTEX_DISPLACE["replace"])
    normals = np.array(mesh.vertex_normals)
    displacement = normals * (weights[:, None] * delta)
    vertices += displacement

    edited = trimesh.Trimesh(vertices=vertices, faces=mesh.faces, process=False)
    edited.fix_normals()
    return edited


def _apply_fallback_operation(mesh, operation: str):
    """Legacy whole-mesh tweak when no mask/camera supplied."""
    import trimesh

    vertices = np.array(mesh.vertices, copy=True)
    if operation == "remove":
        mask = vertices[:, 1] > np.median(vertices[:, 1])
        vertices[mask] *= 0.92
    elif operation == "add":
        mask = vertices[:, 1] > np.median(vertices[:, 1])
        vertices[mask] *= 1.08
    else:
        mask = vertices[:, 2] > np.median(vertices[:, 2])
        vertices[mask, 2] *= 1.06
    edited = trimesh.Trimesh(vertices=vertices, faces=mesh.faces, process=False)
    edited.fix_normals()
    return edited


def run_nano3d_edit(
    source_model_url: str,
    operation: str,
    instruction: str,
    mask_bytes: bytes | None = None,
    reference_bytes: bytes | None = None,
    camera_json: str | None = None,
    region_marks_json: str | None = None,
) -> dict[str, Any]:
    """
    Case 3-compatible edit worker (CPU v1).

    Accepts the same inputs the Next.js editor sends. Returns edited GLB bytes.
    Swap mesh deform + 2D stub for full Nano3D GPU pipeline when weights are ready.
    """
    if nano3d_gpu_enabled():
        return run_nano3d_case3_gpu(
            source_model_url,
            operation,
            instruction,
            mask_bytes,
            reference_bytes,
            camera_json,
            region_marks_json,
        )

    camera: dict[str, Any] | None = None
    if camera_json:
        try:
            camera = json.loads(camera_json)
        except json.JSONDecodeError:
            camera = None

    width = int((camera or {}).get("width") or 512)
    height = int((camera or {}).get("height") or 512)

    edited_2d = _apply_masked_2d_edit(
        reference_bytes, mask_bytes, operation, instruction, width, height
    )

    mesh = _load_mesh_from_url(source_model_url)
    mask_arr = _mask_array(mask_bytes, width, height)
    weights = _project_vertex_weights(np.array(mesh.vertices), camera, mask_arr)

    if weights.max() > 0:
        edited_mesh = _apply_masked_mesh_deform(mesh, weights, operation)
        source_tag = "modal-nano3d-v1-masked"
    else:
        edited_mesh = _apply_fallback_operation(mesh, operation)
        source_tag = "modal-nano3d-v1-fallback"

    glb = edited_mesh.export(file_type="glb")

    region_count = 0
    if region_marks_json:
        try:
            region_count = len(json.loads(region_marks_json))
        except json.JSONDecodeError:
            region_count = 0

    return {
        "format": "glb",
        "source": source_tag,
        "operation": operation,
        "instructionPreview": instruction[:120],
        "maskBytes": len(mask_bytes) if mask_bytes else 0,
        "referenceBytes": len(reference_bytes) if reference_bytes else 0,
        "edited2dBytes": len(edited_2d) if edited_2d else 0,
        "regionMarkCount": region_count,
        "maskedVertexRatio": float(weights.mean()) if weights.size else 0.0,
        "glbBytes": glb,
        "edited2dPng": edited_2d,
    }
