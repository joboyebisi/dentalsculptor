import json

from scripts.build_anatomy_spike_manifest import build_spike_manifest


def _write_inputs(tmp_path):
    assets = []
    families = ("incisor", "canine", "premolar", "molar")
    for family_index, family in enumerate(families):
        for index in range(8):
            digest = f"{family_index * 100 + index:064x}"
            assets.append({
                "id": f"{family}-{index}", "canonicalSha256": digest,
                "groupId": f"g-{family}-{index}", "split": "train",
                "toothFamily": family, "trainingRole": "anatomy-base",
                "canonicalPath": f"meshes/{digest}.ply", "source": "teeth3ds-v1",
                "reviewRequired": True, "reviewFlags": ["open-mesh"],
            })
        assets.append({
            "id": f"held-{family}", "canonicalSha256": f"{900 + family_index:064x}",
            "groupId": f"held-{family}", "split": "validation", "toothFamily": family,
            "trainingRole": "healthy-base", "canonicalPath": "held.ply", "source": "fdi16-v2",
        })
    anatomy = tmp_path / "anatomy.json"
    anatomy.write_text(json.dumps({"datasetId": "test", "assets": assets}), encoding="utf-8")
    reference = tmp_path / "reference.json"
    reference.write_text(json.dumps({"items": [{
        "canonicalSha256": assets[0]["canonicalSha256"], "groupId": assets[0]["groupId"]
    }]}), encoding="utf-8")
    return anatomy, reference


def test_spike_is_balanced_train_only_and_reference_excluded(tmp_path):
    anatomy, reference = _write_inputs(tmp_path)
    result = build_spike_manifest(anatomy, reference, tmp_path / "spike.json", per_family=4)
    assert result["caseCount"] == 16
    assert result["familyCounts"] == {"incisor": 4, "canine": 4, "premolar": 4, "molar": 4}
    assert all(item["sourceSplit"] == "train" for item in result["items"])
    excluded = json.loads(reference.read_text())["items"][0]["canonicalSha256"]
    assert excluded not in {item["canonicalSha256"] for item in result["items"]}
    assert result["clinicalAuditStatus"] == "pending"


def test_spike_selection_is_repeatable_and_labels_crown_scope(tmp_path):
    anatomy, reference = _write_inputs(tmp_path)
    first = build_spike_manifest(anatomy, reference, tmp_path / "a.json", per_family=4)
    second = build_spike_manifest(anatomy, reference, tmp_path / "b.json", per_family=4)
    assert first["selectionFingerprint"] == second["selectionFingerprint"]
    assert first["representationScopeCounts"] == {"crown-only": 16}
    assert first["rootSupervisionCount"] == 0
    assert all(item["clinicalAudit"]["status"] == "pending" for item in first["items"])
