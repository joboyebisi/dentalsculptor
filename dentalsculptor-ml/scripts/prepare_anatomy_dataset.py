"""Validate and canonicalise licensed FDI-labelled meshes for dental fine-tuning."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

ALLOWED_CONDITIONS = {"healthy", "caries", "fracture", "wear", "restoration", "preparation"}


def tooth_family(fdi: int) -> str:
    position = fdi % 10
    if fdi // 10 not in {1, 2, 3, 4} or position not in range(1, 9):
        raise ValueError(f"Invalid permanent FDI number: {fdi}")
    return "incisor" if position <= 2 else "canine" if position == 3 else "premolar" if position <= 5 else "molar"


def vector(row: dict[str, str], prefix: str) -> np.ndarray:
    value = np.array([float(row[f"{prefix}_{axis}"]) for axis in "xyz"], dtype=float)
    length = float(np.linalg.norm(value))
    if length < 1e-8:
        raise ValueError(f"{prefix} must be a non-zero vector")
    return value / length


def canonical_transform(row: dict[str, str], centre: np.ndarray) -> np.ndarray:
    z_axis = vector(row, "crown_axis")
    x_raw = vector(row, "mesial_axis")
    x_axis = x_raw - z_axis * float(np.dot(x_raw, z_axis))
    x_axis /= max(float(np.linalg.norm(x_axis)), 1e-8)
    y_axis = np.cross(z_axis, x_axis)
    rotation = np.vstack((x_axis, y_axis, z_axis))
    units_per_mm = float(row["units_per_mm"])
    if units_per_mm <= 0:
        raise ValueError("units_per_mm must be positive")
    transform = np.eye(4)
    transform[:3, :3] = rotation / units_per_mm
    transform[:3, 3] = -(rotation @ centre) / units_per_mm
    return transform


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_split(group_id: str) -> str:
    bucket = int(hashlib.sha256(group_id.encode()).hexdigest()[:8], 16) % 100
    return "train" if bucket < 80 else "validation" if bucket < 90 else "test"


def prepare(source: Path, metadata_csv: Path, output: Path, dataset_id: str, license_name: str, research_training_approved: bool = False) -> dict:
    rows = list(csv.DictReader(metadata_csv.open(newline="", encoding="utf-8-sig")))
    required = {"relative_path", "group_id", "fdi_number", "condition", "source", "units_per_mm",
                "crown_axis_x", "crown_axis_y", "crown_axis_z", "mesial_axis_x", "mesial_axis_y", "mesial_axis_z"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Metadata CSV must contain: {', '.join(sorted(required))}")
    output.mkdir(parents=True, exist_ok=True)
    mesh_dir = output / "meshes_canonical_mm"
    mesh_dir.mkdir(exist_ok=True)
    assets = []
    for index, row in enumerate(rows):
        path = (source / row["relative_path"]).resolve()
        if not path.is_file() or source.resolve() not in path.parents:
            raise ValueError(f"Mesh is missing or outside source root: {row['relative_path']}")
        fdi = int(row["fdi_number"])
        family = tooth_family(fdi)
        condition = row["condition"].strip().lower()
        if condition not in ALLOWED_CONDITIONS:
            raise ValueError(f"Unsupported condition: {condition}")
        loaded = trimesh.load(path, force="scene")
        meshes = [item for item in loaded.geometry.values() if len(item.faces)]
        if not meshes:
            raise ValueError(f"No mesh geometry: {path}")
        mesh = trimesh.util.concatenate(tuple(meshes))
        if len(mesh.faces) < 100 or not np.isfinite(mesh.vertices).all():
            raise ValueError(f"Mesh fails geometry admission: {path}")
        mesh.apply_transform(canonical_transform(row, np.asarray(mesh.centroid)))
        destination = mesh_dir / f"{index:06d}_fdi{fdi}.ply"
        destination.write_bytes(mesh.export(file_type="ply"))
        assets.append({
            "id": destination.stem, "rawPath": row["relative_path"].replace("\\", "/"),
            "canonicalPath": destination.relative_to(output).as_posix(), "rawSha256": sha256(path),
            "canonicalSha256": sha256(destination), "groupId": row["group_id"], "split": stable_split(row["group_id"]),
            "fdiNumber": fdi, "arch": "upper" if fdi // 10 in {1, 2} else "lower",
            "side": "right" if fdi // 10 in {1, 4} else "left", "toothFamily": family,
            "condition": condition, "trainingRole": "healthy-base" if condition == "healthy" else "pathology-editor",
            "source": row["source"], "vertexCount": int(len(mesh.vertices)), "faceCount": int(len(mesh.faces)),
            "extentsMm": [round(float(value), 4) for value in mesh.extents],
        })
    manifest = {"schemaVersion": 2, "datasetId": dataset_id, "license": license_name,
                "researchTrainingApproved": research_training_approved,
                "assetCount": len(assets), "splits": {name: sum(a["split"] == name for a in assets) for name in ("train", "validation", "test")},
                "assets": assets}
    (output / "anatomy_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--research-training-approved", action="store_true", help="Record completed licence/ethics approval")
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.metadata, args.output, args.dataset_id, args.license, args.research_training_approved), indent=2))


if __name__ == "__main__":
    main()
