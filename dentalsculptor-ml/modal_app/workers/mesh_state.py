"""Serialize TRELLIS mesh tensors for two-phase GLB extraction."""

from __future__ import annotations

import io
from typing import Any


def serialize_mesh(mesh: Any) -> bytes:
    import torch

    state = {
        "vertices": mesh.vertices.detach().cpu(),
        "faces": mesh.faces.detach().cpu(),
        "attrs": mesh.attrs.detach().cpu(),
        "coords": mesh.coords.detach().cpu(),
        "layout": mesh.layout,
        "voxel_size": mesh.voxel_size,
    }
    buffer = io.BytesIO()
    torch.save(state, buffer)
    return buffer.getvalue()


def deserialize_mesh(data: bytes) -> Any:
    import torch

    state = torch.load(io.BytesIO(data), map_location="cpu", weights_only=False)

    class MeshState:
        pass

    mesh = MeshState()
    mesh.vertices = state["vertices"]
    mesh.faces = state["faces"]
    mesh.attrs = state["attrs"]
    mesh.coords = state["coords"]
    mesh.layout = state["layout"]
    mesh.voxel_size = state["voxel_size"]
    return mesh
