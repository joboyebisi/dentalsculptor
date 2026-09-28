import hashlib

from scripts.teeth3ds_ingest import ScanRecord, bind_official_splits


def test_derives_validation_from_train_patients(monkeypatch, tmp_path):
    split_dir = tmp_path / "Teeth3DS_train_test_split"
    split_dir.mkdir()
    (split_dir / "training_upper.txt").write_text("PAT001_upper\nPAT002_upper\n", encoding="utf-8")
    (split_dir / "training_lower.txt").write_text("PAT001_lower\nPAT003_lower\n", encoding="utf-8")
    (split_dir / "testing_upper.txt").write_text("PAT999_upper\n", encoding="utf-8")
    (split_dir / "testing_lower.txt").write_text("PAT888_lower\n", encoding="utf-8")

    records = bind_official_splits(split_dir, validation_fraction=0.5)
    by_key = {record.scan_key: record.official_split for record in records}
    assert by_key["PAT999_upper"] == "test"
    assert by_key["PAT888_lower"] == "test"
    trainish = [key for key, split in by_key.items() if split in {"train", "validation"}]
    assert "PAT001_upper" in trainish
    assert len({record.official_split for record in records if record.scan_key.startswith("PAT00") and record.scan_key.endswith("_upper")}) >= 1
