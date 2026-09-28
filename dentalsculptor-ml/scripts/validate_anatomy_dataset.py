"""Fail-closed validation for an assembled external tooth-anatomy dataset."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

FAMILIES = ("incisor", "canine", "premolar", "molar")
ALLOWED_ROLE_CONDITION = {
    "healthy-base": "healthy",
    "anatomy-base": "unspecified",
}


def validate_dataset(
    manifest_path: Path,
    *,
    expected_dataset_id: str | None = None,
    minimum_per_family: int = 100,
    require_files: bool = True,
) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("Anatomy manifest has no assets.")
    if expected_dataset_id and manifest.get("datasetId") != expected_dataset_id:
        errors.append(f"datasetId must be {expected_dataset_id!r}")
    if not manifest.get("researchTrainingApproved", False):
        errors.append("researchTrainingApproved must be true")
    if manifest.get("assetCount") != len(assets):
        errors.append("assetCount does not match assets length")

    hashes: set[str] = set()
    group_splits: dict[str, str] = {}
    split_counts: Counter[str] = Counter()
    train_family_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    missing_files = 0
    root = manifest_path.parent

    for index, asset in enumerate(assets):
        label = str(asset.get("id") or index)
        split = asset.get("split")
        if split not in {"train", "validation", "test"}:
            errors.append(f"{label}: invalid split {split!r}")
        split_counts[str(split)] += 1
        digest = asset.get("canonicalSha256")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append(f"{label}: invalid canonicalSha256")
        elif digest in hashes:
            errors.append(f"{label}: duplicate canonicalSha256")
        else:
            hashes.add(digest)
        group_id = asset.get("groupId")
        if not group_id:
            errors.append(f"{label}: missing groupId")
        elif group_id in group_splits and group_splits[group_id] != split:
            errors.append(f"{label}: groupId leaks across splits")
        else:
            group_splits[str(group_id)] = str(split)

        family = asset.get("toothFamily")
        if family not in FAMILIES:
            errors.append(f"{label}: invalid toothFamily {family!r}")
        if split == "train" and family in FAMILIES:
            train_family_counts[str(family)] += 1
        role = asset.get("trainingRole")
        condition = asset.get("condition")
        if role not in ALLOWED_ROLE_CONDITION:
            errors.append(f"{label}: pathology or unsupported trainingRole {role!r}")
        elif condition != ALLOWED_ROLE_CONDITION[role]:
            errors.append(f"{label}: {role!r} requires condition {ALLOWED_ROLE_CONDITION[role]!r}")
        role_counts[str(role)] += 1
        if require_files:
            relative = asset.get("canonicalPath")
            if not relative or not (root / str(relative)).is_file():
                missing_files += 1

    for family in FAMILIES:
        if train_family_counts[family] < minimum_per_family:
            errors.append(
                f"train family {family!r} has {train_family_counts[family]} assets; "
                f"minimum is {minimum_per_family}"
            )
    if require_files and missing_files:
        errors.append(f"{missing_files} canonical mesh files are missing")
    declared_splits = manifest.get("splits") or {}
    for split in ("train", "validation", "test"):
        if declared_splits.get(split, 0) != split_counts[split]:
            errors.append(f"declared split count for {split!r} is incorrect")
    if errors:
        preview = "; ".join(errors[:12])
        suffix = f"; plus {len(errors) - 12} more" if len(errors) > 12 else ""
        raise ValueError(f"Anatomy dataset validation failed: {preview}{suffix}")
    return {
        "datasetId": manifest.get("datasetId"),
        "assetCount": len(assets),
        "splits": dict(split_counts),
        "trainFamilyCounts": {family: train_family_counts[family] for family in FAMILIES},
        "roleCounts": dict(role_counts),
        "uniqueGroups": len(group_splits),
        "uniqueMeshes": len(hashes),
        "valid": True,
    }
