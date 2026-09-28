import json
from pathlib import Path

import pytest

from scripts.diagnose_conditional_render import (
    patch_renderer_for_diagnostics,
    select_canary_assets,
    select_family_canary_assets,
    validate_render_artifacts,
)


def test_selects_bounded_canary_assets(tmp_path: Path):
    metadata = tmp_path / "metadata.csv"
    metadata.write_text("sha256,local_path\na,/a.ply\nb,/b.ply\nc,/c.ply\n", encoding="utf-8")
    assert [row["sha256"] for row in select_canary_assets(metadata, 2)] == ["a", "b"]


def test_selects_each_tooth_family(tmp_path: Path):
    metadata = tmp_path / "metadata.csv"
    metadata.write_text(
        "sha256,local_path,caption\n"
        "a,/a.ply,FDI 11 incisor\n"
        "b,/b.ply,FDI 13 canine\n"
        "c,/c.ply,FDI 14 premolar\n"
        "d,/d.ply,FDI 16 molar\n",
        encoding="utf-8",
    )
    assert [row["sha256"] for row in select_family_canary_assets(metadata)] == ["a", "b", "c", "d"]


def test_family_selector_excludes_held_out_rows(tmp_path: Path):
    metadata = tmp_path / "metadata.csv"
    metadata.write_text(
        "sha256,local_path,caption,split\n"
        "a,/a.ply,FDI 11 incisor,train\n"
        "b,/b.ply,FDI 13 canine,train\n"
        "c,/c.ply,FDI 14 premolar,train\n"
        "d,/d.ply,FDI 16 molar,train\n"
        "e,/e.ply,FDI 16 molar,test\n",
        encoding="utf-8",
    )
    selected = select_family_canary_assets(metadata, required_split="train")
    assert [row["sha256"] for row in selected] == ["a", "b", "c", "d"]
    assert all(row["split"] == "train" for row in selected)


def test_renderer_patch_exposes_blender_failure(tmp_path: Path):
    renderer = tmp_path / "render_cond.py"
    renderer.write_text(
        "from subprocess import DEVNULL, call\ncall(args, stdout=DEVNULL, stderr=DEVNULL)\n",
        encoding="utf-8",
    )
    patch_renderer_for_diagnostics(renderer)
    patched = renderer.read_text(encoding="utf-8")
    assert "subprocess.run(args, check=True)" in patched
    assert "stderr=DEVNULL" not in patched


def test_validates_real_render_contract(tmp_path: Path):
    sha = "a" * 64
    asset = tmp_path / "renders_cond" / sha
    asset.mkdir(parents=True)
    (asset / "000.png").write_bytes(b"image")
    (asset / "transforms.json").write_text(
        json.dumps({"frames": [{"file_path": "000.png", "transform_matrix": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]}]}),
        encoding="utf-8",
    )
    evidence = validate_render_artifacts(tmp_path, sha, 1)
    assert evidence["imageCount"] == 1
    assert evidence["minimumImageBytes"] == 5


def test_rejects_missing_render_artifacts(tmp_path: Path):
    with pytest.raises(ValueError, match="Missing transforms"):
        validate_render_artifacts(tmp_path, "a" * 64, 1)
