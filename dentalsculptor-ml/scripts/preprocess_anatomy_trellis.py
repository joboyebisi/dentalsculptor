"""Run pinned TRELLIS.2 data_toolkit stages for an admitted anatomy manifest."""

from __future__ import annotations

import argparse
import csv
import json
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TRELLIS2_PATH = os.environ.get("TRELLIS2_PATH", "/opt/TRELLIS.2")
SUBSET = "DentalAnatomy"
SHAPE_LATENT_SUFFIX = "shape_enc_next_dc_f16c32_fp16"


def remove_empty_record_shards(output_root: Path) -> list[str]:
    """Remove zero-byte/headerless worker shards before upstream metadata merges."""
    removed = []
    for path in output_root.glob("**/new_records/*.csv"):
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.reader(stream)
            header = next(reader, None)
        if not header:
            path.unlink()
            removed.append(str(path))
    return removed


def remove_error_only_render_metadata(output_root: Path) -> bool:
    """Discard a failed render-stage index so Blender can regenerate it cleanly."""
    path = output_root / "renders_cond" / "metadata.csv"
    if not path.is_file():
        return False
    with path.open(newline="", encoding="utf-8") as stream:
        columns = csv.DictReader(stream).fieldnames or []
    if "cond_rendered" in columns:
        return False
    if "error" not in columns:
        raise ValueError(f"Unexpected conditional-render metadata columns: {columns}")
    path.unlink()
    print(f"Removed error-only conditional-render metadata: {path}", flush=True)
    return True


def validate_render_metadata(output_root: Path, expected_count: int) -> dict:
    """Fail closed unless every admitted mesh has a successful render record."""
    path = output_root / "renders_cond" / "metadata.csv"
    if not path.is_file():
        raise ValueError(f"Missing conditional-render metadata: {path}")
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        rows = list(reader)
    required = {"sha256", "cond_rendered"}
    if not required <= set(columns):
        error_count = sum(bool(row.get("error")) for row in rows)
        raise ValueError(
            f"Conditional rendering did not produce success metadata; columns={columns}, "
            f"errors={error_count}."
        )
    unique_successes = len({
        row["sha256"] for row in rows
        if row.get("cond_rendered", "").strip().lower() == "true"
    })
    if unique_successes != expected_count:
        raise ValueError(
            f"Conditional rendering incomplete: {unique_successes}/{expected_count} unique successful assets."
        )
    return {"successfulConditionalRenders": unique_successes}


def run_render_canary(
    toolkit: Path,
    output_root: Path,
    *,
    num_cond_views: int,
    sample_count: int = 2,
) -> dict:
    """Prove the exact Blender/TRELLIS render path on a tiny sample before paid bulk work."""
    metadata_path = output_root / "metadata.csv"
    with metadata_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames or []
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) >= sample_count:
                break
    if not fieldnames or len(rows) < sample_count:
        raise ValueError(
            f"Render canary requires {sample_count} metadata rows; found {len(rows)}."
        )

    with tempfile.TemporaryDirectory(prefix="dentalsculptor-render-canary-") as folder:
        canary_root = Path(folder)
        with (canary_root / "metadata.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        run(
            [
                "python",
                str(toolkit / "render_cond.py"),
                SUBSET,
                "--root",
                str(canary_root),
                "--max_workers",
                "1",
                "--num_cond_views",
                str(num_cond_views),
            ],
            cwd=toolkit,
        )
        build_metadata(toolkit, canary_root)
        evidence = validate_render_metadata(canary_root, sample_count)
        evidence["canaryAssets"] = [row["sha256"] for row in rows]
        evidence["numCondViews"] = num_cond_views
        print(f"Render canary passed: {json.dumps(evidence, sort_keys=True)}", flush=True)
        return evidence


def dump_ply_pickles(output_root: Path) -> None:
    import numpy as np
    import pandas as pd
    import trimesh
    from tqdm import tqdm

    metadata = pd.read_csv(output_root / "metadata.csv")
    dump_dir = output_root / "mesh_dumps"
    records_dir = dump_dir / "new_records"
    dump_dir.mkdir(parents=True, exist_ok=True)
    records_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for row in tqdm(metadata.itertuples(), total=len(metadata), desc="PLY to pickle"):
        destination = dump_dir / f"{row.sha256}.pickle"
        if destination.is_file():
            records.append({"sha256": row.sha256, "mesh_dumped": True})
            continue
        mesh_path = Path(row.local_path)
        loaded = trimesh.load(mesh_path, force="scene")
        meshes = [item for item in loaded.geometry.values() if len(item.faces)]
        mesh = trimesh.util.concatenate(tuple(meshes)) if len(meshes) > 1 else meshes[0]
        payload = {
            "objects": [
                {
                    "vertices": np.asarray(mesh.vertices, dtype=np.float32),
                    "faces": np.asarray(mesh.faces, dtype=np.int64),
                }
            ]
        }
        with destination.open("wb") as stream:
            pickle.dump(payload, stream)
        records.append({"sha256": row.sha256, "mesh_dumped": True})
    pd.DataFrame.from_records(records).to_csv(records_dir / "part_0.csv", index=False)


def normalize_mesh_dumped_flags(output_root: Path) -> None:
    import pandas as pd

    metadata_path = output_root / "metadata.csv"
    metadata = pd.read_csv(metadata_path)
    dump_dir = output_root / "mesh_dumps"
    dumped = metadata["sha256"].apply(lambda digest: (dump_dir / f"{digest}.pickle").is_file())
    metadata["mesh_dumped"] = dumped
    metadata.to_csv(metadata_path, index=False)


def persist_manifest(manifest_path: Path, output_root: Path) -> Path:
    """Copy a manifest into the output unless it is already the same file."""
    destination = output_root / "anatomy_manifest.json"
    if manifest_path.resolve() != destination.resolve():
        shutil.copy2(manifest_path, destination)
    return destination


def run(command: list[str], *, cwd: Path) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def build_metadata(toolkit: Path, output_root: Path) -> None:
    removed = remove_empty_record_shards(output_root)
    if removed:
        print(f"Removed {len(removed)} empty metadata shard(s).", flush=True)
    run(["python", str(toolkit / "build_metadata.py"), SUBSET, "--root", str(output_root)], cwd=toolkit)


def validate_sparse_structure_latents(
    output_root: Path,
    latent_name: str,
    expected_hashes: set[str],
) -> dict:
    import numpy as np

    latent_dir = output_root / "ss_latents" / latent_name
    observed = {path.stem for path in latent_dir.glob("*.npz")}
    missing = sorted(expected_hashes - observed)
    unexpected = sorted(observed - expected_hashes)
    invalid = []
    for digest in sorted(expected_hashes & observed):
        try:
            with np.load(latent_dir / f"{digest}.npz") as packed:
                z = packed["z"]
                if z.size == 0 or not np.isfinite(z).all():
                    invalid.append(digest)
        except Exception:
            invalid.append(digest)
    return {
        "valid": not missing and not unexpected and not invalid,
        "latentName": latent_name,
        "expectedCount": len(expected_hashes),
        "observedCount": len(observed),
        "missing": missing,
        "unexpected": unexpected,
        "invalid": invalid,
    }


def encode_sparse_structure_latents(
    toolkit: Path,
    output_root: Path,
    *,
    shape_latent_name: str,
    resolution: int = 64,
) -> dict:
    """Run and validate the official first-stage sparse-latent encoder."""
    if resolution != 64:
        raise ValueError("The pinned TRELLIS.2 sparse-flow config requires resolution 64")
    manifest_path = output_root / "anatomy_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("Sparse encoding requires the sealed anatomy manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        str(asset["canonicalSha256"])
        for asset in manifest.get("assets", [])
    }
    if not expected:
        raise ValueError("The sealed manifest contains no assets")
    shape_dir = output_root / "shape_latents" / shape_latent_name
    missing_shape = sorted(
        digest for digest in expected if not (shape_dir / f"{digest}.npz").is_file()
    )
    if missing_shape:
        raise FileNotFoundError(
            f"Sparse encoding is missing {len(missing_shape)} prerequisite shape latents"
        )
    command = [
        "python", str(toolkit / "encode_ss_latent.py"),
        "--root", str(output_root),
        "--shape_latent_root", str(output_root),
        "--ss_latent_root", str(output_root),
        "--shape_latent_name", shape_latent_name,
        "--resolution", str(resolution),
    ]
    run(command, cwd=toolkit)
    build_metadata(toolkit, output_root)
    latent_name = f"ss_enc_conv3d_16l8_fp16_{resolution}"
    evidence = validate_sparse_structure_latents(output_root, latent_name, expected)
    if not evidence["valid"]:
        raise RuntimeError(f"Sparse latent validation failed: {json.dumps(evidence)}")
    return evidence


def ensure_data_toolkit(trellis_root: Path) -> Path:
    import io
    import tarfile
    import urllib.request

    toolkit = trellis_root / "data_toolkit"
    if (toolkit / "dump_mesh.py").is_file():
        return toolkit

    archive_url = "https://codeload.github.com/microsoft/TRELLIS.2/tar.gz/refs/heads/main"
    request = urllib.request.Request(archive_url, headers={"User-Agent": "DentalSculptor/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = io.BytesIO(response.read())
    prefix = "TRELLIS.2-main/"
    with tarfile.open(fileobj=payload, mode="r:gz") as archive:
        for member in archive.getmembers():
            if member.name == f"{prefix}asset_stats.py":
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                (trellis_root / "asset_stats.py").write_bytes(extracted.read())
            if not member.name.startswith(f"{prefix}data_toolkit/"):
                continue
            relative = member.name[len(f"{prefix}data_toolkit/") :]
            if not relative:
                continue
            destination = toolkit / relative
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            extracted = archive.extractfile(member)
            if extracted is not None:
                destination.write_bytes(extracted.read())

    if not (toolkit / "dump_mesh.py").is_file():
        raise FileNotFoundError(f"TRELLIS data_toolkit bootstrap failed under {trellis_root}")
    return toolkit


def install_dataset_module(trellis_root: Path, scripts_root: Path) -> None:
    dataset_dir = trellis_root / "data_toolkit" / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    target = dataset_dir / f"{SUBSET}.py"
    source = scripts_root / "trellis_dataset_dental_anatomy.py"
    shutil.copy2(source, target)
    init_path = dataset_dir / "__init__.py"
    if not init_path.exists():
        init_path.write_text("", encoding="utf-8")


def preprocess(
    manifest_path: Path,
    source_root: Path,
    output_root: Path,
    *,
    resolution: int = 512,
    num_cond_views: int = 24,
    trellis_root: Path | None = None,
    scripts_root: Path | None = None,
) -> dict:
    trellis_root = Path(trellis_root or TRELLIS2_PATH)
    scripts_root = scripts_root or Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts_root))
    from scripts.bootstrap_trellis_metadata import bootstrap

    toolkit = ensure_data_toolkit(trellis_root)
    install_dataset_module(trellis_root, scripts_root)
    bootstrap(manifest_path, source_root, output_root, subset=SUBSET)
    root_args = ["--root", str(output_root)]
    worker_args = [*root_args, "--max_workers", "1"]

    remove_error_only_render_metadata(output_root)
    dump_ply_pickles(output_root)
    build_metadata(toolkit, output_root)
    normalize_mesh_dumped_flags(output_root)
    run(
        ["python", str(toolkit / "dual_grid.py"), SUBSET, *worker_args, "--resolution", str(resolution)],
        cwd=toolkit,
    )
    build_metadata(toolkit, output_root)
    run(
        [
            "python",
            str(toolkit / "encode_shape_latent.py"),
            *root_args,
            "--resolution",
            str(resolution),
            "--dual_grid_root",
            str(output_root),
            "--shape_latent_root",
            str(output_root),
        ],
        cwd=toolkit,
    )
    build_metadata(toolkit, output_root)
    blender = Path("/tmp/blender-3.0.1-linux-x64/blender")
    if not blender.is_file():
        raise FileNotFoundError(
            f"Conditional rendering requires Blender at {blender}; preprocessing image is incomplete."
        )
    canary_evidence = run_render_canary(
        toolkit,
        output_root,
        num_cond_views=num_cond_views,
    )
    run(
        ["python", str(toolkit / "render_cond.py"), SUBSET, *worker_args, "--num_cond_views", str(num_cond_views)],
        cwd=toolkit,
    )
    build_metadata(toolkit, output_root)

    latent_name = f"{SHAPE_LATENT_SUFFIX}_{resolution}"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    render_evidence = validate_render_metadata(output_root, int(manifest.get("assetCount", 0)))
    persist_manifest(manifest_path, output_root)
    status = {
        "schemaVersion": 1,
        "stage": "trellis-preprocessed",
        "resolution": resolution,
        "numCondViews": num_cond_views,
        "shapeLatentDir": f"shape_latents/{latent_name}",
        "renderCondDir": "renders_cond",
        "assetCount": manifest.get("assetCount"),
        "renderCanary": canary_evidence,
        **render_evidence,
    }
    (output_root / "preprocess_status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    stats_path = output_root / "asset_stats.json"
    if not stats_path.exists():
        stats_path.write_text(json.dumps({"assetCount": manifest.get("assetCount"), "resolution": resolution}, indent=2) + "\n", encoding="utf-8")
    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--num-cond-views", type=int, default=24)
    parser.add_argument("--trellis-root", type=Path, default=None)
    args = parser.parse_args()
    print(json.dumps(preprocess(args.manifest, args.source, args.output, resolution=args.resolution, num_cond_views=args.num_cond_views, trellis_root=args.trellis_root), indent=2))


if __name__ == "__main__":
    main()
