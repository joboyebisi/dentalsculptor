from pathlib import Path

import pytest

from scripts.preprocess_anatomy_trellis import (
    remove_empty_record_shards,
    remove_error_only_render_metadata,
    run_render_canary,
    validate_render_metadata,
    validate_sparse_structure_latents,
)


def test_persist_manifest_is_idempotent_when_source_is_destination(tmp_path):
    from scripts.preprocess_anatomy_trellis import persist_manifest

    manifest = tmp_path / "anatomy_manifest.json"
    manifest.write_text('{"assetCount": 1}\n', encoding="utf-8")
    result = persist_manifest(manifest, tmp_path)
    assert result == manifest
    assert manifest.read_text(encoding="utf-8") == '{"assetCount": 1}\n'


def test_empty_worker_shards_are_removed_without_touching_valid_records(tmp_path: Path):
    records = tmp_path / "renders_cond" / "new_records"
    records.mkdir(parents=True)
    empty = records / "part_0.csv"
    empty.write_text("", encoding="utf-8")
    valid = records / "part_1.csv"
    valid.write_text("sha256,cond_rendered\naaa,True\n", encoding="utf-8")

    removed = remove_empty_record_shards(tmp_path)

    assert str(empty) in removed
    assert not empty.exists()
    assert valid.exists()


def test_render_validation_requires_every_unique_success(tmp_path: Path):
    folder = tmp_path / "renders_cond"
    folder.mkdir()
    (folder / "metadata.csv").write_text(
        "sha256,cond_rendered\na,True\nb,True\n", encoding="utf-8"
    )
    assert validate_render_metadata(tmp_path, 2)["successfulConditionalRenders"] == 2
    with pytest.raises(ValueError, match="incomplete"):
        validate_render_metadata(tmp_path, 3)


def test_render_validation_rejects_error_only_metadata(tmp_path: Path):
    folder = tmp_path / "renders_cond"
    folder.mkdir()
    (folder / "metadata.csv").write_text(
        "sha256,error\na,blender missing\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="did not produce success metadata"):
        validate_render_metadata(tmp_path, 1)


def test_error_only_render_index_is_removed_but_success_index_is_kept(tmp_path: Path):
    folder = tmp_path / "renders_cond"
    folder.mkdir()
    metadata = folder / "metadata.csv"
    metadata.write_text("sha256,error\na,blender missing\n", encoding="utf-8")
    assert remove_error_only_render_metadata(tmp_path) is True
    assert not metadata.exists()

    metadata.write_text("sha256,cond_rendered\na,True\n", encoding="utf-8")
    assert remove_error_only_render_metadata(tmp_path) is False
    assert metadata.exists()


def test_render_canary_uses_only_bounded_sample_and_requires_success(tmp_path: Path, monkeypatch):
    output = tmp_path / "dataset"
    toolkit = tmp_path / "toolkit"
    output.mkdir()
    toolkit.mkdir()
    (output / "metadata.csv").write_text(
        "sha256,local_path\na,/mesh/a.ply\nb,/mesh/b.ply\nc,/mesh/c.ply\n",
        encoding="utf-8",
    )

    def fake_run(command, *, cwd):
        canary_root = Path(command[command.index("--root") + 1])
        render_dir = canary_root / "renders_cond"
        render_dir.mkdir(parents=True)
        (render_dir / "metadata.csv").write_text(
            "sha256,cond_rendered\na,True\nb,True\n", encoding="utf-8"
        )

    monkeypatch.setattr("scripts.preprocess_anatomy_trellis.run", fake_run)
    monkeypatch.setattr("scripts.preprocess_anatomy_trellis.build_metadata", lambda *_: None)

    evidence = run_render_canary(toolkit, output, num_cond_views=24)

    assert evidence["successfulConditionalRenders"] == 2
    assert evidence["canaryAssets"] == ["a", "b"]


def test_sparse_latent_validation_is_exact_and_finite(tmp_path: Path):
    import numpy as np

    folder = tmp_path / "ss_latents" / "ss_enc_conv3d_16l8_fp16_64"
    folder.mkdir(parents=True)
    np.savez_compressed(folder / "a.npz", z=np.ones((2, 8), dtype=np.float32))
    result = validate_sparse_structure_latents(
        tmp_path, "ss_enc_conv3d_16l8_fp16_64", {"a"}
    )
    assert result["valid"] is True

    np.savez_compressed(folder / "a.npz", z=np.asarray([float("nan")]))
    result = validate_sparse_structure_latents(
        tmp_path, "ss_enc_conv3d_16l8_fp16_64", {"a", "b"}
    )
    assert result["valid"] is False
    assert result["missing"] == ["b"]
    assert result["invalid"] == ["a"]
