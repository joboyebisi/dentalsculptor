import pytest

import trimesh

from scripts.compare_topology_trials import add_direct_geometry_comparison, compare_trials


def _trial(trial_id: str, artifact_hash: str, components: int) -> dict:
    stages = []
    for stage in ("pipeline-decoded", "post-remesh", "final-glb"):
        stages.append({
            "stage": stage,
            "artifactSha256": artifact_hash,
            "topologyWeldControl": {"coincidentVertexWeldedTopology": {
                "componentCount": components,
                "largestComponentAreaFraction": 0.9,
            }},
            "referenceMetrics": {
                "symmetricChamferPercentDiagonal": 1.0,
                "hausdorff95PercentDiagonal": 2.0,
                "surfaceFscoreAt2Percent": 0.8,
                "sortedExtentRelativeError": 0.1,
            },
        })
    return {
        "datasetId": "d", "datasetManifestSha256": "m",
        "baseModelRevision": "b", "trellisCommit": "t", "pipelineType": "512",
        "trialId": trial_id,
        "cases": [{"id": "case", "seed": 7, "inputImageSha256": "i", "stages": stages}],
    }


def test_repeatability_gate_requires_identical_stage_artifacts():
    result = compare_trials(_trial("a", "a" * 64, 1), _trial("b", "b" * 64, 2))
    assert result["repeatabilityGatePassed"] is False
    assert result["cases"][0]["stages"][0]["weldedComponentDelta"] == 1


def test_repeatability_comparison_rejects_contract_drift():
    second = _trial("b", "a" * 64, 1)
    second["pipelineType"] = "1024"
    with pytest.raises(ValueError, match="frozen experiment contract"):
        compare_trials(_trial("a", "a" * 64, 1), second)


def test_direct_geometry_can_pass_when_serialized_bytes_differ(tmp_path):
    first = _trial("a", "a" * 64, 1)
    second = _trial("b", "b" * 64, 1)
    case_id = "case"
    for trial, root in ((first, tmp_path / "a"), (second, tmp_path / "b")):
        case_root = root / case_id
        case_root.mkdir(parents=True)
        for stage in trial["cases"][0]["stages"]:
            suffix = ".glb" if stage["stage"] == "final-glb" else ".ply"
            name = stage["stage"] + suffix
            stage["artifact"] = name
            trimesh.creation.box().export(case_root / name)
    report = add_direct_geometry_comparison(
        compare_trials(first, second), first, second, tmp_path / "a", tmp_path / "b", samples=1000
    )
    assert report["byteRepeatable"] is False
    assert report["directPairwiseGeometryPassed"] is True
    assert report["repeatabilityGatePassed"] is True
