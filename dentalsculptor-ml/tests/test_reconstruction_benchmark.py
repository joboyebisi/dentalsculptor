import numpy as np
import trimesh

from scripts.reconstruction_benchmark import compare_canonical_axial_anatomy, compare_meshes


def test_identical_geometry_scores_near_perfectly():
    reference = trimesh.creation.icosphere(subdivisions=2, radius=4.0)
    result = compare_meshes(reference, reference.copy(), samples=3000, seed=7)
    # Independent surface samples have a non-zero sampling floor.
    assert result["symmetricChamferPercentDiagonal"] < 1.2
    assert result["surfaceFscoreAt2Percent"] > 0.97
    assert result["sortedExtentRelativeError"] == 0.0


def test_shape_change_is_detected_after_scale_and_rigid_alignment():
    reference = trimesh.creation.box(extents=(10.0, 8.0, 6.0))
    changed = trimesh.creation.box(extents=(10.0, 8.0, 3.0))
    result = compare_meshes(reference, changed, samples=4000, seed=11)
    assert result["sortedExtentRelativeError"] > 0.1
    assert result["surfaceFscoreAt1Percent"] < 0.95


def test_axial_proxy_localises_apical_regression_without_clinical_claim():
    rng = np.random.default_rng(12)
    reference = rng.uniform((-0.1, -0.1, -0.5), (0.1, 0.1, 0.5), size=(4000, 3))
    prediction = reference.copy()
    prediction[prediction[:, 2] < -0.25, 0] += 0.08
    result = compare_canonical_axial_anatomy(reference, prediction)
    assert result["clinicalLandmarkClaimPermitted"] is False
    assert result["regions"]["apicalRootProxy"]["symmetricChamferPercentDiagonal"] > 1.0
    assert result["regions"]["crownProxy"]["symmetricChamferPercentDiagonal"] < 0.01
    assert "reviewed-cej-curve" in result["requiredForClinicalLandmarks"]
