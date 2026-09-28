"""Build a training-ready anatomy manifest for the admitted FDI-16 pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build(source_root: Path, qc_manifest: Path, output: Path, dataset_id: str) -> dict:
    admitted = json.loads(qc_manifest.read_text(encoding="utf-8"))
    assets = []
    for item in admitted:
        if not item.get("admitted", False):
            continue
        stem = Path(item["relativePath"]).stem
        assets.append(
            {
                "id": stem,
                "rawPath": item["relativePath"].replace("\\", "/"),
                "sourceMemberPath": item.get("sourceMemberPath"),
                "rawSha256": item["sha256"],
                "canonicalSha256": item.get("canonicalSha256", item["sha256"]),
                "groupId": item.get("sourceMemberPath", stem),
                "split": item["officialSplit"],
                "fdiNumber": 16,
                "arch": "upper",
                "side": "right",
                "toothFamily": "molar",
                "condition": "healthy",
                "trainingRole": "healthy-base",
                "source": "dtu-fdi16-v2",
                "vertexCount": item.get("vertexCount"),
                "faceCount": item.get("faceCount"),
                "extentsMm": item.get("extentsMm"),
                "reviewRequired": item.get("reviewRequired", False),
                "reviewFlags": item.get("reviewFlags", []),
                "qcNote": "Automated QC does not prove clinical health; educator review advised.",
            }
        )
    manifest = {
        "schemaVersion": 2,
        "datasetId": dataset_id,
        "license": "CC-BY-NC-SA-4.0",
        "researchTrainingApproved": True,
        "coverageNote": "FDI-16 molar-only pilot; not an all-tooth generator dataset.",
        "assetCount": len(assets),
        "splits": {name: sum(a["split"] == name for a in assets) for name in ("train", "validation", "test")},
        "trainFamilyCounts": {"molar": sum(a["split"] == "train" for a in assets)},
        "assets": assets,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "anatomy_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "preprocess_status.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "stage": "manifest-ready",
                "nextStages": [
                    "mesh-normalization-mm",
                    "multi-view-render-24",
                    "ovoxel-dual-grid",
                    "shape-latent-encode",
                    "render-cond-and-asset-stats",
                ],
                "sourceRoot": str(source_root.resolve()),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--qc-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-id", default="fdi16-pilot-v1")
    args = parser.parse_args()
    result = build(args.source, args.qc_manifest, args.output, args.dataset_id)
    print(
        json.dumps(
            {
                "datasetId": result["datasetId"],
                "assetCount": result["assetCount"],
                "splits": result["splits"],
                "manifest": str(args.output / "anatomy_manifest.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
