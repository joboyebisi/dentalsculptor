import numpy as np
import trimesh

from scripts.crown_mesh_composition import (
    align_candidate_to_baseline_root,
    compose_candidate_crown_onto_baseline,
)


def test_crown_composition_preserves_protected_vertices_and_connectivity():
    baseline = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
    candidate = baseline.copy()
    crown = candidate.vertices[:, 2] > 0.3
    candidate.vertices[crown, 0] *= 1.15
    original_vertices = baseline.vertices.copy()
    original_faces = baseline.faces.copy()

    composed, receipt = compose_candidate_crown_onto_baseline(
        baseline,
        candidate,
        protected_height=0.60,
        full_transfer_height=0.80,
        maximum_displacement_fraction=0.05,
    )

    normalized_height = (original_vertices[:, 2] - original_vertices[:, 2].min()) / np.ptp(
        original_vertices[:, 2]
    )
    protected = normalized_height <= 0.60
    assert np.array_equal(composed.vertices[protected], original_vertices[protected])
    assert np.array_equal(composed.faces, original_faces)
    assert np.any(composed.vertices[~protected] != original_vertices[~protected])
    assert receipt["protectedVerticesByteIdentical"] is True
    assert receipt["facesByteIdentical"] is True
    assert receipt["maximumObservedDisplacementFraction"] <= 0.05 + 1e-12


def test_crown_composition_rejects_invalid_transition():
    mesh = trimesh.creation.box()
    try:
        compose_candidate_crown_onto_baseline(
            mesh, mesh, protected_height=0.82, full_transfer_height=0.72
        )
    except ValueError as error:
        assert "transition" in str(error)
    else:
        raise AssertionError("invalid transition should fail")


def test_candidate_is_rigidly_registered_using_protected_root():
    baseline = trimesh.creation.icosphere(subdivisions=3, radius=1.0)
    baseline.vertices[:, 0] *= 1.0 + 0.18 * (baseline.vertices[:, 2] + 1.0) / 2.0
    baseline.vertices[:, 1] += 0.08 * baseline.vertices[:, 2] ** 2
    candidate = baseline.copy()
    angle = np.deg2rad(2.0)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    candidate.vertices = candidate.vertices @ rotation.T + np.array([0.15, -0.08, 0.04])
    before = np.mean(np.linalg.norm(candidate.vertices - baseline.vertices, axis=1))

    aligned, receipt = align_candidate_to_baseline_root(
        baseline, candidate, protected_height=0.72, maximum_points=10_000
    )
    after = np.mean(np.linalg.norm(aligned.vertices - baseline.vertices, axis=1))

    assert after < before * 0.2
    assert receipt["scaleApplied"] is False
    assert receipt["rootRmse"] < 0.02
