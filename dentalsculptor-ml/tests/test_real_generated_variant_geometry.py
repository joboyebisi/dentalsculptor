"""Regression checks against real DentalSculptor reconstruction artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from modal_app.workers.variant_geometry import (
    _build_cutters,
    _copy_vertex_colours,
    _quality_metrics,
    _surface_clip_remove,
    _validate_result,
    validate_variant_recipe,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = (
    ROOT / "docs/benchmarks/smoke-runs/20260828-010629/generated.glb",
    ROOT / "docs/benchmarks/smoke-runs/20260828-010904/generated.glb",
)


def _mesh(path: Path):
    scene = trimesh.load(path, force="scene")
    mesh = scene.to_geometry()
    mesh.metadata = dict(mesh.metadata)
    return mesh


def _fracture_recipe():
    return validate_variant_recipe(json.dumps({
        "schemaVersion": 1,
        "presetId": "fracture-oblique",
        "caseId": "fracture",
        "technique": "boolean",
        "operation": "remove",
        "severity": "moderate",
        "angleDeg": 35,
        "depthMm": 1.5,
        "targetSurface": "occlusal",
        "coveragePercent": 12,
        "lesionCount": 1,
    }))


def _geometry_digest(mesh) -> str:
    digest = hashlib.sha256()
    digest.update(np.asarray(mesh.vertices, dtype="<f8").tobytes())
    digest.update(np.asarray(mesh.faces, dtype="<i8").tobytes())
    return digest.hexdigest()


@pytest.mark.parametrize("artifact", ARTIFACTS, ids=lambda path: path.parent.name)
def test_real_reconstruction_fracture_is_local_repeatable_and_exportable(artifact):
    assert artifact.is_file(), f"missing checked-in reconstruction fixture: {artifact}"
    source = _mesh(artifact)
    source_vertices = np.asarray(source.vertices).copy()
    source_faces = np.asarray(source.faces).copy()
    vertices = np.asarray(source.vertices)

    # The checked-in reconstructions use their longest axis for crown-to-root.
    long_axis = int(np.argmax(source.extents))
    crown_threshold = float(np.quantile(vertices[:, long_axis], 0.90))
    transverse = [axis for axis in range(3) if axis != long_axis][0]
    selected = np.flatnonzero(
        (vertices[:, long_axis] >= crown_threshold)
        & (vertices[:, transverse] >= np.quantile(vertices[:, transverse], 0.55))
    )
    assert len(selected) >= 4

    recipe = _fracture_recipe()
    cutters, label = _build_cutters(source, recipe, selected)
    first = _surface_clip_remove(source, cutters)
    second = _surface_clip_remove(source, cutters)
    _copy_vertex_colours(source, first)
    metrics = _quality_metrics(source, first, np.isin(np.arange(len(vertices)), selected), f"{label}-surface-clip")
    _validate_result(source, first, recipe, metrics)

    assert metrics["removedFaces"] > 0
    assert metrics["removedFaces"] < len(source.faces) * 0.20
    assert metrics["capFaces"] > 0
    assert _geometry_digest(first) == _geometry_digest(second)
    assert first.export(file_type="glb")[:4] == b"glTF"

    # Surface clipping must preserve every vertex outside the local cutter.
    retained_distances = cKDTree(np.asarray(first.vertices)).query(source_vertices, k=1)[0]
    unchanged_ratio = float(np.mean(retained_distances <= np.linalg.norm(source.extents) * 1e-9))
    assert unchanged_ratio >= 0.80
    assert np.array_equal(source_vertices, np.asarray(source.vertices))
    assert np.array_equal(source_faces, np.asarray(source.faces))
