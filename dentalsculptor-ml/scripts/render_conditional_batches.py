"""Persistent, receipt-backed TRELLIS conditional-render batches.

This deliberately does not trust renderer progress counters or metadata shards.
Every selected asset must have the expected images and camera transforms on disk.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from math import ceil
from datetime import datetime, timezone
from pathlib import Path

from scripts.diagnose_conditional_render import (
    patch_renderer_for_diagnostics,
    validate_render_artifacts,
)


def training_rows(metadata_path: Path) -> list[dict]:
    with metadata_path.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row.get("split") == "train"]
    rows.sort(key=lambda row: row.get("sha256", ""))
    if not rows:
        raise ValueError(f"No training rows in {metadata_path}.")
    if any(len(row.get("sha256", "")) != 64 for row in rows):
        raise ValueError("Conditional-render batch contains an invalid sha256.")
    return rows


def select_batch(metadata_path: Path, batch_index: int, batch_size: int) -> list[dict]:
    if batch_index < 0:
        raise ValueError("batch_index must be non-negative")
    if batch_size < 1 or batch_size > 100:
        raise ValueError("batch_size must be between 1 and 100")
    rows = training_rows(metadata_path)
    start = batch_index * batch_size
    selected = rows[start : start + batch_size]
    if not selected:
        raise ValueError(
            f"Batch {batch_index} is outside {len(rows)} training rows at size {batch_size}."
        )
    return selected


def batch_window(
    metadata_path: Path,
    *,
    start_batch: int,
    batch_size: int,
    window_size: int = 4,
) -> dict:
    """Plan one bounded, deterministic render window without touching artifacts."""
    if start_batch < 0:
        raise ValueError("start_batch must be non-negative")
    if batch_size < 1 or batch_size > 100:
        raise ValueError("batch_size must be between 1 and 100")
    if window_size < 1 or window_size > 4:
        raise ValueError("window_size must be between 1 and 4")
    rows = training_rows(metadata_path)
    total_batches = ceil(len(rows) / batch_size)
    if start_batch >= total_batches:
        raise ValueError(
            f"start_batch {start_batch} is outside {total_batches} batches at size {batch_size}."
        )
    indices = list(range(start_batch, min(start_batch + window_size, total_batches)))
    return {
        "trainingAssetCount": len(rows),
        "batchSize": batch_size,
        "totalBatches": total_batches,
        "startBatch": start_batch,
        "windowSize": len(indices),
        "batchIndices": indices,
        "nextBatch": indices[-1] + 1 if indices[-1] + 1 < total_batches else None,
    }


def receipt_path(dataset_root: Path, batch_index: int, batch_size: int) -> Path:
    return dataset_root / "render_batches" / f"batch-{batch_index:05d}-size-{batch_size}.json"


def batch_fingerprint(rows: list[dict], num_cond_views: int) -> str:
    payload = json.dumps(
        {"sha256": [row["sha256"] for row in rows], "numCondViews": num_cond_views},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_selected(dataset_root: Path, rows: list[dict], num_cond_views: int) -> tuple[list[dict], list[dict]]:
    passed, failed = [], []
    for row in rows:
        try:
            passed.append(validate_render_artifacts(dataset_root, row["sha256"], num_cond_views))
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            failed.append({"sha256": row["sha256"], "error": str(exc)})
    return passed, failed


def render_selected_assets(
    *, toolkit: Path, dataset_root: Path, subset: str, rows: list[dict], num_cond_views: int
) -> dict:
    """Render an explicit sealed selection and validate files, not progress output."""
    renderer = toolkit / "render_cond.py"
    patch_renderer_for_diagnostics(renderer)
    command = [
        "python", str(renderer), subset,
        "--root", str(dataset_root),
        "--render_cond_root", str(dataset_root),
        "--max_workers", "1",
        "--num_cond_views", str(num_cond_views),
        "--instances", ",".join(row["sha256"] for row in rows),
    ]
    print("+", " ".join(command), flush=True)
    process_error = None
    try:
        subprocess.run(command, cwd=toolkit, check=True)
    except subprocess.CalledProcessError as exc:
        process_error = f"renderer exited with code {exc.returncode}"
    passed, failed = validate_selected(dataset_root, rows, num_cond_views)
    return {
        "valid": not failed and process_error is None and len(passed) == len(rows),
        "successfulCount": len(passed), "failedCount": len(failed),
        "assets": passed, "failures": failed, "processError": process_error,
    }


def render_batch(
    *,
    toolkit: Path,
    dataset_root: Path,
    subset: str,
    batch_index: int,
    batch_size: int,
    num_cond_views: int = 24,
) -> dict:
    rows = select_batch(dataset_root / "metadata.csv", batch_index, batch_size)
    fingerprint = batch_fingerprint(rows, num_cond_views)
    receipt = receipt_path(dataset_root, batch_index, batch_size)
    if receipt.is_file():
        existing = json.loads(receipt.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("fingerprint") == fingerprint:
            passed, failed = validate_selected(dataset_root, rows, num_cond_views)
            if not failed and len(passed) == len(rows):
                return {**existing, "resumed": True}

    rendered = render_selected_assets(
        toolkit=toolkit, dataset_root=dataset_root, subset=subset,
        rows=rows, num_cond_views=num_cond_views,
    )
    passed, failed = rendered["assets"], rendered["failures"]
    process_error = rendered["processError"]
    result = {
        "schemaVersion": 1,
        "valid": not failed and process_error is None and len(passed) == len(rows),
        "batchIndex": batch_index,
        "batchSize": batch_size,
        "selectedCount": len(rows),
        "successfulCount": len(passed),
        "failedCount": len(failed),
        "numCondViews": num_cond_views,
        "fingerprint": fingerprint,
        "assets": passed,
        "failures": failed,
        "processError": process_error,
        "completedAt": datetime.now(timezone.utc).isoformat(),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(receipt)
    return result


def audit_receipts(
    dataset_root: Path,
    *,
    batch_size: int,
    num_cond_views: int = 24,
    max_failure_details: int = 20,
) -> dict:
    if max_failure_details < 0:
        raise ValueError("max_failure_details must be non-negative")
    rows = training_rows(dataset_root / "metadata.csv")
    total_batches = (len(rows) + batch_size - 1) // batch_size
    receipts = []
    covered = set()
    failures = []
    for index in range(total_batches):
        selected = rows[index * batch_size : (index + 1) * batch_size]
        path = receipt_path(dataset_root, index, batch_size)
        if not path.is_file():
            failures.append({"batchIndex": index, "error": "missing receipt"})
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data.get("valid") or data.get("fingerprint") != batch_fingerprint(selected, num_cond_views):
            failures.append({"batchIndex": index, "error": "invalid or stale receipt"})
            continue
        passed, artifact_failures = validate_selected(dataset_root, selected, num_cond_views)
        if artifact_failures:
            failures.append({"batchIndex": index, "error": "artifact validation failed", "assets": artifact_failures})
            continue
        covered.update(item["sha256"] for item in passed)
        receipts.append(str(path))
    return {
        "valid": not failures and len(covered) == len(rows),
        "trainingAssetCount": len(rows),
        "validatedAssetCount": len(covered),
        "totalBatches": total_batches,
        "validReceiptCount": len(receipts),
        "failureCount": len(failures),
        "failures": failures[:max_failure_details],
        "failureDetailsTruncated": len(failures) > max_failure_details,
    }
