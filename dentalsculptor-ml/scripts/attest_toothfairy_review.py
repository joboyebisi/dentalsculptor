"""Record an explicit reviewer attestation without modifying the blank form."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def attest_all(
    queue_path: Path, blank_form_path: Path, output_form_path: Path,
    receipt_path: Path, *, reviewer: str, explicit_accept_all: bool,
) -> dict:
    if not explicit_accept_all:
        raise ValueError("explicit_accept_all must be true")
    reviewer = reviewer.strip()
    if not reviewer:
        raise ValueError("reviewer is required")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    with blank_form_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if len(rows) != len(queue["records"]):
        raise ValueError("blank form and queue row counts differ")
    queue_by_id = {record["id"]: record for record in queue["records"]}
    if {row["id"] for row in rows} != set(queue_by_id):
        raise ValueError("blank form IDs do not match the immutable queue")
    for row in rows:
        record = queue_by_id[row["id"]]
        if record["automaticGate"] != "eligible-for-clinical-review":
            raise ValueError(f"accept-all cannot override quarantined asset {row['id']}")
        row.update({
            "reviewer": reviewer,
            "status": "accepted",
            "toothIdentityCorrect": "true",
            "crownComplete": "true",
            "rootAndApexComplete": "true",
            "segmentationLeakage": "false",
            "artifactSeverity": "none",
            "notes": "",
        })
    output_form_path.parent.mkdir(parents=True, exist_ok=True)
    with output_form_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    receipt = {
        "schemaVersion": 1,
        "action": "explicit-human-review-attestation",
        "reviewer": reviewer,
        "decision": "accept-all",
        "assetCount": len(rows),
        "assertions": {
            "toothIdentityCorrect": True,
            "crownComplete": True,
            "rootAndApexComplete": True,
            "segmentationLeakage": False,
            "artifactSeverity": "none",
        },
        "queueSha256": sha256_file(queue_path),
        "blankFormSha256": sha256_file(blank_form_path),
        "attestedFormSha256": sha256_file(output_form_path),
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--blank-form", type=Path, required=True)
    parser.add_argument("--output-form", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--accept-all", action="store_true")
    args = parser.parse_args()
    receipt = attest_all(
        args.queue, args.blank_form, args.output_form, args.receipt,
        reviewer=args.reviewer, explicit_accept_all=args.accept_all,
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
