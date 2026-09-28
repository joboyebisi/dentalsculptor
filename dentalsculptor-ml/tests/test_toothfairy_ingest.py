import json

import numpy as np
import pytest

from scripts.toothfairy_ingest import (
    _completed_subject_matches,
    _load_volume,
    assemble_manifest,
    convert_subjects,
    label_touches_volume_boundary,
    mesh_label,
    require_nonempty_subject,
    stable_subject_split,
)


def test_boundary_contact_detects_possible_truncation():
    internal = np.zeros((8, 8, 8), dtype=bool)
    internal[2:6, 2:6, 2:6] = True
    boundary = internal.copy()
    boundary[0, 3, 3] = True
    assert not label_touches_volume_boundary(internal)
    assert label_touches_volume_boundary(boundary)


def test_mesh_uses_physical_affine_coordinates():
    pytest.importorskip("skimage")
    pytest.importorskip("trimesh")
    mask = np.zeros((8, 8, 8), dtype=bool)
    mask[2:6, 2:6, 2:6] = True
    affine = np.diag([0.2, 0.3, 0.4, 1.0])
    mesh = mesh_label(mask, affine)
    assert len(mesh.faces) > 100
    assert np.allclose(mesh.extents, [0.8, 1.2, 1.6], atol=1e-6)


def test_loads_official_mha_axis_order_and_geometry(tmp_path):
    sitk = pytest.importorskip("SimpleITK")
    values_zyx = np.zeros((4, 5, 6), dtype=np.uint8)
    values_zyx[1, 2, 3] = 16
    image = sitk.GetImageFromArray(values_zyx)
    image.SetSpacing((0.2, 0.3, 0.4))
    image.SetOrigin((10.0, 20.0, 30.0))
    path = tmp_path / "F001.mha"
    sitk.WriteImage(image, str(path))
    values_xyz, affine, spacing = _load_volume(path)
    assert values_xyz.shape == (6, 5, 4)
    assert values_xyz[3, 2, 1] == 16
    assert spacing == (0.2, 0.3, 0.4)
    assert np.allclose(affine @ [3, 2, 1, 1], [10.6, 20.6, 30.4, 1])


def test_subject_split_is_stable():
    assert stable_subject_split("P001") == stable_subject_split("P001")


def test_zero_tooth_subject_is_a_hard_failure(tmp_path):
    with pytest.raises(ValueError, match="no permanent FDI tooth labels"):
        require_nonempty_subject(tmp_path / "P547.mha", [])


def test_manifest_rejects_patient_leakage(tmp_path):
    subjects = tmp_path / "subjects"
    for name, split in (("a", "train"), ("b", "validation")):
        folder = subjects / name
        folder.mkdir(parents=True)
        asset = {
            "id": name, "groupId": "same-patient", "split": split,
            "toothFamily": "molar", "touchesVolumeBoundary": False,
        }
        (folder / "extraction_receipt.json").write_text(json.dumps({
            "datasetId": "tf", "assets": [asset]
        }), encoding="utf-8")
    try:
        assemble_manifest(tmp_path, "tf", "test")
    except ValueError as error:
        assert "leakage" in str(error).lower()
    else:
        raise AssertionError("Expected subject leakage to be rejected")


def test_resume_receipt_requires_exact_source_hash_and_dataset(tmp_path):
    label = tmp_path / "TF001.mha"
    label.write_bytes(b"label-v1")
    receipt_dir = tmp_path / "output" / "subjects" / "TF001"
    receipt_dir.mkdir(parents=True)
    import hashlib
    digest = hashlib.sha256(label.read_bytes()).hexdigest()
    receipt = {
        "datasetId": "tf-v1", "sourceLabelSha256": digest,
        "assetCount": 1,
    }
    (receipt_dir / "extraction_receipt.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    assert _completed_subject_matches(label, tmp_path / "output", "tf-v1")
    assert not _completed_subject_matches(label, tmp_path / "output", "tf-v2")
    label.write_bytes(b"label-v2")
    assert not _completed_subject_matches(label, tmp_path / "output", "tf-v1")


def test_parallel_conversion_rejects_duplicate_subject_paths(tmp_path):
    label = tmp_path / "TF001.mha"
    label.write_bytes(b"label")
    with pytest.raises(ValueError, match="duplicate label paths"):
        convert_subjects(
            [label, label], tmp_path / "output", dataset_id="tf-v1", workers=2,
        )
