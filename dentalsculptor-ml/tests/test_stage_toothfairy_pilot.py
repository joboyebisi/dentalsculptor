import json
import zipfile

from scripts.stage_toothfairy_pilot import select_entries, stage_pilot


def test_selects_repeatable_balanced_acquisition_sets():
    names = [
        f"Dataset112_ToothFairy2/labelsTr/ToothFairy2{prefix}_{index:03d}.mha"
        for prefix in ("F", "P")
        for index in range(1, 7)
    ]
    first = select_entries(names, per_prefix=3, seed=20260918)
    second = select_entries(list(reversed(names)), per_prefix=3, seed=20260918)
    assert first == second
    assert [item[0] for item in first].count("F") == 3
    assert [item[0] for item in first].count("P") == 3


def test_exclusion_uses_next_deterministic_reserve():
    names = [
        f"root/labelsTr/ToothFairy2{prefix}_{index:03d}.mha"
        for prefix in ("F", "P") for index in range(1, 7)
    ]
    baseline = select_entries(names, per_prefix=3, seed=20260918)
    excluded = baseline[-1][1]
    replacement = select_entries(
        names, per_prefix=3, seed=20260918, exclude_subjects={excluded},
    )
    assert excluded not in {item[1] for item in replacement}
    assert len(replacement) == len(baseline)
    assert replacement[:-1] == baseline[:-1]


def test_stages_only_selected_labels_and_writes_hashes(tmp_path):
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        for prefix in ("F", "P"):
            for index in range(1, 4):
                handle.writestr(
                    f"root/labelsTr/ToothFairy2{prefix}_{index:03d}.mha",
                    f"{prefix}-{index}".encode(),
                )
        handle.writestr("root/imagesTr/ToothFairy2F_001_0000.mha", b"not-staged")
    output = tmp_path / "pilot"
    receipt = stage_pilot(archive, output, per_prefix=1, seed=7)
    assert receipt["subjectCount"] == 2
    assert len(list(output.glob("*.mha"))) == 2
    assert all(len(asset["sha256"]) == 64 for asset in receipt["assets"])
    saved = json.loads((output / "pilot_staging_receipt.json").read_text())
    assert saved == receipt
