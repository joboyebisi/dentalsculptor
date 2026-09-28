import csv
import json

import pytest

from scripts.render_conditional_batches import (
    audit_receipts,
    batch_window,
    batch_fingerprint,
    receipt_path,
    select_batch,
)


def write_metadata(path, count=5):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["sha256", "split", "local_path"])
        writer.writeheader()
        for index in range(count):
            writer.writerow({"sha256": f"{index:064x}", "split": "train", "local_path": f"/{index}.ply"})
        writer.writerow({"sha256": "f" * 64, "split": "validation", "local_path": "/held-out.ply"})


def write_artifacts(root, digest, views=2):
    target = root / "renders_cond" / digest
    target.mkdir(parents=True, exist_ok=True)
    frames = []
    for index in range(views):
        name = f"{index:03d}.png"
        (target / name).write_bytes(b"png")
        frames.append({"file_path": name, "transform_matrix": [[1, 0, 0, 0]] * 4})
    (target / "transforms.json").write_text(json.dumps({"frames": frames}), encoding="utf-8")


def test_select_batch_is_sorted_train_only_and_bounded(tmp_path):
    write_metadata(tmp_path / "metadata.csv")
    selected = select_batch(tmp_path / "metadata.csv", 1, 2)
    assert [row["sha256"] for row in selected] == [f"{2:064x}", f"{3:064x}"]
    with pytest.raises(ValueError):
        select_batch(tmp_path / "metadata.csv", 3, 2)


def test_batch_window_is_bounded_and_reports_resume_cursor(tmp_path):
    write_metadata(tmp_path / "metadata.csv", count=11)
    first = batch_window(tmp_path / "metadata.csv", start_batch=0, batch_size=2)
    assert first["batchIndices"] == [0, 1, 2, 3]
    assert first["totalBatches"] == 6
    assert first["nextBatch"] == 4
    final = batch_window(tmp_path / "metadata.csv", start_batch=4, batch_size=2)
    assert final["batchIndices"] == [4, 5]
    assert final["nextBatch"] is None


def test_batch_window_rejects_unbounded_parallelism(tmp_path):
    write_metadata(tmp_path / "metadata.csv", count=11)
    with pytest.raises(ValueError, match="between 1 and 4"):
        batch_window(tmp_path / "metadata.csv", start_batch=0, batch_size=2, window_size=5)


def test_audit_requires_every_receipt_and_artifact(tmp_path):
    write_metadata(tmp_path / "metadata.csv", count=2)
    rows = select_batch(tmp_path / "metadata.csv", 0, 2)
    for row in rows:
        write_artifacts(tmp_path, row["sha256"])
    path = receipt_path(tmp_path, 0, 2)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"valid": True, "fingerprint": batch_fingerprint(rows, 2)}), encoding="utf-8")
    result = audit_receipts(tmp_path, batch_size=2, num_cond_views=2)
    assert result["valid"] is True
    assert result["validatedAssetCount"] == 2


def test_audit_rejects_stale_receipt(tmp_path):
    write_metadata(tmp_path / "metadata.csv", count=1)
    path = receipt_path(tmp_path, 0, 1)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"valid": True, "fingerprint": "stale"}), encoding="utf-8")
    assert audit_receipts(tmp_path, batch_size=1, num_cond_views=2)["valid"] is False


def test_audit_bounds_failure_details(tmp_path):
    write_metadata(tmp_path / "metadata.csv", count=5)
    result = audit_receipts(tmp_path, batch_size=1, num_cond_views=2, max_failure_details=2)
    assert result["failureCount"] == 5
    assert len(result["failures"]) == 2
    assert result["failureDetailsTruncated"] is True
