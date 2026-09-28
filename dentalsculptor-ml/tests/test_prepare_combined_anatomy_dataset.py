import json
import tempfile
from pathlib import Path

from scripts.build_anatomy_training_mix import build_mix
from scripts.prepare_combined_anatomy_dataset import assemble


def _fixture_manifest(path: Path, dataset_id: str, fdi: int, family: str, digest: str):
    mesh = path.parent / f"{digest}.ply"
    mesh.write_text("ply\n", encoding="utf-8")
    assets = [{
        "id": f"tooth_{digest[:6]}",
        "rawPath": mesh.name,
        "canonicalPath": mesh.name,
        "rawSha256": digest,
        "canonicalSha256": digest,
        "groupId": f"g-{digest[:6]}",
        "split": "train",
        "fdiNumber": fdi,
        "arch": "upper",
        "side": "right",
        "toothFamily": family,
        "condition": "healthy",
        "trainingRole": "healthy-base",
        "source": dataset_id,
    }]
    path.write_text(json.dumps({
        "datasetId": dataset_id,
        "researchTrainingApproved": True,
        "assets": assets,
    }), encoding="utf-8")


def test_assemble_combined_dataset_from_mix():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        fdi_root = root / "fdi16"
        teeth_root = root / "teeth3ds"
        fdi_root.mkdir()
        teeth_root.mkdir()
        fdi_manifest = fdi_root / "anatomy_manifest.json"
        teeth_manifest = teeth_root / "anatomy_manifest.json"
        _fixture_manifest(fdi_manifest, "fdi16-pilot-v1", 16, "molar", "a" * 64)
        _fixture_manifest(teeth_manifest, "teeth3ds-pilot-v1", 11, "incisor", "b" * 64)
        teeth_manifest_data = json.loads(teeth_manifest.read_text(encoding="utf-8"))
        for fdi, family, digest in ((13, "canine", "c" * 64), (14, "premolar", "d" * 64)):
            mesh = teeth_root / f"{digest}.ply"
            mesh.write_text("ply\n", encoding="utf-8")
            teeth_manifest_data["assets"].append({
                "id": f"tooth_{digest[:6]}",
                "rawPath": mesh.name,
                "canonicalPath": mesh.name,
                "rawSha256": digest,
                "canonicalSha256": digest,
                "groupId": f"g-{digest[:6]}",
                "split": "train",
                "fdiNumber": fdi,
                "arch": "upper",
                "side": "right",
                "toothFamily": family,
                "condition": "healthy",
                "trainingRole": "healthy-base",
                "source": "teeth3ds-pilot-v1",
            })
        teeth_manifest.write_text(json.dumps(teeth_manifest_data), encoding="utf-8")
        mix = build_mix([fdi_manifest, teeth_manifest], minimum_per_family=1, maximum_per_fdi=10)
        mix_path = root / "mix.json"
        mix_path.write_text(json.dumps(mix), encoding="utf-8")
        output = root / "combined"
        result = assemble(mix_path, output, {
            "fdi16-pilot-v1": fdi_root,
            "teeth3ds-pilot-v1": teeth_root,
        })
        assert result["assetCount"] == 4
        assert result["anatomyTrainCount"] == 4
        assert result["healthyTrainCount"] == 4
        manifest = json.loads((output / "anatomy_manifest.json").read_text(encoding="utf-8"))
        assert manifest["datasetId"] == "dental-anatomy-v1"
        assert manifest["researchTrainingApproved"] is True
        assert len(list((output / "meshes").glob("*.ply"))) == 4
