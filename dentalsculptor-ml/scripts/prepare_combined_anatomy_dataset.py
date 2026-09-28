"""Assemble a unified TRELLIS-ready dataset from balanced-dental-anatomy-mix.json."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from scripts.anatomy_common import sha256_file

DEFAULT_SOURCE_ROOTS = {
    "fdi16-pilot-v1": "research/datasets/fdi16-v2/prepared-v1",
    "teeth3ds-pilot-v1": "research/datasets/teeth3ds-v1/crowns-v1",
}


def resolve_mesh_path(asset: dict, source_roots: dict[str, Path]) -> Path:
    dataset_id = asset["datasetId"]
    if dataset_id not in source_roots:
        raise KeyError(f"No source root configured for datasetId={dataset_id}")
    root = source_roots[dataset_id]
    for key in ("canonicalPath", "rawPath"):
        relative = asset.get(key)
        if not relative:
            continue
        candidate = root / relative.replace("\\", "/")
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not resolve mesh for asset {asset['id']} under {root}")


def assemble(
    mix_path: Path,
    output: Path,
    source_roots: dict[str, Path],
    dataset_id: str = "dental-anatomy-v1",
) -> dict:
    mix = json.loads(mix_path.read_text(encoding="utf-8"))
    mesh_dir = output / "meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    assets = []
    for index, item in enumerate(mix["assets"]):
        digest = item["canonicalSha256"]
        source_path = resolve_mesh_path(item, source_roots)
        destination = mesh_dir / f"{digest}.ply"
        if not destination.exists():
            shutil.copy2(source_path, destination)
        assets.append(
            {
                "id": item["id"],
                "rawPath": destination.relative_to(output).as_posix(),
                "canonicalPath": destination.relative_to(output).as_posix(),
                "rawSha256": item.get("rawSha256", digest),
                "canonicalSha256": digest,
                "groupId": item["globalGroupId"],
                "split": item["split"],
                "fdiNumber": int(item["fdiNumber"]),
                "arch": item["arch"],
                "side": item["side"],
                "toothFamily": item["toothFamily"],
                "condition": item["condition"],
                "trainingRole": item["trainingRole"],
                "source": item.get("source", item["datasetId"]),
                "originDatasetId": item["datasetId"],
            }
        )
        if (index + 1) % 500 == 0 or index + 1 == len(mix["assets"]):
            print(
                f"Assembly progress {index + 1}/{len(mix['assets'])}: "
                f"copied_or_verified={len(assets)}",
                flush=True,
            )
    train_anatomy = sum(
        a["split"] == "train" and a["trainingRole"] in {"healthy-base", "anatomy-base"}
        for a in assets
    )
    train_healthy = sum(
        a["split"] == "train" and a["trainingRole"] == "healthy-base" for a in assets
    )
    manifest = {
        "schemaVersion": 2,
        "datasetId": dataset_id,
        "license": "research-combined-fdi16-teeth3ds",
        "researchTrainingApproved": True,
        "coverageNote": "Combined FDI-16 molar pilot + Teeth3DS all-tooth crowns; TADPM reserved for future A/B.",
        "assetCount": len(assets),
        "splits": {name: sum(a["split"] == name for a in assets) for name in ("train", "validation", "test")},
        "trainFamilyCounts": {
            family: sum(a["split"] == "train" and a["toothFamily"] == family for a in assets)
            for family in ("incisor", "canine", "premolar", "molar")
        },
        "anatomyTrainCount": train_anatomy,
        "healthyTrainCount": train_healthy,
        "assets": assets,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "anatomy_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "mix_source.json").write_text(
        json.dumps({"mixPath": str(mix_path.resolve()), "sourceRoots": {k: str(v) for k, v in source_roots.items()}}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return {
        "datasetId": dataset_id,
        "assetCount": len(assets),
        "anatomyTrainCount": train_anatomy,
        "healthyTrainCount": train_healthy,
        "trainFamilyCounts": manifest["trainFamilyCounts"],
        "output": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-id", default="dental-anatomy-v1")
    parser.add_argument("--source-root", action="append", default=[], help="datasetId=path")
    args = parser.parse_args()
    roots = dict(DEFAULT_SOURCE_ROOTS)
    for entry in args.source_root:
        dataset_id, path = entry.split("=", 1)
        roots[dataset_id] = path
    source_roots = {key: Path(value) for key, value in roots.items()}
    print(json.dumps(assemble(args.mix, args.output, source_roots, args.dataset_id), indent=2))


if __name__ == "__main__":
    main()
