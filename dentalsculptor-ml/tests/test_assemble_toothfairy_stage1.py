import hashlib
import json

import pytest

from scripts.assemble_toothfairy_stage1 import assemble_stage1


def _component(tmp_path, split, group, content):
    root = tmp_path / split
    mesh = root / "meshes_canonical_mm" / "mesh.ply"
    mesh.parent.mkdir(parents=True)
    mesh.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    manifest = {
        "datasetId": split, "researchTrainingApproved": True,
        "clinicalClaimPermitted": True, "assetCount": 1,
        "sourceCohortFingerprint": split * 8,
        "splits": {"train": int(split == "train"), "validation": int(split == "validation"), "test": int(split == "test")},
        "assets": [{"id": split, "groupId": group, "split": split, "toothFamily": "incisor",
                    "canonicalPath": "meshes_canonical_mm/mesh.ply", "canonicalSha256": digest}],
    }
    (root / "anatomy_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_assembles_three_patient_disjoint_splits(tmp_path):
    roots = [_component(tmp_path, split, f"p-{split}", split.encode()) for split in ("train", "validation", "test")]
    result = assemble_stage1(roots, tmp_path / "out", dataset_id="stage1")
    assert result["splits"] == {"train": 1, "validation": 1, "test": 1}
    assert result["subjectCount"] == 3
    assert all((tmp_path / "out" / asset["canonicalPath"]).is_file() for asset in result["assets"])


def test_rejects_patient_leakage(tmp_path):
    roots = [_component(tmp_path, split, "same", split.encode()) for split in ("train", "validation", "test")]
    with pytest.raises(ValueError, match="patient leakage"):
        assemble_stage1(roots, tmp_path / "out", dataset_id="stage1")
