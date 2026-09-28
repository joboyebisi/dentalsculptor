import json
import tempfile
from pathlib import Path

from scripts.build_anatomy_training_mix import build_mix, is_anatomy_training_asset


def fixture(path: Path, approved=True):
    families = [(11, "incisor"), (13, "canine"), (14, "premolar"), (16, "molar")]
    assets = []
    for fdi, family in families:
        for index in range(3):
            assets.append({"canonicalSha256": f"{fdi}-{index}", "groupId": f"p-{fdi}-{index}", "split": "train",
                           "fdiNumber": fdi, "toothFamily": family, "condition": "healthy", "trainingRole": "healthy-base"})
    path.write_text(json.dumps({"datasetId": "fixture", "researchTrainingApproved": approved, "assets": assets}))


def test_balances_and_requires_explicit_approval():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "manifest.json"
        fixture(path)
        result = build_mix([path], minimum_per_family=2, maximum_per_fdi=2)
        assert result["assetCount"] == 8
        assert set(result["trainFamilyCounts"]) == {"incisor", "canine", "premolar", "molar"}
        fixture(path, approved=False)
        try:
            build_mix([path], minimum_per_family=2, maximum_per_fdi=2)
        except ValueError as error:
            assert "not explicitly approved" in str(error)
        else:
            raise AssertionError("unapproved dataset entered training mix")


def test_accepts_diagnosis_neutral_anatomy_but_rejects_false_health_claims():
    assert is_anatomy_training_asset({"condition": "unspecified", "trainingRole": "anatomy-base"})
    assert is_anatomy_training_asset({"condition": "healthy", "trainingRole": "healthy-base"})
    assert not is_anatomy_training_asset({"condition": "healthy", "trainingRole": "anatomy-base"})
    assert not is_anatomy_training_asset({"condition": "unspecified", "trainingRole": "healthy-base"})
