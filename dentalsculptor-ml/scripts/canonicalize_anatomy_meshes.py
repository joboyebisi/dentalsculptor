"""Center and scale IOS crown meshes for TRELLIS training and mix dedupe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from scripts.anatomy_common import sha256_file


def canonicalize_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    vertices = np.asarray(mesh.vertices, dtype=float)
    if not np.isfinite(vertices).all():
        raise ValueError("non-finite geometry")
    vertices_min = vertices.min(axis=0)
    vertices_max = vertices.max(axis=0)
    center = (vertices_min + vertices_max) / 2.0
    span = float((vertices_max - vertices_min).max())
    if span <= 1e-8:
        raise ValueError("zero-extent geometry")
    scale = 0.99999 / span
    normalized = mesh.copy()
    normalized.apply_translation(-center)
    normalized.apply_scale(scale)
    return normalized


def enrich_manifest(source_root: Path, manifest_path: Path, output_root: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    canonical_dir = output_root / "meshes_canonical_mm"
    canonical_dir.mkdir(parents=True, exist_ok=True)
    updated_assets = []
    for asset in manifest["assets"]:
        raw_path = source_root / asset["rawPath"]
        if not raw_path.is_file():
            raise FileNotFoundError(raw_path)
        loaded = trimesh.load(raw_path, force="scene")
        meshes = [item for item in loaded.geometry.values() if len(item.faces)]
        mesh = trimesh.util.concatenate(tuple(meshes)) if len(meshes) > 1 else meshes[0]
        canonical = canonicalize_mesh(mesh)
        destination = canonical_dir / f"{asset['id']}.ply"
        destination.write_bytes(canonical.export(file_type="ply"))
        canonical_digest = sha256_file(destination)
        updated_assets.append(
            {
                **asset,
                "canonicalPath": destination.relative_to(output_root).as_posix(),
                "canonicalSha256": canonical_digest,
                "extentsMm": [round(float(value), 4) for value in canonical.extents],
            }
        )
    manifest["assets"] = updated_assets
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "anatomy_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = enrich_manifest(args.source, args.manifest, args.output)
    print(json.dumps({"assetCount": result["assetCount"], "output": str(args.output / "anatomy_manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
