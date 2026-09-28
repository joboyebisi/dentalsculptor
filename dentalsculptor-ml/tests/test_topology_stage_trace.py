from pathlib import Path

import pytest
import trimesh

from scripts.analyze_mesh_topology import analyze_mesh
from scripts.topology_stage_trace import build_topology_stage_report


def _stage(name: str, mesh: trimesh.Trimesh) -> dict:
    return {"stage": name, "artifactSha256": name * 8, "topology": analyze_mesh(mesh)}


def test_topology_stage_report_finds_first_fragmentation_boundary():
    single = trimesh.creation.box()
    extra = trimesh.creation.box()
    extra.apply_translation([3, 0, 0])
    fragmented = trimesh.util.concatenate((single, extra))
    report = build_topology_stage_report([
        _stage("pipeline-decoded", single),
        _stage("post-remesh", fragmented),
        _stage("final-glb", fragmented),
    ])
    assert report["decodedGeometryFragmented"] is False
    assert report["firstGeometryFragmentationAmplificationStage"] == "post-remesh"
    assert report["productionPromotionPermitted"] is False


def test_topology_stage_report_rejects_missing_or_reordered_stage():
    mesh = trimesh.creation.box()
    with pytest.raises(ValueError, match="Expected topology stages"):
        build_topology_stage_report([_stage("final-glb", mesh)])
