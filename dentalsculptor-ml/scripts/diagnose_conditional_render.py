"""Small fail-fast diagnostic for TRELLIS conditional rendering."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


def select_canary_assets(metadata_path: Path, count: int) -> list[dict]:
    with metadata_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    selected = [row for row in rows if row.get("local_path")][:count]
    if len(selected) != count:
        raise ValueError(f"Requested {count} canary assets; found {len(selected)} with local paths.")
    return selected


def select_family_canary_assets(
    metadata_path: Path, per_family: int = 1, required_split: str | None = None
) -> list[dict]:
    families = ("incisor", "canine", "premolar", "molar")
    with metadata_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    selected = []
    for family in families:
        matches = [
            row for row in rows
            if row.get("local_path")
            and (required_split is None or row.get("split") == required_split)
            and row.get("caption", "").lower().split()
            and row.get("caption", "").lower().split()[-1] == family
        ][:per_family]
        if len(matches) != per_family:
            raise ValueError(
                f"Family canary requires {per_family} {family} assets"
                f"{f' in split {required_split}' if required_split else ''}; found {len(matches)}."
            )
        selected.extend(matches)
    return selected


def patch_renderer_for_diagnostics(source: Path) -> None:
    """Make the upstream renderer surface Blender failures instead of hiding them."""
    text = source.read_text(encoding="utf-8")
    hidden = "call(args, stdout=DEVNULL, stderr=DEVNULL)"
    visible = "subprocess.run(args, check=True)"
    if visible in text and hidden not in text:
        return
    if hidden not in text:
        raise ValueError("Pinned TRELLIS renderer no longer matches the diagnostic patch contract.")
    text = text.replace("from subprocess import DEVNULL, call", "import subprocess")
    text = text.replace(hidden, visible)
    source.write_text(text, encoding="utf-8")


def validate_render_artifacts(render_root: Path, sha256: str, expected_views: int) -> dict:
    asset_root = render_root / "renders_cond" / sha256
    transforms_path = asset_root / "transforms.json"
    if not transforms_path.is_file():
        raise ValueError(f"Missing transforms.json for render canary {sha256}.")
    transforms = json.loads(transforms_path.read_text(encoding="utf-8"))
    frames = transforms.get("frames")
    if not isinstance(frames, list) or len(frames) != expected_views:
        raise ValueError(
            f"Render canary {sha256} has {len(frames) if isinstance(frames, list) else 0}/"
            f"{expected_views} camera frames."
        )
    images = []
    for frame in frames:
        relative = frame.get("file_path")
        if not relative:
            raise ValueError(f"Render canary {sha256} contains a frame without file_path.")
        image = asset_root / relative
        if not image.is_file() or image.stat().st_size <= 0:
            raise ValueError(f"Missing or empty render canary image: {image}")
        matrix = frame.get("transform_matrix")
        if not isinstance(matrix, list) or len(matrix) != 4 or any(
            not isinstance(row, list) or len(row) != 4 for row in matrix
        ):
            raise ValueError(f"Render canary {sha256} contains an invalid camera matrix.")
        images.append({"path": str(image), "bytes": image.stat().st_size})
    return {
        "sha256": sha256,
        "transforms": str(transforms_path),
        "frameCount": len(frames),
        "imageCount": len(images),
        "minimumImageBytes": min(item["bytes"] for item in images),
    }


def run_diagnostic(
    *,
    toolkit: Path,
    dataset_root: Path,
    render_root: Path,
    subset: str,
    sample_count: int = 1,
    num_cond_views: int = 4,
    balanced_families: bool = False,
) -> dict:
    selected = (
        select_family_canary_assets(dataset_root / "metadata.csv", sample_count)
        if balanced_families
        else select_canary_assets(dataset_root / "metadata.csv", sample_count)
    )
    renderer = toolkit / "render_cond.py"
    patch_renderer_for_diagnostics(renderer)
    command = [
        "python",
        str(renderer),
        subset,
        "--root",
        str(dataset_root),
        "--render_cond_root",
        str(render_root),
        "--max_workers",
        "1",
        "--num_cond_views",
        str(num_cond_views),
        "--instances",
        ",".join(row["sha256"] for row in selected),
    ]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=toolkit, check=True)
    evidence = [
        validate_render_artifacts(render_root, row["sha256"], num_cond_views)
        for row in selected
    ]
    return {
        "valid": True,
        "sampleCount": len(selected),
        "balancedFamilies": balanced_families,
        "numCondViews": num_cond_views,
        "assets": evidence,
    }
