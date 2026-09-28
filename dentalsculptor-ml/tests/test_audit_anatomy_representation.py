import json

from scripts.audit_anatomy_representation import audit_representations


def test_representation_audit_does_not_treat_crowns_as_whole_teeth(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"datasetId": "d", "assets": [
        {"id": "a", "source": "teeth3ds-v1", "toothFamily": "incisor", "split": "train", "reviewRequired": True},
        {"id": "b", "source": "fdi16-v2", "toothFamily": "molar", "split": "train", "reviewRequired": False},
    ]}), encoding="utf-8")
    result = audit_representations(manifest, tmp_path / "audit.json")
    assert result["byFamily"]["incisor"] == {"crown-only": 1}
    assert result["byFamily"]["molar"] == {"whole-tooth": 1}
    assert result["wholeToothAllFamilyTrainingReady"] is False
    assert result["reviewCounts"] == {"required": 1, "notRequired": 1}
