"""Extract per-tooth IOS crown meshes from Teeth3DS OBJ + JSON annotations."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import trimesh

from scripts.anatomy_common import arch_side, tooth_family


def load_scan_mesh(obj_path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(obj_path, force="mesh", process=False)
    if isinstance(loaded, trimesh.Scene):
        meshes = [item for item in loaded.geometry.values() if len(item.faces)]
        if not meshes:
            raise ValueError(f"No mesh geometry in {obj_path}")
        return trimesh.util.concatenate(tuple(meshes))
    return loaded


def dominant_label(labels: np.ndarray, mask: np.ndarray) -> int:
    values = labels[mask]
    values = values[values != 0]
    if values.size == 0:
        return 0
    counts = np.bincount(values.astype(int))
    return int(counts.argmax())


def extract_crowns(obj_path: Path, json_path: Path) -> list[dict]:
    mesh = load_scan_mesh(obj_path)
    annotation = json.loads(json_path.read_text(encoding="utf-8"))
    labels = np.asarray(annotation["labels"], dtype=int)
    instances = np.asarray(annotation["instances"], dtype=int)
    if labels.shape[0] != len(mesh.vertices) or instances.shape[0] != len(mesh.vertices):
        raise ValueError(f"Annotation length mismatch for {obj_path.name}")

    crowns: list[dict] = []
    for instance_id in sorted(set(instances.tolist())):
        if instance_id == 0:
            continue
        vertex_mask = instances == instance_id
        face_mask = vertex_mask[mesh.faces].all(axis=1)
        if not face_mask.any():
            continue
        submesh = mesh.submesh([face_mask], append=True, only_watertight=False)
        fdi = dominant_label(labels, vertex_mask)
        if fdi == 0:
            continue
        arch, side = arch_side(fdi)
        crowns.append(
            {
                "instanceId": int(instance_id),
                "fdiNumber": fdi,
                "toothFamily": tooth_family(fdi),
                "arch": arch,
                "side": side,
                "mesh": submesh,
                "vertexCount": int(len(submesh.vertices)),
                "faceCount": int(len(submesh.faces)),
            }
        )
    return crowns


def run_extraction(source_root: Path, output: Path) -> dict:
    source = json.loads((source_root / "source.json").read_text(encoding="utf-8"))
    manifest = json.loads((source_root / "selection_manifest.json").read_text(encoding="utf-8"))
    merged_root = source_root / "merged"
    crown_dir = output / "raw_crowns"
    crown_dir.mkdir(parents=True, exist_ok=True)

    extracted, skipped = [], []
    index = 0
    for entry in manifest:
        if entry.get("officialSplit") == "test":
            continue
        scan_key = entry["scanKey"]
        obj_rel = entry.get("objPath")
        if not obj_rel:
            skipped.append({**entry, "reason": "missing-obj-path"})
            continue
        obj_path = merged_root / obj_rel
        json_path = obj_path.with_suffix(".json")
        if not obj_path.is_file() or not json_path.is_file():
            skipped.append({**entry, "reason": "missing-scan-files"})
            continue
        try:
            crowns = extract_crowns(obj_path, json_path)
        except ValueError as error:
            skipped.append({**entry, "reason": str(error)})
            continue
        for crown in crowns:
            filename = f"{index:06d}_fdi{crown['fdiNumber']}.ply"
            destination = crown_dir / filename
            destination.write_bytes(crown["mesh"].export(file_type="ply"))
            extracted.append(
                {
                    "index": index,
                    "relativePath": destination.relative_to(output).as_posix(),
                    "scanKey": scan_key,
                    "patientId": entry["patientId"],
                    "jaw": entry["jaw"],
                    "officialSplit": entry["officialSplit"],
                    "instanceId": crown["instanceId"],
                    "fdiNumber": crown["fdiNumber"],
                    "toothFamily": crown["toothFamily"],
                    "arch": crown["arch"],
                    "side": crown["side"],
                    "vertexCount": crown["vertexCount"],
                    "faceCount": crown["faceCount"],
                }
            )
            index += 1

    summary = {
        "schemaVersion": 1,
        "datasetId": source["datasetId"],
        "crownCount": len(extracted),
        "skippedScans": len(skipped),
        "bySplit": {
            split: sum(1 for item in extracted if item["officialSplit"] == split)
            for split in ("train", "validation", "test")
        },
        "byFamily": {},
    }
    for item in extracted:
        summary["byFamily"][item["toothFamily"]] = summary["byFamily"].get(item["toothFamily"], 0) + 1

    (output / "crown_manifest.json").write_text(json.dumps(extracted, indent=2) + "\n", encoding="utf-8")
    (output / "selection_manifest.json").write_text(json.dumps(extracted, indent=2) + "\n", encoding="utf-8")
    (output / "skipped_scans.json").write_text(json.dumps(skipped, indent=2) + "\n", encoding="utf-8")
    (output / "extraction_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(source_root / "source.json", output / "source.json")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="teeth3ds-research-v1 root with merged scans")
    parser.add_argument("--output", type=Path, required=True, help="Output root for raw_crowns/")
    args = parser.parse_args()
    print(json.dumps(run_extraction(args.source, args.output), indent=2))


if __name__ == "__main__":
    main()
