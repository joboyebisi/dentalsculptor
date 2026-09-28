import io

import trimesh

from modal_app.workers.anatomy_quality import assess_generated_glb


def glb(mesh):
    stream = io.BytesIO()
    mesh.export(stream, file_type="glb")
    return stream.getvalue()


def test_accepts_connected_detailed_tooth_proxy():
    mesh = trimesh.creation.icosphere(subdivisions=4)
    mesh.apply_scale((0.72, 0.8, 1.35))
    result = assess_generated_glb(glb(mesh))
    assert result["passed"]
    assert result["score"] >= 0.8
    assert result["largestComponentRatio"] == 1.0


def test_flags_fragmented_generation():
    first = trimesh.creation.icosphere(subdivisions=3)
    second = first.copy()
    second.apply_translation((4, 0, 0))
    result = assess_generated_glb(glb(trimesh.util.concatenate((first, second))))
    assert not result["passed"]
    assert "fragmented-mesh" in result["reasons"]
    assert result["reviewRequired"]
