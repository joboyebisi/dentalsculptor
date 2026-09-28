"""Conservatively transfer a decoded candidate crown onto a baseline tooth.

This is an engineering composition primitive, not a CEJ detector.  Heights are
measured along the shared reconstruction Z axis.  The baseline mesh connectivity
is retained exactly; vertices below the protected crown boundary are unchanged.
"""

from __future__ import annotations

import hashlib

import numpy as np
import trimesh
from scipy.spatial import cKDTree


def array_sha256(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values)
    return hashlib.sha256(contiguous.view(np.uint8)).hexdigest()


def _rigid_fit(source: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    source_mean = source.mean(axis=0)
    target_mean = target.mean(axis=0)
    u, _singular, vt = np.linalg.svd((source - source_mean).T @ (target - target_mean))
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0:
        vt[-1] *= -1
        rotation = vt.T @ u.T
    translation = target_mean - source_mean @ rotation.T
    return rotation, translation


def align_candidate_to_baseline_root(
    baseline: trimesh.Trimesh,
    candidate: trimesh.Trimesh,
    *,
    protected_height: float = 0.72,
    iterations: int = 30,
    maximum_points: int = 100_000,
) -> tuple[trimesh.Trimesh, dict]:
    """Rigidly align candidate to baseline using protected root vertices only."""
    if not 0.0 < protected_height < 1.0:
        raise ValueError("protected height must be in (0, 1)")
    base_vertices = np.asarray(baseline.vertices, dtype=np.float64)
    candidate_vertices = np.asarray(candidate.vertices, dtype=np.float64)

    def protected(vertices: np.ndarray) -> np.ndarray:
        height = (vertices[:, 2] - vertices[:, 2].min()) / max(float(np.ptp(vertices[:, 2])), 1e-12)
        selected = vertices[height <= protected_height]
        if len(selected) < 4:
            raise ValueError("protected root set is empty")
        if len(selected) > maximum_points:
            selected = selected[np.linspace(0, len(selected) - 1, maximum_points, dtype=np.int64)]
        return selected

    target = protected(base_vertices)
    source = protected(candidate_vertices)
    target_tree = cKDTree(target)
    rotation_total = np.eye(3)
    translation_total = target.mean(axis=0) - source.mean(axis=0)
    aligned = source + translation_total
    previous = float("inf")
    iterations_run = 0
    for iterations_run in range(1, iterations + 1):
        distances, indices = target_tree.query(aligned, workers=-1)
        rotation, translation = _rigid_fit(aligned, target[indices])
        aligned = aligned @ rotation.T + translation
        rotation_total = rotation @ rotation_total
        translation_total = translation_total @ rotation.T + translation
        error = float(np.sqrt(np.mean(distances * distances)))
        if abs(previous - error) < 1e-9:
            break
        previous = error
    transformed = candidate_vertices @ rotation_total.T + translation_total
    final_distances = target_tree.query(aligned, workers=-1)[0]
    output = trimesh.Trimesh(
        vertices=transformed,
        faces=np.asarray(candidate.faces).copy(),
        process=False,
    )
    return output, {
        "method": "protected-root-rigid-icp-v1",
        "protectedHeight": protected_height,
        "iterations": iterations_run,
        "sourceRootPointCount": int(len(source)),
        "targetRootPointCount": int(len(target)),
        "rootRmse": float(np.sqrt(np.mean(final_distances * final_distances))),
        "rotation": rotation_total.tolist(),
        "translation": translation_total.tolist(),
        "scaleApplied": False,
    }


def compose_candidate_crown_onto_baseline(
    baseline: trimesh.Trimesh,
    candidate: trimesh.Trimesh,
    *,
    protected_height: float = 0.72,
    full_transfer_height: float = 0.82,
    maximum_displacement_fraction: float = 0.05,
) -> tuple[trimesh.Trimesh, dict]:
    """Return a topology-preserving crown transfer and an invariant receipt."""
    if not 0.0 <= protected_height < full_transfer_height <= 1.0:
        raise ValueError("invalid crown transition heights")
    if not 0.0 < maximum_displacement_fraction <= 0.1:
        raise ValueError("maximum displacement must be in (0, 0.1]")
    base_vertices = np.asarray(baseline.vertices, dtype=np.float64)
    candidate_vertices = np.asarray(candidate.vertices, dtype=np.float64)
    if len(base_vertices) < 4 or len(candidate_vertices) < 4:
        raise ValueError("both meshes must contain surface vertices")
    base_min = float(base_vertices[:, 2].min())
    base_span = float(np.ptp(base_vertices[:, 2]))
    candidate_min = float(candidate_vertices[:, 2].min())
    candidate_span = float(np.ptp(candidate_vertices[:, 2]))
    if base_span <= 1e-9 or candidate_span <= 1e-9:
        raise ValueError("mesh has no usable axial span")
    base_height = (base_vertices[:, 2] - base_min) / base_span
    candidate_height = (candidate_vertices[:, 2] - candidate_min) / candidate_span
    crown_pool = candidate_vertices[candidate_height >= protected_height]
    if len(crown_pool) < 4:
        raise ValueError("candidate crown pool is empty")

    editable = base_height > protected_height
    tree = cKDTree(crown_pool)
    _distances, nearest = tree.query(base_vertices[editable], workers=-1)
    displacement = crown_pool[nearest] - base_vertices[editable]
    diagonal = float(np.linalg.norm(np.ptp(base_vertices, axis=0)))
    cap = maximum_displacement_fraction * diagonal
    norms = np.linalg.norm(displacement, axis=1)
    displacement *= np.minimum(1.0, cap / np.maximum(norms, 1e-12))[:, None]

    t = np.clip(
        (base_height[editable] - protected_height)
        / (full_transfer_height - protected_height),
        0.0,
        1.0,
    )
    smoothstep = t * t * (3.0 - 2.0 * t)
    composed_vertices = base_vertices.copy()
    composed_vertices[editable] += displacement * smoothstep[:, None]
    composed = trimesh.Trimesh(
        vertices=composed_vertices,
        faces=np.asarray(baseline.faces).copy(),
        process=False,
    )
    protected = ~editable
    protected_exact = bool(np.array_equal(composed_vertices[protected], base_vertices[protected]))
    faces_exact = bool(np.array_equal(np.asarray(composed.faces), np.asarray(baseline.faces)))
    receipt = {
        "method": "topology-preserving-nearest-crown-transfer-v1",
        "protectedHeight": protected_height,
        "fullTransferHeight": full_transfer_height,
        "maximumDisplacementFraction": maximum_displacement_fraction,
        "protectedVertexCount": int(np.count_nonzero(protected)),
        "editedVertexCount": int(np.count_nonzero(editable)),
        "protectedVerticesByteIdentical": protected_exact,
        "facesByteIdentical": faces_exact,
        "baselineFacesSha256": array_sha256(np.asarray(baseline.faces)),
        "composedFacesSha256": array_sha256(np.asarray(composed.faces)),
        "maximumObservedDisplacementFraction": float(
            np.max(np.linalg.norm(composed_vertices - base_vertices, axis=1)) / diagonal
        ),
        "clinicalCejClaimPermitted": False,
    }
    if not protected_exact or not faces_exact:
        raise RuntimeError("crown composition violated a baseline preservation invariant")
    return composed, receipt
