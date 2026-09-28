"""Build all-tooth-family anatomy manifest from Teeth3DS QC output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build(qc_manifest: Path, output: Path, dataset_id: str = "teeth3ds-pilot-v1") -> dict:
    admitted = json.loads(qc_manifest.read_text(encoding="utf-8"))
    assets = []
    for item in admitted:
        if not item.get("admitted", False):
            continue
        assets.append(
            {
                "id": Path(item["relativePath"]).stem,
                "rawPath": item["relativePath"].replace("\\", "/"),
                "canonicalPath": item.get("canonicalPath", item["relativePath"]).replace("\\", "/"),
                "rawSha256": item["sha256"],
                "canonicalSha256": item.get("canonicalSha256", item["sha256"]),
                "groupId": item["patientId"],
                "split": item["officialSplit"],
                "fdiNumber": int(item["fdiNumber"]),
                "arch": item["arch"],
                "side": item["side"],
                "toothFamily": item["toothFamily"],
                # Teeth3DS supplies tooth identity/segmentation, not a verified
                # diagnosis. Geometry QC must never be promoted to a clinical
                # "healthy" label.
                "condition": "unspecified",
                "trainingRole": "anatomy-base",
                "clinicalStatusEvidence": "not-provided-by-source",
                "source": "teeth3ds-v1",
                "scanKey": item.get("scanKey"),
                "vertexCount": item.get("vertexCount"),
                "faceCount": item.get("faceCount"),
                "extentsMm": item.get("extentsMm"),
                "reviewRequired": item.get("reviewRequired", False),
                "reviewFlags": item.get("reviewFlags", []),
                "qcNote": "Segmentation-derived crown; geometry admitted, clinical status unverified.",
            }
        )
    manifest = {
        "schemaVersion": 2,
        "datasetId": dataset_id,
        "license": "CC-BY-NC-ND-4.0",
        "researchTrainingApproved": True,
        "researchTrainingBasis": "Non-commercial QMUL research with Teeth3DS attribution.",
        "coverageNote": "All permanent FDI classes from official Teeth3DS_split train/validation; official test sealed.",
        "assetCount": len(assets),
        "splits": {name: sum(a["split"] == name for a in assets) for name in ("train", "validation", "test")},
        "trainFamilyCounts": {
            family: sum(a["split"] == "train" and a["toothFamily"] == family for a in assets)
            for family in ("incisor", "canine", "premolar", "molar")
        },
        "assets": assets,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "anatomy_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qc-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-id", default="teeth3ds-pilot-v1")
    args = parser.parse_args()
    result = build(args.qc_manifest, args.output, args.dataset_id)
    print(json.dumps({"datasetId": result["datasetId"], "assetCount": result["assetCount"], "trainFamilyCounts": result["trainFamilyCounts"]}, indent=2))


if __name__ == "__main__":
    main()
