"""Merge validated review decisions into the extraction-style source manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def merge_audit(source_path: Path, audited_path: Path, output_path: Path) -> dict:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    audited = json.loads(audited_path.read_text(encoding="utf-8"))
    if not audited.get("complete") or not audited.get("researchTrainingApproved"):
        raise ValueError("clinical audit must be complete and training-approved")
    decisions = {asset["id"]: asset["clinicalAudit"] for asset in audited.get("assets", [])}
    if len(decisions) != len(audited.get("assets", [])):
        raise ValueError("audited manifest contains duplicate IDs")
    merged = []
    for asset in source.get("assets", []):
        decision = decisions.get(asset["id"])
        if decision is None:
            continue
        status = decision.get("status")
        merged.append({
            **asset,
            "clinicalAudit": decision,
            "rootCompleteness": "accepted-complete" if status == "accepted" else "clinically-rejected",
            "reviewRequired": False,
        })
    if len(merged) != len(decisions):
        raise ValueError("audited IDs do not match the source review subset")
    accepted = [asset for asset in merged if asset["clinicalAudit"]["status"] == "accepted"]
    result = {
        "schemaVersion": 1,
        "datasetId": source.get("datasetId"),
        "sourceManifestSha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "sourceAuditSha256": hashlib.sha256(audited_path.read_bytes()).hexdigest(),
        "clinicalAuditStatus": "complete",
        "researchTrainingApproved": bool(accepted),
        "assetCount": len(merged),
        "acceptedCount": len(accepted),
        "rejectedCount": len(merged) - len(accepted),
        "familyCountsAccepted": dict(Counter(asset["toothFamily"] for asset in accepted)),
        "assets": merged,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = merge_audit(args.source, args.audit, args.output)
    print(json.dumps({key: result[key] for key in (
        "clinicalAuditStatus", "researchTrainingApproved", "assetCount",
        "acceptedCount", "rejectedCount", "familyCountsAccepted",
    )}, indent=2))


if __name__ == "__main__":
    main()
