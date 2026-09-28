"""Create an immutable extraction-style manifest for a provisional review cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def build_review_subset(
    source_manifest_path: Path,
    cohorts_path: Path,
    output_path: Path,
    *,
    cohort_id: str,
) -> dict:
    source = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    cohorts = json.loads(cohorts_path.read_text(encoding="utf-8"))
    if cohorts.get("admissionMode") != "mechanical-provisional":
        raise ValueError("review subsets must start from a mechanical-provisional cohort")
    matches = [item for item in cohorts.get("cohorts", []) if item.get("cohortId") == cohort_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one cohort named {cohort_id}")
    cohort = matches[0]
    source_by_id = {asset["id"]: asset for asset in source.get("assets", [])}
    if len(source_by_id) != len(source.get("assets", [])):
        raise ValueError("source manifest contains duplicate asset IDs")
    selected = []
    seen_ids: set[str] = set()
    for item in cohort.get("items", []):
        asset_id = item["id"]
        if asset_id in seen_ids:
            raise ValueError(f"duplicate cohort asset ID: {asset_id}")
        seen_ids.add(asset_id)
        asset = source_by_id.get(asset_id)
        if asset is None:
            raise ValueError(f"cohort asset is absent from source manifest: {asset_id}")
        if asset.get("rawMeshSha256") != item.get("rawMeshSha256"):
            raise ValueError(f"source hash mismatch for {asset_id}")
        selected.append(asset)
    if len(selected) != int(cohort.get("size", -1)):
        raise ValueError("cohort size does not match its item count")
    source_manifest_sha = hashlib.sha256(source_manifest_path.read_bytes()).hexdigest()
    cohorts_sha = hashlib.sha256(cohorts_path.read_bytes()).hexdigest()
    result = {
        "schemaVersion": 1,
        "datasetId": f"toothfairy2-{cohort_id.lower()}-clinical-review-v1",
        "sourceDatasetId": source.get("datasetId"),
        "sourceManifestPath": source_manifest_path.as_posix(),
        "sourceManifestSha256": source_manifest_sha,
        "sourceCohortsPath": cohorts_path.as_posix(),
        "sourceCohortsSha256": cohorts_sha,
        "cohortId": cohort_id,
        "cohortFingerprint": cohort.get("fingerprint"),
        "selectionSeed": cohorts.get("selectionSeed"),
        "maximumPerSubject": cohorts.get("maximumPerSubject"),
        "clinicalAuditStatus": "pending-human-review",
        "researchTrainingApproved": False,
        "clinicalClaimPermitted": False,
        "assetCount": len(selected),
        "subjectCount": len({asset["groupId"] for asset in selected}),
        "familyCounts": dict(Counter(asset["toothFamily"] for asset in selected)),
        "quadrantCounts": dict(Counter(str(int(asset["fdiNumber"]) // 10) for asset in selected)),
        "assets": selected,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--cohorts", type=Path, required=True)
    parser.add_argument("--cohort-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_review_subset(
        args.source_manifest, args.cohorts, args.output, cohort_id=args.cohort_id,
    )
    print(json.dumps({key: result[key] for key in (
        "datasetId", "cohortId", "cohortFingerprint", "assetCount",
        "subjectCount", "familyCounts", "quadrantCounts", "clinicalAuditStatus",
    )}, indent=2))


if __name__ == "__main__":
    main()
