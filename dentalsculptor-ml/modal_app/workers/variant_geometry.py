"""Deterministic, mask-local teaching variants derived from an immutable master mesh."""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from modal_app.workers.nano3d_utils import (
    _apply_masked_mesh_deform,
    _load_mesh_from_url,
    _mask_array,
    _project_vertex_weights,
)


def _copy_vertex_colours(source, target):
    import trimesh
    from scipy.spatial import cKDTree

    try:
        colours = np.asarray(source.visual.to_color().vertex_colors)
        nearest = cKDTree(np.asarray(source.vertices)).query(np.asarray(target.vertices), k=1)[1]
        target.visual = trimesh.visual.ColorVisuals(target, vertex_colors=colours[nearest])
    except Exception:
        target.visual = trimesh.visual.ColorVisuals(
            target, vertex_colors=np.tile(np.array([238, 229, 205, 255], dtype=np.uint8), (len(target.vertices), 1))
        )


def run_case_variant(
    source_model_url: str,
    recipe_json: str,
    mask_bytes: bytes | None,
    camera_json: str | None,
) -> dict[str, Any]:
    import trimesh

    recipe = json.loads(recipe_json)
    camera = json.loads(camera_json) if camera_json else None
    width = int((camera or {}).get("width") or 512)
    height = int((camera or {}).get("height") or 512)
    mesh = _load_mesh_from_url(source_model_url)
    weights = _project_vertex_weights(
        np.asarray(mesh.vertices), _camera_or_none(camera), _mask_array(mask_bytes, width, height)
    )
    selected = np.flatnonzero(weights > 0)
    if not len(selected):
        raise ValueError("The marked region does not intersect the tooth. Fit the tooth to view and repaint the target.")

    technique = recipe.get("technique")
    severity = recipe.get("severity", "moderate")
    if technique == "material":
        result = mesh.copy()
        colours = np.asarray(result.visual.to_color().vertex_colors).copy()
        lesion = {"small": [128, 82, 40, 255], "moderate": [100, 58, 29, 255], "large": [70, 38, 20, 255]}[severity]
        colours[selected] = np.asarray(lesion, dtype=np.uint8)
        result.visual = trimesh.visual.ColorVisuals(result, vertex_colors=colours)
        method = "localized-material"
    else:
        centre = np.asarray(mesh.vertices)[selected].mean(axis=0)
        diagonal = float(np.linalg.norm(mesh.extents))
        radius = diagonal * {"small": 0.075, "moderate": 0.12, "large": 0.18}[severity]
        cutter = trimesh.creation.icosphere(subdivisions=3, radius=radius)
        if recipe.get("caseId") == "fracture":
            cutter.apply_scale([1.45, 0.9, 1.2])
        elif recipe.get("caseId") in ("class-i", "endo", "caries"):
            cutter.apply_scale([0.75, 0.75, 1.35])
        cutter.apply_translation(centre)
        try:
            result = trimesh.boolean.difference([mesh, cutter], engine="manifold", check_volume=False)
            if result is None or not len(result.faces):
                raise ValueError("empty boolean result")
            _copy_vertex_colours(mesh, result)
            method = "localized-boolean"
        except Exception:
            # A localized scale-aware deformation is safer than returning no model
            # when an imported mesh is not watertight enough for a Boolean operation.
            result = _apply_masked_mesh_deform(mesh, weights, "remove")
            _copy_vertex_colours(mesh, result)
            method = "localized-deformation-fallback"

    return {
        "format": "glb",
        "source": method,
        "glbBytes": result.export(file_type="glb"),
        "maskedVertexRatio": float(weights.mean()),
        "metrics": {
            "techniqueUsed": method,
            "sourceVertices": int(len(mesh.vertices)),
            "resultVertices": int(len(result.vertices)),
            "sourceFaces": int(len(mesh.faces)),
            "resultFaces": int(len(result.faces)),
            "watertight": bool(result.is_watertight),
            "boundsDriftRatio": float(np.linalg.norm(result.extents - mesh.extents) / max(np.linalg.norm(mesh.extents), 1e-9)),
        },
    }


def _camera_or_none(camera):
    return camera if isinstance(camera, dict) else None
