"""Teeth3DS OSF download, merge, and official split binding."""

from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

DATASET_ID = "teeth3ds-research-v1"
TEETH3DS_LICENSE = "CC-BY-NC-ND-4.0"
TEETH3DS_OSF = "https://osf.io/xctdy/"
TEETH3DS_CITATION = (
    "Ben-Hamadou et al., Teeth3DS: a benchmark for teeth segmentation and labeling from "
    "intra-oral 3D scans, arXiv:2210.06094, 2022."
)

OSF_PARTS = {
    "data_part_1": {"node": "5cmg3", "archive": "data_part_1.zip", "download": "https://osf.io/download/qhprs/"},
    "data_part_2": {"node": "xfcn9", "archive": "data_part_2.zip", "download": "https://osf.io/download/4pwnr/"},
    "data_part_3": {"node": "hw7bj", "archive": "data_part_3.zip", "download": "https://osf.io/download/frwdp/"},
    "data_part_4": {"node": "n9bd7", "archive": "data_part_4.zip", "download": "https://osf.io/download/2arn4/"},
    "data_part_5": {"node": "7az58", "archive": "data_part_5.zip", "download": "https://osf.io/download/xrz5f/"},
    "data_part_6": {"node": "2ybr4", "archive": "data_part_6.zip", "download": "https://osf.io/download/23hgq/"},
}

SPLIT_DOWNLOADS = {
    "training_upper.txt": "https://osf.io/download/zs5cg/",
    "training_lower.txt": "https://osf.io/download/zkge5/",
    "testing_upper.txt": "https://osf.io/download/c8g6u/",
    "testing_lower.txt": "https://osf.io/download/snwye/",
}


@dataclass(frozen=True)
class ScanRecord:
    scan_key: str
    patient_id: str
    jaw: str
    official_split: str


def download_file(url: str, destination: Path, *, chunk_size: int = 8 * 1024 * 1024) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "DentalSculptor/1.0"})
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            output.write(chunk)
            digest.update(chunk)
    sidecar = destination.with_suffix(destination.suffix + ".sha256")
    sidecar.write_text(digest.hexdigest() + "\n", encoding="utf-8")


def extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(destination)


def merge_extracted_parts(parts_dir: Path, merged_root: Path) -> None:
    merged_root.mkdir(parents=True, exist_ok=True)
    for part_name in OSF_PARTS:
        part_root = parts_dir / part_name
        if not part_root.is_dir():
            continue
        for path in part_root.rglob("*"):
            if path.is_dir():
                continue
            relative = path.relative_to(part_root)
            target = merged_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.stat().st_size == path.stat().st_size:
                continue
            shutil.copy2(path, target)


def load_split_keys(split_dir: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for filename, url in SPLIT_DOWNLOADS.items():
        split_path = split_dir / filename
        if not split_path.is_file():
            download_file(url, split_path)
        official = "train" if filename.startswith("training") else "test"
        for line in split_path.read_text(encoding="utf-8").splitlines():
            key = line.strip()
            if key:
                mapping[key] = official
    return mapping


def bind_official_splits(split_dir: Path, *, validation_fraction: float = 0.2) -> list[ScanRecord]:
    split_keys = load_split_keys(split_dir)
    records: list[ScanRecord] = []
    train_patients: set[str] = set()
    for scan_key, official in split_keys.items():
        patient_id, jaw = scan_key.rsplit("_", 1)
        if official == "train":
            train_patients.add(patient_id)
        records.append(ScanRecord(scan_key, patient_id, jaw, official))

    validation_patients = {
        patient
        for patient in sorted(train_patients)
        if int(hashlib.sha256(patient.encode()).hexdigest()[:8], 16) % 100 < int(validation_fraction * 100)
    }
    bound: list[ScanRecord] = []
    for record in records:
        split = record.official_split
        if split == "train" and record.patient_id in validation_patients:
            split = "validation"
        bound.append(ScanRecord(record.scan_key, record.patient_id, record.jaw, split))
    return bound


def find_scan_obj(merged_root: Path, scan_key: str) -> Path | None:
    patient_id, jaw = scan_key.rsplit("_", 1)
    jaw_title = jaw.capitalize()
    candidates = [
        merged_root / "obj" / patient_id / f"{scan_key}.obj",
        merged_root / jaw / patient_id / f"{scan_key}.obj",
        merged_root / jaw_title / patient_id / f"{scan_key}.obj",
        merged_root / "Training" / jaw_title / patient_id / f"{scan_key}.obj",
        merged_root / "Testing" / jaw_title / patient_id / f"{scan_key}.obj",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    matches = list(merged_root.rglob(f"{scan_key}.obj"))
    return matches[0] if matches else None


def build_source_evidence(output: Path, parts: list[str], merged_root: Path, scan_records: list[ScanRecord]) -> dict:
    part_digests = {}
    for part in parts:
        archive = output / "archives" / OSF_PARTS[part]["archive"]
        if archive.is_file():
            part_digests[part] = archive.with_suffix(archive.suffix + ".sha256").read_text(encoding="utf-8").strip()
    split_counts = {
        split: sum(1 for item in scan_records if item.official_split == split)
        for split in ("train", "validation", "test")
    }
    return {
        "schemaVersion": 2,
        "datasetId": DATASET_ID,
        "sourceUrl": TEETH3DS_OSF,
        "license": TEETH3DS_LICENSE,
        "researchTrainingApproved": True,
        "researchTrainingBasis": "Non-commercial academic research with attribution per Teeth3DS benchmark statement.",
        "citation": TEETH3DS_CITATION,
        "osfParts": parts,
        "partSha256": part_digests,
        "mergedRoot": str(merged_root.resolve()),
        "officialSplitName": "Teeth3DS_split",
        "scanCounts": split_counts,
    }


def ingest_parts(output: Path, parts: list[str] | None = None, *, skip_download: bool = False) -> dict:
    selected = parts or list(OSF_PARTS)
    unknown = [part for part in selected if part not in OSF_PARTS]
    if unknown:
        raise ValueError(f"Unknown OSF parts: {unknown}")

    archives_dir = output / "archives"
    extracted_dir = output / "extracted"
    merged_root = output / "merged"
    split_dir = output / "Teeth3DS_train_test_split"
    split_dir.mkdir(parents=True, exist_ok=True)

    for part in selected:
        archive_path = archives_dir / OSF_PARTS[part]["archive"]
        if not skip_download or not archive_path.is_file():
            download_file(OSF_PARTS[part]["download"], archive_path)
        extract_zip(archive_path, extracted_dir / part)

    merge_extracted_parts(extracted_dir, merged_root)
    scan_records = bind_official_splits(split_dir)
    selection_manifest = [
        {
            "scanKey": record.scan_key,
            "patientId": record.patient_id,
            "jaw": record.jaw,
            "officialSplit": record.official_split,
            "objPath": (
                find_scan_obj(merged_root, record.scan_key).relative_to(merged_root).as_posix()
                if find_scan_obj(merged_root, record.scan_key)
                else None
            ),
        }
        for record in scan_records
    ]
    evidence = build_source_evidence(output, selected, merged_root, scan_records)
    output.mkdir(parents=True, exist_ok=True)
    (output / "source.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (output / "selection_manifest.json").write_text(json.dumps(selection_manifest, indent=2) + "\n", encoding="utf-8")
    return evidence


def load_existing_evidence(output: Path) -> dict | None:
    source = output / "source.json"
    if not source.is_file():
        return None
    return json.loads(source.read_text(encoding="utf-8"))
