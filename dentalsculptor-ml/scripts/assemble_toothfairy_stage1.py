"""Assemble immutable clinical train/validation/test ToothFairy components."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assemble_stage1(components: list[Path], output: Path, *, dataset_id: str) -> dict:
    if len(components) != 3:
        raise ValueError("exactly three component roots are required")
    manifests = []
    for root in components:
        manifest_path = root / "anatomy_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not manifest.get("researchTrainingApproved") or not manifest.get("clinicalClaimPermitted"):
            raise ValueError(f"component is not clinically approved: {root}")
        manifests.append((root, manifest_path, manifest))
    observed_splits = [next(split for split, count in manifest["splits"].items() if count) for _, _, manifest in manifests]
    if set(observed_splits) != {"train", "validation", "test"}:
        raise ValueError("components must contain exactly train, validation and test")
    groups_by_split: dict[str, set[str]] = {}
    hashes: set[str] = set()
    assets = []
    component_receipts = []
    for root, manifest_path, manifest in manifests:
        split = next(split for split, count in manifest["splits"].items() if count)
        groups = {asset["groupId"] for asset in manifest["assets"]}
        groups_by_split[split] = groups
        for asset in manifest["assets"]:
            if asset["split"] != split:
                raise ValueError(f"asset split mismatch in {manifest_path}")
            digest = asset["canonicalSha256"]
            if digest in hashes:
                raise ValueError("duplicate canonical mesh hash across components")
            hashes.add(digest)
            source = root / asset["canonicalPath"]
            if sha256_file(source) != digest:
                raise ValueError(f"canonical mesh hash mismatch: {source}")
            destination = output / "meshes_canonical_mm" / split / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            assets.append({
                **asset,
                "datasetId": dataset_id,
                "canonicalPath": destination.relative_to(output).as_posix(),
            })
        component_receipts.append({
            "datasetId": manifest["datasetId"],
            "split": split,
            "assetCount": manifest["assetCount"],
            "manifestSha256": sha256_file(manifest_path),
            "sourceCohortFingerprint": manifest["sourceCohortFingerprint"],
        })
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        overlap = groups_by_split[left] & groups_by_split[right]
        if overlap:
            raise ValueError(f"patient leakage between {left} and {right}: {sorted(overlap)}")
    split_counts = Counter(asset["split"] for asset in assets)
    family_by_split = {
        split: dict(Counter(asset["toothFamily"] for asset in assets if asset["split"] == split))
        for split in ("train", "validation", "test")
    }
    result = {
        "schemaVersion": 2,
        "datasetId": dataset_id,
        "license": "ToothFairy2 challenge research terms; verify redistribution before release",
        "researchTrainingApproved": True,
        "trainingPurpose": "registered-stage1",
        "clinicalClaimPermitted": True,
        "assetCount": len(assets),
        "subjectCount": len(set().union(*groups_by_split.values())),
        "splits": {split: split_counts[split] for split in ("train", "validation", "test")},
        "familyCounts": dict(Counter(asset["toothFamily"] for asset in assets)),
        "familyCountsBySplit": family_by_split,
        "componentReceipts": component_receipts,
        "assets": assets,
    }
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "anatomy_manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schemaVersion": 1,
        "stage": "assembled-clinical-stage1-dataset",
        "datasetId": dataset_id,
        "manifestSha256": sha256_file(manifest_path),
        "assetCount": len(assets),
        "splitCounts": result["splits"],
        "patientLeakageCount": 0,
        "allCanonicalHashesVerified": True,
        "optimizerPermitted": False,
    }
    (output / "assembly_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-id", required=True)
    args = parser.parse_args()
    result = assemble_stage1(args.component, args.output, dataset_id=args.dataset_id)
    print(json.dumps({key: result[key] for key in (
        "datasetId", "assetCount", "subjectCount", "splits",
        "familyCountsBySplit", "researchTrainingApproved",
    )}, indent=2))


if __name__ == "__main__":
    main()
