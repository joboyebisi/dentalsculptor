import json

import pytest

from scripts.build_toothfairy_review_subset import build_review_subset


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_builds_ordered_traceable_review_subset(tmp_path):
    source_path = tmp_path / "source.json"
    cohorts_path = tmp_path / "cohorts.json"
    output_path = tmp_path / "review.json"
    assets = [
        {"id": "a", "rawMeshSha256": "ha", "groupId": "p1", "fdiNumber": 11, "toothFamily": "incisor"},
        {"id": "b", "rawMeshSha256": "hb", "groupId": "p2", "fdiNumber": 24, "toothFamily": "premolar"},
    ]
    _write(source_path, {"datasetId": "source-v1", "assets": assets})
    _write(cohorts_path, {
        "admissionMode": "mechanical-provisional", "selectionSeed": 7,
        "maximumPerSubject": 4,
        "cohorts": [{"cohortId": "TF-PW2", "size": 2, "fingerprint": "fp", "items": [
            {"id": "b", "rawMeshSha256": "hb"}, {"id": "a", "rawMeshSha256": "ha"},
        ]}],
    })
    result = build_review_subset(source_path, cohorts_path, output_path, cohort_id="TF-PW2")
    assert [asset["id"] for asset in result["assets"]] == ["b", "a"]
    assert result["familyCounts"] == {"premolar": 1, "incisor": 1}
    assert result["researchTrainingApproved"] is False
    assert len(result["sourceManifestSha256"]) == 64


def test_rejects_source_hash_drift(tmp_path):
    source_path = tmp_path / "source.json"
    cohorts_path = tmp_path / "cohorts.json"
    _write(source_path, {"datasetId": "source-v1", "assets": [
        {"id": "a", "rawMeshSha256": "actual", "groupId": "p1", "fdiNumber": 11, "toothFamily": "incisor"},
    ]})
    _write(cohorts_path, {
        "admissionMode": "mechanical-provisional", "cohorts": [{
            "cohortId": "TF-PW1", "size": 1, "items": [{"id": "a", "rawMeshSha256": "stale"}],
        }],
    })
    with pytest.raises(ValueError, match="hash mismatch"):
        build_review_subset(source_path, cohorts_path, tmp_path / "out.json", cohort_id="TF-PW1")
