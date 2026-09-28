"""Convert FDI-labelled ToothFairy CBCT masks into traceable per-tooth meshes.

This module deliberately stops before anatomical canonicalisation.  A CBCT label
map and its NIfTI affine are the source of truth; the extracted mesh remains in
physical patient coordinates so orientation mistakes cannot be hidden by an
automatic PCA transform.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

try:
    # Package-style import used by tests and ``python -m`` execution.
    from scripts.anatomy_common import arch_side, sha256_file, tooth_family
except ModuleNotFoundError:
    # Direct CLI execution places this script's directory on sys.path.
    from anatomy_common import arch_side, sha256_file, tooth_family


VALID_FDI = tuple(
    quadrant * 10 + position
    for quadrant in (1, 2, 3, 4)
    for position in range(1, 9)
)


def stable_subject_split(subject_id: str) -> str:
    """Create a patient-level 80/10/10 split, never a tooth-level split."""
    bucket = int(hashlib.sha256(subject_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    return "train" if bucket < 80 else "validation" if bucket < 90 else "test"


def label_touches_volume_boundary(mask: np.ndarray) -> bool:
    if mask.ndim != 3 or not mask.any():
        return False
    return bool(
        mask[0].any() or mask[-1].any()
        or mask[:, 0].any() or mask[:, -1].any()
        or mask[:, :, 0].any() or mask[:, :, -1].any()
    )


def mesh_label(mask: np.ndarray, affine: np.ndarray):
    """March a binary label and transform vertices into NIfTI world millimetres."""
    try:
        from skimage.measure import marching_cubes
        import trimesh
    except ImportError as error:  # pragma: no cover - exercised in deployed research image
        raise RuntimeError(
            "ToothFairy conversion requires scikit-image and trimesh; install requirements-research.txt"
        ) from error
    if mask.ndim != 3 or mask.dtype != np.bool_:
        raise ValueError("mask must be a three-dimensional boolean array")
    if int(mask.sum()) < 8:
        raise ValueError("label contains too few voxels to mesh")
    padded = np.pad(mask.astype(np.uint8), 1)
    vertices, faces, _normals, _values = marching_cubes(padded, level=0.5)
    vertices -= 1.0
    homogeneous = np.column_stack((vertices, np.ones(len(vertices))))
    world_vertices = (np.asarray(affine, dtype=float) @ homogeneous.T).T[:, :3]
    mesh = trimesh.Trimesh(vertices=world_vertices, faces=faces, process=False)
    mesh.remove_unreferenced_vertices()
    return mesh


def _load_volume(path: Path):
    """Load NIfTI or the official ToothFairy2 MetaImage format in world mm."""
    if path.suffix.lower() in {".mha", ".mhd"}:
        try:
            import SimpleITK as sitk
        except ImportError as error:  # pragma: no cover
            raise RuntimeError(
                "MetaImage conversion requires SimpleITK; install requirements-research.txt"
            ) from error
        image = sitk.ReadImage(str(path))
        # SimpleITK arrays are z,y,x. Marching cubes expects array axes to match
        # the affine columns, so transpose into x,y,z before applying LPS geometry.
        values = np.transpose(sitk.GetArrayFromImage(image), (2, 1, 0))
        spacing = np.asarray(image.GetSpacing(), dtype=float)
        direction = np.asarray(image.GetDirection(), dtype=float).reshape(3, 3)
        origin = np.asarray(image.GetOrigin(), dtype=float)
        affine = np.eye(4)
        affine[:3, :3] = direction @ np.diag(spacing)
        affine[:3, 3] = origin
        return values, affine, tuple(float(value) for value in spacing)
    try:
        import nibabel as nib
    except ImportError as error:  # pragma: no cover
        raise RuntimeError(
            "ToothFairy conversion requires nibabel; install requirements-research.txt"
        ) from error
    image = nib.load(str(path))
    return np.asarray(image.dataobj), np.asarray(image.affine), image.header.get_zooms()[:3]


def convert_subject(
    label_path: Path,
    output_root: Path,
    *,
    subject_id: str | None = None,
    dataset_id: str = "toothfairy2-whole-tooth-v1",
) -> list[dict]:
    """Extract every permanent FDI label from one subject without smoothing."""
    subject_id = subject_id or label_path.name.removesuffix(".nii.gz").removesuffix(".nii").removesuffix(".mha").removesuffix(".mhd")
    labels, affine, spacing = _load_volume(label_path)
    if labels.ndim != 3:
        raise ValueError(f"Expected a 3D label volume, got {labels.shape}")
    rounded = np.rint(labels).astype(np.int16)
    if not np.allclose(labels, rounded):
        raise ValueError("Label volume contains non-integer values")
    subject_dir = output_root / "subjects" / subject_id
    raw_mesh_dir = subject_dir / "meshes_raw_world_mm"
    raw_mesh_dir.mkdir(parents=True, exist_ok=True)
    assets = []
    for fdi in VALID_FDI:
        mask = rounded == fdi
        voxel_count = int(mask.sum())
        if not voxel_count:
            continue
        mesh = mesh_label(mask, affine)
        arch, side = arch_side(fdi)
        destination = raw_mesh_dir / f"fdi{fdi}.ply"
        destination.write_bytes(mesh.export(file_type="ply"))
        touches_boundary = label_touches_volume_boundary(mask)
        bounds = np.asarray(mesh.bounds)
        extents = np.asarray(mesh.extents)
        flags = []
        if touches_boundary:
            flags.append("volume-boundary-contact-possible-apex-truncation")
        if not mesh.is_watertight:
            flags.append("non-watertight-extracted-surface")
        assets.append({
            "id": f"{dataset_id}-{subject_id}-fdi{fdi}",
            "datasetId": dataset_id,
            "source": "ToothFairy2",
            "groupId": subject_id,
            "split": stable_subject_split(subject_id),
            "fdiNumber": fdi,
            "toothFamily": tooth_family(fdi),
            "arch": arch,
            "side": side,
            "representationScope": "whole-tooth",
            "rootSupervision": True,
            "condition": "unspecified",
            "trainingRole": "anatomy-base",
            "rawVolumePath": label_path.as_posix(),
            "rawVolumeSha256": sha256_file(label_path),
            "rawMeshPath": destination.relative_to(output_root).as_posix(),
            "rawMeshSha256": sha256_file(destination),
            "voxelSpacingMm": [float(value) for value in spacing],
            "voxelCount": voxel_count,
            "vertexCount": int(len(mesh.vertices)),
            "faceCount": int(len(mesh.faces)),
            "boundsWorldMm": bounds.round(5).tolist(),
            "extentsMm": extents.round(5).tolist(),
            "touchesVolumeBoundary": touches_boundary,
            "rootCompleteness": "review-required" if touches_boundary else "not-yet-clinically-audited",
            "reviewRequired": True,
            "reviewFlags": flags,
            "geometryStage": "raw-world-mm",
        })
    receipt = {
        "schemaVersion": 1,
        "datasetId": dataset_id,
        "subjectId": subject_id,
        "sourceLabelPath": label_path.as_posix(),
        "sourceLabelSha256": sha256_file(label_path),
        "assetCount": len(assets),
        "assets": assets,
    }
    (subject_dir / "extraction_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return assets


def require_nonempty_subject(label_path: Path, assets: list[dict]) -> None:
    if not assets:
        raise ValueError(
            f"{label_path} contains no permanent FDI tooth labels; "
            "record an exclusion and use the next deterministic reserve subject"
        )


def assemble_manifest(output_root: Path, dataset_id: str, license_name: str) -> dict:
    assets = []
    for receipt_path in sorted((output_root / "subjects").glob("*/extraction_receipt.json")):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("datasetId") != dataset_id:
            raise ValueError(f"Mixed dataset IDs in {receipt_path}")
        assets.extend(receipt.get("assets", []))
    ids = [asset["id"] for asset in assets]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate tooth asset IDs")
    groups_by_split: dict[str, set[str]] = {name: set() for name in ("train", "validation", "test")}
    for asset in assets:
        groups_by_split[asset["split"]].add(asset["groupId"])
    if any(groups_by_split[a] & groups_by_split[b] for a, b in (("train", "validation"), ("train", "test"), ("validation", "test"))):
        raise ValueError("Patient leakage across splits")
    manifest = {
        "schemaVersion": 1,
        "datasetId": dataset_id,
        "sourceRepresentation": "FDI-labelled CBCT segmentation",
        "targetRepresentation": "per-tooth raw surface mesh in physical world millimetres",
        "license": license_name,
        "researchTrainingApproved": False,
        "clinicalAuditStatus": "pending",
        "canonicalisationStatus": "pending",
        "assetCount": len(assets),
        "subjectCount": len({asset["groupId"] for asset in assets}),
        "splitCounts": dict(Counter(asset["split"] for asset in assets)),
        "familyCounts": dict(Counter(asset["toothFamily"] for asset in assets)),
        "boundaryContactCount": sum(asset["touchesVolumeBoundary"] for asset in assets),
        "assets": assets,
    }
    output = output_root / "toothfairy_extraction_manifest.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _completed_subject_matches(label_path: Path, output_root: Path, dataset_id: str) -> bool:
    """Return true only when a prior subject receipt matches the exact source file."""
    subject_id = label_path.name.removesuffix(".nii.gz").removesuffix(".nii").removesuffix(".mha").removesuffix(".mhd")
    receipt_path = output_root / "subjects" / subject_id / "extraction_receipt.json"
    if not receipt_path.exists():
        return False
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        receipt.get("datasetId") == dataset_id
        and receipt.get("sourceLabelSha256") == sha256_file(label_path)
        and int(receipt.get("assetCount", 0)) > 0
    )


def _convert_subject_job(args: tuple[Path, Path, str]) -> int:
    label_path, output_root, dataset_id = args
    assets = convert_subject(label_path, output_root, dataset_id=dataset_id)
    require_nonempty_subject(label_path, assets)
    return len(assets)


def convert_subjects(
    label_paths: list[Path],
    output_root: Path,
    *,
    dataset_id: str,
    workers: int = 1,
    resume: bool = False,
) -> dict:
    """Convert subjects with bounded process parallelism and receipt-based resume."""
    if workers < 1:
        raise ValueError("workers must be positive")
    resolved = [path.resolve() for path in label_paths]
    if len(resolved) != len(set(resolved)):
        raise ValueError("duplicate label paths")
    skipped = [
        path for path in resolved
        if resume and _completed_subject_matches(path, output_root, dataset_id)
    ]
    pending = [path for path in resolved if path not in skipped]
    jobs = [(path, output_root, dataset_id) for path in pending]
    if workers == 1:
        counts = [_convert_subject_job(job) for job in jobs]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            counts = list(executor.map(_convert_subject_job, jobs))
    return {
        "requestedSubjects": len(resolved),
        "convertedSubjects": len(pending),
        "resumedSubjects": len(skipped),
        "convertedAssets": sum(counts),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-id", default="toothfairy2-whole-tooth-v1")
    parser.add_argument("--license", default="CC-BY-SA-4.0; verify source terms before training")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    summary = convert_subjects(
        args.labels, args.output, dataset_id=args.dataset_id,
        workers=args.workers, resume=args.resume,
    )
    manifest = assemble_manifest(args.output, args.dataset_id, args.license)
    print(json.dumps({"conversion": summary, "manifest": manifest}, indent=2))


if __name__ == "__main__":
    main()
