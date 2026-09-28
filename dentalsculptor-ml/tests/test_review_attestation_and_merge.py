import csv
import json

import pytest

from scripts.attest_toothfairy_review import attest_all
from scripts.apply_toothfairy_clinical_review import apply_review
from scripts.merge_toothfairy_clinical_audit import merge_audit


FIELDS = [
    "id", "groupId", "split", "fdiNumber", "toothFamily", "automaticGate",
    "reviewRenderPath", "reviewer", "status", "toothIdentityCorrect",
    "crownComplete", "rootAndApexComplete", "segmentationLeakage",
    "artifactSeverity", "notes",
]


def _fixture(tmp_path):
    queue = tmp_path / "queue.json"
    blank = tmp_path / "blank.csv"
    record = {
        "id": "a", "groupId": "p1", "split": "train", "fdiNumber": 11,
        "toothFamily": "incisor", "rawMeshPath": "a.ply", "rawMeshSha256": "h",
        "automaticGate": "eligible-for-clinical-review", "automaticExclusionReasons": [],
        "clinicalAudit": {"status": "pending"},
    }
    queue.write_text(json.dumps({"datasetId": "tf-review", "records": [record]}), encoding="utf-8")
    with blank.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        form_row = {field: "" for field in FIELDS}
        form_row.update({
            "id": "a", "groupId": "p1", "split": "train", "fdiNumber": 11,
            "toothFamily": "incisor", "automaticGate": "eligible-for-clinical-review",
            "status": "pending", "reviewRenderPath": "a.png",
        })
        writer.writerow(form_row)
    return queue, blank


def test_attestation_applies_and_merges_registered_fields(tmp_path):
    queue, blank = _fixture(tmp_path)
    attested, receipt = tmp_path / "attested.csv", tmp_path / "receipt.json"
    attest_all(queue, blank, attested, receipt, reviewer="Reviewer", explicit_accept_all=True)
    audited = tmp_path / "audited.json"
    result = apply_review(queue, attested, audited, require_complete=True)
    assert result["acceptedCount"] == 1
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"datasetId": "tf", "assets": [{
        "id": "a", "groupId": "p1", "split": "train", "fdiNumber": 11,
        "toothFamily": "incisor", "representationScope": "whole-tooth",
        "rawMeshSha256": "h", "rawMeshPath": "a.ply",
    }]}), encoding="utf-8")
    merged = merge_audit(source, audited, tmp_path / "merged.json")
    assert merged["assets"][0]["rootCompleteness"] == "accepted-complete"
    assert merged["assets"][0]["clinicalAudit"]["reviewer"] == "Reviewer"


def test_attestation_requires_explicit_accept_all(tmp_path):
    queue, blank = _fixture(tmp_path)
    with pytest.raises(ValueError, match="explicit_accept_all"):
        attest_all(queue, blank, tmp_path / "out.csv", tmp_path / "receipt.json", reviewer="R", explicit_accept_all=False)
