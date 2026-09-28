import csv
import tempfile
from pathlib import Path

import trimesh

from scripts.prepare_anatomy_dataset import prepare, tooth_family


def test_family_mapping():
    assert tooth_family(11) == "incisor"
    assert tooth_family(23) == "canine"
    assert tooth_family(35) == "premolar"
    assert tooth_family(48) == "molar"


def test_prepare_canonical_dataset():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        source = root / "source"
        source.mkdir()
        mesh_path = source / "subject1_tooth16.ply"
        mesh = trimesh.creation.icosphere(subdivisions=3)
        mesh.apply_scale((4, 5, 10))
        mesh_path.write_bytes(mesh.export(file_type="ply"))
        metadata = root / "metadata.csv"
        fields = ["relative_path", "group_id", "fdi_number", "condition", "source", "units_per_mm",
                  "crown_axis_x", "crown_axis_y", "crown_axis_z", "mesial_axis_x", "mesial_axis_y", "mesial_axis_z"]
        with metadata.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow(dict(zip(fields, [mesh_path.name, "subject1", 16, "healthy", "IOS", 1, 0, 0, 1, 1, 0, 0])))
        result = prepare(source, metadata, root / "output", "fixture", "test-only", True)
        assert result["assetCount"] == 1
        assert result["researchTrainingApproved"] is True
        asset = result["assets"][0]
        assert asset["fdiNumber"] == 16
        assert asset["toothFamily"] == "molar"
        assert asset["trainingRole"] == "healthy-base"
        assert (root / "output" / asset["canonicalPath"]).is_file()
