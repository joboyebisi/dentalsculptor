"""Reference-mesh metrics for external dental anatomy reconstruction.

Meshes are centred and scaled by bounding-box diagonal, then aligned with a
rigid ICP step. Reported distances are percentages of the reference diagonal,
which makes the benchmark usable when image-generated meshes have no reliable
physical scale. Clinical millimetre claims require independently calibrated
inputs and are deliberately outside this harness.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree


def load_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(path, force="scene")
    meshes = [mesh for mesh in loaded.geometry.values() if len(mesh.faces)]
    if not meshes:
        raise ValueError(f"No surface geometry in {path}")
    return trimesh.util.concatenate(tuple(meshes))


def sample_normalized(mesh: trimesh.Trimesh, count: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    state = np.random.get_state()
    np.random.seed(seed)
    try:
        points, _ = trimesh.sample.sample_surface(mesh, count)
    finally:
        np.random.set_state(state)
    bounds = np.asarray(mesh.bounds, dtype=float)
    diagonal = float(np.linalg.norm(bounds[1] - bounds[0]))
    if not np.isfinite(diagonal) or diagonal <= 1e-9:
        raise ValueError("Mesh has an invalid bounding-box diagonal")
    centre = (bounds[0] + bounds[1]) / 2.0
    extents = np.sort(np.asarray(mesh.extents, dtype=float) / diagonal)
    return (np.asarray(points, dtype=float) - centre) / diagonal, extents


def _rigid_fit(source: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    source_mean = source.mean(axis=0)
    target_mean = target.mean(axis=0)
    covariance = (source - source_mean).T @ (target - target_mean)
    u, _, vt = np.linalg.svd(covariance)
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0:
        vt[-1] *= -1
        rotation = vt.T @ u.T
    translation = target_mean - source_mean @ rotation.T
    return rotation, translation


def rigid_icp(source: np.ndarray, target: np.ndarray, iterations: int = 40) -> np.ndarray:
    aligned = source.copy()
    tree = cKDTree(target)
    previous = float("inf")
    for _ in range(iterations):
        distances, indices = tree.query(aligned, workers=-1)
        rotation, translation = _rigid_fit(aligned, target[indices])
        aligned = aligned @ rotation.T + translation
        error = float(np.mean(distances))
        if abs(previous - error) < 1e-7:
            break
        previous = error
    return aligned


AXIAL_REGION_BANDS = {
    "apicalRootProxy": (0.00, 0.25),
    "middleRootProxy": (0.25, 0.55),
    "cervicalProxy": (0.55, 0.72),
    "crownProxy": (0.72, 1.01),
}


def compare_canonical_axial_anatomy(
    reference_points: np.ndarray,
    aligned_prediction_points: np.ndarray,
) -> dict:
    """Compare crown-up axial regions without claiming annotated landmarks.

    ToothFairy canonical meshes have a known crown-up Z axis but no CEJ, cusp,
    furcation or apex annotations. Fixed normalized-height bands are therefore
    useful non-regression proxies only. True landmark metrics are deliberately
    unavailable until reviewed annotations are supplied.
    """
    z_min = float(reference_points[:, 2].min())
    z_span = float(reference_points[:, 2].max() - z_min)
    if z_span <= 1e-9:
        raise ValueError("Reference has no usable crown-root axial span")
    ref_height = (reference_points[:, 2] - z_min) / z_span
    pred_height = (aligned_prediction_points[:, 2] - z_min) / z_span
    regions = {}
    for name, (low, high) in AXIAL_REGION_BANDS.items():
        ref = reference_points[(ref_height >= low) & (ref_height < high)]
        pred = aligned_prediction_points[(pred_height >= low) & (pred_height < high)]
        if len(ref) < 20 or len(pred) < 20:
            regions[name] = {
                "available": False,
                "referenceSampleCount": int(len(ref)),
                "predictionSampleCount": int(len(pred)),
            }
            continue
        ref_tree = cKDTree(ref)
        pred_tree = cKDTree(pred)
        pred_to_ref = ref_tree.query(pred, workers=-1)[0]
        ref_to_pred = pred_tree.query(ref, workers=-1)[0]
        both = np.concatenate((pred_to_ref, ref_to_pred))

        def fscore(threshold: float) -> float:
            precision = float(np.mean(pred_to_ref <= threshold))
            recall = float(np.mean(ref_to_pred <= threshold))
            return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)

        regions[name] = {
            "available": True,
            "symmetricChamferPercentDiagonal": round(float(np.mean(both)) * 100, 6),
            "hausdorff95PercentDiagonal": round(float(np.percentile(both, 95)) * 100, 6),
            "surfaceFscoreAt1Percent": round(fscore(0.01), 6),
            "surfaceFscoreAt2Percent": round(fscore(0.02), 6),
            "referenceSampleCount": int(len(ref)),
            "predictionSampleCount": int(len(pred)),
            "sampleShareAbsoluteError": round(
                abs(len(pred) / len(aligned_prediction_points) - len(ref) / len(reference_points)), 6
            ),
        }

    def robust_pole(points: np.ndarray, upper: bool) -> np.ndarray:
        threshold = np.quantile(points[:, 2], 0.99 if upper else 0.01)
        selected = points[points[:, 2] >= threshold] if upper else points[points[:, 2] <= threshold]
        return selected.mean(axis=0)

    return {
        "schemaVersion": 1,
        "method": "canonical-crown-up-fixed-axial-bands-v1",
        "clinicalLandmarkClaimPermitted": False,
        "regionBandsNormalizedReferenceZ": {
            name: [low, high] for name, (low, high) in AXIAL_REGION_BANDS.items()
        },
        "regions": regions,
        "robustPoleProxyErrorsPercentDiagonal": {
            "apical": round(float(np.linalg.norm(
                robust_pole(aligned_prediction_points, False) - robust_pole(reference_points, False)
            )) * 100, 6),
            "coronal": round(float(np.linalg.norm(
                robust_pole(aligned_prediction_points, True) - robust_pole(reference_points, True)
            )) * 100, 6),
        },
        "requiredForClinicalLandmarks": [
            "reviewed-cej-curve", "reviewed-cusp-points", "reviewed-root-tip-points",
            "reviewed-furcation-points-for-multirooted-teeth",
        ],
    }


def compare_meshes(reference: trimesh.Trimesh, prediction: trimesh.Trimesh, *, samples: int = 10000, seed: int = 0) -> dict:
    reference_points, reference_extents = sample_normalized(reference, samples, seed)
    prediction_points, prediction_extents = sample_normalized(prediction, samples, seed + 1)
    aligned = rigid_icp(prediction_points, reference_points)

    reference_tree = cKDTree(reference_points)
    prediction_tree = cKDTree(aligned)
    prediction_to_reference = reference_tree.query(aligned, workers=-1)[0]
    reference_to_prediction = prediction_tree.query(reference_points, workers=-1)[0]
    both = np.concatenate((prediction_to_reference, reference_to_prediction))

    def fscore(threshold: float) -> float:
        precision = float(np.mean(prediction_to_reference <= threshold))
        recall = float(np.mean(reference_to_prediction <= threshold))
        return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)

    return {
        "symmetricChamferPercentDiagonal": round(float(np.mean(both)) * 100, 6),
        "hausdorff95PercentDiagonal": round(float(np.percentile(both, 95)) * 100, 6),
        "surfaceFscoreAt1Percent": round(fscore(0.01), 6),
        "surfaceFscoreAt2Percent": round(fscore(0.02), 6),
        "sortedExtentRelativeError": round(float(np.mean(np.abs(prediction_extents - reference_extents) / np.maximum(reference_extents, 1e-9))), 6),
        "referenceFaceCount": int(len(reference.faces)),
        "predictionFaceCount": int(len(prediction.faces)),
        "canonicalAxialAnatomyProxy": compare_canonical_axial_anatomy(
            reference_points, aligned
        ),
    }


def run_manifest(manifest_path: Path, output_path: Path, samples: int) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent
    results = []
    for item in manifest["items"]:
        reference = load_mesh(root / item["referenceMesh"])
        models = {
            name: compare_meshes(reference, load_mesh(root / relative), samples=samples, seed=int(manifest.get("seed", 0)))
            for name, relative in item["predictions"].items()
        }
        results.append({"id": item["id"], "toothFamily": item["toothFamily"], "fdiNumber": item.get("fdiNumber"), "models": models})
    report = {"schemaVersion": 1, "benchmarkId": manifest["benchmarkId"], "caseCount": len(results), "items": results}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=10000)
    args = parser.parse_args()
    print(json.dumps(run_manifest(args.manifest, args.output, args.samples), indent=2))


if __name__ == "__main__":
    main()
