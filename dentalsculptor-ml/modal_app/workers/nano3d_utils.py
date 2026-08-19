"""Nano3D edit placeholder — CPU mesh tweak until Case 3 pipeline is wired."""

from __future__ import annotations

import io
import urllib.request
from typing import Any

import numpy as np


def _load_mesh_from_url(url: str):
    import trimesh

    with urllib.request.urlopen(url, timeout=120) as resp:
        data = resp.read()
    return trimesh.load(io.BytesIO(data), file_type="glb", force="mesh")


def _apply_operation(mesh, operation: str):
    """Simple vertex displacement stand-in for masked Nano3D edits."""
    import trimesh

    vertices = np.array(mesh.vertices, copy=True)
    if operation == "remove":
        # Shrink upper half — simulates carving away material.
        mask = vertices[:, 1] > np.median(vertices[:, 1])
        vertices[mask] *= 0.92
    elif operation == "add":
        mask = vertices[:, 1] > np.median(vertices[:, 1])
        vertices[mask] *= 1.08
    else:
        # replace / default — slight bulge on buccal (+Z) side
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
) -> dict[str, Any]:
    """
    Placeholder edit worker.
    mask_bytes reserved for Nano3D Case 3 — currently ignored beyond logging size.
    """
    mesh = _load_mesh_from_url(source_model_url)
    edited = _apply_operation(mesh, operation)
    glb = edited.export(file_type="glb")
    return {
        "format": "glb",
        "source": "modal-nano3d-v0",
        "operation": operation,
        "instructionPreview": instruction[:120],
        "maskBytes": len(mask_bytes) if mask_bytes else 0,
        "glbBytes": glb,
    }
