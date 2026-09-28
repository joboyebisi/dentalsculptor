"""Shared FDI-16 archive verification, split-aware selection, and extraction."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

FDI16_URL = "https://ndownloader.figshare.com/files/44571158"
FDI16_FILE_ID = 44571158
FDI16_EXPECTED_BYTES = 7_160_405_142
FDI16_MD5 = "9824c7d342f6f13887084452d2c75c68"
FDI16_CITATION = (
    "Ye, Johan Ziruo; Ørkild, Thomas; Søndergaard, Peter Lempel; Hauberg, Søren (2023). "
    "3Shape FDI 16 Meshes from Intraoral Scans. Technical University of Denmark. "
    "https://doi.org/10.11583/DTU.23626650.v2"
)
FDI16_LICENSE = "CC-BY-NC-SA-4.0"
DATASET_ID = "fdi16-research-v2"

OFFICIAL_SPLIT_COUNTS = {"train": 4844, "validation": 1465, "test": 1423}
DEFAULT_PILOT_TARGETS = {"train": 500, "validation": 125, "test": 125}

_SPLIT_PATTERN = re.compile(
    r"(?:^|[/\\])(train(?:ing)?|validation|val|test(?:ing)?)(?:[/\\]|$)",
    re.IGNORECASE,
)
_SPLIT_ALIASES = {
    "train": "train",
    "training": "train",
    "validation": "validation",
    "val": "validation",
    "test": "test",
    "testing": "test",
}


@dataclass(frozen=True)
class MeshMember:
    filename: str
    file_size: int
    official_split: str | None


def verify_archive_md5(archive: Path, expected_md5: str = FDI16_MD5) -> str:
    digest = hashlib.md5()  # nosec B324 - publisher checksum only
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected_md5:
        raise ValueError(f"FDI-16 archive checksum mismatch: expected {expected_md5}, got {actual}")
    return actual


def infer_official_split(member_path: str) -> str | None:
    normalized = member_path.replace("\\", "/")
    match = _SPLIT_PATTERN.search(normalized)
    if not match:
        return None
    return _SPLIT_ALIASES.get(match.group(1).lower())


def list_mesh_members(bundle: zipfile.ZipFile) -> list[MeshMember]:
    members: list[MeshMember] = []
    for item in bundle.infolist():
        if not item.filename.lower().endswith("_mesh.ply"):
            continue
        members.append(MeshMember(item.filename, item.file_size, infer_official_split(item.filename)))
    return members


def pilot_targets(max_meshes: int, official_counts: dict[str, int] | None = None) -> dict[str, int]:
    if max_meshes < 500 or max_meshes > 2000:
        raise ValueError("max_meshes must be between 500 and 2000")
    if max_meshes == 750:
        return dict(DEFAULT_PILOT_TARGETS)
    counts = official_counts or OFFICIAL_SPLIT_COUNTS
    total = sum(counts.values())
    raw = {split: max_meshes * count / total for split, count in counts.items()}
    rounded = {split: int(raw[split]) for split in raw}
    remainder = max_meshes - sum(rounded.values())
    for split in sorted(raw, key=lambda name: raw[name] - rounded[name], reverse=True):
        if remainder <= 0:
            break
        rounded[split] += 1
        remainder -= 1
    return rounded


def select_stratified_members(
    members: Iterable[MeshMember],
    max_meshes: int,
    targets: dict[str, int] | None = None,
) -> list[MeshMember]:
    grouped: dict[str, list[MeshMember]] = {"train": [], "validation": [], "test": [], "unknown": []}
    for member in members:
        split = member.official_split or "unknown"
        grouped.setdefault(split, []).append(member)

    if grouped["unknown"]:
        raise ValueError(
            f"Could not infer official split for {len(grouped['unknown'])} mesh files; "
            "inspect ZIP member paths before ingestion."
        )

    desired = targets or pilot_targets(max_meshes)
    selected: list[MeshMember] = []
    for split in ("train", "validation", "test"):
        pool = sorted(grouped.get(split, []), key=lambda item: item.filename)
        need = desired[split]
        if len(pool) < need:
            raise ValueError(f"Archive split '{split}' has only {len(pool)} meshes; need {need}")
        selected.extend(pool[:need])
    if len(selected) != max_meshes:
        raise ValueError(f"Selected {len(selected)} meshes; expected {max_meshes}")
    return selected


def extract_selected_members(
    bundle: zipfile.ZipFile,
    selected: list[MeshMember],
    output: Path,
    *,
    skip_existing: bool = True,
) -> list[dict]:
    manifest_entries: list[dict] = []
    raw_dir = output / "raw_meshes"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for index, member in enumerate(selected):
        destination = raw_dir / f"{index:06d}_fdi16.ply"
        zip_member = bundle.getinfo(member.filename)
        if skip_existing and destination.is_file() and destination.stat().st_size == zip_member.file_size:
            pass
        else:
            with bundle.open(zip_member) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target, length=4 * 1024 * 1024)
        manifest_entries.append(
            {
                "index": index,
                "relativePath": destination.relative_to(output).as_posix(),
                "sourceMemberPath": member.filename.replace("\\", "/"),
                "officialSplit": member.official_split,
                "bytes": zip_member.file_size,
            }
        )
    return manifest_entries


def build_source_evidence(
    *,
    mesh_count: int,
    split_counts: dict[str, int],
    selection_manifest: list[dict],
    archive_md5: str = FDI16_MD5,
) -> dict:
    return {
        "schemaVersion": 2,
        "datasetId": DATASET_ID,
        "meshCount": mesh_count,
        "sourceUrl": FDI16_URL,
        "sourceFileId": FDI16_FILE_ID,
        "sourceBytes": FDI16_EXPECTED_BYTES,
        "sourceMd5": archive_md5,
        "license": FDI16_LICENSE,
        "researchOnly": True,
        "citation": FDI16_CITATION,
        "officialSplitCounts": OFFICIAL_SPLIT_COUNTS,
        "pilotSplitCounts": split_counts,
        "selectionManifest": selection_manifest,
    }


def ingest_from_archive(archive: Path, output: Path, max_meshes: int = 750, *, verify_md5: bool = True) -> dict:
    if verify_md5:
        verify_archive_md5(archive)
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        members = list_mesh_members(bundle)
        if len(members) < max_meshes:
            raise ValueError(f"Archive contains only {len(members)} mesh files")
        selected = select_stratified_members(members, max_meshes)
        manifest_entries = extract_selected_members(bundle, selected, output)
    split_counts = {
        split: sum(1 for item in manifest_entries if item["officialSplit"] == split)
        for split in ("train", "validation", "test")
    }
    evidence = build_source_evidence(
        mesh_count=max_meshes,
        split_counts=split_counts,
        selection_manifest=manifest_entries,
    )
    (output / "source.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (output / "selection_manifest.json").write_text(json.dumps(manifest_entries, indent=2) + "\n", encoding="utf-8")
    return evidence


def load_existing_evidence(output: Path) -> dict | None:
    source = output / "source.json"
    if not source.is_file():
        return None
    return json.loads(source.read_text(encoding="utf-8"))
