"""Build nested whole-tooth cohorts for a smallest-sufficient-dataset study."""

from __future__ import annotations

import hashlib
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

FAMILIES = ("incisor", "canine", "premolar", "molar")
QUADRANTS = (1, 2, 3, 4)


def _rank(asset: dict, seed: int) -> str:
    value = f"{seed}:{asset['groupId']}:{asset['fdiNumber']}:{asset['rawMeshSha256']}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_nested_cohorts(
    manifest_path: Path,
    output_path: Path,
    *,
    sizes: tuple[int, ...] = (32, 64, 128, 256, 500),
    seed: int = 20260918,
    maximum_per_subject: int = 4,
    admission_mode: str = "clinical",
    eligible_split: str = "train",
) -> dict:
    """Select deterministic, nested, family-balanced, train-only cohorts.

    Only clinically accepted, apex-complete assets are admissible.  Selection is
    round-robin by family so each prefix remains as balanced as the target size
    permits. A subject cap prevents one CBCT volume dominating the experiment.
    """
    if tuple(sorted(set(sizes))) != sizes or not sizes or sizes[0] < 4:
        raise ValueError("sizes must be unique, ascending, and at least four")
    source = json.loads(manifest_path.read_text(encoding="utf-8"))
    if admission_mode not in {"clinical", "mechanical-provisional"}:
        raise ValueError("admission_mode must be clinical or mechanical-provisional")
    def admissible(asset: dict) -> bool:
        common = (
            asset.get("split") == eligible_split
            and asset.get("representationScope") == "whole-tooth"
            and int(asset.get("fdiNumber", 0)) % 10 != 8
        )
        if not common:
            return False
        if admission_mode == "clinical":
            return (
                asset.get("clinicalAudit", {}).get("status") == "accepted"
                and asset.get("rootCompleteness") == "accepted-complete"
            )
        return (
            not asset.get("touchesVolumeBoundary", False)
            and "non-watertight-extracted-surface" not in asset.get("reviewFlags", [])
        )
    eligible = [asset for asset in source.get("assets", []) if admissible(asset)]
    by_stratum = defaultdict(list)
    for asset in eligible:
        by_stratum[(asset["toothFamily"], int(asset["fdiNumber"]) // 10)].append(asset)
    for family in FAMILIES:
        for quadrant in QUADRANTS:
            by_stratum[(family, quadrant)].sort(key=lambda asset: _rank(asset, seed))

    selected = []
    selected_hashes = set()
    subject_counts: Counter[str] = Counter()
    cursors = Counter()
    family_pick_counts = Counter()
    while len(selected) < sizes[-1]:
        made_progress = False
        for family in FAMILIES:
            preferred = family_pick_counts[family] % len(QUADRANTS)
            picked = False
            for offset in range(len(QUADRANTS)):
                quadrant = QUADRANTS[(preferred + offset) % len(QUADRANTS)]
                stratum = (family, quadrant)
                candidates = by_stratum[stratum]
                while cursors[stratum] < len(candidates):
                    asset = candidates[cursors[stratum]]
                    cursors[stratum] += 1
                    if asset["rawMeshSha256"] in selected_hashes:
                        continue
                    if subject_counts[asset["groupId"]] >= maximum_per_subject:
                        continue
                    selected.append(asset)
                    selected_hashes.add(asset["rawMeshSha256"])
                    subject_counts[asset["groupId"]] += 1
                    family_pick_counts[family] += 1
                    made_progress = True
                    picked = True
                    break
                if picked:
                    break
            if len(selected) == sizes[-1]:
                break
        if not made_progress:
            break
    if len(selected) < sizes[-1]:
        counts = Counter(asset["toothFamily"] for asset in selected)
        raise ValueError(
            f"Only {len(selected)} {admission_mode} assets available for S{sizes[-1]}: {dict(counts)}"
        )

    cohorts = []
    previous = set()
    for size in sizes:
        items = selected[:size]
        hashes = {item["rawMeshSha256"] for item in items}
        if not previous.issubset(hashes):
            raise AssertionError("Cohorts are not nested")
        previous = hashes
        fingerprint = hashlib.sha256(
            json.dumps(sorted(hashes), separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        cohorts.append({
            "cohortId": (
                f"TF-{'W' if eligible_split == 'train' else 'V' if eligible_split == 'validation' else 'T'}{size}"
                if admission_mode == "clinical"
                else f"TF-P{'W' if eligible_split == 'train' else 'V' if eligible_split == 'validation' else 'T'}{size}"
            ),
            "size": size,
            "familyCounts": dict(Counter(item["toothFamily"] for item in items)),
            "subjectCount": len({item["groupId"] for item in items}),
            "quadrantCounts": dict(Counter(str(item["fdiNumber"] // 10) for item in items)),
            "fingerprint": fingerprint,
            "items": [{
                "id": item["id"], "groupId": item["groupId"],
                "fdiNumber": item["fdiNumber"], "toothFamily": item["toothFamily"],
                "rawMeshSha256": item["rawMeshSha256"], "rawMeshPath": item["rawMeshPath"],
            } for item in items],
        })
    result = {
        "schemaVersion": 1,
        "studyId": "toothfairy-minimal-sufficient-whole-tooth-v1",
        "selectionSeed": seed,
        "selectionPolicy": "nested-family-and-fdi-quadrant-round-robin-with-subject-cap",
        "maximumPerSubject": maximum_per_subject,
        "admissionMode": admission_mode,
        "eligibleSplit": eligible_split,
        "clinicalClaimPermitted": admission_mode == "clinical",
        "trainingPurpose": "registered-study" if admission_mode == "clinical" else "engineering-smoke-only",
        "eligibility": (
            [eligible_split, "whole-tooth", "clinical-audit-accepted", "root-complete", "exclude-third-molars"]
            if admission_mode == "clinical"
            else [eligible_split, "whole-tooth", "no-boundary-contact", "watertight", "exclude-third-molars", "unreviewed"]
        ),
        "cohorts": cohorts,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sizes", type=int, nargs="+", default=[32, 64, 128, 256, 500])
    parser.add_argument("--seed", type=int, default=20260918)
    parser.add_argument("--maximum-per-subject", type=int, default=4)
    parser.add_argument("--admission-mode", choices=("clinical", "mechanical-provisional"), default="clinical")
    parser.add_argument("--eligible-split", choices=("train", "validation", "test"), default="train")
    args = parser.parse_args()
    result = build_nested_cohorts(
        args.manifest, args.output, sizes=tuple(args.sizes), seed=args.seed,
        maximum_per_subject=args.maximum_per_subject, admission_mode=args.admission_mode,
        eligible_split=args.eligible_split,
    )
    print(json.dumps({
        "admissionMode": result["admissionMode"],
        "clinicalClaimPermitted": result["clinicalClaimPermitted"],
        "cohorts": [{key: cohort[key] for key in (
            "cohortId", "size", "familyCounts", "quadrantCounts", "subjectCount", "fingerprint"
        )} for cohort in result["cohorts"]],
    }, indent=2))


if __name__ == "__main__":
    main()
