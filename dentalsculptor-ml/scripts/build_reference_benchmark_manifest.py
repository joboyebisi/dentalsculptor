"""Select a deterministic, family-balanced reference-mesh benchmark cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

FAMILIES = ("incisor", "canine", "premolar", "molar")


def build_reference_manifest(
    anatomy_manifest_path: Path,
    output_path: Path,
    *,
    per_family: int = 8,
    seed: int = 20260915,
) -> dict:
    source = json.loads(anatomy_manifest_path.read_text(encoding="utf-8"))
    assets = source.get("assets", [])
    train_hashes = {a["canonicalSha256"] for a in assets if a.get("split") == "train"}
    train_groups = {a["groupId"] for a in assets if a.get("split") == "train"}
    selected: list[dict] = []
    used_groups: set[str] = set()

    for family in FAMILIES:
        candidates = [
            asset for asset in assets
            if asset.get("split") in {"validation", "test"}
            and asset.get("toothFamily") == family
            and asset.get("canonicalSha256") not in train_hashes
            and asset.get("groupId") not in train_groups
        ]
        candidates.sort(key=lambda asset: hashlib.sha256(
            f"{seed}:{family}:{asset['groupId']}:{asset['canonicalSha256']}".encode()
        ).hexdigest())
        family_selection = []
        for asset in candidates:
            if asset["groupId"] in used_groups:
                continue
            family_selection.append(asset)
            used_groups.add(asset["groupId"])
            if len(family_selection) == per_family:
                break
        if len(family_selection) != per_family:
            raise ValueError(
                f"Need {per_family} held-out groups for {family}; found {len(family_selection)}."
            )
        selected.extend(family_selection)

    items = [{
        "id": asset["id"],
        "toothFamily": asset["toothFamily"],
        "fdiNumber": asset.get("fdiNumber"),
        "groupId": asset["groupId"],
        "sourceSplit": asset["split"],
        "referenceMesh": asset["canonicalPath"],
        "canonicalSha256": asset["canonicalSha256"],
        "source": asset.get("source"),
        "predictions": {},
    } for asset in selected]
    counts = Counter(item["toothFamily"] for item in items)
    result = {
        "schemaVersion": 1,
        "benchmarkId": "dentalsculptor-external-anatomy-v1",
        "datasetId": source.get("datasetId"),
        "selectionSeed": seed,
        "sealedAtSelection": True,
        "optimizerExcluded": True,
        "caseCount": len(items),
        "familyCounts": {family: counts[family] for family in FAMILIES},
        "items": items,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anatomy-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--per-family", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260915)
    args = parser.parse_args()
    print(json.dumps(build_reference_manifest(
        args.anatomy_manifest, args.output, per_family=args.per_family, seed=args.seed
    ), indent=2))


if __name__ == "__main__":
    main()
