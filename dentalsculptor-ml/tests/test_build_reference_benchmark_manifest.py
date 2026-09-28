import json

import pytest

from scripts.build_reference_benchmark_manifest import build_reference_manifest


def _manifest(tmp_path, held_out_per_family=8):
    assets = []
    counter = 0
    for family in ("incisor", "canine", "premolar", "molar"):
        assets.append({"id": f"train-{family}", "split": "train", "toothFamily": family,
                       "groupId": f"train-{family}", "canonicalSha256": f"{counter:064x}",
                       "canonicalPath": f"meshes/{counter}.ply"})
        counter += 1
        for index in range(held_out_per_family):
            assets.append({"id": f"held-{family}-{index}", "split": "validation", "toothFamily": family,
                           "groupId": f"held-{family}-{index}", "canonicalSha256": f"{counter:064x}",
                           "canonicalPath": f"meshes/{counter}.ply", "fdiNumber": 11})
            counter += 1
    path = tmp_path / "anatomy_manifest.json"
    path.write_text(json.dumps({"datasetId": "fixture", "assets": assets}), encoding="utf-8")
    return path


def test_builds_repeatable_balanced_nontraining_cohort(tmp_path):
    source = _manifest(tmp_path)
    first = build_reference_manifest(source, tmp_path / "a.json")
    second = build_reference_manifest(source, tmp_path / "b.json")
    assert first == second
    assert first["caseCount"] == 32
    assert set(first["familyCounts"].values()) == {8}
    assert all(item["sourceSplit"] != "train" for item in first["items"])
    assert len({item["groupId"] for item in first["items"]}) == 32


def test_fails_when_a_family_cannot_meet_floor(tmp_path):
    source = _manifest(tmp_path, held_out_per_family=7)
    with pytest.raises(ValueError, match="Need 8 held-out groups"):
        build_reference_manifest(source, tmp_path / "benchmark.json")
