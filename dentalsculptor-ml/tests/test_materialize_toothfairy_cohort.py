import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from scripts.materialize_toothfairy_cohort import materialize


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_materialize_verifies_hash_and_preserves_scale(tmp_path: Path):
    source = tmp_path / "source"
    mesh_path = source / "subjects" / "s1" / "meshes_raw_world_mm" / "fdi11.ply"
    mesh_path.parent.mkdir(parents=True)
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=3.0)
    mesh.apply_translation([20.0, 30.0, 40.0])
    mesh_path.write_bytes(mesh.export(file_type="ply"))
    raw_hash = _hash(mesh_path)
    fingerprint = "a" * 64
    cohort_path = tmp_path / "cohort.json"
    cohort_path.write_text(json.dumps({
        "admissionMode": "mechanical-provisional",
        "cohorts": [{
            "cohortId": "TF-PW1", "size": 1, "fingerprint": fingerprint,
            "items": [{
                "id": "s1-fdi11", "groupId": "s1", "fdiNumber": 11,
                "toothFamily": "incisor", "rawMeshSha256": raw_hash,
                "rawMeshPath": "subjects/s1/meshes_raw_world_mm/fdi11.ply",
            }],
        }],
    }), encoding="utf-8")
    output = tmp_path / "out"
    result = materialize(cohort_path, source, output, cohort_id="TF-PW1", dataset_id="test")
    asset = result["assets"][0]
    canonical = trimesh.load(output / asset["canonicalPath"], force="mesh", process=False)
    assert result["researchTrainingApproved"] is False
    assert result["trainingPurpose"] == "engineering-smoke-only"
    assert asset["canonicalization"]["scaleApplied"] == 1.0
    assert np.allclose(canonical.centroid, np.zeros(3), atol=1e-5)
    assert np.allclose(np.sort(canonical.extents), np.sort(mesh.extents), atol=1e-5)
    assert (output / "materialization_receipt.json").is_file()


def test_materialize_rejects_changed_source(tmp_path: Path):
    source = tmp_path / "source"
    mesh_path = source / "mesh.ply"
    source.mkdir()
    mesh_path.write_bytes(trimesh.creation.box().export(file_type="ply"))
    cohort_path = tmp_path / "cohort.json"
    cohort_path.write_text(json.dumps({
        "admissionMode": "mechanical-provisional",
        "cohorts": [{"cohortId": "x", "size": 1, "fingerprint": "b" * 64, "items": [{
            "id": "x", "groupId": "g", "fdiNumber": 31, "toothFamily": "incisor",
            "rawMeshSha256": "0" * 64, "rawMeshPath": "mesh.ply",
        }]}],
    }), encoding="utf-8")
    try:
        materialize(cohort_path, source, tmp_path / "out", cohort_id="x")
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("Expected source hash mismatch")


def test_materialize_clinical_cohort_preserves_approval(tmp_path: Path):
    source = tmp_path / "source"
    mesh_path = source / "mesh.ply"
    source.mkdir()
    mesh_path.write_bytes(trimesh.creation.icosphere(subdivisions=2).export(file_type="ply"))
    cohort_path = tmp_path / "cohort.json"
    cohort_path.write_text(json.dumps({
        "admissionMode": "clinical", "clinicalClaimPermitted": True,
        "cohorts": [{"cohortId": "TF-W1", "size": 1, "fingerprint": "c" * 64, "items": [{
            "id": "x", "groupId": "g", "fdiNumber": 31, "toothFamily": "incisor",
            "rawMeshSha256": _hash(mesh_path), "rawMeshPath": "mesh.ply",
        }]}],
    }), encoding="utf-8")
    result = materialize(cohort_path, source, tmp_path / "out", cohort_id="TF-W1")
    assert result["researchTrainingApproved"] is True
    assert result["clinicalClaimPermitted"] is True
    assert result["trainingPurpose"] == "registered-stage1"


def test_materialize_preserves_heldout_split(tmp_path: Path):
    source = tmp_path / "source"
    mesh_path = source / "mesh.ply"
    source.mkdir()
    mesh_path.write_bytes(trimesh.creation.icosphere(subdivisions=2).export(file_type="ply"))
    cohort_path = tmp_path / "cohort.json"
    cohort_path.write_text(json.dumps({
        "admissionMode": "clinical", "clinicalClaimPermitted": True,
        "eligibleSplit": "test",
        "cohorts": [{"cohortId": "TF-T1", "size": 1, "fingerprint": "d" * 64, "items": [{
            "id": "x", "groupId": "heldout", "fdiNumber": 31, "toothFamily": "incisor",
            "rawMeshSha256": _hash(mesh_path), "rawMeshPath": "mesh.ply",
        }]}],
    }), encoding="utf-8")
    result = materialize(cohort_path, source, tmp_path / "out", cohort_id="TF-T1")
    assert result["assets"][0]["split"] == "test"
    assert result["splits"] == {"train": 0, "validation": 0, "test": 1}
