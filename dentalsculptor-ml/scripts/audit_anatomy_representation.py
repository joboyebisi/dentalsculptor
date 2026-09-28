"""Audit crown-only versus whole-tooth supervision without inferring missing anatomy."""

from __future__ import annotations

import json
import argparse
from collections import Counter, defaultdict
from pathlib import Path

try:
    from scripts.build_anatomy_spike_manifest import FAMILIES, representation_scope
except ModuleNotFoundError:  # direct script execution
    from build_anatomy_spike_manifest import FAMILIES, representation_scope


def audit_representations(manifest_path: Path, output_path: Path) -> dict:
    source = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = source.get("assets", [])
    by_family: dict[str, Counter] = defaultdict(Counter)
    by_source: dict[str, Counter] = defaultdict(Counter)
    by_split: dict[str, Counter] = defaultdict(Counter)
    review = Counter()
    unknown = []
    for asset in assets:
        scope = representation_scope(asset)
        family = asset.get("toothFamily", "unknown")
        source_name = asset.get("source", "unknown")
        split = asset.get("split", "unknown")
        by_family[family][scope] += 1
        by_source[source_name][scope] += 1
        by_split[split][scope] += 1
        review["required" if asset.get("reviewRequired") else "notRequired"] += 1
        if scope == "unknown":
            unknown.append({"id": asset.get("id"), "source": source_name})
    train_whole_families = {
        family: by_family[family]["whole-tooth"]
        for family in FAMILIES
    }
    result = {
        "schemaVersion": 1,
        "datasetId": source.get("datasetId"),
        "assetCount": len(assets),
        "byFamily": {key: dict(value) for key, value in sorted(by_family.items())},
        "bySource": {key: dict(value) for key, value in sorted(by_source.items())},
        "bySplit": {key: dict(value) for key, value in sorted(by_split.items())},
        "reviewCounts": dict(review),
        "unknownScopeCount": len(unknown),
        "unknownScopeExamples": unknown[:20],
        "wholeToothCoverageByFamily": train_whole_families,
        "wholeToothAllFamilyTrainingReady": all(value > 0 for value in train_whole_families.values()),
        "interpretation": (
            "Crown-only records supervise external crown morphology but cannot supervise roots. "
            "Whole-tooth deployment requires explicit root non-regression evaluation."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_representations(args.manifest, args.output), indent=2))


if __name__ == "__main__":
    main()
