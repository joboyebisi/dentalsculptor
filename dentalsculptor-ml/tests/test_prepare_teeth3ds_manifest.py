import json
from pathlib import Path

from scripts.prepare_teeth3ds_manifest import build


def test_geometry_qc_does_not_claim_clinical_health(tmp_path: Path):
    qc_manifest = tmp_path / "admitted.json"
    qc_manifest.write_text(
        json.dumps(
            [
                {
                    "admitted": True,
                    "relativePath": "raw_crowns/tooth_fdi16.ply",
                    "sha256": "abc123",
                    "patientId": "patient-1",
                    "officialSplit": "train",
                    "fdiNumber": 16,
                    "arch": "upper",
                    "side": "right",
                    "toothFamily": "molar",
                }
            ]
        ),
        encoding="utf-8",
    )

    manifest = build(qc_manifest, tmp_path / "prepared")
    asset = manifest["assets"][0]

    assert asset["condition"] == "unspecified"
    assert asset["trainingRole"] == "anatomy-base"
    assert asset["clinicalStatusEvidence"] == "not-provided-by-source"
