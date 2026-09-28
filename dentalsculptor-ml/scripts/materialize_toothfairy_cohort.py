"""Materialise a frozen ToothFairy cohort without mutating source meshes.

The ToothFairy labels are extracted in a shared patient/world coordinate frame.
For conditional 3D training we remove scanner translation and rotate maxillary
teeth by 180 degrees around X so crown-to-root direction is consistent across
arches.  Scale remains millimetres and left/right anatomy is deliberately kept.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import trimesh


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_single_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(path, force="scene", process=False)
    meshes = [geometry for geometry in loaded.geometry.values() if len(geometry.faces)]
    if not meshes:
        raise ValueError(f"No mesh geometry in {path}")
    mesh = trimesh.util.concatenate(tuple(meshes))
    if len(mesh.faces) < 100 or not np.isfinite(mesh.vertices).all():
        raise ValueError(f"Mesh fails geometry admission: {path}")
    return mesh


def canonical_transform(mesh: trimesh.Trimesh, fdi_number: int) -> np.ndarray:
    """Return world-mm -> centred, crown-up transform.

    ToothFairy uses one patient frame. In that frame maxillary and mandibular
    crown/root axes oppose each other. We retain the mandibular orientation and
    rotate maxillary teeth 180 degrees about X before centring. No isotropic
    scaling is applied: physical size is preserved in millimetres.
    """
    quadrant = fdi_number // 10
    if quadrant not in {1, 2, 3, 4}:
        raise ValueError(f"Invalid permanent FDI number: {fdi_number}")
    rotation = np.eye(4)
    if quadrant in {1, 2}:
        rotation[1, 1] = -1.0
        rotation[2, 2] = -1.0
    rotated_centroid = (rotation @ np.r_[np.asarray(mesh.centroid), 1.0])[:3]
    translation = np.eye(4)
    translation[:3, 3] = -rotated_centroid
    return translation @ rotation


def materialize(
    cohort_path: Path,
    source_root: Path,
    output_root: Path,
    *,
    cohort_id: str = "TF-PW32",
    dataset_id: str = "toothfairy-tf-pw32-v1",
) -> dict:
    cohort_document = json.loads(cohort_path.read_text(encoding="utf-8"))
    cohorts = {entry["cohortId"]: entry for entry in cohort_document.get("cohorts", [])}
    if cohort_id not in cohorts:
        raise ValueError(f"Cohort {cohort_id!r} not found")
    cohort = cohorts[cohort_id]
    admission_mode = cohort_document.get("admissionMode")
    if admission_mode not in {"mechanical-provisional", "clinical"}:
        raise ValueError("Unsupported cohort admission mode")
    clinically_accepted = (
        admission_mode == "clinical"
        and cohort_document.get("clinicalClaimPermitted") is True
    )
    if admission_mode == "clinical" and not clinically_accepted:
        raise ValueError("Clinical cohort is missing explicit clinical-claim permission")
    eligible_split = cohort_document.get("eligibleSplit", "train")
    if eligible_split not in {"train", "validation", "test"}:
        raise ValueError("Unsupported cohort split")
    mesh_dir = output_root / "meshes_canonical_mm"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    assets = []
    for index, item in enumerate(cohort["items"]):
        source_path = (source_root / item["rawMeshPath"]).resolve()
        if source_root.resolve() not in source_path.parents or not source_path.is_file():
            raise FileNotFoundError(f"Missing or out-of-root source mesh: {item['rawMeshPath']}")
        observed_hash = sha256_file(source_path)
        if observed_hash != item["rawMeshSha256"]:
            raise ValueError(f"Source hash mismatch for {item['id']}")
        mesh = _load_single_mesh(source_path)
        transform = canonical_transform(mesh, int(item["fdiNumber"]))
        mesh.apply_transform(transform)
        destination = mesh_dir / f"{index:06d}_fdi{item['fdiNumber']}.ply"
        destination.write_bytes(mesh.export(file_type="ply"))
        canonical_hash = sha256_file(destination)
        fdi = int(item["fdiNumber"])
        assets.append({
            "id": item["id"],
            "rawPath": item["rawMeshPath"].replace("\\", "/"),
            "canonicalPath": destination.relative_to(output_root).as_posix(),
            "rawSha256": observed_hash,
            "canonicalSha256": canonical_hash,
            "groupId": item["groupId"],
            "split": eligible_split,
            "fdiNumber": fdi,
            "arch": "upper" if fdi // 10 in {1, 2} else "lower",
            "side": "right" if fdi // 10 in {1, 4} else "left",
            "toothFamily": item["toothFamily"],
            "condition": "unspecified",
            "trainingRole": "anatomy-base",
            "source": "ToothFairy2",
            "representationScope": "whole-tooth",
            "rootSupervision": True,
            "vertexCount": int(len(mesh.vertices)),
            "faceCount": int(len(mesh.faces)),
            "watertight": bool(mesh.is_watertight),
            "extentsMm": [round(float(value), 4) for value in mesh.extents],
            "canonicalization": {
                "convention": "centred-mm-crown-up-v1",
                "matrixWorldMmToCanonicalMm": transform.round(12).tolist(),
                "scaleApplied": 1.0,
            },
        })
    if len(assets) != int(cohort["size"]):
        raise AssertionError("Materialized asset count does not match frozen cohort")
    if not all(asset["watertight"] for asset in assets):
        raise ValueError("The frozen cohort unexpectedly contains a non-watertight mesh")
    manifest = {
        "schemaVersion": 2,
        "datasetId": dataset_id,
        "license": "ToothFairy2 challenge research terms; verify redistribution before release",
        "researchTrainingApproved": clinically_accepted,
        "trainingPurpose": "registered-stage1" if clinically_accepted else "engineering-smoke-only",
        "clinicalClaimPermitted": clinically_accepted,
        "sourceCohortId": cohort_id,
        "sourceCohortFingerprint": cohort["fingerprint"],
        "sourceCohortManifestSha256": sha256_file(cohort_path),
        "assetCount": len(assets),
        "splits": {
            "train": len(assets) if eligible_split == "train" else 0,
            "validation": len(assets) if eligible_split == "validation" else 0,
            "test": len(assets) if eligible_split == "test" else 0,
        },
        "familyCounts": dict(Counter(asset["toothFamily"] for asset in assets)),
        "quadrantCounts": dict(Counter(str(asset["fdiNumber"] // 10) for asset in assets)),
        "assets": assets,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "anatomy_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schemaVersion": 1,
        "stage": "materialized-clinical-training-cohort" if clinically_accepted else "materialized-provisional-training-cohort",
        "datasetId": dataset_id,
        "manifestSha256": sha256_file(manifest_path),
        "assetCount": len(assets),
        "allSourceHashesVerified": True,
        "allCanonicalMeshesWatertight": True,
        "physicalScalePreserved": True,
        "clinicalClaimPermitted": clinically_accepted,
    }
    (output_root / "materialization_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cohort-id", default="TF-PW32")
    parser.add_argument("--dataset-id", default="toothfairy-tf-pw32-v1")
    args = parser.parse_args()
    result = materialize(
        args.cohort, args.source, args.output,
        cohort_id=args.cohort_id, dataset_id=args.dataset_id,
    )
    print(json.dumps({key: result[key] for key in (
        "datasetId", "assetCount", "splits", "familyCounts", "quadrantCounts",
        "trainingPurpose", "clinicalClaimPermitted",
    )}, indent=2))


if __name__ == "__main__":
    main()
