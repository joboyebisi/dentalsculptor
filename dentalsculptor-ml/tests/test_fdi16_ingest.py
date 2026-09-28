import tempfile
import zipfile
from pathlib import Path

import pytest

from scripts.fdi16_ingest import (
    DEFAULT_PILOT_TARGETS,
    MeshMember,
    infer_official_split,
    pilot_targets,
    select_stratified_members,
)


def test_infer_official_split_from_zip_paths():
    assert infer_official_split("train/subject001_mesh.ply") == "train"
    assert infer_official_split("validation/subject001_mesh.ply") == "validation"
    assert infer_official_split("test/subject001_mesh.ply") == "test"
    assert infer_official_split("FDI16/test/subject001_mesh.ply") == "test"
    assert infer_official_split("misc/subject001_mesh.ply") is None


def test_pilot_targets_match_750_budget():
    assert pilot_targets(750) == DEFAULT_PILOT_TARGETS


def test_select_stratified_members_preserves_official_split():
    members = []
    for split, count in (("train", 600), ("validation", 200), ("test", 200)):
        for index in range(count):
            members.append(MeshMember(f"{split}/case_{index:04d}_mesh.ply", 1000, split))
    selected = select_stratified_members(members, 750)
    counts = {
        split: sum(1 for item in selected if item.official_split == split)
        for split in ("train", "validation", "test")
    }
    assert counts == DEFAULT_PILOT_TARGETS
    assert len(selected) == 750


def test_ingest_from_archive_writes_manifest(tmp_path):
    archive = tmp_path / "fdi16.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for split, count in (("train", 520), ("validation", 130), ("test", 130)):
            for index in range(count):
                bundle.writestr(f"{split}/case_{index:04d}_mesh.ply", b"ply\n")

    from scripts.fdi16_ingest import ingest_from_archive

    output = tmp_path / "pilot"
    evidence = ingest_from_archive(archive, output, 750, verify_md5=False)
    assert evidence["meshCount"] == 750
    assert evidence["pilotSplitCounts"] == DEFAULT_PILOT_TARGETS
    assert len(list((output / "raw_meshes").glob("*.ply"))) == 750
    manifest = (output / "selection_manifest.json").read_text(encoding="utf-8")
    assert "sourceMemberPath" in manifest
