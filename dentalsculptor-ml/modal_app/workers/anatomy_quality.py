"""Fast, deterministic geometry gate for generated dental meshes.

This is deliberately a release/triage gate, not a clinical diagnosis model.
Landmark accuracy is added during blinded reference evaluation when FDI-labelled
ground truth is available.
"""

from __future__ import annotations

import io
from typing import Any

import numpy as np


def assess_generated_glb(glb_bytes: bytes) -> dict[str, Any]:
    import trimesh

    loaded = trimesh.load(io.BytesIO(glb_bytes), file_type="glb", force="scene")
    geometries = [geometry for geometry in loaded.geometry.values() if len(geometry.faces) > 0]
    if not geometries:
        return {"passed": False, "score": 0.0, "reasons": ["empty-mesh"]}
    mesh = trimesh.util.concatenate(tuple(geometries))
    components = mesh.split(only_watertight=False)
    extents = np.asarray(mesh.extents, dtype=float)
    positive = extents[extents > 1e-8]
    aspect_ratio = float(positive.max() / positive.min()) if len(positive) == 3 else float("inf")
    areas = np.asarray(mesh.area_faces)
    degenerate_ratio = float(np.count_nonzero(areas < max(float(mesh.area), 1e-9) * 1e-12) / max(len(areas), 1))
    finite = bool(np.isfinite(np.asarray(mesh.vertices)).all())
    largest_component_ratio = float(max((len(part.faces) for part in components), default=0) / max(len(mesh.faces), 1))

    reasons: list[str] = []
    if not finite:
        reasons.append("non-finite-vertices")
    if len(mesh.faces) < 500:
        reasons.append("insufficient-surface-detail")
    if largest_component_ratio < 0.96:
        reasons.append("fragmented-mesh")
    if not 1.05 <= aspect_ratio <= 8.0:
        reasons.append("implausible-proportions")
    if degenerate_ratio > 0.005:
        reasons.append("degenerate-faces")

    score = 1.0
    score -= min(0.35, (1 - largest_component_ratio) * 2.5)
    score -= min(0.2, degenerate_ratio * 20)
    score -= 0.15 if not mesh.is_watertight else 0
    score -= 0.2 if aspect_ratio < 1.05 or aspect_ratio > 8 else 0
    score -= 0.3 if len(mesh.faces) < 500 else 0
    score = float(np.clip(score, 0, 1))
    return {
        "passed": not reasons,
        "score": round(score, 4),
        "reviewRequired": bool(reasons) or score < 0.8,
        "reasons": reasons,
        "faceCount": int(len(mesh.faces)),
        "componentCount": int(len(components)),
        "largestComponentRatio": round(largest_component_ratio, 4),
        "watertight": bool(mesh.is_watertight),
        "aspectRatio": round(aspect_ratio, 4),
        "degenerateFaceRatio": round(degenerate_ratio, 6),
    }
