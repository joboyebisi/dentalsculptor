import json

import pytest

from scripts.build_sample_efficiency_cohorts import build_nested_cohorts


def _manifest(tmp_path, per_family=10):
    assets = []
    for family_index, family in enumerate(("incisor", "canine", "premolar", "molar")):
        for index in range(per_family):
            value = family_index * 100 + index + 1
            assets.append({
                "id": f"{family}-{index}", "groupId": f"p-{family}-{index}",
                "split": "train", "fdiNumber": 11 + family_index,
                "toothFamily": family, "representationScope": "whole-tooth",
                "rawMeshSha256": f"{value:064x}", "rawMeshPath": f"{value}.ply",
                "rootCompleteness": "accepted-complete",
                "clinicalAudit": {"status": "accepted"},
            })
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"assets": assets}), encoding="utf-8")
    return path


def test_builds_repeatable_balanced_nested_cohorts(tmp_path):
    manifest = _manifest(tmp_path)
    first = build_nested_cohorts(manifest, tmp_path / "a.json", sizes=(8, 16, 32))
    second = build_nested_cohorts(manifest, tmp_path / "b.json", sizes=(8, 16, 32))
    assert [c["fingerprint"] for c in first["cohorts"]] == [c["fingerprint"] for c in second["cohorts"]]
    assert first["cohorts"][0]["familyCounts"] == {
        "incisor": 2, "canine": 2, "premolar": 2, "molar": 2
    }
    small = {item["rawMeshSha256"] for item in first["cohorts"][0]["items"]}
    large = {item["rawMeshSha256"] for item in first["cohorts"][-1]["items"]}
    assert small < large


def test_rejects_unreviewed_assets(tmp_path):
    manifest = _manifest(tmp_path, per_family=2)
    data = json.loads(manifest.read_text())
    data["assets"][0]["clinicalAudit"]["status"] = "pending"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Only"):
        build_nested_cohorts(manifest, tmp_path / "out.json", sizes=(8,))


def test_builds_explicit_provisional_cohort_without_clinical_claim(tmp_path):
    manifest = _manifest(tmp_path, per_family=3)
    data = json.loads(manifest.read_text())
    for asset in data["assets"]:
        asset.pop("clinicalAudit")
        asset["rootCompleteness"] = "not-yet-clinically-audited"
        asset["touchesVolumeBoundary"] = False
        asset["reviewFlags"] = []
    manifest.write_text(json.dumps(data), encoding="utf-8")
    result = build_nested_cohorts(
        manifest, tmp_path / "out.json", sizes=(8,), admission_mode="mechanical-provisional"
    )
    assert result["cohorts"][0]["familyCounts"] == {
        "incisor": 2, "canine": 2, "premolar": 2, "molar": 2
    }
    assert result["cohorts"][0]["cohortId"] == "TF-PW8"
    assert result["clinicalClaimPermitted"] is False
    assert result["trainingPurpose"] == "engineering-smoke-only"


def test_balances_fdi_quadrants_when_available(tmp_path):
    assets = []
    for family_index, family in enumerate(("incisor", "canine", "premolar", "molar"), start=1):
        for quadrant in (1, 2, 3, 4):
            for repeat in range(2):
                fdi = quadrant * 10 + family_index
                assets.append({
                    "id": f"{family}-{quadrant}-{repeat}",
                    "groupId": f"p-{family}-{quadrant}-{repeat}", "split": "train",
                    "fdiNumber": fdi, "toothFamily": family, "representationScope": "whole-tooth",
                    "rawMeshSha256": f"{len(assets) + 1:064x}", "rawMeshPath": f"{len(assets)}.ply",
                    "rootCompleteness": "accepted-complete", "clinicalAudit": {"status": "accepted"},
                })
    manifest = tmp_path / "quadrants.json"
    manifest.write_text(json.dumps({"assets": assets}), encoding="utf-8")
    cohort = build_nested_cohorts(manifest, tmp_path / "out.json", sizes=(32,))["cohorts"][0]
    assert cohort["quadrantCounts"] == {"1": 8, "2": 8, "3": 8, "4": 8}


def test_selects_validation_without_admitting_train_assets(tmp_path):
    manifest = _manifest(tmp_path, per_family=4)
    data = json.loads(manifest.read_text())
    for asset in data["assets"]:
        asset["split"] = "validation"
    data["assets"].append({**data["assets"][0], "id": "train-only", "split": "train", "rawMeshSha256": "f" * 64})
    manifest.write_text(json.dumps(data), encoding="utf-8")
    result = build_nested_cohorts(
        manifest, tmp_path / "validation.json", sizes=(8,), eligible_split="validation",
    )
    assert result["eligibleSplit"] == "validation"
    assert result["cohorts"][0]["cohortId"] == "TF-V8"
    assert "train-only" not in {item["id"] for item in result["cohorts"][0]["items"]}
