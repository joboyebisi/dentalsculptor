"""Shared mesh utilities for Modal workers (no Modal app here)."""

from __future__ import annotations

import base64
import io
import uuid
from typing import Any


def placeholder_tooth_glb(image_bytes: bytes) -> bytes:
    """CPU placeholder — extruded silhouette until TRELLIS.2 is wired."""
    import numpy as np
    from PIL import Image
    import trimesh

    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    img = img.resize((128, 128))
    arr = np.array(img, dtype=np.float32) / 255.0
    height = (1.0 - arr) * 3.0 + 0.5
    x = np.linspace(-6, 6, 128)
    y = np.linspace(-6, 6, 128)
    xx, yy = np.meshgrid(x, y)
    zz = height
    vertices = np.stack([xx.ravel(), zz.ravel(), yy.ravel()], axis=1)
    faces = []
    for i in range(127):
        for j in range(127):
            a = i * 128 + j
            b = a + 1
            c = a + 128
            d = c + 1
            faces.append([a, c, b])
            faces.append([b, c, d])
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    mesh.fix_normals()
    return mesh.export(file_type="glb")


def generate_response_from_image(image_bytes: bytes) -> dict[str, Any]:
    glb = placeholder_tooth_glb(image_bytes)
    return {
        "jobId": str(uuid.uuid4()),
        "status": "completed",
        "format": "glb",
        "source": "modal-pipeline-v0",
        "message": "TRELLIS.2 not wired — CPU silhouette placeholder for pipeline testing.",
        "modelBase64": base64.b64encode(glb).decode("ascii"),
    }
