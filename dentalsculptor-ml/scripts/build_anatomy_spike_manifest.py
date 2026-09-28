"""Build a deterministic, leakage-safe, family-balanced pre-audit spike cohort."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

FAMILIES = ("incisor", "canine", "premolar", "molar")
ALLOWED_ROLES = {"healthy-base", "anatomy-base"}


def representation_scope(asset: dict) -> str:
    source = str(asset.get("source", "")).lower()
    if "teeth3ds" in source:
        return "crown-only"
    if "fdi16" in source or "fdi-16" in source:
        return "whole-tooth"
    return "unknown"


def _score(asset: dict, seed: int) -> str:
    payload = f"{seed}:{asset['toothFamily']}:{asset['groupId']}:{asset['canonicalSha256']}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_spike_manifest(
    anatomy_manifest_path: Path,
    reference_manifest_path: Path,
    output_path: Path,
    *,
    per_family: int = 125,
    seed: int = 20260918,
    maximum_per_group: int = 4,
) -> dict:
    if per_family < 1:
        raise ValueError("per_family must be positive")
    if maximum_per_group < 1:
        raise ValueError("maximum_per_group must be positive")
    source = json.loads(anatomy_manifest_path.read_text(encoding="utf-8"))
    reference = json.loads(reference_manifest_path.read_text(encoding="utf-8"))
    reference_hashes = {item["canonicalSha256"] for item in reference.get("items", [])}
    reference_groups = {item["groupId"] for item in reference.get("items", [])}
    selected: list[dict] = []
    group_counts: Counter[str] = Counter()

    for family in FAMILIES:
        candidates = [
            asset for asset in source.get("assets", [])
            if asset.get("split") == "train"
            and asset.get("toothFamily") == family
            and asset.get("trainingRole") in ALLOWED_ROLES
            and asset.get("canonicalSha256") not in reference_hashes
            and asset.get("groupId") not in reference_groups
        ]
        candidates.sort(key=lambda asset: _score(asset, seed))
        family_selection = []
        for asset in candidates:
            group = asset["groupId"]
            if group_counts[group] >= maximum_per_group:
                continue
            family_selection.append(asset)
            group_counts[group] += 1
            if len(family_selection) == per_family:
                break
        if len(family_selection) != per_family:
            raise ValueError(
                f"Need {per_family} eligible {family} assets; selected {len(family_selection)} "
                f"with maximum_per_group={maximum_per_group}."
            )
        selected.extend(family_selection)

    items = []
    for asset in selected:
        scope = representation_scope(asset)
        items.append({
            "id": asset["id"],
            "canonicalSha256": asset["canonicalSha256"],
            "groupId": asset["groupId"],
            "source": asset.get("source"),
            "sourceSplit": asset["split"],
            "referenceMesh": asset["canonicalPath"],
            "fdiNumber": asset.get("fdiNumber"),
            "toothFamily": asset["toothFamily"],
            "arch": asset.get("arch"),
            "side": asset.get("side"),
            "trainingRole": asset.get("trainingRole"),
            "representationScope": scope,
            "rootSupervision": scope == "whole-tooth",
            "sourceReviewRequired": bool(asset.get("reviewRequired")),
            "sourceReviewFlags": asset.get("reviewFlags", []),
            "clinicalAudit": {"status": "pending", "reviewer": None, "exclusionReason": None},
        })

    family_counts = Counter(item["toothFamily"] for item in items)
    scope_counts = Counter(item["representationScope"] for item in items)
    result = {
        "schemaVersion": 1,
        "cohortId": "dental-anatomy-spike-500-v1",
        "datasetId": source.get("datasetId"),
        "selectionSeed": seed,
        "optimizerSplit": "train-only",
        "referenceExcluded": True,
        "clinicalAuditStatus": "pending",
        "perFamily": per_family,
        "maximumPerGroup": maximum_per_group,
        "caseCount": len(items),
        "uniqueGroupCount": len(group_counts),
        "familyCounts": {family: family_counts[family] for family in FAMILIES},
        "representationScopeCounts": dict(scope_counts),
        "rootSupervisionCount": sum(bool(item["rootSupervision"]) for item in items),
        "items": items,
    }
    fingerprint_payload = json.dumps(
        [(item["canonicalSha256"], item["groupId"]) for item in items],
        separators=(",", ":"),
    )
    result["selectionFingerprint"] = hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
