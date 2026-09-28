"""Create an immutable, hashed dental-mesh manifest and leakage-safe splits.

This deliberately does not download restricted datasets or invoke TRELLIS.2.
After license review, point it at an extracted dataset and then run the pinned
upstream data toolkit against the emitted split manifests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def split_for(group: str) -> str:
    bucket = int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) % 100
    return "train" if bucket < 80 else "validation" if bucket < 90 else "test"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--group-map", type=Path, help="CSV columns: relative_path,group_id; required when filenames do not encode subjects")
    args = parser.parse_args()
    if not args.source.is_dir():
        raise SystemExit(f"Source directory does not exist: {args.source}")

    groups: dict[str, str] = {}
    if args.group_map:
        with args.group_map.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                groups[row["relative_path"].replace("\\", "/")] = row["group_id"]

    assets = []
    for path in sorted(p for p in args.source.rglob("*") if p.suffix.lower() in {".ply", ".stl", ".obj", ".glb"}):
        relative = path.relative_to(args.source).as_posix()
        group = groups.get(relative) or path.stem.split("_")[0]
        assets.append({"path": relative, "groupId": group, "split": split_for(group), "sha256": digest(path), "bytes": path.stat().st_size})
    if not assets:
        raise SystemExit("No supported meshes found.")

    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": 1,
        "datasetId": args.dataset_id,
        "license": args.license,
        "sourceRoot": str(args.source.resolve()),
        "assetCount": len(assets),
        "splits": {name: sum(a["split"] == name for a in assets) for name in ("train", "validation", "test")},
        "assets": assets,
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for split in ("train", "validation", "test"):
        (args.output / f"{split}.json").write_text(json.dumps([a for a in assets if a["split"] == split], indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(args.output / "manifest.json"), "assets": len(assets), "splits": manifest["splits"]}, indent=2))


if __name__ == "__main__":
    main()
