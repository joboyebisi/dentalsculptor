"""Shared anatomy helpers for dental dataset ingestion."""

from __future__ import annotations

import hashlib


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tooth_family(fdi: int) -> str:
    quadrant = fdi // 10
    position = fdi % 10
    if quadrant not in {1, 2, 3, 4} or position not in range(1, 9):
        raise ValueError(f"Invalid permanent FDI number: {fdi}")
    if position <= 2:
        return "incisor"
    if position == 3:
        return "canine"
    if position <= 5:
        return "premolar"
    return "molar"


def arch_side(fdi: int) -> tuple[str, str]:
    return ("upper" if fdi // 10 in {1, 2} else "lower", "right" if fdi // 10 in {1, 4} else "left")


def stable_validation_bucket(group_id: str) -> bool:
    bucket = int(hashlib.sha256(group_id.encode()).hexdigest()[:8], 16) % 100
    return bucket < 20
