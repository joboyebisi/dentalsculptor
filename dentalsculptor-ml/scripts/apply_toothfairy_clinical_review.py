"""Validate clinical-review decisions and produce an audited ToothFairy manifest."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


TRUE_VALUES = {"true", "yes", "1"}
FALSE_VALUES = {"false", "no", "0"}


def parse_bool(value: str, field: str) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"{field} must be true or false")


def validate_decision(row: dict) -> dict:
    status = row["status"].strip().lower()
    if status not in {"accepted", "rejected"}:
        raise ValueError("status must be accepted or rejected")
    reviewer = row["reviewer"].strip()
    if not reviewer:
        raise ValueError("reviewer is required")
    identity = parse_bool(row["toothIdentityCorrect"], "toothIdentityCorrect")
    crown = parse_bool(row["crownComplete"], "crownComplete")
    root = parse_bool(row["rootAndApexComplete"], "rootAndApexComplete")
    leakage = parse_bool(row["segmentationLeakage"], "segmentationLeakage")
    severity = row["artifactSeverity"].strip().lower()
    if severity not in {"none", "mild", "moderate", "severe"}:
        raise ValueError("artifactSeverity must be none, mild, moderate or severe")
    acceptance_conditions = identity and crown and root and not leakage and severity in {"none", "mild"}
    if status == "accepted" and not acceptance_conditions:
        raise ValueError("accepted row does not satisfy the registered anatomy gates")
    notes = row["notes"].strip()
    if (status == "rejected" or severity != "none") and not notes:
        raise ValueError("notes are required for rejections and non-none artifacts")
    return {
        "status": status,
        "reviewer": reviewer,
        "toothIdentityCorrect": identity,
        "crownComplete": crown,
        "rootAndApexComplete": root,
        "segmentationLeakage": leakage,
        "artifactSeverity": severity,
        "notes": notes or None,
    }


def apply_review(queue_path: Path, form_path: Path, output: Path, *, require_complete: bool) -> dict:
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    records = {record["id"]: record for record in queue["records"]}
    with form_path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(records) or {row["id"] for row in rows} != set(records):
        raise ValueError("review form IDs must match the immutable queue exactly")
    decisions = {}
    pending = []
    for row in rows:
        record = records[row["id"]]
        if record["automaticGate"] == "quarantined":
            if row["status"].strip().lower() != "automatically-excluded":
                raise ValueError(f"quarantined row cannot be overridden: {row['id']}")
            continue
        if row["status"].strip().lower() == "pending":
            pending.append(row["id"])
            continue
        decisions[row["id"]] = validate_decision(row)
    if require_complete and pending:
        raise ValueError(f"clinical review is incomplete: {len(pending)} rows remain pending")
    audited = []
    for record in queue["records"]:
        decision = decisions.get(record["id"], record["clinicalAudit"])
        audited.append({**record, "clinicalAudit": decision})
    accepted = [record for record in audited if record["clinicalAudit"]["status"] == "accepted"]
    result = {
        "schemaVersion": 1,
        "datasetId": queue["datasetId"],
        "sourceQueue": queue_path.as_posix(),
        "complete": not pending,
        "acceptedCount": len(accepted),
        "rejectedCount": sum(record["clinicalAudit"]["status"] == "rejected" for record in audited),
        "automaticExclusionCount": sum(
            record["clinicalAudit"]["status"] == "automatically-excluded" for record in audited
        ),
        "pendingCount": len(pending),
        "researchTrainingApproved": not pending and bool(accepted),
        "assets": audited,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--form", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = apply_review(
        args.queue, args.form, args.output, require_complete=args.require_complete
    )
    print(json.dumps({key: result[key] for key in (
        "complete", "acceptedCount", "rejectedCount", "automaticExclusionCount",
        "pendingCount", "researchTrainingApproved",
    )}, indent=2))


if __name__ == "__main__":
    main()
