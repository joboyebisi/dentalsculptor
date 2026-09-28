import pytest

from scripts.apply_toothfairy_clinical_review import parse_bool, validate_decision


def accepted_row():
    return {
        "status": "accepted", "reviewer": "educator-1",
        "toothIdentityCorrect": "true", "crownComplete": "true",
        "rootAndApexComplete": "true", "segmentationLeakage": "false",
        "artifactSeverity": "none", "notes": "",
    }


def test_acceptance_requires_every_registered_gate():
    decision = validate_decision(accepted_row())
    assert decision["status"] == "accepted"
    broken = accepted_row()
    broken["rootAndApexComplete"] = "false"
    with pytest.raises(ValueError, match="registered anatomy gates"):
        validate_decision(broken)


def test_rejection_and_artifact_require_notes():
    row = accepted_row()
    row.update({"status": "rejected", "artifactSeverity": "severe"})
    with pytest.raises(ValueError, match="notes are required"):
        validate_decision(row)


def test_boolean_parser_is_strict():
    assert parse_bool("YES", "field") is True
    assert parse_bool("0", "field") is False
    with pytest.raises(ValueError, match="true or false"):
        parse_bool("maybe", "field")
