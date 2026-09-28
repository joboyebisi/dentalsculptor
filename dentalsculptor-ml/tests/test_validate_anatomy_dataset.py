import json
from pathlib import Path

import pytest

from scripts.validate_anatomy_dataset import validate_dataset


def _write_manifest(root: Path) -> Path:
    assets = []
    for index, family in enumerate(("incisor", "canine", "premolar", "molar")):
        digest = f"{index + 1:064x}"
        mesh = root / "meshes" / f"{digest}.ply"
        mesh.parent.mkdir(exist_ok=True)
        mesh.write_text("ply\n", encoding="utf-8")
        assets.append({
            "id": family,
            "canonicalPath": f"meshes/{digest}.ply",
            "canonicalSha256": digest,
            "groupId": f"patient-{index}",
            "split": "train",
            "fdiNumber": 11 + index,
            "toothFamily": family,
            "condition": "unspecified",
            "trainingRole": "anatomy-base",
        })
    path = root / "anatomy_manifest.json"
    path.write_text(json.dumps({
        "datasetId": "dental-anatomy-v1",
        "researchTrainingApproved": True,
        "assetCount": 4,
        "splits": {"train": 4, "validation": 0, "test": 0},
        "assets": assets,
    }), encoding="utf-8")
    return path


def test_valid_anatomy_manifest_passes(tmp_path):
    result = validate_dataset(_write_manifest(tmp_path), minimum_per_family=1)
    assert result["valid"] is True
    assert result["uniqueMeshes"] == 4


def test_rejects_duplicate_hash_and_group_leakage(tmp_path):
    path = _write_manifest(tmp_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["assets"][1]["canonicalSha256"] = manifest["assets"][0]["canonicalSha256"]
    manifest["assets"][1]["groupId"] = manifest["assets"][0]["groupId"]
    manifest["assets"][1]["split"] = "validation"
    manifest["splits"] = {"train": 3, "validation": 1, "test": 0}
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate canonicalSha256.*leaks across splits"):
        validate_dataset(path, minimum_per_family=0, require_files=False)


def test_rejects_pathology_role(tmp_path):
    path = _write_manifest(tmp_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["assets"][0].update({"condition": "caries", "trainingRole": "pathology-target"})
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="pathology or unsupported trainingRole"):
        validate_dataset(path, minimum_per_family=1)
