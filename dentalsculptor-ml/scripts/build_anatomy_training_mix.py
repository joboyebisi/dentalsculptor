"""Build a balanced, leakage-safe external tooth-anatomy training index."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

FAMILIES = ("incisor", "canine", "premolar", "molar")


def is_anatomy_training_asset(item: dict) -> bool:
    """Admit verified healthy bases and diagnosis-neutral anatomy bases."""
    role = item.get("trainingRole")
    condition = item.get("condition")
    return (role == "healthy-base" and condition == "healthy") or (
        role == "anatomy-base" and condition == "unspecified"
    )


def build_mix(manifest_paths: list[Path], minimum_per_family: int, maximum_per_fdi: int) -> dict:
    assets = []
    seen_hashes, group_splits = set(), {}
    for manifest_path in manifest_paths:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not manifest.get("researchTrainingApproved", False):
            raise ValueError(f"Manifest is not explicitly approved for research training: {manifest_path}")
        for item in manifest["assets"]:
            if not is_anatomy_training_asset(item):
                continue
            digest = item["canonicalSha256"]
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            global_group = f"{manifest['datasetId']}:{item['groupId']}"
            prior_split = group_splits.setdefault(global_group, item["split"])
            if prior_split != item["split"]:
                raise ValueError(f"Subject leakage across splits: {global_group}")
            assets.append({**item, "datasetId": manifest["datasetId"], "globalGroupId": global_group,
                           "manifestPath": str(manifest_path.resolve())})
    counts = Counter(item["toothFamily"] for item in assets if item["split"] == "train")
    missing = {family: minimum_per_family - counts[family] for family in FAMILIES if counts[family] < minimum_per_family}
    if missing:
        raise ValueError(f"Insufficient anatomy training coverage: {missing}")
    buckets = defaultdict(list)
    for item in assets:
        buckets[(item["split"], int(item["fdiNumber"]))].append(item)
    selected = []
    for key in sorted(buckets):
        selected.extend(sorted(buckets[key], key=lambda item: item["canonicalSha256"])[:maximum_per_fdi])
    return {"schemaVersion": 1, "kind": "balanced-dental-anatomy-mix", "assetCount": len(selected),
            "minimumPerFamily": minimum_per_family, "maximumPerFdi": maximum_per_fdi,
            "trainFamilyCounts": dict(Counter(item["toothFamily"] for item in selected if item["split"] == "train")),
            "trainRoleCounts": dict(Counter(item["trainingRole"] for item in selected if item["split"] == "train")),
            "trainFdiCounts": dict(Counter(str(item["fdiNumber"]) for item in selected if item["split"] == "train")),
            "assets": selected}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-per-family", type=int, default=100)
    parser.add_argument("--maximum-per-fdi", type=int, default=750)
    args = parser.parse_args()
    result = build_mix(args.manifest, args.minimum_per_family, args.maximum_per_fdi)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("assetCount", "trainFamilyCounts", "trainFdiCounts")}, indent=2))


if __name__ == "__main__":
    main()
