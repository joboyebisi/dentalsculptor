#!/usr/bin/env python3
"""Offline regression matrix for deterministic edit strategies."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modal_app.workers.variant_geometry import (  # noqa: E402
    PRESET_CONTRACT,
    _build_cutters,
    _surface_clip_remove,
    build_case_variant,
    validate_variant_recipe,
)


def mask_bytes(size: int = 256) -> bytes:
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    draw.ellipse((size * 0.48, size * 0.08, size * 0.88, size * 0.53), fill=255)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def recipe(preset_id: str) -> dict:
    case_id, technique, operation = PRESET_CONTRACT[preset_id]
    return {
        "schemaVersion": 1,
        "presetId": preset_id,
        "caseId": case_id,
        "technique": technique,
        "operation": operation,
        "severity": "moderate",
        "angleDeg": 35,
        "depthMm": 1.5,
        "targetSurface": "occlusal",
        "label": preset_id,
    }


def main() -> int:
    camera = {
        "viewMatrix": np.eye(4).reshape(-1, order="F").tolist(),
        "projectionMatrix": np.eye(4).reshape(-1, order="F").tolist(),
        "position": [0, 0, 3],
        "width": 256,
        "height": 256,
    }
    deterministic = [
        preset_id
        for preset_id, (_, technique, _) in PRESET_CONTRACT.items()
        if technique in {"boolean", "deform", "material"}
    ]

    for preset_id in deterministic:
        source = trimesh.creation.icosphere(subdivisions=4, radius=1.0)
        source.visual = trimesh.visual.ColorVisuals(
            source,
            vertex_colors=np.tile(np.array([230, 220, 195, 255], dtype=np.uint8), (len(source.vertices), 1)),
        )
        source_vertices = np.asarray(source.vertices).copy()
        source_faces = np.asarray(source.faces).copy()
        validated = validate_variant_recipe(json.dumps(recipe(preset_id)))
        result = build_case_variant(source, validated, mask_bytes(), camera)
        metrics = result["metrics"]

        assert result["glbBytes"][:4] == b"glTF", f"{preset_id}: invalid GLB"
        assert 0 < metrics["maskedVertexRatio"] < 0.55, f"{preset_id}: invalid locality"
        assert metrics["boundsDriftRatio"] <= 0.38, f"{preset_id}: global bounds drift"
        assert metrics["centroidDriftRatio"] <= 0.16, f"{preset_id}: global centroid drift"
        assert np.array_equal(source_vertices, np.asarray(source.vertices)), f"{preset_id}: mutated source vertices"
        assert np.array_equal(source_faces, np.asarray(source.faces)), f"{preset_id}: mutated source faces"
        print(f"OK {preset_id}: {metrics['techniqueUsed']}")

    # Generated reconstructions can contain holes. The deterministic fallback
    # must still remove and cap the selected enamel instead of returning master.
    source = trimesh.creation.icosphere(subdivisions=4, radius=1.0)
    open_faces = np.asarray(source.faces)[np.asarray(source.triangles_center)[:, 1] > -0.92]
    source = trimesh.Trimesh(vertices=source.vertices, faces=open_faces, process=False)
    source.remove_unreferenced_vertices()
    assert not source.is_watertight
    vertices = np.asarray(source.vertices)
    selected = np.flatnonzero((vertices[:, 0] > 0.25) & (vertices[:, 1] > 0.25))
    fracture_recipe = validate_variant_recipe(json.dumps(recipe("fracture-oblique")))
    cutters, _ = _build_cutters(source, fracture_recipe, selected)
    clipped = _surface_clip_remove(source, cutters)
    assert len(clipped.faces) < len(source.faces), "open-mesh fracture did not remove source faces"
    assert int(clipped.metadata.get("surfaceClipRemovedFaces", 0)) > 0
    assert int(clipped.metadata.get("surfaceClipCapFaces", 0)) > 0
    assert clipped.export(file_type="glb")[:4] == b"glTF"
    print("OK non-watertight fracture: capped surface-clip fallback")

    # Educator-facing Class I/caries controls must map to deterministic cutter
    # counts, and coverage must change the physical extent of the edit.
    source = trimesh.creation.icosphere(subdivisions=3, radius=1.0)
    selected = np.flatnonzero(np.asarray(source.vertices)[:, 1] > 0.3)

    class_one = recipe("class1-small")
    class_one.update({"lesionCount": 3, "coveragePercent": 15})
    class_one_cutters, class_one_method = _build_cutters(
        source, validate_variant_recipe(json.dumps(class_one)), selected
    )
    assert len(class_one_cutters) == 3
    assert "3-site" in class_one_method

    caries = recipe("caries-excavate")
    caries.update({"lesionCount": 2, "coveragePercent": 10})
    caries_cutters, caries_method = _build_cutters(
        source, validate_variant_recipe(json.dumps(caries)), selected
    )
    assert len(caries_cutters) == 2
    assert "2-site" in caries_method

    compact = recipe("class1-small")
    compact["coveragePercent"] = 5
    broad = recipe("class1-small")
    broad["coveragePercent"] = 40
    compact_cutters, _ = _build_cutters(
        source, validate_variant_recipe(json.dumps(compact)), selected
    )
    broad_cutters, _ = _build_cutters(
        source, validate_variant_recipe(json.dumps(broad)), selected
    )
    assert np.prod(broad_cutters[0].extents) > np.prod(compact_cutters[0].extents)

    for field, value in (("lesionCount", 4), ("coveragePercent", 61)):
        invalid = recipe("class1-small")
        invalid[field] = value
        try:
            validate_variant_recipe(json.dumps(invalid))
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid {field} was accepted")
    print("OK clinical controls: count, coverage, and validation")

    print(f"Validated {len(deterministic)} deterministic variant strategies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
