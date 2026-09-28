"""Promotion-safe TRELLIS.2 dental shape fine-tuning jobs on Modal.

Usage:
  modal run -m modal_app.train_anatomy::plan --dataset-name dental-anatomy-v1
  modal run -m modal_app.train_anatomy::train --dataset-name dental-anatomy-v1 --run-name fdi16-spike-v1
"""

from __future__ import annotations

import json
import subprocess
import hashlib
import tempfile
import urllib.request
import csv
import math
import re
from pathlib import Path

import modal

from modal_app.images.trellis_gpu import hf_cache_volume, hf_secret, trellis_gpu_image
from modal_app.trellis_config import (
    BASE_MODEL_NAME,
    BASE_MODEL_REVISION,
    MODEL_NAME,
    MODEL_REVISION,
    TRELLIS2_PATH,
    TRELLIS_COMMIT,
    get_quality_preset,
    sampler_params_for_steps,
)

app = modal.App("dentalsculptor-anatomy-training")
dataset_volume = modal.Volume.from_name("dentalsculptor-anatomy-datasets-v1", create_if_missing=True)
checkpoint_volume = modal.Volume.from_name("dentalsculptor-anatomy-checkpoints-v1", create_if_missing=True)
TRAINING_CODE_COMMIT = "75fbf0183001ed9876c8dbb35de6b68552ee08bd"
BASE_SHAPE_FLOW_FILE = "ckpts/slat_flow_img2shape_dit_1_3B_512_bf16"
BASE_SPARSE_FLOW_FILE = "ckpts/ss_flow_img_dit_1_3B_64_bf16"
ingestion_image = (
    modal.Image.debian_slim(python_version="3.11")
    # scipy and networkx supply trimesh's component/boundary graph backends.
    .pip_install("trimesh", "numpy", "pandas", "scipy", "networkx")
    .add_local_dir("scripts", remote_path="/root/scripts")
)

FDI16_URL = "https://ndownloader.figshare.com/files/44571158"
FDI16_MD5 = "9824c7d342f6f13887084452d2c75c68"
FDI16_CITATION = "Ye, Johan Ziruo; Ørkild, Thomas; Søndergaard, Peter Lempel; Hauberg, Søren (2023). 3Shape FDI 16 Meshes from Intraoral Scans. Technical University of Denmark. https://doi.org/10.11583/DTU.23626650.v2"

MODAL_SOURCE_ROOTS = {
    "fdi16-pilot-v1": Path("/datasets/fdi16-pilot-v1"),
    "teeth3ds-pilot-v1": Path("/datasets/teeth3ds-crowns-v1"),
}


def select_mixed_representation_ceiling_cases(
    toothfairy_manifest: dict, crown_manifest: dict
) -> list[dict]:
    """Select the sealed 12-case, source-aware Stage-0 ceiling cohort."""
    families = ("incisor", "canine", "premolar", "molar")
    if toothfairy_manifest.get("datasetId") != "toothfairy-tf-pw32-v1":
        raise ValueError("Mixed Stage 0 requires the sealed TF-PW32 manifest")
    if crown_manifest.get("datasetId") != "dental-anatomy-v1":
        raise ValueError("Mixed Stage 0 requires the assembled crown manifest")

    def ordered(rows: list[dict]) -> list[dict]:
        return sorted(rows, key=lambda row: (row["canonicalSha256"], row["id"]))

    selected: list[dict] = []
    whole_teeth = toothfairy_manifest.get("assets", [])
    for family in families:
        matches = ordered([
            row for row in whole_teeth
            if row.get("split") == "train"
            and row.get("toothFamily") == family
            and row.get("representationScope") == "whole-tooth"
            and row.get("rootSupervision") is True
        ])
        if not matches:
            raise ValueError(f"Mixed Stage 0 lacks a whole-tooth {family}")
        selected.append({
            **matches[0], "ceilingSource": "toothfairy2",
            "ceilingDatasetRoot": "toothfairy-tf-pw32-v1",
            "representationScope": "whole-tooth", "rootSupervision": True,
        })

    crowns = crown_manifest.get("assets", [])
    for family in families:
        matches = ordered([
            row for row in crowns
            if row.get("split") == "train"
            and row.get("toothFamily") == family
            and row.get("originDatasetId") == "teeth3ds-pilot-v1"
        ])
        if not matches:
            raise ValueError(f"Mixed Stage 0 lacks a Teeth3DS {family} crown")
        selected.append({
            **matches[0], "ceilingSource": "teeth3ds",
            "ceilingDatasetRoot": "dental-anatomy-v1",
            "representationScope": "crown-only", "rootSupervision": False,
        })

    dtu = ordered([
        row for row in crowns
        if row.get("split") == "train"
        and row.get("originDatasetId") == "fdi16-pilot-v1"
        and int(row.get("fdiNumber", 0)) == 16
    ])
    dtu_groups = set()
    for row in dtu:
        if row.get("groupId") in dtu_groups:
            continue
        dtu_groups.add(row.get("groupId"))
        selected.append({
            **row, "ceilingSource": "dtu-fdi16",
            "ceilingDatasetRoot": "dental-anatomy-v1",
            "representationScope": "crown-only", "rootSupervision": False,
        })
        if len(dtu_groups) == 4:
            break
    if len(dtu_groups) != 4:
        raise ValueError("Mixed Stage 0 requires four distinct DTU FDI16 crowns")
    if len(selected) != 12 or len({row["canonicalSha256"] for row in selected}) != 12:
        raise ValueError("Mixed Stage 0 must contain 12 unique assets")
    return selected


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    timeout=3 * 60 * 60,
)
def ingest_fdi16(max_meshes: int = 750) -> dict:
    """Verify the official archive and retain a bounded mesh-only research subset."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.fdi16_ingest import ingest_from_archive, load_existing_evidence

    target = Path("/datasets/fdi16-research-v2")
    existing = load_existing_evidence(target)
    if existing and existing.get("meshCount") == max_meshes:
        return existing
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        archive = Path(folder) / "fdi16_dataset.zip"
        digest = hashlib.md5()  # nosec B324 - required only to verify publisher checksum
        with urllib.request.urlopen(FDI16_URL, timeout=120) as response, archive.open("wb") as output:
            while chunk := response.read(8 * 1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
        if digest.hexdigest() != FDI16_MD5:
            raise ValueError("FDI-16 archive checksum does not match the official manifest")
        evidence = ingest_from_archive(archive, target, max_meshes, verify_md5=False)
    dataset_volume.commit()
    return evidence


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    timeout=12 * 60 * 60,
)
def ingest_teeth3ds(parts: str = "1,2,3,4,5,6") -> dict:
    """Download OSF Teeth3DS parts, merge scans, and bind official splits."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.teeth3ds_ingest import OSF_PARTS, ingest_parts, load_existing_evidence

    selected = [f"data_part_{item.strip()}" for item in parts.split(",") if item.strip()]
    unknown = [part for part in selected if part not in OSF_PARTS]
    if unknown:
        raise ValueError(f"Unsupported Teeth3DS parts: {unknown}")
    target = Path("/datasets/teeth3ds-research-v1")
    existing = load_existing_evidence(target)
    if existing and set(existing.get("osfParts", [])) >= set(selected):
        return existing
    evidence = ingest_parts(target, selected)
    dataset_volume.commit()
    return evidence


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    timeout=6 * 60 * 60,
)
def extract_teeth3ds_crowns() -> dict:
    """Extract per-tooth crowns from ingested Teeth3DS scans (train/validation only)."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.extract_teeth3ds_crowns import run_extraction

    source = Path("/datasets/teeth3ds-research-v1")
    output = Path("/datasets/teeth3ds-crowns-v1")
    summary = run_extraction(source, output)
    dataset_volume.commit()
    return summary


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    timeout=8 * 60 * 60,
)
def qc_and_prepare_teeth3ds() -> dict:
    """QC extracted crowns and write teeth3ds-pilot-v1 manifest on the volume."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.prepare_teeth3ds_manifest import build
    from scripts.qc_fdi16_meshes import run_qc

    source = Path("/datasets/teeth3ds-crowns-v1")
    qc_dir = Path("/datasets/teeth3ds-qc-v1")
    prepared = Path("/datasets/teeth3ds-pilot-v1")
    summary = run_qc(source, qc_dir)
    manifest = build(qc_dir / "admitted_manifest.json", prepared, dataset_id="teeth3ds-pilot-v1")
    dataset_volume.commit()
    return {"qc": summary, "manifest": {"assetCount": manifest["assetCount"], "trainFamilyCounts": manifest["trainFamilyCounts"]}}


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    timeout=4 * 60 * 60,
)
def assemble_dental_anatomy_v1(minimum_per_family: int = 100, maximum_per_fdi: int = 750) -> dict:
    """Build dental-anatomy-v1 from FDI-16 + Teeth3DS manifests already on the volume."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.build_anatomy_training_mix import build_mix
    from scripts.prepare_combined_anatomy_dataset import assemble

    fdi16_manifest = Path("/datasets/fdi16-pilot-v1/anatomy_manifest.json")
    teeth3ds_manifest = Path("/datasets/teeth3ds-pilot-v1/anatomy_manifest.json")
    if not teeth3ds_manifest.is_file():
        raise FileNotFoundError("Run qc_and_prepare_teeth3ds after crown extraction.")
    mix = build_mix([fdi16_manifest, teeth3ds_manifest], minimum_per_family, maximum_per_fdi)
    mix_path = Path("/datasets/balanced-dental-anatomy-mix.json")
    mix_path.write_text(json.dumps(mix, indent=2) + "\n", encoding="utf-8")
    result = assemble(mix_path, Path("/datasets/dental-anatomy-v1"), MODAL_SOURCE_ROOTS, dataset_id="dental-anatomy-v1")
    dataset_volume.commit()
    print(json.dumps(result, indent=2), flush=True)
    return result


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    timeout=60 * 60,
)
def validate_anatomy_dataset(dataset_name: str = "dental-anatomy-v1", minimum_per_family: int = 100) -> dict:
    """Audit the assembled manifest, split isolation, labels, and physical files."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.validate_anatomy_dataset import validate_dataset

    manifest = Path(f"/datasets/{dataset_name}/anatomy_manifest.json")
    if not manifest.is_file():
        raise FileNotFoundError(f"Missing anatomy manifest: {manifest}")
    result = validate_dataset(
        manifest,
        expected_dataset_id=dataset_name,
        minimum_per_family=minimum_per_family,
        require_files=True,
    )
    print(json.dumps(result, indent=2), flush=True)
    return result


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    timeout=30 * 60,
)
def build_reference_benchmark(dataset_name: str = "dental-anatomy-v1", per_family: int = 8) -> dict:
    """Seal a balanced evaluation cohort that never enters optimizer metadata."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.build_reference_benchmark_manifest import build_reference_manifest

    root = Path(f"/datasets/{dataset_name}")
    result = build_reference_manifest(
        root / "anatomy_manifest.json",
        root / "benchmark_reference_manifest.json",
        per_family=per_family,
    )
    dataset_volume.commit()
    return result


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    timeout=30 * 60,
)
def build_spike_cohort(
    dataset_name: str = "dental-anatomy-v1",
    per_family: int = 125,
    maximum_per_group: int = 4,
) -> dict:
    """Seal the balanced pre-audit cohort; this does not authorize training."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.build_anatomy_spike_manifest import build_spike_manifest

    root = Path(f"/datasets/{dataset_name}")
    reference = root / "benchmark_reference_manifest.json"
    if not reference.is_file():
        raise FileNotFoundError("Seal benchmark_reference_manifest.json before selecting a spike cohort.")
    result = build_spike_manifest(
        root / "anatomy_manifest.json",
        reference,
        root / "spike_500_pre_audit_manifest.json",
        per_family=per_family,
        maximum_per_group=maximum_per_group,
    )
    dataset_volume.commit()
    print(json.dumps({key: value for key, value in result.items() if key != "items"}, indent=2), flush=True)
    return result


preprocess_image = (
    trellis_gpu_image
    .apt_install(
        "wget",
        "xz-utils",
        "libxrender1",
        "libxi6",
        "libxkbcommon-x11-0",
        "libsm6",
        "libxfixes3",
        "libgl1",
    )
    .run_commands(
        "wget -q https://download.blender.org/release/Blender3.0/blender-3.0.1-linux-x64.tar.xz -O /tmp/blender.tar.xz",
        "tar -xJf /tmp/blender.tar.xz -C /tmp",
        "test -x /tmp/blender-3.0.1-linux-x64/blender",
    )
    .pip_install("pandas")
    .add_local_dir("scripts", remote_path="/root/scripts", copy=True)
)


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    timeout=2 * 60 * 60,
)
def prepare_reference_baseline_inputs(
    dataset_name: str = "dental-anatomy-v1",
    num_cond_views: int = 24,
    selected_view: int = 0,
) -> dict:
    """Render and seal fixed single-image inputs for the unchanged-model baseline."""
    import shutil
    import sys

    sys.path.insert(0, "/root")
    from scripts.preprocess_anatomy_trellis import ensure_data_toolkit, install_dataset_module
    from scripts.render_conditional_batches import render_selected_assets, validate_selected

    if selected_view < 0 or selected_view >= num_cond_views:
        raise ValueError("selected_view must be within num_cond_views")
    root = Path(f"/datasets/{dataset_name}")
    reference_path = root / "benchmark_reference_manifest.json"
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    rows = [{"sha256": item["canonicalSha256"]} for item in reference["items"]]
    toolkit = ensure_data_toolkit(Path(TRELLIS2_PATH))
    install_dataset_module(Path(TRELLIS2_PATH), Path("/root/scripts"))
    rendered = render_selected_assets(
        toolkit=toolkit, dataset_root=root, subset="DentalAnatomy",
        rows=rows, num_cond_views=num_cond_views,
    )
    if not rendered["valid"]:
        dataset_volume.commit()
        raise RuntimeError(f"Reference input rendering failed: {json.dumps(rendered)}")
    target = root / "benchmark_inputs_v1"
    target.mkdir(parents=True, exist_ok=True)
    cases = []
    for item in reference["items"]:
        source = root / "renders_cond" / item["canonicalSha256"] / f"{selected_view:03d}.png"
        destination = target / f"{item['id']}.png"
        shutil.copyfile(source, destination)
        cases.append({
            "id": item["id"], "toothFamily": item["toothFamily"],
            "fdiNumber": item.get("fdiNumber"), "groupId": item["groupId"],
            "referenceMesh": item["referenceMesh"],
            "referenceMeshSha256": item["canonicalSha256"],
            "inputImage": str(destination.relative_to(root)).replace("\\", "/"),
            "inputImageSha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "viewIndex": selected_view, "generationSeed": 1724708096,
            "quality": "standard", "baselineStatus": "pending",
        })
    result = {
        "schemaVersion": 1, "benchmarkId": reference["benchmarkId"],
        "caseCount": len(cases), "numCondViews": num_cond_views,
        "selectedView": selected_view, "modelRole": "unchanged-production-baseline",
        "cases": cases,
    }
    (root / "benchmark_inputs_v1.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    dataset_volume.commit()
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, indent=2), flush=True)
    return result


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100",
    timeout=2 * 60 * 60,
)
def generate_reference_baseline(
    dataset_name: str = "dental-anatomy-v1",
    max_cases: int = 4,
    samples: int = 5000,
) -> dict:
    """Generate a resumable, family-balanced baseline from the pinned raw model."""
    import sys

    if MODEL_NAME != BASE_MODEL_NAME or MODEL_REVISION != BASE_MODEL_REVISION:
        raise RuntimeError(
            "Baseline generation requires the unchanged pinned base model; "
            f"resolved {MODEL_NAME}@{MODEL_REVISION}"
        )
    if max_cases < 1 or max_cases > 32:
        raise ValueError("max_cases must be between 1 and 32")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    root = Path(f"/datasets/{dataset_name}")
    inputs_path = root / "benchmark_inputs_v1.json"
    if not inputs_path.is_file():
        raise FileNotFoundError(
            "Missing sealed benchmark inputs; run prepare_reference_baseline_inputs first"
        )
    inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    selected = []
    per_family = {family: [] for family in ("incisor", "canine", "premolar", "molar")}
    for case in inputs["cases"]:
        per_family[case["toothFamily"]].append(case)
    while len(selected) < max_cases:
        made_progress = False
        for family in per_family:
            if per_family[family] and len(selected) < max_cases:
                selected.append(per_family[family].pop(0))
                made_progress = True
        if not made_progress:
            break
    output_dir = root / "baseline_outputs_v1"
    receipt_dir = root / "baseline_receipts_v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    generator = TrellisGenerator()
    generator.load_model()
    receipts = []
    for index, case in enumerate(selected, start=1):
        output_path = output_dir / f"{case['id']}.glb"
        receipt_path = receipt_dir / f"{case['id']}.json"
        if output_path.is_file() and receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if (
                receipt.get("inputImageSha256") == case["inputImageSha256"]
                and receipt.get("baseModelRevision") == BASE_MODEL_REVISION
                and receipt.get("generationSeed") == case["generationSeed"]
            ):
                receipts.append(receipt)
                continue
        image_path = root / case["inputImage"]
        image_bytes = image_path.read_bytes()
        trace_id = f"baseline-{case['id']}"
        glb, resolved_seed, timings, pipeline_type = generator.generate_glb_from_bytes(
            image_bytes,
            quality=case["quality"],
            seed=case["generationSeed"],
            content_type="image/png",
            trace_id=trace_id,
        )
        output_path.write_bytes(glb)
        reference = load_mesh(root / case["referenceMesh"])
        prediction = load_mesh(output_path)
        metrics = compare_meshes(
            reference, prediction, samples=samples, seed=case["generationSeed"]
        )
        receipt = {
            "schemaVersion": 1,
            "id": case["id"],
            "toothFamily": case["toothFamily"],
            "fdiNumber": case.get("fdiNumber"),
            "inputImage": case["inputImage"],
            "inputImageSha256": case["inputImageSha256"],
            "referenceMesh": case["referenceMesh"],
            "referenceMeshSha256": case["referenceMeshSha256"],
            "outputGlb": str(output_path.relative_to(root)).replace("\\", "/"),
            "outputGlbSha256": hashlib.sha256(glb).hexdigest(),
            "generationSeed": resolved_seed,
            "quality": case["quality"],
            "pipelineType": pipeline_type,
            "timings": timings,
            "anatomyQuality": generator.last_metrics.get("anatomyQuality"),
            "metrics": metrics,
            "modelRole": "unchanged-raw-base-model",
            "modelName": BASE_MODEL_NAME,
            "baseModelRevision": BASE_MODEL_REVISION,
            "trellisCommit": TRELLIS_COMMIT,
        }
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        receipts.append(receipt)
        dataset_volume.commit()
        print(f"Baseline {index}/{len(selected)} complete: {case['id']}", flush=True)
    report = {
        "schemaVersion": 1,
        "benchmarkId": inputs["benchmarkId"],
        "modelRole": "unchanged-raw-base-model",
        "modelName": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "caseCount": len(receipts),
        "completeForRequestedCases": len(receipts) == len(selected),
        "receipts": receipts,
    }
    (root / "baseline_report_v1.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    dataset_volume.commit()
    return {key: value for key, value in report.items() if key != "receipts"}


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={"/datasets": dataset_volume},
    cpu=4,
    memory=32768,
    timeout=60 * 60,
)
def analyze_reference_baseline_topology(dataset_name: str = "dental-anatomy-v1") -> dict:
    """Measure raw baseline component structure without repairing or replacing it."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.analyze_mesh_topology import analyze_mesh
    from scripts.reconstruction_benchmark import load_mesh

    root = Path(f"/datasets/{dataset_name}")
    report_path = root / "baseline_report_v1.json"
    if not report_path.is_file():
        raise FileNotFoundError(report_path)
    baseline = json.loads(report_path.read_text(encoding="utf-8"))
    cases = []
    for receipt in baseline.get("receipts", []):
        prediction_path = root / receipt["outputGlb"]
        reference_path = root / receipt["referenceMesh"]
        cases.append({
            "id": receipt["id"],
            "toothFamily": receipt["toothFamily"],
            "prediction": analyze_mesh(load_mesh(prediction_path)),
            "reference": analyze_mesh(load_mesh(reference_path)),
            "predictionSha256": receipt["outputGlbSha256"],
            "referenceSha256": receipt["referenceMeshSha256"],
        })
        print(f"Topology analysed: {receipt['id']}", flush=True)
    result = {
        "schemaVersion": 1,
        "sourceReport": "baseline_report_v1.json",
        "sourceModelRole": baseline.get("modelRole"),
        "caseCount": len(cases),
        "cases": cases,
    }
    output = root / "baseline_topology_analysis_v1.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return result


def summarize_candidate_comparison(
    baseline_receipts: list[dict], candidate_receipts: list[dict]
) -> dict:
    """Create an explicit, direction-aware preliminary comparison.

    This four-case screen can reject a candidate, but it cannot authorize a
    clinical claim or production promotion.
    """
    baseline_by_id = {row["id"]: row for row in baseline_receipts}
    candidate_by_id = {row["id"]: row for row in candidate_receipts}
    if set(baseline_by_id) != set(candidate_by_id):
        raise ValueError("Candidate and baseline case IDs must match exactly")
    definitions = {
        "symmetricChamferPercentDiagonal": "lower",
        "hausdorff95PercentDiagonal": "lower",
        "surfaceFscoreAt2Percent": "higher",
        "sortedExtentRelativeError": "lower",
    }
    cases = []
    for case_id in baseline_by_id:
        baseline = baseline_by_id[case_id]
        candidate = candidate_by_id[case_id]
        deltas = {}
        for metric, direction in definitions.items():
            before = float(baseline["metrics"][metric])
            after = float(candidate["metrics"][metric])
            raw = after - before
            deltas[metric] = {
                "baseline": before,
                "candidate": after,
                "absoluteDelta": round(raw, 6),
                "improved": raw < 0 if direction == "lower" else raw > 0,
                "direction": direction,
            }
        cases.append({
            "id": case_id,
            "toothFamily": baseline["toothFamily"],
            "metrics": deltas,
            "baselineTopology": baseline.get("topology"),
            "candidateTopology": candidate.get("topology"),
        })
    aggregate = {}
    for metric, direction in definitions.items():
        before = sum(row["metrics"][metric]["baseline"] for row in cases) / len(cases)
        after = sum(row["metrics"][metric]["candidate"] for row in cases) / len(cases)
        raw = after - before
        aggregate[metric] = {
            "baselineMean": round(before, 6),
            "candidateMean": round(after, 6),
            "absoluteDelta": round(raw, 6),
            "relativeDelta": round(raw / before, 6) if before else None,
            "improved": raw < 0 if direction == "lower" else raw > 0,
            "direction": direction,
        }
    preliminary_pass = (
        aggregate["symmetricChamferPercentDiagonal"]["improved"]
        and aggregate["surfaceFscoreAt2Percent"]["improved"]
        and aggregate["hausdorff95PercentDiagonal"]["relativeDelta"] <= 0.05
        and aggregate["sortedExtentRelativeError"]["relativeDelta"] <= 0.05
    )
    return {
        "caseCount": len(cases),
        "cases": cases,
        "aggregate": aggregate,
        "preliminaryScreenPassed": preliminary_pass,
        "productionPromotionPermitted": False,
        "clinicalClaimPermitted": False,
        "screenInterpretation": (
            "eligible-for-larger-blinded-evaluation" if preliminary_pass
            else "reject-or-revise-before-larger-evaluation"
        ),
    }


def assert_paired_sparse_condition_identity(
    baseline_receipts: list[dict], candidate_receipts: list[dict]
) -> None:
    """Fail closed unless every model pair consumed one identical frozen tensor."""
    baseline_by_id = {row["id"]: row for row in baseline_receipts}
    candidate_by_id = {row["id"]: row for row in candidate_receipts}
    if set(baseline_by_id) != set(candidate_by_id) or not baseline_by_id:
        raise ValueError("Paired sparse validation requires identical non-empty case IDs")
    for case_id in sorted(baseline_by_id):
        baseline = baseline_by_id[case_id]
        candidate = candidate_by_id[case_id]
        base_frozen = baseline.get("frozenSparseCondition", {}).get("coordsSha256")
        candidate_frozen = candidate.get("frozenSparseCondition", {}).get("coordsSha256")
        base_observed = baseline.get("boundary", {}).get("sparseCoordsSha256")
        candidate_observed = candidate.get("boundary", {}).get("sparseCoordsSha256")
        if not base_frozen or len({base_frozen, candidate_frozen, base_observed, candidate_observed}) != 1:
            raise RuntimeError(f"Frozen sparse condition identity failed for paired case {case_id}")


def summarize_stage1_validation(
    baseline_receipts: list[dict],
    candidate_receipts: list[dict],
    *,
    bootstrap_samples: int = 10_000,
    bootstrap_seed: int = 20260919,
) -> dict:
    """Apply the preregistered paired Stage-1 anatomy and non-regression gates."""
    import numpy as np

    if bootstrap_samples != 10_000 or bootstrap_seed != 20260919:
        raise ValueError("Stage-1 bootstrap contract is fixed at 10,000 samples and seed 20260919")
    baseline_by_id = {row["id"]: row for row in baseline_receipts}
    candidate_by_id = {row["id"]: row for row in candidate_receipts}
    if set(baseline_by_id) != set(candidate_by_id) or len(baseline_by_id) != 12:
        raise ValueError("Stage-1 validation requires the same 12 cases for base and candidate")
    improvements = []
    family_improvements = {family: [] for family in ("incisor", "canine", "premolar", "molar")}
    for case_id in sorted(baseline_by_id):
        baseline = baseline_by_id[case_id]
        candidate = candidate_by_id[case_id]
        before = float(baseline["metrics"]["symmetricChamferPercentDiagonal"])
        after = float(candidate["metrics"]["symmetricChamferPercentDiagonal"])
        if before <= 0:
            raise ValueError(f"Baseline Chamfer must be positive for {case_id}")
        improvement = (before - after) / before
        improvements.append(improvement)
        family_improvements[baseline["toothFamily"]].append(improvement)
    values = np.asarray(improvements, dtype=np.float64)
    rng = np.random.default_rng(bootstrap_seed)
    indices = rng.integers(0, len(values), size=(bootstrap_samples, len(values)))
    bootstrap_medians = np.median(values[indices], axis=1)
    ci_low, ci_high = np.quantile(bootstrap_medians, [0.025, 0.975])
    engineering = evaluate_e3_engineering_gates(baseline_receipts, candidate_receipts)
    comparison = summarize_candidate_comparison(baseline_receipts, candidate_receipts)
    repeatability = {
        "criterion": "normalized-surface-repeatability-v1",
        "limits": {
            "symmetricChamferPercentDiagonal": 0.25,
            "hausdorff95PercentDiagonal": 0.75,
            "sortedExtentRelativeError": 0.01,
        },
        "baseEveryFamilyStable": all(
            row.get("repeatability", {}).get("geometricallyStable") is True
            for row in baseline_receipts if row.get("repeatability") is not None
        ),
        "candidateEveryFamilyStable": all(
            row.get("repeatability", {}).get("geometricallyStable") is True
            for row in candidate_receipts if row.get("repeatability") is not None
        ),
        "baseFamilyCount": sum(row.get("repeatability") is not None for row in baseline_receipts),
        "candidateFamilyCount": sum(row.get("repeatability") is not None for row in candidate_receipts),
    }
    repeatability["passed"] = (
        repeatability["baseEveryFamilyStable"]
        and repeatability["candidateEveryFamilyStable"]
        and repeatability["baseFamilyCount"] == 4
        and repeatability["candidateFamilyCount"] == 4
    )
    median_improvement = float(np.median(values))
    passed = (
        median_improvement >= 0.05
        and float(ci_low) > 0.0
        and engineering["passed"]
        and repeatability["passed"]
    )
    return {
        "schemaVersion": 1,
        "gate": "stage1-whole-tooth-validation-v1",
        "caseCount": len(values),
        "pairedChamferRelativeImprovements": [float(value) for value in values],
        "medianPairedChamferRelativeImprovement": median_improvement,
        "bootstrap95PercentInterval": [float(ci_low), float(ci_high)],
        "bootstrapSamples": bootstrap_samples,
        "bootstrapSeed": bootstrap_seed,
        "familyMedianImprovements": {
            family: float(np.median(rows)) for family, rows in family_improvements.items()
        },
        "engineeringNonRegression": engineering,
        "repeatability": repeatability,
        "comparison": comparison,
        "passed": passed,
        "seedBAuthorized": passed,
        "clinicalImprovementClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def summarize_e10_g2_screen(
    baseline_receipts: list[dict], candidate_receipts: list[dict]
) -> dict:
    """Seal E10 G2: one frozen-condition, repeatable case per tooth family.

    G2 is an engineering safety screen, not an efficacy claim.  It authorizes
    the bounded 50-step canary only when every family preserves the registered
    crown/root proxies and welded topology at the raw decode boundary.
    """
    expected = {"incisor", "canine", "premolar", "molar"}
    assert_paired_sparse_condition_identity(baseline_receipts, candidate_receipts)
    for role, rows in (("base", baseline_receipts), ("candidate", candidate_receipts)):
        families = [row.get("toothFamily") for row in rows]
        if len(rows) != 4 or set(families) != expected or len(set(families)) != 4:
            raise ValueError(f"E10 G2 {role} requires exactly one case per tooth family")
        if not all(row.get("repeatability", {}).get("rawShapeExact") is True for row in rows):
            raise ValueError(f"E10 G2 {role} raw decode repeatability failed")
    engineering = evaluate_e3_engineering_gates(baseline_receipts, candidate_receipts)
    by_id = {row["id"]: row for row in baseline_receipts}
    deltas = {}
    for candidate in candidate_receipts:
        baseline = by_id[candidate["id"]]
        before = float(baseline["metrics"]["symmetricChamferPercentDiagonal"])
        after = float(candidate["metrics"]["symmetricChamferPercentDiagonal"])
        deltas[candidate["toothFamily"]] = {
            "base": before,
            "candidate": after,
            "relativeImprovement": (before - after) / before,
        }
    passed = engineering["passed"]
    return {
        "schemaVersion": 1,
        "gate": "e10-g2-four-family-engineering-screen-v1",
        "caseCount": 4,
        "familyChamfer": deltas,
        "engineeringNonRegression": engineering,
        "rawRepeatabilityPassed": True,
        "passed": passed,
        "g3Authorized": passed,
        "clinicalImprovementClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def summarize_e12_g2_decoder_screen(
    baseline_receipts: list[dict], candidate_receipts: list[dict]
) -> dict:
    """Four-family decoder screen with explicit crown gain and root safety."""
    import numpy as np

    expected = {"incisor", "canine", "premolar", "molar"}
    baseline_by_id = {row["id"]: row for row in baseline_receipts}
    candidate_by_id = {row["id"]: row for row in candidate_receipts}
    if set(baseline_by_id) != set(candidate_by_id) or len(baseline_by_id) != 4:
        raise ValueError("E12 G2 requires four identical paired case IDs")
    if {row.get("toothFamily") for row in baseline_receipts} != expected:
        raise ValueError("E12 G2 baseline must contain one case per tooth family")
    if {row.get("toothFamily") for row in candidate_receipts} != expected:
        raise ValueError("E12 G2 candidate must contain one case per tooth family")
    rows = []
    for case_id in sorted(baseline_by_id):
        baseline = baseline_by_id[case_id]
        candidate = candidate_by_id[case_id]
        latent_hashes = {
            baseline.get("frozenLatentSha256"), candidate.get("frozenLatentSha256"),
            baseline.get("boundary", {}).get("inputLatentSha256"),
            candidate.get("boundary", {}).get("inputLatentSha256"),
        }
        if None in latent_hashes or len(latent_hashes) != 1:
            raise RuntimeError(f"E12 G2 frozen latent identity failed for {case_id}")
        if not baseline.get("repeatability", {}).get("rawShapeExact"):
            raise RuntimeError(f"E12 G2 base repeatability failed for {case_id}")
        if not candidate.get("repeatability", {}).get("rawShapeExact"):
            raise RuntimeError(f"E12 G2 candidate repeatability failed for {case_id}")
        base_crown = baseline["metrics"]["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]
        candidate_crown = candidate["metrics"]["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]
        before = float(base_crown["symmetricChamferPercentDiagonal"])
        after = float(candidate_crown["symmetricChamferPercentDiagonal"])
        whole_before = float(baseline["metrics"]["symmetricChamferPercentDiagonal"])
        whole_after = float(candidate["metrics"]["symmetricChamferPercentDiagonal"])
        rows.append({
            "id": case_id,
            "toothFamily": baseline["toothFamily"],
            "crownChamferRelativeImprovement": (before - after) / before,
            "wholeToothChamferRelativeImprovement": (whole_before - whole_after) / whole_before,
        })
    engineering = evaluate_e3_engineering_gates(baseline_receipts, candidate_receipts)
    crown_values = np.asarray(
        [row["crownChamferRelativeImprovement"] for row in rows], dtype=np.float64
    )
    whole_values = np.asarray(
        [row["wholeToothChamferRelativeImprovement"] for row in rows], dtype=np.float64
    )
    crown_improved_families = int(np.sum(crown_values > 0.0))
    passed = (
        engineering["passed"]
        and float(np.median(crown_values)) > 0.0
        and crown_improved_families >= 3
        and float(np.median(whole_values)) >= 0.0
    )
    return {
        "schemaVersion": 1,
        "gate": "e12-g2-four-family-decoder-screen-v1",
        "caseCount": 4,
        "cases": rows,
        "medianCrownChamferRelativeImprovement": float(np.median(crown_values)),
        "familiesWithCrownChamferImprovement": crown_improved_families,
        "medianWholeToothChamferRelativeImprovement": float(np.median(whole_values)),
        "engineeringNonRegression": engineering,
        "rawRepeatabilityPassed": True,
        "passed": passed,
        "e13Authorized": passed,
        "clinicalImprovementClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def summarize_r04d_four_family_screen(
    baseline_receipts: list[dict], candidate_receipts: list[dict]
) -> dict:
    """Seal the first matched image-conditioned screen of the R0.4C adapter.

    This is an efficacy *screen*, not a clinical claim.  The candidate may
    advance only when crown error improves across families while the existing
    root, cervical, topology, and exact-repeatability contracts do not regress.
    """
    import numpy as np

    expected = {"incisor", "canine", "premolar", "molar"}
    baseline_by_id = {row["id"]: row for row in baseline_receipts}
    candidate_by_id = {row["id"]: row for row in candidate_receipts}
    if set(baseline_by_id) != set(candidate_by_id) or len(baseline_by_id) != 4:
        raise ValueError("R0.4D requires four identical paired case IDs")
    for role, receipts in (("base", baseline_receipts), ("candidate", candidate_receipts)):
        if {row.get("toothFamily") for row in receipts} != expected:
            raise ValueError(f"R0.4D {role} requires one case per tooth family")
        if not all(row.get("repeatability", {}).get("rawShapeExact") for row in receipts):
            raise ValueError(f"R0.4D {role} raw repeatability failed")

    rows = []
    for case_id in sorted(baseline_by_id):
        baseline = baseline_by_id[case_id]
        candidate = candidate_by_id[case_id]
        pairing = {
            "inputImageSha256": baseline.get("inputImageSha256") == candidate.get("inputImageSha256"),
            "referenceMeshSha256": baseline.get("referenceMeshSha256") == candidate.get("referenceMeshSha256"),
            "generationSeed": baseline.get("generationSeed") == candidate.get("generationSeed"),
            "quality": baseline.get("quality") == candidate.get("quality"),
        }
        if not all(pairing.values()):
            raise RuntimeError(f"R0.4D matched-input contract failed for {case_id}: {pairing}")
        base_crown = baseline["metrics"]["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]
        candidate_crown = candidate["metrics"]["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]
        crown_before = float(base_crown["symmetricChamferPercentDiagonal"])
        crown_after = float(candidate_crown["symmetricChamferPercentDiagonal"])
        whole_before = float(baseline["metrics"]["symmetricChamferPercentDiagonal"])
        whole_after = float(candidate["metrics"]["symmetricChamferPercentDiagonal"])
        rows.append({
            "id": case_id,
            "toothFamily": baseline["toothFamily"],
            "pairing": pairing,
            "crownChamferRelativeImprovement": (crown_before - crown_after) / crown_before,
            "wholeToothChamferRelativeImprovement": (whole_before - whole_after) / whole_before,
        })

    engineering = evaluate_e3_engineering_gates(baseline_receipts, candidate_receipts)
    crown = np.asarray([row["crownChamferRelativeImprovement"] for row in rows], dtype=np.float64)
    whole = np.asarray([row["wholeToothChamferRelativeImprovement"] for row in rows], dtype=np.float64)
    families_improved = int(np.sum(crown > 0.0))
    passed = (
        engineering["passed"]
        and float(np.median(crown)) > 0.0
        and families_improved >= 3
        and float(np.median(whole)) >= 0.0
    )
    return {
        "schemaVersion": 1,
        "gate": "r04d-four-family-image-conditioned-screen-v1",
        "caseCount": 4,
        "cases": rows,
        "medianCrownChamferRelativeImprovement": float(np.median(crown)),
        "familiesWithCrownChamferImprovement": families_improved,
        "medianWholeToothChamferRelativeImprovement": float(np.median(whole)),
        "engineeringNonRegression": engineering,
        "rawRepeatabilityPassed": True,
        "passed": passed,
        "boundedTrainingAuthorized": passed,
        "clinicalImprovementClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def summarize_r0_stage_attribution(
    oracle_receipts: list[dict], product_receipts: list[dict]
) -> dict:
    """Attribute reference-latent versus image-conditioned crown error."""
    import numpy as np
    from collections import Counter

    oracle = {row["id"]: row for row in oracle_receipts}
    product = {row["id"]: row for row in product_receipts}
    if set(oracle) != set(product) or len(oracle) != 12:
        raise ValueError("R0 requires twelve identical oracle/product case IDs")
    families = Counter(row["toothFamily"] for row in oracle_receipts)
    if families != Counter({family: 3 for family in ("incisor", "canine", "premolar", "molar")}):
        raise ValueError("R0 requires three cases per tooth family")
    product_families = Counter(row["toothFamily"] for row in product_receipts)
    if product_families != families:
        raise ValueError("R0 product family balance does not match the oracle cohort")
    rows = []
    for case_id in sorted(oracle):
        left, right = oracle[case_id], product[case_id]
        if (
            left.get("referenceMeshSha256") != right.get("referenceMeshSha256")
            or left.get("toothFamily") != right.get("toothFamily")
            or left.get("groupId") != right.get("groupId")
        ):
            raise ValueError(f"R0 pairing drift for {case_id}")
        left_regions = left["metrics"]["canonicalAxialAnatomyProxy"]["regions"]
        right_regions = right["metrics"]["canonicalAxialAnatomyProxy"]["regions"]
        oracle_crown = float(left_regions["crownProxy"]["symmetricChamferPercentDiagonal"])
        product_crown = float(right_regions["crownProxy"]["symmetricChamferPercentDiagonal"])
        compared_root_regions = [
            name for name in ("apicalRootProxy", "middleRootProxy")
            if isinstance(left_regions.get(name, {}).get("symmetricChamferPercentDiagonal"), (int, float))
            and isinstance(right_regions.get(name, {}).get("symmetricChamferPercentDiagonal"), (int, float))
        ]
        if not compared_root_regions:
            raise ValueError(f"R0 has no paired available root region for {case_id}")
        oracle_root = float(np.median([
            left_regions[name]["symmetricChamferPercentDiagonal"]
            for name in compared_root_regions
        ]))
        product_root = float(np.median([
            right_regions[name]["symmetricChamferPercentDiagonal"]
            for name in compared_root_regions
        ]))
        if min(oracle_crown, product_crown, oracle_root, product_root) <= 0.0:
            raise ValueError(f"R0 requires positive regional Chamfer values for {case_id}")
        rows.append({
            "id": case_id,
            "toothFamily": left["toothFamily"],
            "groupId": left["groupId"],
            "oracleCrownChamferPercentDiagonal": oracle_crown,
            "productCrownChamferPercentDiagonal": product_crown,
            "productToOracleCrownErrorRatio": product_crown / oracle_crown,
            "oracleRootChamferPercentDiagonal": oracle_root,
            "productRootChamferPercentDiagonal": product_root,
            "productToOracleRootErrorRatio": product_root / oracle_root,
            "comparedRootRegions": compared_root_regions,
        })
    crown_oracle = np.asarray([row["oracleCrownChamferPercentDiagonal"] for row in rows])
    crown_product = np.asarray([row["productCrownChamferPercentDiagonal"] for row in rows])
    crown_ratio = np.asarray([row["productToOracleCrownErrorRatio"] for row in rows])
    root_ratio = np.asarray([row["productToOracleRootErrorRatio"] for row in rows])
    oracle_ceiling_adequate = float(np.median(crown_oracle)) <= 1.0
    product_gap_dominant = float(np.median(crown_ratio)) >= 1.5
    dominant = (
        "image-conditioned-generation"
        if oracle_ceiling_adequate and product_gap_dominant
        else "representation-or-decoder"
        if not oracle_ceiling_adequate
        else "inconclusive"
    )
    family_rows = {}
    for family in ("incisor", "canine", "premolar", "molar"):
        selected = [row for row in rows if row["toothFamily"] == family]
        family_rows[family] = {
            "caseCount": len(selected),
            "medianProductToOracleCrownErrorRatio": float(np.median([
                row["productToOracleCrownErrorRatio"] for row in selected
            ])),
            "medianProductToOracleRootErrorRatio": float(np.median([
                row["productToOracleRootErrorRatio"] for row in selected
            ])),
        }
    return {
        "schemaVersion": 1,
        "caseCount": 12,
        "familyCounts": dict(families),
        "cases": rows,
        "familySummary": family_rows,
        "medianOracleCrownChamferPercentDiagonal": float(np.median(crown_oracle)),
        "medianProductCrownChamferPercentDiagonal": float(np.median(crown_product)),
        "medianProductToOracleCrownErrorRatio": float(np.median(crown_ratio)),
        "medianProductToOracleRootErrorRatio": float(np.median(root_ratio)),
        "casesWithBothRootProxyBands": int(sum(
            len(row["comparedRootRegions"]) == 2 for row in rows
        )),
        "oracleCrownCeilingAdequateForAttribution": oracle_ceiling_adequate,
        "productCrownGapDominant": product_gap_dominant,
        "dominantMeasuredBoundary": dominant,
        "trainingBoundaryRecommendation": (
            "image-conditioned-shape-inference"
            if dominant == "image-conditioned-generation" else "do-not-select-yet"
        ),
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def summarize_r01_conditioning_decomposition(
    oracle_receipts: list[dict], product_receipts: list[dict],
    reference_support_receipts: list[dict],
) -> dict:
    """Attribute image-conditioned error to sparse support or shape features."""
    import numpy as np
    from collections import Counter

    roles = {
        "oracle": {row["id"]: row for row in oracle_receipts},
        "product": {row["id"]: row for row in product_receipts},
        "referenceSupport": {row["id"]: row for row in reference_support_receipts},
    }
    ids = set(roles["oracle"])
    if len(ids) != 12 or any(set(rows) != ids for rows in roles.values()):
        raise ValueError("R0.1 requires twelve identical IDs across all three paths")
    families = Counter(row["toothFamily"] for row in oracle_receipts)
    if families != Counter({family: 3 for family in ("incisor", "canine", "premolar", "molar")}):
        raise ValueError("R0.1 requires three cases per tooth family")
    rows = []
    for case_id in sorted(ids):
        oracle = roles["oracle"][case_id]
        product = roles["product"][case_id]
        support = roles["referenceSupport"][case_id]
        identity = {
            (row.get("referenceMeshSha256"), row.get("toothFamily"), row.get("groupId"))
            for row in (oracle, product, support)
        }
        if len(identity) != 1:
            raise ValueError(f"R0.1 pairing drift for {case_id}")
        crown = {}
        for name, receipt in (("oracle", oracle), ("product", product), ("referenceSupport", support)):
            crown[name] = float(
                receipt["metrics"]["canonicalAxialAnatomyProxy"]["regions"]
                ["crownProxy"]["symmetricChamferPercentDiagonal"]
            )
        gap = crown["product"] - crown["oracle"]
        fraction_closed = (
            (crown["product"] - crown["referenceSupport"]) / gap
            if gap > 0.0 else 0.0
        )
        rows.append({
            "id": case_id,
            "toothFamily": oracle["toothFamily"],
            "groupId": oracle["groupId"],
            "oracleCrownChamferPercentDiagonal": crown["oracle"],
            "productCrownChamferPercentDiagonal": crown["product"],
            "referenceSupportCrownChamferPercentDiagonal": crown["referenceSupport"],
            "crownGapFractionClosedByReferenceSupport": fraction_closed,
            "referenceSupportToOracleCrownErrorRatio": (
                crown["referenceSupport"] / crown["oracle"]
            ),
        })
    fractions = np.asarray([
        row["crownGapFractionClosedByReferenceSupport"] for row in rows
    ], dtype=np.float64)
    median_fraction = float(np.median(fractions))
    dominant = (
        "image-to-sparse-structure"
        if median_fraction >= 0.5 else
        "image-conditioned-shape-features"
        if median_fraction <= 0.2 else
        "mixed-sparse-structure-and-shape-features"
    )
    family_summary = {}
    for family in ("incisor", "canine", "premolar", "molar"):
        selected = [row for row in rows if row["toothFamily"] == family]
        family_summary[family] = {
            "caseCount": 3,
            "medianCrownGapFractionClosedByReferenceSupport": float(np.median([
                row["crownGapFractionClosedByReferenceSupport"] for row in selected
            ])),
            "medianReferenceSupportToOracleCrownErrorRatio": float(np.median([
                row["referenceSupportToOracleCrownErrorRatio"] for row in selected
            ])),
        }
    return {
        "schemaVersion": 1,
        "caseCount": 12,
        "familyCounts": dict(families),
        "cases": rows,
        "familySummary": family_summary,
        "medianCrownGapFractionClosedByReferenceSupport": median_fraction,
        "casesWithPositiveCrownGapClosure": int(np.sum(fractions > 0.0)),
        "dominantMeasuredSubBoundary": dominant,
        "adapterTargetRecommendation": dominant,
        "decisionThresholds": {
            "sparseStructureDominantAtOrAbove": 0.5,
            "shapeFeaturesDominantAtOrBelow": 0.2,
        },
        "trainingAuthorized": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def resolve_e12_g2_validation_cases(
    validation: dict, manifest: dict,
    families: tuple[str, ...] = ("incisor", "canine", "premolar", "molar"),
) -> list[dict]:
    """Join sealed validation cases to canonical manifest assets fail-closed."""
    assets_by_id: dict[str, list[dict]] = {}
    for asset in manifest.get("assets", []):
        assets_by_id.setdefault(asset.get("id"), []).append(asset)
    resolved = []
    for family in families:
        matches = sorted(
            (case for case in validation.get("cases", []) if case.get("toothFamily") == family),
            key=lambda case: case["id"],
        )
        if not matches:
            raise ValueError(f"E12 G2 has no sealed validation case for {family}")
        case = matches[0]
        assets = assets_by_id.get(case["id"], [])
        if len(assets) != 1:
            raise ValueError(
                f"E12 G2 requires one canonical manifest asset for {case['id']}, found {len(assets)}"
            )
        asset = assets[0]
        checks = {
            "split": asset.get("split") == "validation",
            "toothFamily": asset.get("toothFamily") == case.get("toothFamily"),
            "groupId": asset.get("groupId") == case.get("groupId"),
            "fdiNumber": int(asset.get("fdiNumber")) == int(case.get("fdiNumber")),
            "canonicalPath": asset.get("canonicalPath") == case.get("referenceMesh"),
            "canonicalSha256": asset.get("canonicalSha256") == case.get("referenceMeshSha256"),
        }
        if not all(checks.values()):
            failed = sorted(name for name, passed in checks.items() if not passed)
            raise ValueError(f"E12 G2 manifest join drift for {case['id']}: {failed}")
        digest = asset.get("canonicalSha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"E12 G2 canonical digest is invalid for {case['id']}")
        resolved.append({**case, "canonicalSha256": digest})
    if len({case["id"] for case in resolved}) != len(families):
        raise ValueError("E12 G2 resolved duplicate validation cases")
    return resolved


def evaluate_e3_engineering_gates(
    baseline_receipts: list[dict], candidate_receipts: list[dict]
) -> dict:
    """Apply every executable E3 engineering non-regression gate per case."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.regional_anatomy_gate import evaluate_regional_non_regression

    baseline_by_id = {row["id"]: row for row in baseline_receipts}
    candidate_by_id = {row["id"]: row for row in candidate_receipts}
    if set(baseline_by_id) != set(candidate_by_id) or not baseline_by_id:
        raise ValueError("E3 gate inputs require identical non-empty case IDs")
    cases = []
    reasons = []
    for case_id in sorted(baseline_by_id):
        baseline = baseline_by_id[case_id]
        candidate = candidate_by_id[case_id]
        regional = evaluate_regional_non_regression(
            baseline["metrics"], candidate["metrics"]
        )
        before = baseline["topology"]["coincidentVertexWeldedTopology"]
        after = candidate["topology"]["coincidentVertexWeldedTopology"]
        topology_checks = {
            "componentCount": after["componentCount"] <= before["componentCount"],
            "largestComponentAreaFraction": (
                after["largestComponentAreaFraction"] + 1e-6
                >= before["largestComponentAreaFraction"]
            ),
            "boundaryEdgeCount": after["boundaryEdgeCount"] <= before["boundaryEdgeCount"],
            "nonManifoldEdgeCount": (
                after["nonManifoldEdgeCount"] <= before["nonManifoldEdgeCount"]
            ),
        }
        if not regional["passed"]:
            reasons.extend(f"{case_id}:regional:{reason}" for reason in regional["reasons"])
        for name, passed in topology_checks.items():
            if not passed:
                reasons.append(f"{case_id}:topology:{name}-regressed")
        cases.append({
            "id": case_id,
            "toothFamily": baseline["toothFamily"],
            "regional": regional,
            "topologyChecks": topology_checks,
            "passed": regional["passed"] and all(topology_checks.values()),
        })
    return {
        "schemaVersion": 1,
        "gate": "e3-engineering-non-regression-v1",
        "passed": not reasons,
        "cases": cases,
        "reasons": reasons,
        "clinicalLandmarkClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def sparse_occupancy_metrics(coords: object, resolution: int) -> dict:
    """Summarize one decoded sparse occupancy without downstream mesh inference."""
    import numpy as np

    array = np.asarray(coords, dtype=np.int64)
    if array.ndim != 2 or array.shape[1] not in (3, 4):
        raise ValueError("Sparse coordinates must have shape [N, 3] or [N, 4]")
    if array.shape[1] == 4:
        if array.size and np.any(array[:, 0] != 0):
            raise ValueError("Diagnostic accepts exactly one sparse occupancy batch")
        array = array[:, 1:]
    if resolution <= 0 or (array.size and (array.min() < 0 or array.max() >= resolution)):
        raise ValueError("Sparse coordinates fall outside the declared resolution")
    unique = {tuple(int(value) for value in row) for row in array}
    if not unique:
        raise ValueError("Decoded sparse occupancy is empty")

    remaining = set(unique)
    component_sizes: list[int] = []
    offsets = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        size = 0
        while stack:
            voxel = stack.pop()
            size += 1
            for offset in offsets:
                neighbor = tuple(voxel[axis] + offset[axis] for axis in range(3))
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        component_sizes.append(size)

    ordered = np.asarray(sorted(unique), dtype=np.int64)
    minimum = ordered.min(axis=0)
    maximum = ordered.max(axis=0)
    return {
        "resolution": int(resolution),
        "voxelCount": len(unique),
        "coordinateSha256": hashlib.sha256(ordered.tobytes()).hexdigest(),
        "boundsMin": minimum.tolist(),
        "boundsMax": maximum.tolist(),
        "boundsExtent": (maximum - minimum + 1).tolist(),
        "centroid": ordered.mean(axis=0).tolist(),
        "componentCount6Connected": len(component_sizes),
        "largestComponentVoxelFraction": max(component_sizes) / len(unique),
    }


def compare_sparse_occupancies(base_coords: object, candidate_coords: object, resolution: int) -> dict:
    """Compare decoded occupancy sets at the representation boundary."""
    import numpy as np

    def coordinate_set(coords: object) -> set[tuple[int, int, int]]:
        array = np.asarray(coords, dtype=np.int64)
        if array.ndim != 2 or array.shape[1] not in (3, 4):
            raise ValueError("Sparse coordinates must have shape [N, 3] or [N, 4]")
        if array.shape[1] == 4:
            if array.size and np.any(array[:, 0] != 0):
                raise ValueError("Diagnostic accepts exactly one sparse occupancy batch")
            array = array[:, 1:]
        return {tuple(int(value) for value in row) for row in array}

    base = coordinate_set(base_coords)
    candidate = coordinate_set(candidate_coords)
    if not base or not candidate:
        raise ValueError("Both sparse occupancies must be non-empty")
    intersection = base & candidate
    union = base | candidate
    base_metrics = sparse_occupancy_metrics(np.asarray(sorted(base)), resolution)
    candidate_metrics = sparse_occupancy_metrics(np.asarray(sorted(candidate)), resolution)
    centroid_shift = math.dist(base_metrics["centroid"], candidate_metrics["centroid"])
    return {
        "base": base_metrics,
        "candidate": candidate_metrics,
        "intersectionVoxelCount": len(intersection),
        "unionVoxelCount": len(union),
        "voxelIoU": len(intersection) / len(union),
        "addedVoxelCount": len(candidate - base),
        "removedVoxelCount": len(base - candidate),
        "candidateVoxelCountRelativeChange": (
            candidate_metrics["voxelCount"] - base_metrics["voxelCount"]
        ) / base_metrics["voxelCount"],
        "centroidShiftVoxels": centroid_shift,
        "centroidShiftFractionResolution": centroid_shift / resolution,
        "exactlyEqual": base == candidate,
    }


def characterize_sparse_support_error(
    reference_coords: object, predicted_coords: object, resolution: int = 64,
) -> dict:
    """Measure sparse-support error globally and in canonical axial proxy bands."""
    import numpy as np

    def coordinate_set(coords: object) -> set[tuple[int, int, int]]:
        array = np.asarray(coords, dtype=np.int64)
        if array.ndim != 2 or array.shape[1] not in (3, 4):
            raise ValueError("Sparse coordinates must have shape [N, 3] or [N, 4]")
        if array.shape[1] == 4:
            if array.size and np.any(array[:, 0] != 0):
                raise ValueError("R0.2 accepts one sparse occupancy batch")
            array = array[:, 1:]
        result = {tuple(int(value) for value in row) for row in array}
        if not result:
            raise ValueError("R0.2 sparse occupancy cannot be empty")
        if min(min(row) for row in result) < 0 or max(max(row) for row in result) >= resolution:
            raise ValueError("R0.2 coordinates fall outside the declared resolution")
        return result

    reference = coordinate_set(reference_coords)
    predicted = coordinate_set(predicted_coords)
    reference_array = np.asarray(sorted(reference), dtype=np.int64)
    predicted_array = np.asarray(sorted(predicted), dtype=np.int64)
    z_min, z_max = int(reference_array[:, 2].min()), int(reference_array[:, 2].max())
    z_span = max(z_max - z_min, 1)
    bands = {
        "apicalRootProxy": (0.0, 0.25),
        "middleRootProxy": (0.25, 0.55),
        "cervicalProxy": (0.55, 0.72),
        "crownProxy": (0.72, 1.0000001),
    }

    def select_band(values: set[tuple[int, int, int]], lower: float, upper: float):
        selected = set()
        for row in values:
            normalized = min(max((row[2] - z_min) / z_span, 0.0), 1.0)
            if lower <= normalized < upper:
                selected.add(row)
        return selected

    def overlap(reference_set, predicted_set):
        intersection = reference_set & predicted_set
        union = reference_set | predicted_set
        return {
            "referenceVoxelCount": len(reference_set),
            "predictedVoxelCount": len(predicted_set),
            "intersectionVoxelCount": len(intersection),
            "missingVoxelCount": len(reference_set - predicted_set),
            "extraVoxelCount": len(predicted_set - reference_set),
            "precision": len(intersection) / len(predicted_set) if predicted_set else 0.0,
            "recall": len(intersection) / len(reference_set) if reference_set else 0.0,
            "voxelIoU": len(intersection) / len(union) if union else 0.0,
        }

    reference_metrics = sparse_occupancy_metrics(reference_array, resolution)
    predicted_metrics = sparse_occupancy_metrics(predicted_array, resolution)
    band_metrics = {}
    for name, (lower, upper) in bands.items():
        reference_band = select_band(reference, lower, upper)
        predicted_band = select_band(predicted, lower, upper)
        if not reference_band:
            raise ValueError(f"R0.2 reference has no occupancy in {name}")
        band_metrics[name] = overlap(reference_band, predicted_band)
    reference_extent = np.asarray(reference_metrics["boundsExtent"], dtype=np.float64)
    predicted_extent = np.asarray(predicted_metrics["boundsExtent"], dtype=np.float64)
    return {
        "schemaVersion": 1,
        "resolution": resolution,
        "reference": reference_metrics,
        "predicted": predicted_metrics,
        "global": overlap(reference, predicted),
        "bands": band_metrics,
        "centroidShiftVoxels": float(math.dist(
            reference_metrics["centroid"], predicted_metrics["centroid"]
        )),
        "extentRelativeErrorByAxis": (
            np.abs(predicted_extent - reference_extent) / reference_extent
        ).tolist(),
        "apicalPoleAbsoluteErrorVoxels": abs(
            int(predicted_array[:, 2].min()) - z_min
        ),
        "coronalPoleAbsoluteErrorVoxels": abs(
            int(predicted_array[:, 2].max()) - z_max
        ),
        "proxyBandDisclaimer": "canonical axial engineering proxies; not clinical CEJ/enamel/root labels",
    }


def build_crown_transition_weights_from_occupancy(
    occupancy: object,
    transition_start: float = 0.55,
    crown_start: float = 0.72,
) -> tuple[object, list[dict]]:
    """Build per-tooth crown weights while leaving the root region exactly zero.

    The longest occupied spatial axis is treated as the dental long axis. The
    wider terminal is selected as the crown proxy. Values are zero root-side,
    smoothstep through the cervical transition, and one in the crown. This is
    an engineering proxy until reviewed CEJ annotations replace it.
    """
    import torch

    mask = torch.as_tensor(occupancy, dtype=torch.bool)
    if mask.ndim == 4:
        mask = mask[:, None]
    if mask.ndim != 5 or mask.shape[1] != 1:
        raise ValueError("E14 occupancy must have shape [B,1,D,H,W] or [B,D,H,W]")
    if not 0.0 < transition_start < crown_start < 1.0:
        raise ValueError("E14 crown thresholds must satisfy 0 < transition < crown < 1")
    weights = torch.zeros_like(mask, dtype=torch.float32)
    receipts = []
    for batch_index in range(mask.shape[0]):
        occupied = mask[batch_index, 0]
        indices = occupied.nonzero(as_tuple=False)
        if indices.numel() == 0:
            raise ValueError(f"E14 occupancy is empty for batch {batch_index}")
        bounds = [(int(indices[:, axis].min()), int(indices[:, axis].max())) for axis in range(3)]
        axial_axis = max(range(3), key=lambda axis: bounds[axis][1] - bounds[axis][0])
        axial_min, axial_max = bounds[axial_axis]
        axial_span = max(axial_max - axial_min, 1)
        coordinates = torch.arange(mask.shape[axial_axis + 2], device=mask.device, dtype=torch.float32)
        normalized = ((coordinates - axial_min) / float(axial_span)).clamp(0.0, 1.0)
        view_shape = [1, 1, 1]
        view_shape[axial_axis] = mask.shape[axial_axis + 2]
        normalized_grid = normalized.view(view_shape)
        lower_terminal = normalized_grid <= (1.0 - crown_start)
        upper_terminal = normalized_grid >= crown_start
        lower_count = int((occupied & lower_terminal).sum().item())
        upper_count = int((occupied & upper_terminal).sum().item())
        crown_is_upper = upper_count >= lower_count
        crown_coordinate = normalized_grid if crown_is_upper else 1.0 - normalized_grid
        progress = ((crown_coordinate - transition_start) / (crown_start - transition_start)).clamp(0.0, 1.0)
        sample_weights = progress.square() * (3.0 - 2.0 * progress)
        weights[batch_index, 0] = sample_weights.expand_as(occupied)
        receipts.append({
            "batchIndex": batch_index,
            "axialSpatialOffset": axial_axis,
            "axialBounds": [axial_min, axial_max],
            "crownDirection": "upper" if crown_is_upper else "lower",
            "lowerTerminalReferenceVoxelCount": lower_count,
            "upperTerminalReferenceVoxelCount": upper_count,
            "rootVoxelCount": int((sample_weights == 0).sum().item()),
            "transitionVoxelCount": int(((sample_weights > 0) & (sample_weights < 1)).sum().item()),
            "crownVoxelCount": int((sample_weights == 1).sum().item()),
        })
    return weights, receipts


def compose_crown_residual_logits(base_logits: object, residual_logits: object, weights: object):
    """Apply residuals only where E14 weights are positive; copy roots exactly."""
    import torch

    base = torch.as_tensor(base_logits)
    residual = torch.as_tensor(residual_logits, device=base.device, dtype=base.dtype)
    blend = torch.as_tensor(weights, device=base.device, dtype=base.dtype)
    if base.shape != residual.shape or base.shape != blend.shape:
        raise ValueError("E14 base, residual and weight tensors must share a shape")
    return torch.where(blend > 0, base + residual * blend, base)


def summarize_r02_sparse_support_characterization(
    case_receipts: list[dict], r01_summary: dict,
) -> dict:
    """Summarize R0.2 sparse errors and link them to R0.1 geometry response."""
    import numpy as np
    from collections import Counter

    if len(case_receipts) != 12 or len({row["id"] for row in case_receipts}) != 12:
        raise ValueError("R0.2 requires twelve unique case receipts")
    families = Counter(row["toothFamily"] for row in case_receipts)
    if families != Counter({family: 3 for family in ("incisor", "canine", "premolar", "molar")}):
        raise ValueError("R0.2 requires three cases per tooth family")
    response_by_id = {
        row["id"]: row["crownGapFractionClosedByReferenceSupport"]
        for row in r01_summary.get("cases", [])
    }
    if set(response_by_id) != {row["id"] for row in case_receipts}:
        raise ValueError("R0.2/R0.1 case IDs must pair exactly")
    bands = ("apicalRootProxy", "middleRootProxy", "cervicalProxy", "crownProxy")
    rows = []
    for receipt in case_receipts:
        metrics = receipt["metrics"]
        rows.append({
            "id": receipt["id"],
            "toothFamily": receipt["toothFamily"],
            "globalPrecision": metrics["global"]["precision"],
            "globalRecall": metrics["global"]["recall"],
            "globalVoxelIoU": metrics["global"]["voxelIoU"],
            "centroidShiftVoxels": metrics["centroidShiftVoxels"],
            "crownGapFractionClosedByReferenceSupport": response_by_id[receipt["id"]],
            "bandPrecision": {name: metrics["bands"][name]["precision"] for name in bands},
            "bandRecall": {name: metrics["bands"][name]["recall"] for name in bands},
            "bandIoU": {name: metrics["bands"][name]["voxelIoU"] for name in bands},
        })
    global_precision = np.asarray([row["globalPrecision"] for row in rows])
    global_recall = np.asarray([row["globalRecall"] for row in rows])
    gap_closure = np.asarray([row["crownGapFractionClosedByReferenceSupport"] for row in rows])
    recall_gap_correlation = (
        float(np.corrcoef(global_recall, gap_closure)[0, 1])
        if float(np.std(global_recall)) > 0.0 and float(np.std(gap_closure)) > 0.0
        else None
    )
    band_summary = {}
    for name in bands:
        band_summary[name] = {
            "medianPrecision": float(np.median([row["bandPrecision"][name] for row in rows])),
            "medianRecall": float(np.median([row["bandRecall"][name] for row in rows])),
            "medianVoxelIoU": float(np.median([row["bandIoU"][name] for row in rows])),
        }
    weakest_recall_band = min(bands, key=lambda name: band_summary[name]["medianRecall"])
    dominant_error = (
        "missing-reference-occupancy"
        if float(np.median(global_recall)) < float(np.median(global_precision))
        else "extra-predicted-occupancy"
    )
    family_summary = {}
    for family in ("incisor", "canine", "premolar", "molar"):
        selected = [row for row in rows if row["toothFamily"] == family]
        family_summary[family] = {
            "caseCount": 3,
            "medianGlobalPrecision": float(np.median([row["globalPrecision"] for row in selected])),
            "medianGlobalRecall": float(np.median([row["globalRecall"] for row in selected])),
            "medianGlobalVoxelIoU": float(np.median([row["globalVoxelIoU"] for row in selected])),
            "medianCrownRecall": float(np.median([row["bandRecall"]["crownProxy"] for row in selected])),
        }
    return {
        "schemaVersion": 1,
        "caseCount": 12,
        "familyCounts": dict(families),
        "cases": rows,
        "medianGlobalPrecision": float(np.median(global_precision)),
        "medianGlobalRecall": float(np.median(global_recall)),
        "medianGlobalVoxelIoU": float(np.median([row["globalVoxelIoU"] for row in rows])),
        "medianCentroidShiftVoxels": float(np.median([row["centroidShiftVoxels"] for row in rows])),
        "bandSummary": band_summary,
        "familySummary": family_summary,
        "dominantSparseErrorPattern": dominant_error,
        "weakestMedianRecallBand": weakest_recall_band,
        "pearsonGlobalRecallVersusCrownGapClosure": recall_gap_correlation,
        "adapterDesignAuthorized": True,
        "optimizerRunAuthorized": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def align_sparse_support_integer_translation(
    reference_coords: object, predicted_coords: object,
    *, resolution: int = 32, maximum_shift: int = 6,
) -> dict:
    """Find the deterministic bounded integer translation maximizing sparse IoU."""
    import numpy as np

    def xyz(coords: object) -> np.ndarray:
        array = np.asarray(coords, dtype=np.int64)
        if array.ndim != 2 or array.shape[1] not in (3, 4):
            raise ValueError("R0.3 coordinates must have shape [N, 3] or [N, 4]")
        if array.shape[1] == 4:
            if array.size and np.any(array[:, 0] != 0):
                raise ValueError("R0.3 accepts one sparse occupancy batch")
            array = array[:, 1:]
        if not len(array):
            raise ValueError("R0.3 occupancy cannot be empty")
        return np.asarray(sorted(set(map(tuple, array.tolist()))), dtype=np.int64)

    if maximum_shift != 6 or resolution != 32:
        raise ValueError("R0.3 search is sealed to resolution 32 and +/-6 voxels")
    reference = xyz(reference_coords)
    predicted = xyz(predicted_coords)
    reference_set = set(map(tuple, reference.tolist()))
    raw_metrics = characterize_sparse_support_error(reference, predicted, resolution)
    shifts = sorted(
        (
            (dx, dy, dz)
            for dx in range(-maximum_shift, maximum_shift + 1)
            for dy in range(-maximum_shift, maximum_shift + 1)
            for dz in range(-maximum_shift, maximum_shift + 1)
        ),
        key=lambda shift: (
            sum(abs(value) for value in shift),
            sum(value * value for value in shift),
            shift,
        ),
    )
    best_shift = (0, 0, 0)
    best_intersection = len(reference_set & set(map(tuple, predicted.tolist())))
    best_array = predicted
    for shift in shifts:
        translated = predicted + np.asarray(shift, dtype=np.int64)
        if translated.min() < 0 or translated.max() >= resolution:
            continue
        intersection = sum(tuple(row) in reference_set for row in translated.tolist())
        if intersection > best_intersection:
            best_intersection = intersection
            best_shift = shift
            best_array = translated
    aligned_metrics = characterize_sparse_support_error(reference, best_array, resolution)
    raw_iou = float(raw_metrics["global"]["voxelIoU"])
    aligned_iou = float(aligned_metrics["global"]["voxelIoU"])
    raw_crown_iou = float(raw_metrics["bands"]["crownProxy"]["voxelIoU"])
    aligned_crown_iou = float(aligned_metrics["bands"]["crownProxy"]["voxelIoU"])
    return {
        "schemaVersion": 1,
        "resolution": resolution,
        "maximumShiftVoxelsPerAxis": maximum_shift,
        "bestTranslationXYZ": list(best_shift),
        "bestTranslationMagnitudeVoxels": float(math.dist((0, 0, 0), best_shift)),
        "raw": raw_metrics,
        "aligned": aligned_metrics,
        "globalIoUAbsoluteGain": aligned_iou - raw_iou,
        "globalIoUErrorFractionClosed": (
            (aligned_iou - raw_iou) / (1.0 - raw_iou) if raw_iou < 1.0 else 0.0
        ),
        "crownIoUAbsoluteGain": aligned_crown_iou - raw_crown_iou,
        "crownIoUErrorFractionClosed": (
            (aligned_crown_iou - raw_crown_iou) / (1.0 - raw_crown_iou)
            if raw_crown_iou < 1.0 else 0.0
        ),
    }


def summarize_r03_alignment_decomposition(case_receipts: list[dict]) -> dict:
    """Decide whether rigid coordinate alignment or morphology dominates."""
    import numpy as np
    from collections import Counter

    if len(case_receipts) != 12 or len({row["id"] for row in case_receipts}) != 12:
        raise ValueError("R0.3 requires twelve unique cases")
    families = Counter(row["toothFamily"] for row in case_receipts)
    if families != Counter({family: 3 for family in ("incisor", "canine", "premolar", "molar")}):
        raise ValueError("R0.3 requires three cases per family")
    global_closed = np.asarray([
        row["alignment"]["globalIoUErrorFractionClosed"] for row in case_receipts
    ])
    crown_closed = np.asarray([
        row["alignment"]["crownIoUErrorFractionClosed"] for row in case_receipts
    ])
    median_global = float(np.median(global_closed))
    median_crown = float(np.median(crown_closed))
    dominant = (
        "coordinate-frame-alignment"
        if median_crown >= 0.5 else
        "morphology-and-occupancy"
        if median_crown <= 0.2 else
        "mixed-alignment-and-morphology"
    )
    family_summary = {}
    for family in ("incisor", "canine", "premolar", "molar"):
        selected = [row for row in case_receipts if row["toothFamily"] == family]
        family_summary[family] = {
            "caseCount": 3,
            "medianGlobalIoUErrorFractionClosed": float(np.median([
                row["alignment"]["globalIoUErrorFractionClosed"] for row in selected
            ])),
            "medianCrownIoUErrorFractionClosed": float(np.median([
                row["alignment"]["crownIoUErrorFractionClosed"] for row in selected
            ])),
            "medianAlignedCrownIoU": float(np.median([
                row["alignment"]["aligned"]["bands"]["crownProxy"]["voxelIoU"]
                for row in selected
            ])),
        }
    return {
        "schemaVersion": 1,
        "caseCount": 12,
        "familyCounts": dict(families),
        "medianGlobalIoUErrorFractionClosedByTranslation": median_global,
        "medianCrownIoUErrorFractionClosedByTranslation": median_crown,
        "medianTranslationMagnitudeVoxels": float(np.median([
            row["alignment"]["bestTranslationMagnitudeVoxels"] for row in case_receipts
        ])),
        "casesWithNonzeroBestTranslation": int(sum(
            row["alignment"]["bestTranslationXYZ"] != [0, 0, 0]
            for row in case_receipts
        )),
        "familySummary": family_summary,
        "dominantMeasuredSubBoundary": dominant,
        "decisionThresholds": {
            "alignmentDominantAtOrAboveCrownErrorFractionClosed": 0.5,
            "morphologyDominantAtOrBelowCrownErrorFractionClosed": 0.2,
        },
        "adapterObjectiveDesignAuthorized": dominant != "coordinate-frame-alignment",
        "optimizerRunAuthorized": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def qualify_r04_sparse_adapter_objective(
    reference_coords: object,
    predicted_coords: object,
    *,
    resolution: int = 32,
    adapter_rank: int = 4,
    seed: int = 20260921,
) -> dict:
    """Zero-step differentiability probe for the crown support objective.

    This deliberately does not load or update TRELLIS.2.  It places a tiny,
    deterministic residual adapter over the union of the sealed predicted and
    reference sparse supports and proves that missing crown occupancy, extra
    crown occupancy and non-crown preservation all provide usable gradients.
    Passing this probe authorizes model-integration work, never training.
    """
    import numpy as np
    import torch
    import torch.nn.functional as F

    if resolution != 32 or adapter_rank != 4 or seed != 20260921:
        raise ValueError("R0.4 objective probe is sealed to resolution 32, rank 4 and seed 20260921")

    def support(value: object) -> set[tuple[int, int, int]]:
        array = np.asarray(value, dtype=np.int64)
        if array.ndim != 2 or array.shape[1] not in (3, 4):
            raise ValueError("R0.4 coordinates must have shape [N, 3] or [N, 4]")
        if array.shape[1] == 4:
            if array.size and np.any(array[:, 0] != 0):
                raise ValueError("R0.4 accepts one sparse occupancy batch")
            array = array[:, 1:]
        result = {tuple(map(int, row)) for row in array.tolist()}
        if not result:
            raise ValueError("R0.4 support cannot be empty")
        if min(map(min, result)) < 0 or max(map(max, result)) >= resolution:
            raise ValueError("R0.4 support falls outside the sealed grid")
        return result

    reference, predicted = support(reference_coords), support(predicted_coords)
    union = sorted(reference | predicted)
    coordinates = torch.tensor(union, dtype=torch.float32)
    normalized_xyz = (coordinates / float(resolution - 1)) * 2.0 - 1.0
    predicted_present = torch.tensor(
        [float(row in predicted) for row in union], dtype=torch.float32,
    )
    target = torch.tensor(
        [float(row in reference) for row in union], dtype=torch.float32,
    )
    features = torch.cat([
        normalized_xyz,
        predicted_present[:, None],
        torch.ones((len(union), 1), dtype=torch.float32),
    ], dim=1)

    generator = torch.Generator(device="cpu").manual_seed(seed)
    down = torch.nn.Parameter(torch.randn((adapter_rank, 5), generator=generator) * 0.02)
    up = torch.nn.Parameter(torch.randn((1, adapter_rank), generator=generator) * 0.02)
    down_bias = torch.nn.Parameter(torch.randn((adapter_rank,), generator=generator) * 0.01)
    up_bias = torch.nn.Parameter(torch.randn((1,), generator=generator) * 0.01)
    parameters = {
        "down.weight": down, "down.bias": down_bias,
        "up.weight": up, "up.bias": up_bias,
    }
    delta = F.linear(F.silu(F.linear(features, down, down_bias)), up, up_bias).squeeze(1)
    base_logits = torch.where(predicted_present > 0.5, 2.0, -2.0)
    logits = base_logits + delta

    reference_z = torch.tensor([row[2] for row in reference], dtype=torch.float32)
    z_min, z_max = reference_z.min(), reference_z.max()
    normalized_z = ((coordinates[:, 2] - z_min) / (z_max - z_min).clamp_min(1.0)).clamp(0, 1)
    crown = normalized_z >= 0.72
    missing_crown = crown & (target > 0.5) & (predicted_present < 0.5)
    extra_crown = crown & (target < 0.5) & (predicted_present > 0.5)
    non_crown = ~crown
    if not non_crown.any():
        raise ValueError("R0.4 requires non-crown support for preservation")

    native = F.binary_cross_entropy_with_logits(logits, target)
    # A real case may contain only one crown error direction.  An absent
    # category is represented by a differentiable exact zero; cohort-level
    # qualification below still requires both missing and extra voxels.
    missing = (
        F.binary_cross_entropy_with_logits(logits[missing_crown], target[missing_crown])
        if missing_crown.any() else logits.sum() * 0.0
    )
    extra = (
        F.binary_cross_entropy_with_logits(logits[extra_crown], target[extra_crown])
        if extra_crown.any() else logits.sum() * 0.0
    )
    preservation = delta[non_crown].square().mean()
    loss = native + 0.5 * missing + 0.5 * extra + 0.05 * preservation

    component_gradients = {}
    for name, component in {
        "nativeSupportBce": native,
        "crownMissingBce": missing,
        "crownExtraBce": extra,
        "nonCrownTeacherMse": preservation,
    }.items():
        grads = torch.autograd.grad(component, list(parameters.values()), retain_graph=True, allow_unused=True)
        component_gradients[name] = {
            key: None if grad is None else float(grad.detach().float().norm().item())
            for key, grad in zip(parameters, grads)
        }
    total_grads = torch.autograd.grad(loss, list(parameters.values()))
    gradient_norms = {
        key: float(grad.detach().float().norm().item())
        for key, grad in zip(parameters, total_grads)
    }
    finite_terms = all(math.isfinite(float(value.detach().item())) for value in (
        native, missing, extra, preservation, loss,
    ))
    finite_nonzero = all(math.isfinite(value) and value > 0.0 for value in gradient_norms.values())
    preservation_active = any(
        value is not None and math.isfinite(value) and value > 0.0
        for value in component_gradients["nonCrownTeacherMse"].values()
    )
    return {
        "schemaVersion": 1,
        "optimizerSteps": 0,
        "adapterRank": adapter_rank,
        "adapterParameterTensorCount": len(parameters),
        "adapterParameterCount": int(sum(parameter.numel() for parameter in parameters.values())),
        "unionVoxelCount": len(union),
        "missingCrownVoxelCount": int(missing_crown.sum().item()),
        "extraCrownVoxelCount": int(extra_crown.sum().item()),
        "nonCrownVoxelCount": int(non_crown.sum().item()),
        "terms": {
            "nativeSupportBce": float(native.detach().item()),
            "crownMissingBce": float(missing.detach().item()),
            "crownExtraBce": float(extra.detach().item()),
            "nonCrownTeacherMse": float(preservation.detach().item()),
            "loss": float(loss.detach().item()),
        },
        "componentGradientNorms": component_gradients,
        "totalGradientNorms": gradient_norms,
        "finiteObjectiveTerms": finite_terms,
        "everyAdapterTensorFiniteNonzeroGradient": finite_nonzero,
        "nonCrownPreservationGradientActive": preservation_active,
        "objectiveQualified": finite_terms and finite_nonzero and preservation_active,
        "modelIntegrationAuthorized": finite_terms and finite_nonzero and preservation_active,
        "oneStepIntegrationAuthorized": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def summarize_r04_sparse_adapter_objective(case_receipts: list[dict]) -> dict:
    """Require the zero-step objective to qualify on all four tooth families."""
    from collections import Counter

    if len(case_receipts) != 12 or len({row["id"] for row in case_receipts}) != 12:
        raise ValueError("R0.4 requires twelve unique cases")
    families = Counter(row["toothFamily"] for row in case_receipts)
    expected = Counter({family: 3 for family in ("incisor", "canine", "premolar", "molar")})
    if families != expected:
        raise ValueError("R0.4 requires three cases per tooth family")
    total_missing = sum(row["probe"]["missingCrownVoxelCount"] for row in case_receipts)
    total_extra = sum(row["probe"]["extraCrownVoxelCount"] for row in case_receipts)
    passed = (
        total_missing > 0
        and total_extra > 0
        and all(row["probe"]["objectiveQualified"] for row in case_receipts)
    )
    return {
        "schemaVersion": 1,
        "caseCount": 12,
        "familyCounts": dict(families),
        "qualifiedCaseCount": sum(row["probe"]["objectiveQualified"] for row in case_receipts),
        "missingCrownVoxelCount": total_missing,
        "extraCrownVoxelCount": total_extra,
        "allCasesObjectiveQualified": passed,
        "allCasesPreservationGradientActive": all(
            row["probe"]["nonCrownPreservationGradientActive"] for row in case_receipts
        ),
        "modelIntegrationAuthorized": passed,
        "oneStepIntegrationAuthorized": False,
        "optimizerRunAuthorized": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def r04b_sparse_adapter_target(model_config: dict) -> str:
    """Resolve the one sealed LoRA insertion point from the official model config."""
    model = model_config.get("models", {}).get("denoiser", {})
    args = model.get("args", {})
    if model.get("name") != "SparseStructureFlowModel":
        raise ValueError("R0.4B requires the official SparseStructureFlowModel")
    block_count = int(args.get("num_blocks", 0))
    channels = int(args.get("model_channels", 0))
    if block_count <= 0 or channels <= 0:
        raise ValueError("R0.4B requires positive transformer depth and width")
    return f"blocks.{block_count - 1}.mlp.mlp.2"


def r04b_lora_wrapper_source() -> str:
    """Return the audited rank-4 residual wrapper used by the real-model probe."""
    return '''import torch

class DentalSculptorR04BLoRALinear(torch.nn.Module):
    def __init__(self, base, rank=4, seed=20260921):
        super().__init__()
        if not isinstance(base, torch.nn.Linear) or rank != 4:
            raise ValueError("R0.4B requires a Linear target and rank four")
        self.base = base.requires_grad_(False)
        generator = torch.Generator(device="cpu").manual_seed(seed)
        self.lora_down = torch.nn.Parameter((torch.randn(rank, base.in_features, generator=generator, dtype=torch.float32) * 1e-4).to(base.weight.device))
        self.lora_up = torch.nn.Parameter((torch.randn(base.out_features, rank, generator=generator, dtype=torch.float32) * 1e-4).to(base.weight.device))
        self.scale = 1.0 / rank
    def forward(self, value):
        base_value = self.base(value)
        adapted = torch.nn.functional.linear(
            torch.nn.functional.linear(value.float(), self.lora_down), self.lora_up
        ) * self.scale
        return base_value + adapted.to(dtype=base_value.dtype)
'''


def r04b_install_adapter_flow_source(source: str) -> str:
    """Install the sealed LoRA after base trainer construction; never add it to an optimizer."""
    anchor = "        super().__init__(*args, **kwargs)\n        self.t_schedule = t_schedule"
    replacement = (
        "        super().__init__(*args, **kwargs)\n"
        "        model = self.models['denoiser']\n"
        "        if len(model.blocks) != 30:\n"
        "            raise RuntimeError('R0.4B sparse transformer depth drifted')\n"
        "        for parameter in model.parameters():\n"
        "            parameter.requires_grad_(False)\n"
        "        target = model.blocks[29].mlp.mlp[2]\n"
        "        if not isinstance(target, torch.nn.Linear):\n"
        "            raise RuntimeError('R0.4B target is no longer Linear')\n"
        "        model.blocks[29].mlp.mlp[2] = DentalSculptorR04BLoRALinear(target)\n"
        "        self.dentalsculptor_r04b_adapter = model.blocks[29].mlp.mlp[2]\n"
        "        self.dentalsculptor_r04b_frozen_hashes = {}\n"
        "        for name, parameter in model.named_parameters():\n"
        "            if '.lora_' in name:\n"
        "                continue\n"
        "            normalized_name = name.replace('.base.', '.')\n"
        "            raw = parameter.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()\n"
        "            self.dentalsculptor_r04b_frozen_hashes[normalized_name] = hashlib.sha256(raw).hexdigest()\n"
        "        self.t_schedule = t_schedule"
    )
    if source.count(anchor) != 1:
        raise ValueError("Pinned flow initialization changed; refusing R0.4B adapter patch")
    return r04b_lora_wrapper_source() + "\nimport hashlib\n" + source.replace(anchor, replacement)


def r04b_zero_step_sparse_loss_source(source: str) -> str:
    """Measure real native-loss adapter gradients and stop before optimizer execution."""
    anchor = (
        "        terms[\"mse\"] = F.mse_loss(pred.feats, target.feats)\n"
        "        terms[\"loss\"] = terms[\"mse\"]"
    )
    replacement = anchor + (
        "\n        receipt_path = os.environ.get('DENTALSCULPTOR_R04B_RECEIPT')\n"
        "        if receipt_path:\n"
        "            adapter = self.dentalsculptor_r04b_adapter\n"
        "            named_adapter = [('lora_down', adapter.lora_down), ('lora_up', adapter.lora_up)]\n"
        "            gradients = torch.autograd.grad(terms['loss'], [p for _, p in named_adapter], allow_unused=True)\n"
        "            gradient_rows = []\n"
        "            for (name, parameter), gradient in zip(named_adapter, gradients):\n"
        "                gradient_rows.append({'name': name, 'shape': list(parameter.shape), 'missing': gradient is None, 'finite': bool(gradient is not None and gradient.isfinite().all()), 'norm': None if gradient is None else float(gradient.detach().float().norm().item())})\n"
        "            frozen_after = {}\n"
        "            for name, parameter in self.models['denoiser'].named_parameters():\n"
        "                if '.lora_' in name:\n"
        "                    continue\n"
        "                normalized_name = name.replace('.base.', '.')\n"
        "                raw = parameter.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()\n"
        "                frozen_after[normalized_name] = hashlib.sha256(raw).hexdigest()\n"
        "            receipt = {'schemaVersion': 1, 'valid': True, 'optimizerSteps': 0, 'adapterTarget': 'blocks.29.mlp.mlp.2', 'adapterRank': 4, 'nativeMse': float(terms['mse'].detach().item()), 'adapterGradients': gradient_rows, 'frozenTensorCount': len(frozen_after), 'frozenStateByteIdentical': frozen_after == self.dentalsculptor_r04b_frozen_hashes}\n"
        "            with open(receipt_path, 'w', encoding='utf-8') as stream:\n"
        "                stream.write(json.dumps(receipt, sort_keys=True) + '\\n')\n"
        "            raise RuntimeError('DENTALSCULPTOR_R04B_ZERO_STEP_COMPLETE')"
    )
    if source.count(anchor) != 1:
        raise ValueError("Pinned sparse loss changed; refusing R0.4B gradient patch")
    return source.replace(anchor, replacement)


def r04b_basic_zero_step_probe_source(source: str) -> str:
    """Seal adapter gradients after the effective backward and before any optimizer path."""
    anchor = "        ## gradient clip\n        if self.grad_clip is not None:"
    replacement = (
        "        ## DentalSculptor R0.4B real-model zero-step gate\n"
        "        receipt_path = os.environ.get('DENTALSCULPTOR_R04B_RECEIPT')\n"
        "        if receipt_path:\n"
        "            adapter = self.dentalsculptor_r04b_adapter\n"
        "            named_adapter = [('lora_down', adapter.lora_down), ('lora_up', adapter.lora_up)]\n"
        "            gradient_rows = []\n"
        "            for name, parameter in named_adapter:\n"
        "                gradient = parameter.grad\n"
        "                gradient_rows.append({'name': name, 'shape': list(parameter.shape), 'missing': gradient is None, 'finite': bool(gradient is not None and gradient.isfinite().all()), 'norm': None if gradient is None else float(gradient.detach().float().norm().item())})\n"
        "            frozen_after = {}\n"
        "            for name, parameter in self.models['denoiser'].named_parameters():\n"
        "                if '.lora_' in name:\n"
        "                    continue\n"
        "                normalized_name = name.replace('.base.', '.')\n"
        "                raw = parameter.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()\n"
        "                frozen_after[normalized_name] = __import__('hashlib').sha256(raw).hexdigest()\n"
        "            native_mse = losses[-1].get('mse') if losses else None\n"
        "            receipt = {'schemaVersion': 2, 'valid': True, 'probeBoundary': 'BasicTrainer.run_step.after-effective-backward-before-gradient-clip', 'optimizerSteps': 0, 'adapterTarget': 'blocks.29.mlp.mlp.2', 'adapterRank': 4, 'nativeMse': native_mse, 'adapterGradients': gradient_rows, 'frozenTensorCount': len(frozen_after), 'frozenStateByteIdentical': frozen_after == self.dentalsculptor_r04b_frozen_hashes}\n"
        "            with open(receipt_path, 'w', encoding='utf-8') as stream:\n"
        "                stream.write(json.dumps(receipt, sort_keys=True) + '\\n')\n"
        "            raise RuntimeError('DENTALSCULPTOR_R04B_ZERO_STEP_COMPLETE')\n"
        "        ## gradient clip\n"
        "        if self.grad_clip is not None:"
    )
    if source.count(anchor) != 1:
        raise ValueError("Pinned BasicTrainer gradient boundary changed; refusing R0.4B probe patch")
    patched = source.replace(anchor, replacement)
    marker = patched.index("DENTALSCULPTOR_R04B_ZERO_STEP_COMPLETE")
    optimizer = patched.index("self.optimizer.step()")
    if marker >= optimizer:
        raise ValueError("R0.4B probe no longer precedes the optimizer boundary")
    return patched


def r04c_install_trainable_adapter_flow_source(source: str) -> str:
    """Install the sealed adapter and replace the optimizer with adapter-only AdamW."""
    patched = r04b_install_adapter_flow_source(source)
    anchor = "        self.dentalsculptor_r04b_adapter = model.blocks[29].mlp.mlp[2]\n"
    replacement = anchor + (
        "        adapter_parameters = [self.dentalsculptor_r04b_adapter.lora_down, self.dentalsculptor_r04b_adapter.lora_up]\n"
        "        self.model_params = adapter_parameters\n"
        "        self.master_params = adapter_parameters\n"
        "        self.optimizer = torch.optim.AdamW(adapter_parameters, lr=1e-6, weight_decay=0.0, betas=(0.9, 0.95), eps=1e-8)\n"
        "        self.dentalsculptor_r04c_adapter_initial = {name: parameter.detach().clone() for name, parameter in [('lora_down', adapter_parameters[0]), ('lora_up', adapter_parameters[1])]}\n"
    )
    if patched.count(anchor) != 1:
        raise ValueError("R0.4C adapter installation boundary changed")
    return patched.replace(anchor, replacement)


def r04c_basic_one_step_probe_source(source: str) -> str:
    """Seal one adapter update after optimizer.step and before scheduler/EMA work."""
    anchor = "        ## adjust learning rate\n        if self.lr_scheduler_config is not None:"
    replacement = (
        "        ## DentalSculptor R0.4C exactly-one-step adapter gate\n"
        "        receipt_path = os.environ.get('DENTALSCULPTOR_R04C_RECEIPT')\n"
        "        checkpoint_path = os.environ.get('DENTALSCULPTOR_R04C_CHECKPOINT')\n"
        "        if receipt_path and checkpoint_path:\n"
        "            adapter = self.dentalsculptor_r04b_adapter\n"
        "            named_adapter = [('lora_down', adapter.lora_down), ('lora_up', adapter.lora_up)]\n"
        "            gradients = []\n"
        "            deltas = []\n"
        "            for name, parameter in named_adapter:\n"
        "                gradient = parameter.grad\n"
        "                delta = parameter.detach().float() - self.dentalsculptor_r04c_adapter_initial[name].float()\n"
        "                gradients.append({'name': name, 'missing': gradient is None, 'finite': bool(gradient is not None and gradient.isfinite().all()), 'norm': None if gradient is None else float(gradient.detach().float().norm().item())})\n"
        "                deltas.append({'name': name, 'finite': bool(delta.isfinite().all()), 'norm': float(delta.norm().item())})\n"
        "            frozen_after = {}\n"
        "            for name, parameter in self.models['denoiser'].named_parameters():\n"
        "                if '.lora_' in name:\n"
        "                    continue\n"
        "                normalized_name = name.replace('.base.', '.')\n"
        "                raw = parameter.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()\n"
        "                frozen_after[normalized_name] = __import__('hashlib').sha256(raw).hexdigest()\n"
        "            merged = {}\n"
        "            for name, value in self.models['denoiser'].state_dict().items():\n"
        "                if '.lora_' in name:\n"
        "                    continue\n"
        "                normalized_name = name.replace('.base.', '.')\n"
        "                merged[normalized_name] = value.detach().cpu().clone()\n"
        "            merged['blocks.29.mlp.mlp.2.weight'] = (adapter.base.weight.detach().float() + adapter.scale * torch.matmul(adapter.lora_up.detach().float(), adapter.lora_down.detach().float())).to(dtype=adapter.base.weight.dtype).cpu()\n"
        "            torch.save(merged, checkpoint_path)\n"
        "            receipt = {'schemaVersion': 1, 'valid': True, 'probeBoundary': 'BasicTrainer.run_step.after-exactly-one-optimizer-step-before-scheduler-and-ema', 'optimizerSteps': 1, 'adapterTarget': 'blocks.29.mlp.mlp.2', 'adapterRank': 4, 'learningRate': 1e-6, 'adapterGradients': gradients, 'adapterDeltas': deltas, 'frozenTensorCount': len(frozen_after), 'frozenStateByteIdentical': frozen_after == self.dentalsculptor_r04b_frozen_hashes, 'mergedCheckpointEntryCount': len(merged)}\n"
        "            with open(receipt_path, 'w', encoding='utf-8') as stream:\n"
        "                stream.write(json.dumps(receipt, sort_keys=True) + '\\n')\n"
        "            raise RuntimeError('DENTALSCULPTOR_R04C_ONE_STEP_COMPLETE')\n"
        "        ## adjust learning rate\n"
        "        if self.lr_scheduler_config is not None:"
    )
    if source.count(anchor) != 1:
        raise ValueError("Pinned BasicTrainer post-step boundary changed; refusing R0.4C patch")
    patched = source.replace(anchor, replacement)
    if patched.index("self.optimizer.step()") >= patched.index("DENTALSCULPTOR_R04C_ONE_STEP_COMPLETE"):
        raise ValueError("R0.4C probe no longer follows the optimizer step")
    return patched


def r05a_install_adapter_flow_source(source: str) -> str:
    """Install the sealed rank-4 adapter with an auditable base-only switch."""
    patched = r04b_install_adapter_flow_source(source)
    anchor = "        base_value = self.base(value)\n        adapted = torch.nn.functional.linear("
    replacement = (
        "        base_value = self.base(value)\n"
        "        if not getattr(self, 'dentalsculptor_adapter_enabled', True):\n"
        "            return base_value\n"
        "        adapted = torch.nn.functional.linear("
    )
    if patched.count(anchor) != 1:
        raise ValueError("R0.5A adapter forward boundary changed")
    return patched.replace(anchor, replacement)


def r05a_regional_objective_sparse_loss_source(source: str) -> str:
    """Add decoded crown occupancy and frozen-base non-crown preservation.

    The native flow loss remains active. Candidate and frozen-base velocities
    are converted back to clean sparse latents and decoded with the official,
    frozen sparse-structure decoder. Only the union of reference/base support
    participates, preventing the empty background from dominating BCE.
    """
    anchor = (
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"loss\"] = terms[\"mse\"]"
    )
    replacement = anchor + (
        "\n        adapter = self.dentalsculptor_r04b_adapter\n"
        "        adapter.dentalsculptor_adapter_enabled = False\n"
        "        try:\n"
        "            with torch.no_grad():\n"
        "                base_pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        finally:\n"
        "            adapter.dentalsculptor_adapter_enabled = True\n"
        "        if not hasattr(self, 'dentalsculptor_r05a_decoder'):\n"
        "            self.dataset._loading_ss_dec()\n"
        "            self.dentalsculptor_r05a_decoder = self.dataset.ss_dec.eval()\n"
        "            for parameter in self.dentalsculptor_r05a_decoder.parameters():\n"
        "                parameter.requires_grad_(False)\n"
        "        candidate_x0 = self.reverse_diffuse(x_t, t, pred)\n"
        "        with torch.no_grad():\n"
        "            base_x0 = self.reverse_diffuse(x_t, t, base_pred)\n"
        "            reference_logits = self.dentalsculptor_r05a_decoder(x_0)\n"
        "            base_logits = self.dentalsculptor_r05a_decoder(base_x0)\n"
        "        candidate_logits = self.dentalsculptor_r05a_decoder(candidate_x0)\n"
        "        reference_occ = reference_logits > 0\n"
        "        base_occ = base_logits > 0\n"
        "        support_union = reference_occ | base_occ\n"
        "        occupied_indices = reference_occ.nonzero(as_tuple=False)\n"
        "        if occupied_indices.numel() == 0:\n"
        "            raise RuntimeError('R0.5A reference decoder occupancy is empty')\n"
        "        spatial_dims = list(range(reference_occ.ndim - 3, reference_occ.ndim))\n"
        "        spatial_bounds = []\n"
        "        for dim in spatial_dims:\n"
        "            values = occupied_indices[:, dim]\n"
        "            spatial_bounds.append((int(values.min().item()), int(values.max().item())))\n"
        "        axial_offset = max(range(3), key=lambda offset: spatial_bounds[offset][1] - spatial_bounds[offset][0])\n"
        "        axial_dim = spatial_dims[axial_offset]\n"
        "        axial_min, axial_max = spatial_bounds[axial_offset]\n"
        "        axial_span = max(axial_max - axial_min, 1)\n"
        "        axial_coordinates = torch.arange(reference_occ.shape[axial_dim], device=reference_occ.device)\n"
        "        axial_shape = [1] * reference_occ.ndim\n"
        "        axial_shape[axial_dim] = reference_occ.shape[axial_dim]\n"
        "        normalized_axial = ((axial_coordinates - axial_min).float() / float(axial_span)).view(axial_shape)\n"
        "        lower_terminal = normalized_axial <= 0.28\n"
        "        upper_terminal = normalized_axial >= 0.72\n"
        "        lower_count = int((reference_occ & lower_terminal).sum().item())\n"
        "        upper_count = int((reference_occ & upper_terminal).sum().item())\n"
        "        crown_is_upper = upper_count >= lower_count\n"
        "        crown = upper_terminal.expand_as(reference_occ) if crown_is_upper else lower_terminal.expand_as(reference_occ)\n"
        "        crown_positive = crown & reference_occ & support_union\n"
        "        extra_crown = crown & ~reference_occ & base_occ\n"
        "        non_crown = ~crown & support_union\n"
        "        if not non_crown.any():\n"
        "            raise RuntimeError('R0.5A non-crown preservation mask is empty')\n"
        "        zero = candidate_logits.sum() * 0.0\n"
        "        crown_positive_bce = F.binary_cross_entropy_with_logits(candidate_logits[crown_positive], torch.ones_like(candidate_logits[crown_positive])) if crown_positive.any() else zero\n"
        "        crown_extra = F.binary_cross_entropy_with_logits(candidate_logits[extra_crown], torch.zeros_like(candidate_logits[extra_crown])) if extra_crown.any() else zero\n"
        "        non_crown_teacher = F.mse_loss(candidate_logits[non_crown], base_logits[non_crown])\n"
        "        non_crown_teacher_probe = F.mse_loss(candidate_logits[non_crown] + 1e-3, base_logits[non_crown])\n"
        "        terms['crown_positive_bce'] = crown_positive_bce\n"
        "        terms['crown_extra_bce'] = crown_extra\n"
        "        terms['non_crown_teacher_mse'] = non_crown_teacher\n"
        "        terms['loss'] = terms['mse'] + 0.5 * crown_positive_bce + 0.5 * crown_extra + 0.05 * non_crown_teacher\n"
        "        named_adapter = [('lora_down', adapter.lora_down), ('lora_up', adapter.lora_up)]\n"
        "        component_gradients = {}\n"
        "        for component_name, component in [('nativeMse', terms['mse']), ('crownPositiveBce', crown_positive_bce), ('crownExtraBce', crown_extra), ('nonCrownTeacherMse', non_crown_teacher), ('nonCrownTeacherProbe', non_crown_teacher_probe)]:\n"
        "            gradients = torch.autograd.grad(component, [parameter for _, parameter in named_adapter], retain_graph=True, allow_unused=True)\n"
        "            component_gradients[component_name] = [{'name': name, 'missing': gradient is None, 'finite': bool(gradient is not None and gradient.isfinite().all()), 'norm': None if gradient is None else float(gradient.detach().float().norm().item())} for (name, _), gradient in zip(named_adapter, gradients)]\n"
        "        self.dentalsculptor_r05a_objective_receipt = {'nativeMse': float(terms['mse'].detach().item()), 'crownPositiveBce': float(crown_positive_bce.detach().item()), 'crownExtraBce': float(crown_extra.detach().item()), 'nonCrownTeacherMse': float(non_crown_teacher.detach().item()), 'nonCrownTeacherProbe': float(non_crown_teacher_probe.detach().item()), 'totalLoss': float(terms['loss'].detach().item()), 'referenceVoxelCount': int(reference_occ.sum().item()), 'supportUnionVoxelCount': int(support_union.sum().item()), 'crownMaskVoxelCount': int((crown & support_union).sum().item()), 'crownPositiveVoxelCount': int(crown_positive.sum().item()), 'extraCrownVoxelCount': int(extra_crown.sum().item()), 'nonCrownVoxelCount': int(non_crown.sum().item()), 'axialSpatialOffset': int(axial_offset), 'axialTensorDimension': int(axial_dim), 'axialBounds': [int(axial_min), int(axial_max)], 'lowerTerminalReferenceVoxelCount': int(lower_count), 'upperTerminalReferenceVoxelCount': int(upper_count), 'crownDirection': 'upper' if crown_is_upper else 'lower', 'componentGradients': component_gradients}\n"
    )
    if source.count(anchor) != 1:
        raise ValueError("Pinned sparse loss changed; refusing R0.5A objective patch")
    return source.replace(anchor, replacement)


def r05a_basic_zero_step_probe_source(source: str) -> str:
    """Seal the integrated objective after backward and before every update."""
    anchor = "        ## gradient clip\n        if self.grad_clip is not None:"
    replacement = (
        "        ## DentalSculptor R0.5A decoded-regional zero-step gate\n"
        "        receipt_path = os.environ.get('DENTALSCULPTOR_R05A_RECEIPT')\n"
        "        if receipt_path:\n"
        "            adapter = self.dentalsculptor_r04b_adapter\n"
        "            gradients = []\n"
        "            for name, parameter in [('lora_down', adapter.lora_down), ('lora_up', adapter.lora_up)]:\n"
        "                gradient = parameter.grad\n"
        "                gradients.append({'name': name, 'missing': gradient is None, 'finite': bool(gradient is not None and gradient.isfinite().all()), 'norm': None if gradient is None else float(gradient.detach().float().norm().item())})\n"
        "            frozen_after = {}\n"
        "            for name, parameter in self.models['denoiser'].named_parameters():\n"
        "                if '.lora_' in name:\n"
        "                    continue\n"
        "                normalized_name = name.replace('.base.', '.')\n"
        "                raw = parameter.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()\n"
        "                frozen_after[normalized_name] = __import__('hashlib').sha256(raw).hexdigest()\n"
        "            receipt = {'schemaVersion': 1, 'valid': True, 'probeBoundary': 'BasicTrainer.run_step.after-integrated-objective-backward-before-gradient-clip', 'optimizerSteps': 0, 'adapterTarget': 'blocks.29.mlp.mlp.2', 'adapterRank': 4, 'objective': self.dentalsculptor_r05a_objective_receipt, 'adapterGradients': gradients, 'frozenTensorCount': len(frozen_after), 'frozenStateByteIdentical': frozen_after == self.dentalsculptor_r04b_frozen_hashes}\n"
        "            with open(receipt_path, 'w', encoding='utf-8') as stream:\n"
        "                stream.write(json.dumps(receipt, sort_keys=True) + '\\n')\n"
        "            raise RuntimeError('DENTALSCULPTOR_R05A_ZERO_STEP_COMPLETE')\n"
        "        ## gradient clip\n"
        "        if self.grad_clip is not None:"
    )
    if source.count(anchor) != 1:
        raise ValueError("Pinned BasicTrainer boundary changed; refusing R0.5A probe")
    patched = source.replace(anchor, replacement)
    if patched.index("DENTALSCULPTOR_R05A_ZERO_STEP_COMPLETE") >= patched.index("self.optimizer.step()"):
        raise ValueError("R0.5A zero-step boundary no longer precedes optimizer")
    return patched


def r05b_install_trainable_adapter_flow_source(source: str) -> str:
    """Install the audited base switch and restrict optimization to the adapter."""
    patched = r05a_install_adapter_flow_source(source)
    anchor = "        self.dentalsculptor_r04b_adapter = model.blocks[29].mlp.mlp[2]\n"
    replacement = anchor + (
        "        adapter_parameters = [self.dentalsculptor_r04b_adapter.lora_down, self.dentalsculptor_r04b_adapter.lora_up]\n"
        "        self.model_params = adapter_parameters\n"
        "        self.master_params = adapter_parameters\n"
        "        self.optimizer = torch.optim.AdamW(adapter_parameters, lr=1e-6, weight_decay=0.0, betas=(0.9, 0.95), eps=1e-8)\n"
        "        self.dentalsculptor_r05b_adapter_initial = {name: parameter.detach().clone() for name, parameter in [('lora_down', adapter_parameters[0]), ('lora_up', adapter_parameters[1])]}\n"
    )
    if patched.count(anchor) != 1:
        raise ValueError("R0.5B adapter installation boundary changed")
    return patched.replace(anchor, replacement)


def r05b_basic_one_step_probe_source(source: str) -> str:
    """Seal one regional-objective adapter update before scheduler and EMA."""
    anchor = "        ## adjust learning rate\n        if self.lr_scheduler_config is not None:"
    replacement = (
        "        ## DentalSculptor R0.5B exactly-one-step regional-objective gate\n"
        "        receipt_path = os.environ.get('DENTALSCULPTOR_R05B_RECEIPT')\n"
        "        checkpoint_path = os.environ.get('DENTALSCULPTOR_R05B_CHECKPOINT')\n"
        "        if receipt_path and checkpoint_path:\n"
        "            adapter = self.dentalsculptor_r04b_adapter\n"
        "            named_adapter = [('lora_down', adapter.lora_down), ('lora_up', adapter.lora_up)]\n"
        "            gradients = []\n"
        "            deltas = []\n"
        "            for name, parameter in named_adapter:\n"
        "                gradient = parameter.grad\n"
        "                delta = parameter.detach().float() - self.dentalsculptor_r05b_adapter_initial[name].float()\n"
        "                gradients.append({'name': name, 'missing': gradient is None, 'finite': bool(gradient is not None and gradient.isfinite().all()), 'norm': None if gradient is None else float(gradient.detach().float().norm().item())})\n"
        "                deltas.append({'name': name, 'finite': bool(delta.isfinite().all()), 'norm': float(delta.norm().item())})\n"
        "            frozen_after = {}\n"
        "            for name, parameter in self.models['denoiser'].named_parameters():\n"
        "                if '.lora_' in name:\n"
        "                    continue\n"
        "                normalized_name = name.replace('.base.', '.')\n"
        "                raw = parameter.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()\n"
        "                frozen_after[normalized_name] = __import__('hashlib').sha256(raw).hexdigest()\n"
        "            merged = {}\n"
        "            for name, value in self.models['denoiser'].state_dict().items():\n"
        "                if '.lora_' in name:\n"
        "                    continue\n"
        "                normalized_name = name.replace('.base.', '.')\n"
        "                merged[normalized_name] = value.detach().cpu().clone()\n"
        "            merged['blocks.29.mlp.mlp.2.weight'] = (adapter.base.weight.detach().float() + adapter.scale * torch.matmul(adapter.lora_up.detach().float(), adapter.lora_down.detach().float())).to(dtype=adapter.base.weight.dtype).cpu()\n"
        "            torch.save(merged, checkpoint_path)\n"
        "            receipt = {'schemaVersion': 1, 'valid': True, 'probeBoundary': 'BasicTrainer.run_step.after-exactly-one-regional-objective-step-before-scheduler-and-ema', 'optimizerSteps': 1, 'adapterTarget': 'blocks.29.mlp.mlp.2', 'adapterRank': 4, 'learningRate': 1e-6, 'objective': self.dentalsculptor_r05a_objective_receipt, 'adapterGradients': gradients, 'adapterDeltas': deltas, 'frozenTensorCount': len(frozen_after), 'frozenStateByteIdentical': frozen_after == self.dentalsculptor_r04b_frozen_hashes, 'mergedCheckpointEntryCount': len(merged)}\n"
        "            with open(receipt_path, 'w', encoding='utf-8') as stream:\n"
        "                stream.write(json.dumps(receipt, sort_keys=True) + '\\n')\n"
        "            raise RuntimeError('DENTALSCULPTOR_R05B_ONE_STEP_COMPLETE')\n"
        "        ## adjust learning rate\n"
        "        if self.lr_scheduler_config is not None:"
    )
    if source.count(anchor) != 1:
        raise ValueError("Pinned BasicTrainer post-step boundary changed; refusing R0.5B patch")
    patched = source.replace(anchor, replacement)
    if patched.index("self.optimizer.step()") >= patched.index("DENTALSCULPTOR_R05B_ONE_STEP_COMPLETE"):
        raise ValueError("R0.5B probe no longer follows the optimizer step")
    return patched


def interpolate_sparse_task_vector(
    base_state: dict,
    candidate_state: dict,
    alpha: float,
    *,
    permitted_candidate_only_keys: tuple[str, ...] = ("rope_phases",),
) -> dict:
    """Scale a learned sparse-flow update toward its pinned base checkpoint."""
    if not 0.0 < alpha < 1.0:
        raise ValueError("Task-vector alpha must be strictly between zero and one")
    base_keys = set(base_state)
    candidate_keys = set(candidate_state)
    missing = base_keys - candidate_keys
    extra = candidate_keys - base_keys
    if missing or extra - set(permitted_candidate_only_keys):
        raise ValueError(f"Checkpoint schema mismatch: missing={sorted(missing)}, extra={sorted(extra)}")
    result = {}
    for key in sorted(candidate_keys):
        candidate = candidate_state[key]
        if not all(hasattr(candidate, name) for name in ("shape", "dtype", "float", "detach")):
            raise TypeError(f"Candidate checkpoint entry is not a tensor: {key}")
        if key not in base_state:
            result[key] = candidate.detach().clone()
            continue
        base = base_state[key]
        if not hasattr(base, "shape") or base.shape != candidate.shape:
            raise ValueError(f"Checkpoint tensor mismatch: {key}")
        if candidate.is_floating_point():
            blended = base.float().add(candidate.float().sub(base.float()), alpha=alpha)
            result[key] = blended.to(dtype=candidate.dtype)
        else:
            if not base.equal(candidate):
                raise ValueError(f"Non-floating checkpoint entry changed: {key}")
            result[key] = candidate.detach().clone()
    return result


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="A100",
    timeout=2 * 60 * 60,
)
def evaluate_provisional_tf_pw32_candidate(
    dataset_name: str = "dental-anatomy-v1",
    run_name: str = "toothfairy-tf-pw32-step50-v2",
    samples: int = 5000,
) -> dict:
    """Evaluate the sealed step-50 candidate against the exact frozen baseline cases."""
    import sys

    if run_name != "toothfairy-tf-pw32-step50-v2":
        raise ValueError("Only the sealed TF-PW32 step-50 candidate may be evaluated")
    if MODEL_NAME != BASE_MODEL_NAME or MODEL_REVISION != BASE_MODEL_REVISION:
        raise RuntimeError("Candidate evaluation must start from the pinned unchanged base pipeline")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    root = Path(f"/datasets/{dataset_name}")
    inputs = json.loads((root / "benchmark_inputs_v1.json").read_text(encoding="utf-8"))
    baseline = json.loads((root / "baseline_report_v1.json").read_text(encoding="utf-8"))
    if not baseline.get("completeForRequestedCases") or baseline.get("caseCount") != 4:
        raise ValueError("A complete four-case frozen baseline is required")
    input_by_id = {case["id"]: case for case in inputs["cases"]}
    selected = [input_by_id[receipt["id"]] for receipt in baseline["receipts"]]
    checkpoint = Path(
        f"/checkpoints/{run_name}/ckpts/denoiser_ema0.9999_step0000050.pt"
    )
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)

    output_dir = root / "candidate_tf_pw32_step50_v2_outputs"
    receipt_dir = root / "candidate_tf_pw32_step50_v2_receipts"
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    generator = TrellisGenerator()
    generator.load_model()
    checkpoint_receipt = generator.load_shape_checkpoint(str(checkpoint))

    receipts = []
    baseline_by_id = {row["id"]: row for row in baseline["receipts"]}
    for index, case in enumerate(selected, start=1):
        if case["quality"] != baseline_by_id[case["id"]]["quality"]:
            raise ValueError(f"Quality mismatch for frozen case {case['id']}")
        output_path = output_dir / f"{case['id']}.glb"
        image_bytes = (root / case["inputImage"]).read_bytes()
        if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
            raise ValueError(f"Input image hash drift for {case['id']}")
        glb, resolved_seed, timings, pipeline_type = generator.generate_glb_from_bytes(
            image_bytes,
            quality=case["quality"],
            seed=case["generationSeed"],
            content_type="image/png",
            trace_id=f"candidate-tf-pw32-step50-v2-{case['id']}",
        )
        if resolved_seed != baseline_by_id[case["id"]]["generationSeed"]:
            raise RuntimeError(f"Generation seed drift for {case['id']}")
        if pipeline_type != baseline_by_id[case["id"]]["pipelineType"]:
            raise RuntimeError(f"Pipeline type drift for {case['id']}")
        output_path.write_bytes(glb)
        reference = load_mesh(root / case["referenceMesh"])
        prediction = load_mesh(output_path)
        receipt = {
            "schemaVersion": 1,
            "id": case["id"],
            "toothFamily": case["toothFamily"],
            "fdiNumber": case.get("fdiNumber"),
            "inputImage": case["inputImage"],
            "inputImageSha256": case["inputImageSha256"],
            "referenceMesh": case["referenceMesh"],
            "referenceMeshSha256": case["referenceMeshSha256"],
            "outputGlb": str(output_path.relative_to(root)).replace("\\", "/"),
            "outputGlbSha256": hashlib.sha256(glb).hexdigest(),
            "generationSeed": resolved_seed,
            "quality": case["quality"],
            "pipelineType": pipeline_type,
            "timings": timings,
            "anatomyQuality": generator.last_metrics.get("anatomyQuality"),
            "metrics": compare_meshes(
                reference, prediction, samples=samples, seed=case["generationSeed"]
            ),
            "topology": analyze_mesh(prediction),
            "modelRole": "provisional-small-data-candidate",
            "runName": run_name,
            "checkpointSha256": checkpoint_receipt["checkpointSha256"],
        }
        (receipt_dir / f"{case['id']}.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        receipts.append(receipt)
        dataset_volume.commit()
        print(f"Candidate {index}/{len(selected)} complete: {case['id']}", flush=True)

    baseline_for_comparison = []
    for row in baseline["receipts"]:
        enriched = dict(row)
        enriched["topology"] = analyze_mesh(load_mesh(root / row["outputGlb"]))
        baseline_for_comparison.append(enriched)
    comparison = summarize_candidate_comparison(baseline_for_comparison, receipts)
    report = {
        "schemaVersion": 1,
        "benchmarkId": inputs["benchmarkId"],
        "modelRole": "provisional-small-data-candidate",
        "runName": run_name,
        "checkpoint": checkpoint_receipt,
        "baseModelName": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trellisCommit": TRELLIS_COMMIT,
        "caseCount": len(receipts),
        "completeForRequestedCases": len(receipts) == len(selected),
        "receipts": receipts,
        "comparison": comparison,
    }
    report_path = root / "candidate_tf_pw32_step50_v2_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return {
        "reportPath": str(report_path),
        "caseCount": len(receipts),
        "comparison": comparison["aggregate"],
        "preliminaryScreenPassed": comparison["preliminaryScreenPassed"],
        "screenInterpretation": comparison["screenInterpretation"],
    }


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="A100",
    timeout=3 * 60 * 60,
)
def evaluate_stage1_seed_a_validation(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "toothfairy-stage1-shape-step50-seed1724708096-v1",
    samples: int = 5000,
) -> dict:
    """Evaluate base and seed-A EMA on the exact same 12 heldout whole teeth."""
    import os
    import sys

    if (
        dataset_name != "toothfairy-stage1-v1"
        or run_name != "toothfairy-stage1-shape-step50-seed1724708096-v1"
        or samples != 5000
    ):
        raise ValueError("The Stage-1 seed-A validation contract is sealed")
    if MODEL_NAME != BASE_MODEL_NAME or MODEL_REVISION != BASE_MODEL_REVISION:
        raise RuntimeError("Stage-1 evaluation must begin from the pinned unchanged base pipeline")
    sys.path.insert(0, "/root")
    import torch
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    root = Path(f"/datasets/{dataset_name}")
    inputs_path = root / "stage1_validation_inputs_v1.json"
    inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    if (
        not inputs.get("valid")
        or inputs.get("caseCount") != 12
        or inputs.get("trainingPatientOverlapCount") != 0
    ):
        raise ValueError("Sealed Stage-1 validation inputs are missing or invalid")
    checkpoint = Path(
        f"/checkpoints/{run_name}/ckpts/denoiser_ema0.9999_step0000050.pt"
    )
    evidence_path = Path(f"/checkpoints/{run_name}/stage1-canary-evidence.json")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not evidence.get("valid") or not evidence.get("checkpointReloaded"):
        raise ValueError("Seed-A training evidence is not valid")
    if not checkpoint.is_file() or checkpoint.stat().st_size == 0:
        raise FileNotFoundError(checkpoint)
    report_path = root / "stage1_seed_a_validation_v1.json"
    if report_path.is_file():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
        if existing.get("complete") and existing.get("caseCount") == 12:
            return {**existing, "resumed": True}
        raise ValueError("Existing Stage-1 validation report is incomplete; do not overwrite")

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    generator = TrellisGenerator()
    generator.load_model()
    output_root = root / "stage1_seed_a_validation_v1_outputs"
    output_root.mkdir(parents=True, exist_ok=True)

    def generate_role(role: str, repeat_families: bool) -> list[dict]:
        role_dir = output_root / role
        role_dir.mkdir(parents=True, exist_ok=True)
        repeated = set()
        receipts = []
        for index, case in enumerate(inputs["cases"], start=1):
            receipt_path = role_dir / f"{case['id']}.json"
            output = role_dir / f"{case['id']}.glb"
            if receipt_path.is_file() and output.is_file():
                saved = json.loads(receipt_path.read_text(encoding="utf-8"))
                expected_repeat = case["toothFamily"] not in repeated
                saved_repeat = saved.get("repeatability")
                reusable = (
                    saved.get("validationContract") == "stage1-paired-validation-v2"
                    and saved.get("modelRole") == role
                    and saved.get("inputImageSha256") == case["inputImageSha256"]
                    and saved.get("referenceMeshSha256") == case["referenceMeshSha256"]
                    and saved.get("generationSeed") == case["generationSeed"]
                    and saved.get("outputGlbSha256") == hashlib.sha256(output.read_bytes()).hexdigest()
                    and (not expected_repeat or saved_repeat is not None)
                )
                if reusable:
                    if expected_repeat:
                        repeated.add(case["toothFamily"])
                    receipts.append(saved)
                    print(f"Stage-1 {role} {index}/12 resumed: {case['id']}", flush=True)
                    continue
            image_bytes = (root / case["inputImage"]).read_bytes()
            if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
                raise ValueError(f"Validation input hash drift for {case['id']}")
            glb, resolved_seed, timings, pipeline_type = generator.generate_glb_from_bytes(
                image_bytes,
                quality=case["quality"],
                seed=case["generationSeed"],
                content_type="image/png",
                trace_id=f"stage1-{role}-{case['id']}",
            )
            if resolved_seed != case["generationSeed"]:
                raise RuntimeError(f"Generation seed drift for {role}:{case['id']}")
            output.write_bytes(glb)
            repeatability = None
            if repeat_families and case["toothFamily"] not in repeated:
                repeated.add(case["toothFamily"])
                repeated_glb, repeated_seed, _, repeated_pipeline = generator.generate_glb_from_bytes(
                    image_bytes,
                    quality=case["quality"],
                    seed=case["generationSeed"],
                    content_type="image/png",
                    trace_id=f"stage1-{role}-repeat-{case['id']}",
                )
                repeat_output = role_dir / f"{case['id']}.repeat.glb"
                repeat_output.write_bytes(repeated_glb)
                first_mesh = load_mesh(output)
                repeat_mesh = load_mesh(repeat_output)
                repeat_metrics = compare_meshes(
                    first_mesh,
                    repeat_mesh,
                    samples=samples,
                    seed=case["generationSeed"],
                )
                repeat_limits = {
                    "symmetricChamferPercentDiagonal": 0.25,
                    "hausdorff95PercentDiagonal": 0.75,
                    "sortedExtentRelativeError": 0.01,
                }
                repeatability = {
                    "criterion": "normalized-surface-repeatability-v1",
                    "limits": repeat_limits,
                    "generationSeed": repeated_seed,
                    "pipelineType": repeated_pipeline,
                    "firstSha256": hashlib.sha256(glb).hexdigest(),
                    "repeatSha256": hashlib.sha256(repeated_glb).hexdigest(),
                    "exactGlbMatch": glb == repeated_glb,
                    "repeatOutputGlb": str(repeat_output.relative_to(root)).replace("\\", "/"),
                    "metrics": repeat_metrics,
                    "geometricallyStable": all(
                        float(repeat_metrics[name]) <= limit
                        for name, limit in repeat_limits.items()
                    ),
                }
            reference = load_mesh(root / case["referenceMesh"])
            prediction = load_mesh(output)
            receipt = {
                "schemaVersion": 1,
                "validationContract": "stage1-paired-validation-v2",
                "id": case["id"],
                "toothFamily": case["toothFamily"],
                "fdiNumber": case.get("fdiNumber"),
                "groupId": case["groupId"],
                "inputImageSha256": case["inputImageSha256"],
                "referenceMesh": case["referenceMesh"],
                "referenceMeshSha256": case["referenceMeshSha256"],
                "outputGlb": str(output.relative_to(root)).replace("\\", "/"),
                "outputGlbSha256": hashlib.sha256(glb).hexdigest(),
                "generationSeed": resolved_seed,
                "quality": case["quality"],
                "pipelineType": pipeline_type,
                "timings": timings,
                "metrics": compare_meshes(
                    reference, prediction, samples=samples, seed=case["generationSeed"]
                ),
                "topology": analyze_mesh_with_weld_control(prediction),
                "repeatability": repeatability,
                "modelRole": role,
            }
            (role_dir / f"{case['id']}.json").write_text(
                json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
            )
            receipts.append(receipt)
            dataset_volume.commit()
            print(f"Stage-1 {role} {index}/12: {case['id']}", flush=True)
        if repeated != {"incisor", "canine", "premolar", "molar"}:
            raise ValueError(f"Repeatability family coverage incomplete for {role}: {repeated}")
        return receipts

    baseline = generate_role("unchanged-base", repeat_families=True)
    checkpoint_receipt = generator.load_shape_checkpoint(str(checkpoint))
    candidate = generate_role("stage1-seed-a-ema", repeat_families=True)
    summary = summarize_stage1_validation(baseline, candidate)
    report = {
        "schemaVersion": 1,
        "stage": "stage1-seed-a-paired-validation",
        "complete": True,
        "datasetId": dataset_name,
        "runName": run_name,
        "caseCount": 12,
        "samplesPerMesh": samples,
        "baseModel": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "candidateCheckpoint": checkpoint_receipt,
        "deterministicControls": {
            "cublasWorkspaceConfig": ":4096:8",
            "tf32": False,
            "cudnnDeterministic": True,
            "torchDeterministicAlgorithms": True,
        },
        "baseline": baseline,
        "candidate": candidate,
        "summary": summary,
        "seedBAuthorized": summary["seedBAuthorized"],
        "clinicalImprovementClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return {
        "reportPath": str(report_path),
        "caseCount": 12,
        "passed": summary["passed"],
        "seedBAuthorized": summary["seedBAuthorized"],
        "medianPairedChamferRelativeImprovement": summary[
            "medianPairedChamferRelativeImprovement"
        ],
        "bootstrap95PercentInterval": summary["bootstrap95PercentInterval"],
        "engineeringNonRegressionPassed": summary["engineeringNonRegression"]["passed"],
        "repeatabilityPassed": summary["repeatability"]["passed"],
    }


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="A100",
    timeout=3 * 60 * 60,
)
def evaluate_stage1_seed_a_raw_validation(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "toothfairy-stage1-shape-step50-seed1724708096-v1",
    samples: int = 5000,
) -> dict:
    """Evaluate Stage-1 at the repeatable raw shape-decode boundary.

    Texture sampling, CuMesh remeshing and GLB serialization are deliberately
    excluded: prior sealed diagnostics localized nondeterminism after raw shape
    decode. Sparse-coordinate identity is checked per pair so the comparison
    isolates the fine-tuned 512 shape-flow checkpoint.
    """
    import io
    import os
    import random
    import sys

    import numpy as np
    import torch
    import trimesh
    from PIL import Image

    if (
        dataset_name != "toothfairy-stage1-v1"
        or run_name != "toothfairy-stage1-shape-step50-seed1724708096-v1"
        or samples != 5000
    ):
        raise ValueError("The Stage-1 raw validation contract is sealed")
    if MODEL_NAME != BASE_MODEL_NAME or MODEL_REVISION != BASE_MODEL_REVISION:
        raise RuntimeError("Raw validation must begin from the pinned unchanged base pipeline")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    root = Path(f"/datasets/{dataset_name}")
    inputs = json.loads((root / "stage1_validation_inputs_v1.json").read_text(encoding="utf-8"))
    if (
        not inputs.get("valid")
        or inputs.get("caseCount") != 12
        or inputs.get("trainingPatientOverlapCount") != 0
    ):
        raise ValueError("Sealed Stage-1 validation inputs are missing or invalid")
    checkpoint = Path(f"/checkpoints/{run_name}/ckpts/denoiser_ema0.9999_step0000050.pt")
    evidence = json.loads(
        Path(f"/checkpoints/{run_name}/stage1-canary-evidence.json").read_text(encoding="utf-8")
    )
    if not evidence.get("valid") or not evidence.get("checkpointReloaded"):
        raise ValueError("Seed-A training evidence is not valid")
    if not checkpoint.is_file() or checkpoint.stat().st_size == 0:
        raise FileNotFoundError(checkpoint)
    report_path = root / "stage1_seed_a_raw_validation_v2.json"
    if report_path.is_file():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
        if existing.get("complete") and existing.get("caseCount") == 12:
            return {**existing, "resumed": True}
        raise ValueError("Existing raw validation report is incomplete; refusing overwrite")

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    generator = TrellisGenerator()
    generator.load_model()
    params = sampler_params_for_steps(int(get_quality_preset("standard")["steps"]))
    output_root = root / "stage1_seed_a_raw_validation_v2_outputs"
    output_root.mkdir(parents=True, exist_ok=True)
    frozen_root = output_root / "frozen_sparse_conditions"
    frozen_root.mkdir(parents=True, exist_ok=True)

    def tensor_sha256(tensor: torch.Tensor) -> str:
        array = tensor.detach().cpu().contiguous().numpy()
        return hashlib.sha256(array.tobytes()).hexdigest()

    def load_image_and_conditions(case: dict):
        seed = int(case["generationSeed"])
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        image_bytes = (root / case["inputImage"]).read_bytes()
        if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
            raise ValueError(f"Validation input hash drift for {case['id']}")
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        processed = generator.pipeline.preprocess_image(image)
        cond_512 = generator.pipeline.get_cond([processed], 512)
        cond_1024 = generator.pipeline.get_cond([processed], 1024)
        return cond_512, cond_1024

    def load_or_create_frozen_coords(case: dict) -> tuple[torch.Tensor, dict]:
        """Materialize one immutable sparse condition for both model roles."""
        coords_path = frozen_root / f"{case['id']}.pt"
        receipt_path = frozen_root / f"{case['id']}.json"
        if coords_path.is_file() and receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            coords = torch.load(coords_path, map_location="cpu", weights_only=True)
            if (
                receipt.get("validationContract") != "stage1-frozen-sparse-condition-v2"
                or receipt.get("caseId") != case["id"]
                or receipt.get("inputImageSha256") != case["inputImageSha256"]
                or receipt.get("generationSeed") != int(case["generationSeed"])
                or receipt.get("coordsSha256") != tensor_sha256(coords)
                or receipt.get("artifactSha256") != hashlib.sha256(coords_path.read_bytes()).hexdigest()
            ):
                raise ValueError(f"Frozen sparse condition is invalid for {case['id']}")
            return coords, receipt
        if coords_path.exists() or receipt_path.exists():
            raise ValueError(f"Incomplete frozen sparse condition for {case['id']}")
        cond_512, _ = load_image_and_conditions(case)
        with torch.inference_mode():
            coords = generator.pipeline.sample_sparse_structure(
                cond_512, 32, sampler_params=params["sparse_structure"]
            )
        coords = coords.detach().cpu().contiguous()
        torch.save(coords, coords_path)
        receipt = {
            "schemaVersion": 1,
            "validationContract": "stage1-frozen-sparse-condition-v2",
            "caseId": case["id"],
            "inputImageSha256": case["inputImageSha256"],
            "generationSeed": int(case["generationSeed"]),
            "coordsSha256": tensor_sha256(coords),
            "artifact": str(coords_path.relative_to(root)).replace("\\", "/"),
            "artifactSha256": hashlib.sha256(coords_path.read_bytes()).hexdigest(),
        }
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        dataset_volume.commit()
        del cond_512
        torch.cuda.empty_cache()
        return coords, receipt

    def sample_raw(case: dict, frozen_coords: torch.Tensor) -> tuple[trimesh.Trimesh, dict]:
        seed = int(case["generationSeed"])
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        cond_512, cond_1024 = load_image_and_conditions(case)
        # TRELLIS sequentially offloads shape modules after each cascade, so a
        # model parameter may be on CPU between calls even though sparse input
        # must enter the sampler on the active CUDA device. Restore the frozen
        # artifact to CUDA explicitly; the Modal function is GPU-only.
        if not torch.cuda.is_available():
            raise RuntimeError("Stage-1 raw validation requires CUDA")
        coords = frozen_coords.to(
            device=torch.device("cuda", torch.cuda.current_device()), non_blocking=True
        )
        with torch.inference_mode():
            slat, resolution = generator.pipeline.sample_shape_slat_cascade(
                cond_512,
                cond_1024,
                generator.pipeline.models["shape_slat_flow_model_512"],
                generator.pipeline.models["shape_slat_flow_model_1024"],
                512,
                1024,
                coords,
                params["shape"],
            )
            meshes, _ = generator.pipeline.decode_shape_slat(slat, resolution)
        torch.cuda.synchronize()
        if len(meshes) != 1:
            raise RuntimeError(f"Expected one raw decoded mesh for {case['id']}")
        raw = meshes[0]
        receipt = {
            "sparseCoordsSha256": tensor_sha256(coords),
            "shapeLatentCoordsSha256": tensor_sha256(slat.coords),
            "shapeLatentFeaturesSha256": tensor_sha256(slat.feats),
            "rawVerticesSha256": tensor_sha256(raw.vertices),
            "rawFacesSha256": tensor_sha256(raw.faces),
            "resolvedResolution": int(resolution),
        }
        mesh = trimesh.Trimesh(
            vertices=raw.vertices.detach().cpu().numpy(),
            faces=raw.faces.detach().cpu().numpy(),
            process=False,
        )
        del meshes, raw, slat, coords, cond_512, cond_1024
        torch.cuda.empty_cache()
        return mesh, receipt

    frozen_conditions = {
        case["id"]: load_or_create_frozen_coords(case) for case in inputs["cases"]
    }

    def generate_role(role: str) -> list[dict]:
        role_dir = output_root / role
        role_dir.mkdir(parents=True, exist_ok=True)
        repeated: set[str] = set()
        receipts = []
        for index, case in enumerate(inputs["cases"], start=1):
            receipt_path = role_dir / f"{case['id']}.json"
            mesh_path = role_dir / f"{case['id']}.ply"
            if receipt_path.is_file() and mesh_path.is_file():
                saved = json.loads(receipt_path.read_text(encoding="utf-8"))
                expected_repeat = case["toothFamily"] not in repeated
                if (
                    saved.get("validationContract") == "stage1-raw-paired-validation-v2"
                    and saved.get("modelRole") == role
                    and saved.get("frozenSparseCondition", {}).get("coordsSha256")
                    == frozen_conditions[case["id"]][1]["coordsSha256"]
                    and saved.get("meshArtifactSha256") == hashlib.sha256(mesh_path.read_bytes()).hexdigest()
                    and (not expected_repeat or saved.get("repeatability", {}).get("rawShapeExact") is True)
                ):
                    if expected_repeat:
                        repeated.add(case["toothFamily"])
                    receipts.append(saved)
                    print(f"Stage-1 raw {role} {index}/12 resumed: {case['id']}", flush=True)
                    continue
            frozen_coords, frozen_receipt = frozen_conditions[case["id"]]
            mesh, boundary = sample_raw(case, frozen_coords)
            mesh_bytes = mesh.export(file_type="ply", encoding="binary")
            mesh_path.write_bytes(mesh_bytes)
            repeatability = None
            if case["toothFamily"] not in repeated:
                repeated.add(case["toothFamily"])
                _, repeat_boundary = sample_raw(case, frozen_coords)
                compared = (
                    "sparseCoordsSha256",
                    "shapeLatentCoordsSha256",
                    "shapeLatentFeaturesSha256",
                    "rawVerticesSha256",
                    "rawFacesSha256",
                )
                equality = {name: boundary[name] == repeat_boundary[name] for name in compared}
                repeatability = {
                    "criterion": "bit-identical-raw-shape-boundary-v1",
                    "boundaryEquality": equality,
                    "rawShapeExact": all(equality.values()),
                }
            reference = load_mesh(root / case["referenceMesh"])
            receipt = {
                "schemaVersion": 1,
                "validationContract": "stage1-raw-paired-validation-v2",
                "id": case["id"],
                "toothFamily": case["toothFamily"],
                "fdiNumber": case.get("fdiNumber"),
                "groupId": case["groupId"],
                "inputImageSha256": case["inputImageSha256"],
                "referenceMesh": case["referenceMesh"],
                "referenceMeshSha256": case["referenceMeshSha256"],
                "meshArtifact": str(mesh_path.relative_to(root)).replace("\\", "/"),
                "meshArtifactSha256": hashlib.sha256(mesh_bytes).hexdigest(),
                "generationSeed": int(case["generationSeed"]),
                "frozenSparseCondition": frozen_receipt,
                "quality": case["quality"],
                "boundary": boundary,
                "metrics": compare_meshes(
                    reference, mesh, samples=samples, seed=int(case["generationSeed"])
                ),
                "topology": analyze_mesh_with_weld_control(mesh),
                "repeatability": repeatability,
                "modelRole": role,
            }
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            receipts.append(receipt)
            dataset_volume.commit()
            print(f"Stage-1 raw {role} {index}/12: {case['id']}", flush=True)
        if repeated != {"incisor", "canine", "premolar", "molar"}:
            raise ValueError(f"Raw repeatability family coverage incomplete for {role}: {repeated}")
        return receipts

    baseline = generate_role("unchanged-base")
    checkpoint_receipt = generator.load_shape_checkpoint(str(checkpoint))
    candidate = generate_role("stage1-seed-a-ema")
    assert_paired_sparse_condition_identity(baseline, candidate)
    # The summary's repeatability field is representation-agnostic. Map the
    # proven exact raw boundary into its stable boolean without weakening it.
    for rows in (baseline, candidate):
        for row in rows:
            if row["repeatability"] is not None:
                row["repeatability"]["geometricallyStable"] = row["repeatability"]["rawShapeExact"]
    summary = summarize_stage1_validation(baseline, candidate)
    report = {
        "schemaVersion": 1,
        "stage": "stage1-seed-a-raw-paired-validation-v2-frozen-sparse",
        "complete": True,
        "datasetId": dataset_name,
        "runName": run_name,
        "caseCount": 12,
        "samplesPerMesh": samples,
        "measurementBoundary": "raw-shape-decode-before-texture-remesh-and-serialization",
        "excludedNondeterministicStages": ["texture-sampling", "CuMesh-remeshing", "GLB-serialization"],
        "pairingContract": "one persisted sparse-coordinate tensor per case, shared by both model roles",
        "candidateCheckpoint": checkpoint_receipt,
        "baseline": baseline,
        "candidate": candidate,
        "summary": summary,
        "seedBAuthorized": summary["seedBAuthorized"],
        "clinicalImprovementClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return {
        "reportPath": str(report_path),
        "caseCount": 12,
        "passed": summary["passed"],
        "seedBAuthorized": summary["seedBAuthorized"],
        "medianPairedChamferRelativeImprovement": summary["medianPairedChamferRelativeImprovement"],
        "bootstrap95PercentInterval": summary["bootstrap95PercentInterval"],
        "repeatabilityPassed": summary["repeatability"]["passed"],
    }


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="A100",
    timeout=3 * 60 * 60,
)
def evaluate_e3_sparse_tf_pw32_candidate(
    dataset_name: str = "dental-anatomy-v1",
    run_name: str = "e3-sparse-tf-pw32-step50-v1",
    samples: int = 5000,
) -> dict:
    """Evaluate E3-B with only sparse flow changed and fail closed on every gate."""
    import os
    import sys
    import torch

    if run_name != "e3-sparse-tf-pw32-step50-v1" or samples != 5000:
        raise ValueError("The E3-B evaluation contract is sealed")
    if MODEL_NAME != BASE_MODEL_NAME or MODEL_REVISION != BASE_MODEL_REVISION:
        raise RuntimeError("E3 evaluation must start from the pinned unchanged base pipeline")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    root = Path(f"/datasets/{dataset_name}")
    inputs = json.loads((root / "benchmark_inputs_v1.json").read_text(encoding="utf-8"))
    baseline = json.loads((root / "baseline_report_v1.json").read_text(encoding="utf-8"))
    if not baseline.get("completeForRequestedCases") or baseline.get("caseCount") != 4:
        raise ValueError("A complete frozen four-case baseline is required")
    evaluation_id = "e3_sparse_tf_pw32_step50_eval_v2"
    report_path = root / f"{evaluation_id}_report.json"
    if report_path.exists():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
        if existing.get("completeForRequestedCases"):
            return {**existing, "resumed": True}
        raise ValueError("Existing E3 report is incomplete; do not overwrite")
    checkpoint = Path(
        f"/checkpoints/{run_name}/ckpts/denoiser_ema0.9999_step0000050.pt"
    )
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    input_by_id = {case["id"]: case for case in inputs["cases"]}
    selected = [input_by_id[row["id"]] for row in baseline["receipts"]]
    baseline_by_id = {row["id"]: row for row in baseline["receipts"]}
    output_dir = root / f"{evaluation_id}_outputs"
    receipt_dir = root / f"{evaluation_id}_receipts"
    output_dir.mkdir(parents=True, exist_ok=False)
    receipt_dir.mkdir(parents=True, exist_ok=False)

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    generator = TrellisGenerator()
    generator.load_model()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    if not (
        not torch.backends.cuda.matmul.allow_tf32
        and not torch.backends.cudnn.allow_tf32
        and torch.backends.cudnn.deterministic
        and torch.are_deterministic_algorithms_enabled()
    ):
        raise RuntimeError("Strict E3 deterministic controls were not retained")
    checkpoint_receipt = generator.load_sparse_structure_checkpoint(str(checkpoint))

    receipts = []
    repeatability = []
    for index, case in enumerate(selected, start=1):
        baseline_case = baseline_by_id[case["id"]]
        if case["quality"] != baseline_case["quality"]:
            raise ValueError(f"Quality mismatch for frozen case {case['id']}")
        image_bytes = (root / case["inputImage"]).read_bytes()
        if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
            raise ValueError(f"Input image hash drift for {case['id']}")
        generated = []
        for trial in ("a", "b"):
            glb, resolved_seed, timings, pipeline_type = generator.generate_glb_from_bytes(
                image_bytes,
                quality=case["quality"],
                seed=case["generationSeed"],
                content_type="image/png",
                trace_id=f"{evaluation_id}-{case['id']}-{trial}",
            )
            if resolved_seed != baseline_case["generationSeed"]:
                raise RuntimeError(f"Generation seed drift for {case['id']}")
            if pipeline_type != baseline_case["pipelineType"]:
                raise RuntimeError(f"Pipeline type drift for {case['id']}")
            path = output_dir / f"{case['id']}-{trial}.glb"
            path.write_bytes(glb)
            generated.append({
                "trial": trial, "bytes": glb, "path": path,
                "sha256": hashlib.sha256(glb).hexdigest(), "timings": timings,
                "pipelineType": pipeline_type,
            })
        identical = generated[0]["sha256"] == generated[1]["sha256"]
        repeatability.append({
            "id": case["id"], "byteIdentical": identical,
            "sha256": [item["sha256"] for item in generated],
        })
        reference = load_mesh(root / case["referenceMesh"])
        prediction = load_mesh(generated[0]["path"])
        receipt = {
            "schemaVersion": 1,
            "id": case["id"],
            "toothFamily": case["toothFamily"],
            "fdiNumber": case.get("fdiNumber"),
            "inputImage": case["inputImage"],
            "inputImageSha256": case["inputImageSha256"],
            "referenceMesh": case["referenceMesh"],
            "referenceMeshSha256": case["referenceMeshSha256"],
            "outputGlb": str(generated[0]["path"].relative_to(root)).replace("\\", "/"),
            "outputGlbSha256": generated[0]["sha256"],
            "generationSeed": case["generationSeed"],
            "quality": case["quality"],
            "pipelineType": generated[0]["pipelineType"],
            "timings": generated[0]["timings"],
            "metrics": compare_meshes(
                reference, prediction, samples=samples, seed=case["generationSeed"]
            ),
            "topology": analyze_mesh_with_weld_control(prediction),
            "modelRole": "e3-sparse-structure-engineering-candidate",
            "runName": run_name,
            "checkpointSha256": checkpoint_receipt["checkpointSha256"],
        }
        (receipt_dir / f"{case['id']}.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        receipts.append(receipt)
        dataset_volume.commit()
        print(f"E3 sparse candidate {index}/{len(selected)} complete", flush=True)

    baseline_enriched = []
    for row in baseline["receipts"]:
        enriched = dict(row)
        enriched["topology"] = analyze_mesh_with_weld_control(load_mesh(root / row["outputGlb"]))
        if "canonicalAxialAnatomyProxy" not in enriched.get("metrics", {}):
            case = input_by_id[row["id"]]
            enriched["metrics"] = compare_meshes(
                load_mesh(root / case["referenceMesh"]),
                load_mesh(root / row["outputGlb"]),
                samples=samples,
                seed=case["generationSeed"],
            )
        baseline_enriched.append(enriched)
    comparison = summarize_candidate_comparison(baseline_enriched, receipts)
    engineering_gates = evaluate_e3_engineering_gates(baseline_enriched, receipts)
    repeatability_passed = all(row["byteIdentical"] for row in repeatability)
    all_gates_passed = bool(
        comparison["preliminaryScreenPassed"]
        and engineering_gates["passed"]
        and repeatability_passed
    )
    report = {
        "schemaVersion": 1,
        "benchmarkId": inputs["benchmarkId"],
        "evaluationId": evaluation_id,
        "modelRole": "e3-sparse-structure-engineering-candidate",
        "runName": run_name,
        "checkpoint": checkpoint_receipt,
        "baseModelName": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trellisCommit": TRELLIS_COMMIT,
        "caseCount": len(receipts),
        "completeForRequestedCases": len(receipts) == len(selected),
        "receipts": receipts,
        "comparison": comparison,
        "engineeringGates": engineering_gates,
        "repeatability": {"passed": repeatability_passed, "cases": repeatability},
        "allEngineeringGatesPassed": all_gates_passed,
        "advanceToStep250Permitted": all_gates_passed,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return report


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    timeout=20 * 60,
)
def finalize_e3_sparse_early_stop(
    dataset_name: str = "dental-anatomy-v1",
    evaluation_id: str = "e3_sparse_tf_pw32_step50_eval_v2",
) -> dict:
    """Seal an interrupted E3 evaluation once a prospective stopping rule fails."""
    if evaluation_id != "e3_sparse_tf_pw32_step50_eval_v2":
        raise ValueError("Only the registered interrupted E3-B evaluation may be finalized")
    root = Path(f"/datasets/{dataset_name}")
    receipt_dir = root / f"{evaluation_id}_receipts"
    output_dir = root / f"{evaluation_id}_outputs"
    receipts = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(receipt_dir.glob("*.json"))]
    if len(receipts) != 1:
        raise ValueError(f"Expected exactly one committed case before early stop; found {len(receipts)}")
    case_id = receipts[0]["id"]
    outputs = [output_dir / f"{case_id}-{trial}.glb" for trial in ("a", "b")]
    if any(not path.is_file() for path in outputs):
        raise FileNotFoundError("Both fixed-runtime trial outputs are required")
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in outputs]
    byte_identical = hashes[0] == hashes[1]
    if byte_identical:
        raise ValueError("Early-stop condition is not present; trials are byte-identical")
    baseline = json.loads((root / "baseline_report_v1.json").read_text(encoding="utf-8"))
    baseline_case = next(row for row in baseline["receipts"] if row["id"] == case_id)
    import sys
    sys.path.insert(0, "/root")
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    input_manifest = json.loads((root / "benchmark_inputs_v1.json").read_text(encoding="utf-8"))
    input_case = next(row for row in input_manifest["cases"] if row["id"] == case_id)
    baseline_case = dict(baseline_case)
    baseline_case["topology"] = analyze_mesh_with_weld_control(
        load_mesh(root / baseline_case["outputGlb"])
    )
    if "canonicalAxialAnatomyProxy" not in baseline_case.get("metrics", {}):
        baseline_case["metrics"] = compare_meshes(
            load_mesh(root / input_case["referenceMesh"]),
            load_mesh(root / baseline_case["outputGlb"]),
            samples=5000,
            seed=input_case["generationSeed"],
        )
    engineering = evaluate_e3_engineering_gates([baseline_case], receipts)
    report = {
        "schemaVersion": 1,
        "evaluationId": evaluation_id,
        "runName": "e3-sparse-tf-pw32-step50-v1",
        "status": "rejected-early",
        "earlyStopped": True,
        "stoppingRule": "fixed-runtime-repeatability-failed",
        "evaluatedCaseCount": 1,
        "requestedCaseCount": 4,
        "completeForRequestedCases": False,
        "repeatability": {
            "passed": False,
            "cases": [{"id": case_id, "byteIdentical": False, "sha256": hashes}],
        },
        "firstCaseEngineeringGates": engineering,
        "allEngineeringGatesPassed": False,
        "advanceToStep250Permitted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
        "receipts": receipts,
    }
    report_path = root / f"{evaluation_id}_early_stop_report.json"
    if report_path.exists():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
        if existing == report:
            return {**existing, "resumed": True}
        raise ValueError("Existing early-stop report differs; refusing overwrite")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return report


@app.function(
    image=trellis_gpu_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="A100",
    timeout=90 * 60,
)
def diagnose_e3_sparse_occupancy(
    dataset_name: str = "dental-anatomy-v1",
    run_name: str = "e3-sparse-tf-pw32-step50-v1",
) -> dict:
    """Compare base/candidate occupancy before shape decoding or remeshing."""
    import io
    import os
    import random
    import sys

    import numpy as np
    import torch
    from PIL import Image

    if dataset_name != "dental-anatomy-v1" or run_name != "e3-sparse-tf-pw32-step50-v1":
        raise ValueError("The E3 sparse-occupancy diagnostic contract is sealed")
    if MODEL_NAME != BASE_MODEL_NAME or MODEL_REVISION != BASE_MODEL_REVISION:
        raise RuntimeError("Diagnostic must begin from the pinned base pipeline")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator

    root = Path(f"/datasets/{dataset_name}")
    diagnostic_id = "e3_sparse_occupancy_diagnostic_v1"
    report_path = root / f"{diagnostic_id}.json"
    arrays_path = root / f"{diagnostic_id}.npz"
    if report_path.exists() or arrays_path.exists():
        if report_path.is_file() and arrays_path.is_file():
            existing = json.loads(report_path.read_text(encoding="utf-8"))
            if existing.get("status") == "complete":
                return {**existing, "resumed": True}
        raise ValueError("Incomplete diagnostic artifact exists; refusing overwrite")

    inputs = json.loads((root / "benchmark_inputs_v1.json").read_text(encoding="utf-8"))
    case = next((row for row in inputs["cases"] if row["id"] == "004029_fdi21"), None)
    if case is None:
        raise ValueError("Frozen incisor diagnostic case is missing")
    if case["quality"] != "standard" or case["generationSeed"] != 1724708096:
        raise ValueError("Frozen incisor quality or seed drifted")
    image_bytes = (root / case["inputImage"]).read_bytes()
    if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
        raise ValueError("Frozen diagnostic input image hash drifted")
    checkpoint = Path(f"/checkpoints/{run_name}/ckpts/denoiser_ema0.9999_step0000050.pt")
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    generator = TrellisGenerator()
    generator.load_model()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    if not torch.are_deterministic_algorithms_enabled():
        raise RuntimeError("Strict deterministic algorithms were not enabled")

    image = Image.open(io.BytesIO(image_bytes))
    image.load()
    processed = generator.pipeline.preprocess_image(image)
    conditioning = generator.pipeline.get_cond([processed], 512)
    sampler_params = sampler_params_for_steps(int(get_quality_preset("standard")["steps"]))
    resolution = 32
    seed = int(case["generationSeed"])

    def sample() -> np.ndarray:
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        with torch.inference_mode():
            coords = generator.pipeline.sample_sparse_structure(
                conditioning,
                resolution,
                sampler_params=sampler_params["sparse_structure"],
            )
        torch.cuda.synchronize()
        array = coords.detach().cpu().numpy().astype(np.int32, copy=False)
        sparse_occupancy_metrics(array, resolution)
        return array

    base = sample()
    checkpoint_receipt = generator.load_sparse_structure_checkpoint(str(checkpoint))
    candidate_a = sample()
    candidate_b = sample()
    base_vs_candidate = compare_sparse_occupancies(base, candidate_a, resolution)
    candidate_repeatability = compare_sparse_occupancies(candidate_a, candidate_b, resolution)

    np.savez_compressed(
        arrays_path,
        base=base,
        candidate_a=candidate_a,
        candidate_b=candidate_b,
    )
    arrays_sha256 = hashlib.sha256(arrays_path.read_bytes()).hexdigest()
    repeatable = bool(candidate_repeatability["exactlyEqual"])
    report = {
        "schemaVersion": 1,
        "diagnosticId": diagnostic_id,
        "status": "complete",
        "caseId": case["id"],
        "toothFamily": case["toothFamily"],
        "fdiNumber": case.get("fdiNumber"),
        "inputImage": case["inputImage"],
        "inputImageSha256": case["inputImageSha256"],
        "seed": seed,
        "quality": case["quality"],
        "sparseResolution": resolution,
        "samplerSteps": sampler_params["sparse_structure"]["steps"],
        "baseModelName": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trellisCommit": TRELLIS_COMMIT,
        "candidateCheckpoint": checkpoint_receipt,
        "baseVsCandidate": base_vs_candidate,
        "candidateRepeatability": candidate_repeatability,
        "candidateOccupancyRepeatable": repeatable,
        "arraysArtifact": str(arrays_path.relative_to(root)).replace("\\", "/"),
        "arraysArtifactSha256": arrays_sha256,
        "downstreamShapeDecodeExecuted": False,
        "downstreamRemeshingExecuted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
        "interpretation": (
            "Sparse occupancy is already non-repeatable at the pre-shape boundary."
            if not repeatable else
            "Sparse occupancy is repeatable; downstream shape decoding/extraction remains the repeatability suspect."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return report


@app.function(
    image=trellis_gpu_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="A100",
    timeout=90 * 60,
)
def diagnose_e3_shape_boundary(
    dataset_name: str = "dental-anatomy-v1",
    run_name: str = "e3-sparse-tf-pw32-step50-v1",
) -> dict:
    """Locate repeatability drift at shape latent or raw shape decode boundary."""
    import io
    import os
    import random
    import sys

    import numpy as np
    import torch
    from PIL import Image

    if dataset_name != "dental-anatomy-v1" or run_name != "e3-sparse-tf-pw32-step50-v1":
        raise ValueError("The E3 shape-boundary diagnostic contract is sealed")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator

    root = Path(f"/datasets/{dataset_name}")
    diagnostic_id = "e3_shape_boundary_diagnostic_v1"
    report_path = root / f"{diagnostic_id}.json"
    if report_path.exists():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return {**existing, "resumed": True}
        raise ValueError("Incomplete shape-boundary diagnostic exists; refusing overwrite")
    inputs = json.loads((root / "benchmark_inputs_v1.json").read_text(encoding="utf-8"))
    case = next((row for row in inputs["cases"] if row["id"] == "004029_fdi21"), None)
    if case is None or case["generationSeed"] != 1724708096 or case["quality"] != "standard":
        raise ValueError("Frozen incisor diagnostic case drifted")
    image_bytes = (root / case["inputImage"]).read_bytes()
    if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
        raise ValueError("Frozen diagnostic image hash drifted")
    checkpoint = Path(f"/checkpoints/{run_name}/ckpts/denoiser_ema0.9999_step0000050.pt")
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    generator = TrellisGenerator()
    generator.load_model()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    checkpoint_receipt = generator.load_sparse_structure_checkpoint(str(checkpoint))

    image = Image.open(io.BytesIO(image_bytes))
    image.load()
    processed = generator.pipeline.preprocess_image(image)
    cond_512 = generator.pipeline.get_cond([processed], 512)
    cond_1024 = generator.pipeline.get_cond([processed], 1024)
    params = sampler_params_for_steps(int(get_quality_preset("standard")["steps"]))
    seed = int(case["generationSeed"])

    def tensor_receipt(tensor: torch.Tensor) -> dict:
        array = tensor.detach().cpu().contiguous().numpy()
        return {
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "sha256": hashlib.sha256(array.tobytes()).hexdigest(),
            "finite": bool(np.isfinite(array).all()),
        }

    def structure_receipt(value: object) -> dict:
        if isinstance(value, torch.Tensor):
            return {"kind": "tensor", **tensor_receipt(value)}
        if hasattr(value, "coords") and hasattr(value, "feats"):
            coords_receipt = tensor_receipt(value.coords)
            features_receipt = tensor_receipt(value.feats)
            combined = f"{coords_receipt['sha256']}:{features_receipt['sha256']}"
            return {
                "kind": type(value).__name__,
                "coords": coords_receipt,
                "features": features_receipt,
                "sha256": hashlib.sha256(combined.encode("ascii")).hexdigest(),
            }
        if isinstance(value, (list, tuple)):
            children = [structure_receipt(item) for item in value]
            canonical = json.dumps(children, sort_keys=True, separators=(",", ":"))
            return {
                "kind": type(value).__name__,
                "length": len(children),
                "children": children,
                "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            }
        if isinstance(value, dict):
            children = {str(key): structure_receipt(item) for key, item in sorted(value.items())}
            canonical = json.dumps(children, sort_keys=True, separators=(",", ":"))
            return {
                "kind": "dict",
                "children": children,
                "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            }
        raise TypeError(f"Unsupported decoded diagnostic structure: {type(value).__name__}")

    def trial(label: str) -> dict:
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        with torch.inference_mode():
            coords = generator.pipeline.sample_sparse_structure(
                cond_512, 32, sampler_params=params["sparse_structure"]
            )
            slat, resolved_resolution = generator.pipeline.sample_shape_slat_cascade(
                cond_512,
                cond_1024,
                generator.pipeline.models["shape_slat_flow_model_512"],
                generator.pipeline.models["shape_slat_flow_model_1024"],
                512,
                1024,
                coords,
                params["shape"],
            )
            meshes, substructures = generator.pipeline.decode_shape_slat(
                slat, resolved_resolution
            )
        torch.cuda.synchronize()
        if len(meshes) != 1:
            raise RuntimeError("Expected exactly one raw decoded mesh")
        substructure_receipt = structure_receipt(substructures)
        receipt = {
            "label": label,
            "sparseCoords": tensor_receipt(coords),
            "shapeLatentCoords": tensor_receipt(slat.coords),
            "shapeLatentFeatures": tensor_receipt(slat.feats),
            "resolvedResolution": int(resolved_resolution),
            "rawMeshVertices": tensor_receipt(meshes[0].vertices),
            "rawMeshFaces": tensor_receipt(meshes[0].faces),
            "decodedSubstructures": substructure_receipt,
        }
        del meshes, substructures, slat, coords
        torch.cuda.empty_cache()
        return receipt

    trials = [trial("a"), trial("b")]
    compared_fields = (
        "sparseCoords", "shapeLatentCoords", "shapeLatentFeatures",
        "rawMeshVertices", "rawMeshFaces",
        "decodedSubstructures",
    )
    equality = {
        field: trials[0][field]["sha256"] == trials[1][field]["sha256"]
        for field in compared_fields
    }
    first_drift = next((field for field in compared_fields if not equality[field]), None)
    report = {
        "schemaVersion": 1,
        "diagnosticId": diagnostic_id,
        "status": "complete",
        "caseId": case["id"],
        "inputImageSha256": case["inputImageSha256"],
        "seed": seed,
        "quality": case["quality"],
        "samplerSteps": params["shape"]["steps"],
        "baseModelName": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trellisCommit": TRELLIS_COMMIT,
        "candidateCheckpoint": checkpoint_receipt,
        "trials": trials,
        "boundaryEquality": equality,
        "firstNonRepeatableBoundary": first_drift,
        "allShapeBoundariesRepeatable": first_drift is None,
        "textureSamplingExecuted": False,
        "glbExtractionExecuted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
        "interpretation": (
            f"Repeatability first diverges at {first_drift}." if first_drift else
            "Shape sampling and raw decode are repeatable; remaining drift is in texture sampling, post-processing, or GLB serialization."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return report

training_image = (
    trellis_gpu_image
    .pip_install("pandas", "tensorboard")
    .run_commands(
        f"cd {TRELLIS2_PATH} && git fetch origin {TRAINING_CODE_COMMIT} && git checkout {TRAINING_CODE_COMMIT}"
    )
    .add_local_dir("scripts", remote_path="/root/scripts", copy=True)
)

# E12 imports the official shape-VAE geometry objective, whose loss module has
# an additional LPIPS dependency that the flow-training image does not need.
# Keep this isolated from every existing production and research worker, and
# fail during image construction rather than after allocating an H100.
e12_training_image = (
    training_image
    .pip_install("lpips==0.1.4")
    .run_commands(
        "python -c \"import lpips; print('E12 LPIPS import verified')\""
    )
)

# E14 validates the decoded crown-refiner support with marching cubes and a
# stored PLY. Keep these research-only dependencies out of production images,
# and prove the numerical runtime imports while the image is built rather than
# after reserving an H100.
e14_training_image = (
    training_image
    .pip_install("scikit-image", "trimesh", "shapely")
    .run_commands(
        "python -c \"import numpy as np; assert np.ndarray; import scipy; import skimage; import trimesh; import shapely\""
    )
)


@app.function(
    image=e12_training_image,
    gpu="T4",
    timeout=10 * 60,
)
def validate_e12_training_imports() -> dict:
    """GPU-backed, zero-optimizer import gate for the official E12 trainer."""
    import lpips
    from trellis2.trainers.vae.shape_vae import ShapeVaeTrainer

    return {
        "valid": True,
        "lpipsVersion": getattr(lpips, "__version__", "0.1.4"),
        "trainer": ShapeVaeTrainer.__name__,
        "optimizerSteps": 0,
    }


@app.function(
    image=training_image,
    volumes={
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    cpu=8,
    memory=32768,
    timeout=2 * 60 * 60,
)
def materialize_e4_sparse_trust_region() -> dict:
    """Create immutable task-vector-scaled sparse checkpoints without training."""
    import torch
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file

    def sha256_path(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(8 * 1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    run_name = "e4-sparse-task-vector-v1"
    alphas = (0.05, 0.10, 0.20)
    root = Path(f"/checkpoints/{run_name}")
    receipt_path = root / "materialization_receipt.json"
    if receipt_path.exists():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return {**existing, "resumed": True}
        raise ValueError("Incomplete E4 materialization exists; refusing overwrite")
    candidate_path = Path(
        "/checkpoints/e3-sparse-tf-pw32-step50-v1/ckpts/"
        "denoiser_ema0.9999_step0000050.pt"
    )
    if not candidate_path.is_file():
        raise FileNotFoundError(candidate_path)
    base_path = Path(hf_hub_download(
        repo_id=BASE_MODEL_NAME,
        filename=f"{BASE_SPARSE_FLOW_FILE}.safetensors",
        revision=BASE_MODEL_REVISION,
        cache_dir="/cache/huggingface",
        local_files_only=True,
    ))

    candidate_state = torch.load(candidate_path, map_location="cpu", weights_only=True, mmap=True)
    base_state = load_file(str(base_path), device="cpu")
    outputs = []
    root.mkdir(parents=True, exist_ok=False)
    for alpha in alphas:
        label = f"alpha-{int(round(alpha * 100)):03d}"
        output_dir = root / label
        output_dir.mkdir()
        output = output_dir / "denoiser_ema0.9999_step0000050.pt"
        blended = interpolate_sparse_task_vector(base_state, candidate_state, alpha)
        torch.save(blended, output)
        digest = sha256_path(output)
        outputs.append({
            "alpha": alpha,
            "label": label,
            "checkpointPath": str(output),
            "checkpointBytes": output.stat().st_size,
            "checkpointSha256": digest,
            "entryCount": len(blended),
        })
        del blended
    receipt = {
        "schemaVersion": 1,
        "experimentId": run_name,
        "status": "complete",
        "method": "base-plus-alpha-times-e3-step50-task-vector",
        "baseModelName": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trellisCommit": TRELLIS_COMMIT,
        "sourceCandidatePath": str(candidate_path),
        "sourceCandidateSha256": sha256_path(candidate_path),
        "alphas": list(alphas),
        "outputs": outputs,
        "trainingExecuted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return receipt


@app.function(
    image=trellis_gpu_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="A100",
    timeout=90 * 60,
)
def screen_e4_sparse_trust_region() -> dict:
    """Screen scaled sparse updates before any downstream mesh generation."""
    import io
    import os
    import random
    import sys

    import numpy as np
    import torch
    from PIL import Image

    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator

    dataset_root = Path("/datasets/dental-anatomy-v1")
    experiment_id = "e4_sparse_trust_region_screen_v1"
    report_path = dataset_root / f"{experiment_id}.json"
    if report_path.exists():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return {**existing, "resumed": True}
        raise ValueError("Incomplete E4 screen exists; refusing overwrite")
    materialization = json.loads(Path(
        "/checkpoints/e4-sparse-task-vector-v1/materialization_receipt.json"
    ).read_text(encoding="utf-8"))
    if materialization.get("status") != "complete" or materialization.get("alphas") != [0.05, 0.1, 0.2]:
        raise ValueError("Sealed E4 materialization receipt is required")
    inputs = json.loads((dataset_root / "benchmark_inputs_v1.json").read_text(encoding="utf-8"))
    case = next(row for row in inputs["cases"] if row["id"] == "004029_fdi21")
    image_bytes = (dataset_root / case["inputImage"]).read_bytes()
    if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
        raise ValueError("Frozen E4 input image hash drifted")

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    generator = TrellisGenerator()
    generator.load_model()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    image = Image.open(io.BytesIO(image_bytes))
    image.load()
    processed = generator.pipeline.preprocess_image(image)
    conditioning = generator.pipeline.get_cond([processed], 512)
    params = sampler_params_for_steps(12)["sparse_structure"]
    seed = int(case["generationSeed"])

    def sample() -> np.ndarray:
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        with torch.inference_mode():
            coords = generator.pipeline.sample_sparse_structure(
                conditioning, 32, sampler_params=params
            )
        return coords.detach().cpu().numpy().astype(np.int32, copy=False)

    base = sample()
    candidates = []
    passing = []
    for output in materialization["outputs"]:
        checkpoint_receipt = generator.load_sparse_structure_checkpoint(output["checkpointPath"])
        coords = sample()
        comparison = compare_sparse_occupancies(base, coords, 32)
        gate_checks = {
            "voxelIoUAtLeast0.95": comparison["voxelIoU"] >= 0.95,
            "absoluteVoxelCountChangeAtMost0.02": abs(
                comparison["candidateVoxelCountRelativeChange"]
            ) <= 0.02,
            "centroidShiftFractionAtMost0.01": (
                comparison["centroidShiftFractionResolution"] <= 0.01
            ),
            "singleConnectedComponent": (
                comparison["candidate"]["componentCount6Connected"] == 1
            ),
        }
        passed = all(gate_checks.values())
        row = {
            "alpha": output["alpha"],
            "label": output["label"],
            "checkpoint": checkpoint_receipt,
            "comparison": comparison,
            "gateChecks": gate_checks,
            "passedOccupancyPreservationGate": passed,
        }
        candidates.append(row)
        if passed:
            passing.append(row)

    selected = max(passing, key=lambda row: row["alpha"]) if passing else None
    selected_repeatability = None
    if selected is not None:
        generator.load_sparse_structure_checkpoint(selected["checkpoint"]["checkpointPath"])
        first = sample()
        second = sample()
        selected_repeatability = compare_sparse_occupancies(first, second, 32)
        if not selected_repeatability["exactlyEqual"]:
            selected = None

    report = {
        "schemaVersion": 1,
        "experimentId": experiment_id,
        "status": "complete",
        "caseId": case["id"],
        "inputImageSha256": case["inputImageSha256"],
        "seed": seed,
        "preservationThresholds": {
            "minimumVoxelIoU": 0.95,
            "maximumAbsoluteVoxelCountRelativeChange": 0.02,
            "maximumCentroidShiftFractionResolution": 0.01,
            "requiredComponentCount6Connected": 1,
        },
        "candidates": candidates,
        "selectedCandidate": None if selected is None else {
            "alpha": selected["alpha"], "label": selected["label"],
            "checkpoint": selected["checkpoint"],
        },
        "selectedRepeatability": selected_repeatability,
        "fullMeshEvaluationPermitted": selected is not None,
        "trainingExecuted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return report


@app.function(
    image=training_image,
    volumes={
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    cpu=8,
    memory=32768,
    timeout=2 * 60 * 60,
)
def materialize_e4_sparse_refinement() -> dict:
    """Materialize the pre-registered smaller E4 task-vector bracket."""
    import torch
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file

    def sha256_path(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(8 * 1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    run_name = "e4-sparse-task-vector-refinement-v1"
    alphas = (0.01, 0.025, 0.04)
    root = Path(f"/checkpoints/{run_name}")
    receipt_path = root / "materialization_receipt.json"
    if receipt_path.exists():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return {**existing, "resumed": True}
        raise ValueError("Incomplete E4 refinement materialization exists")
    candidate_path = Path(
        "/checkpoints/e3-sparse-tf-pw32-step50-v1/ckpts/"
        "denoiser_ema0.9999_step0000050.pt"
    )
    base_path = Path(hf_hub_download(
        repo_id=BASE_MODEL_NAME,
        filename=f"{BASE_SPARSE_FLOW_FILE}.safetensors",
        revision=BASE_MODEL_REVISION,
        cache_dir="/cache/huggingface",
        local_files_only=True,
    ))
    if not candidate_path.is_file():
        raise FileNotFoundError(candidate_path)
    candidate_state = torch.load(candidate_path, map_location="cpu", weights_only=True, mmap=True)
    base_state = load_file(str(base_path), device="cpu")
    root.mkdir(parents=True, exist_ok=False)
    outputs = []
    for alpha in alphas:
        label = f"alpha-{int(round(alpha * 1000)):03d}"
        output_dir = root / label
        output_dir.mkdir()
        output = output_dir / "denoiser_ema0.9999_step0000050.pt"
        blended = interpolate_sparse_task_vector(base_state, candidate_state, alpha)
        torch.save(blended, output)
        outputs.append({
            "alpha": alpha,
            "label": label,
            "checkpointPath": str(output),
            "checkpointBytes": output.stat().st_size,
            "checkpointSha256": sha256_path(output),
            "entryCount": len(blended),
        })
        del blended
    receipt = {
        "schemaVersion": 1,
        "experimentId": run_name,
        "status": "complete",
        "method": "base-plus-alpha-times-e3-step50-task-vector",
        "baseModelName": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trellisCommit": TRELLIS_COMMIT,
        "sourceCandidateSha256": sha256_path(candidate_path),
        "alphas": list(alphas),
        "outputs": outputs,
        "selectionDeclaredBeforeEvaluation": True,
        "trainingExecuted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return receipt


@app.function(
    image=trellis_gpu_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="A100",
    timeout=2 * 60 * 60,
)
def screen_e4_sparse_refinement() -> dict:
    """Apply the unchanged occupancy gate across four frozen tooth families."""
    import io
    import os
    import random
    import sys

    import numpy as np
    import torch
    from PIL import Image

    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator

    dataset_root = Path("/datasets/dental-anatomy-v1")
    experiment_id = "e4_sparse_trust_region_refinement_v1"
    report_path = dataset_root / f"{experiment_id}.json"
    if report_path.exists():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return {**existing, "resumed": True}
        raise ValueError("Incomplete E4 refinement screen exists")
    materialization = json.loads(Path(
        "/checkpoints/e4-sparse-task-vector-refinement-v1/materialization_receipt.json"
    ).read_text(encoding="utf-8"))
    if materialization.get("alphas") != [0.01, 0.025, 0.04]:
        raise ValueError("Pre-registered E4 refinement bracket drifted")
    inputs = json.loads((dataset_root / "benchmark_inputs_v1.json").read_text(encoding="utf-8"))
    frozen_ids = ("004029_fdi21", "001363_fdi13", "008934_fdi34", "001341_fdi16")
    by_id = {row["id"]: row for row in inputs["cases"]}
    if any(case_id not in by_id for case_id in frozen_ids):
        raise ValueError("A frozen four-family case is missing")
    cases = [by_id[case_id] for case_id in frozen_ids]
    if {row["toothFamily"] for row in cases} != {
        "incisor", "canine", "premolar", "molar"
    }:
        raise ValueError("Frozen four-family benchmark is required")

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    generator = TrellisGenerator()
    generator.load_model()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    params = sampler_params_for_steps(12)["sparse_structure"]

    prepared = {}
    for case in cases:
        image_bytes = (dataset_root / case["inputImage"]).read_bytes()
        if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
            raise ValueError(f"Input image hash drifted: {case['id']}")
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        processed = generator.pipeline.preprocess_image(image)
        prepared[case["id"]] = {
            "case": case,
            "conditioning": generator.pipeline.get_cond([processed], 512),
        }

    def sample(case_id: str) -> np.ndarray:
        case = prepared[case_id]["case"]
        seed = int(case["generationSeed"])
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        with torch.inference_mode():
            coords = generator.pipeline.sample_sparse_structure(
                prepared[case_id]["conditioning"], 32, sampler_params=params
            )
        return coords.detach().cpu().numpy().astype(np.int32, copy=False)

    base = {case["id"]: sample(case["id"]) for case in cases}
    candidates = []
    passing = []
    cached_candidate_coords = {}
    for output in materialization["outputs"]:
        checkpoint_receipt = generator.load_sparse_structure_checkpoint(output["checkpointPath"])
        case_rows = []
        all_cases_passed = True
        for case in cases:
            coords = sample(case["id"])
            cached_candidate_coords[(output["label"], case["id"])] = coords
            comparison = compare_sparse_occupancies(base[case["id"]], coords, 32)
            checks = {
                "voxelIoUAtLeast0.95": comparison["voxelIoU"] >= 0.95,
                "absoluteVoxelCountChangeAtMost0.02": abs(
                    comparison["candidateVoxelCountRelativeChange"]
                ) <= 0.02,
                "centroidShiftFractionAtMost0.01": (
                    comparison["centroidShiftFractionResolution"] <= 0.01
                ),
                "singleConnectedComponent": (
                    comparison["candidate"]["componentCount6Connected"] == 1
                ),
            }
            passed = all(checks.values())
            all_cases_passed = all_cases_passed and passed
            case_rows.append({
                "id": case["id"],
                "toothFamily": case["toothFamily"],
                "comparison": comparison,
                "gateChecks": checks,
                "passed": passed,
            })
        row = {
            "alpha": output["alpha"],
            "label": output["label"],
            "checkpoint": checkpoint_receipt,
            "cases": case_rows,
            "allFamiliesPassed": all_cases_passed,
        }
        candidates.append(row)
        if all_cases_passed:
            passing.append(row)

    selected = max(passing, key=lambda row: row["alpha"]) if passing else None
    repeatability = []
    if selected is not None:
        generator.load_sparse_structure_checkpoint(selected["checkpoint"]["checkpointPath"])
        for case in cases:
            original = cached_candidate_coords[(selected["label"], case["id"])]
            repeated = sample(case["id"])
            comparison = compare_sparse_occupancies(original, repeated, 32)
            repeatability.append({
                "id": case["id"],
                "toothFamily": case["toothFamily"],
                "exactlyEqual": comparison["exactlyEqual"],
                "comparison": comparison,
            })
        if not all(row["exactlyEqual"] for row in repeatability):
            selected = None

    report = {
        "schemaVersion": 1,
        "experimentId": experiment_id,
        "status": "complete",
        "caseCount": 4,
        "toothFamilies": ["incisor", "canine", "premolar", "molar"],
        "preservationThresholds": {
            "minimumVoxelIoU": 0.95,
            "maximumAbsoluteVoxelCountRelativeChange": 0.02,
            "maximumCentroidShiftFractionResolution": 0.01,
            "requiredComponentCount6Connected": 1,
            "mustPassEveryFamily": True,
        },
        "candidates": candidates,
        "selectedCandidate": None if selected is None else {
            "alpha": selected["alpha"],
            "label": selected["label"],
            "checkpoint": selected["checkpoint"],
        },
        "selectedRepeatability": repeatability,
        "fullMeshEvaluationPermitted": selected is not None,
        "trainingExecuted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return report


@app.function(
    image=trellis_gpu_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="A100",
    timeout=2 * 60 * 60,
)
def screen_sparse_canary_occupancy(experiment: str = "e5") -> dict:
    """Apply one unchanged four-family occupancy gate to sealed candidate EMAs."""
    import io
    import os
    import random
    import sys

    import numpy as np
    import torch
    from PIL import Image

    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator

    dataset_root = Path("/datasets/dental-anatomy-v1")
    contracts = {
        "e5": {
            "experimentId": "e5_sparse_trust_region_step10_occupancy_v1",
            "evidencePath": (
                "/checkpoints/e5-sparse-trust-region-step10-v1/canary-evidence.json"
            ),
            "expectedSteps": 10,
            "permissionKey": "fourFamilyOccupancyScreenPermitted",
        },
        "e6": {
            "experimentId": "e6_sparse_teacher_consistency_step10_occupancy_v1",
            "evidencePath": (
                "/checkpoints/e6-sparse-teacher-consistency-step10-v1/"
                "canary-evidence.json"
            ),
            "expectedSteps": 10,
            "permissionKey": "fourFamilyOccupancyScreenPermitted",
        },
        "e7": {
            "experimentId": "e7_sparse_calibrated_anchor_step10_occupancy_v1",
            "evidencePath": (
                "/checkpoints/e7-sparse-calibrated-anchor-step10-v1/"
                "canary-evidence.json"
            ),
            "expectedSteps": 10,
            "permissionKey": "fourFamilyOccupancyScreenPermitted",
        },
        "e8-smoke": {
            "experimentId": "e8_sparse_decoded_occupancy_step2_screen_v1",
            "evidencePath": (
                "/checkpoints/e8-sparse-decoded-occupancy-smoke-v1/"
                "smoke-evidence.json"
            ),
            "expectedSteps": 2,
            "permissionKey": "incisorTwoStepScreenPermitted",
            "candidateCheckpointPath": (
                "/checkpoints/e8-sparse-decoded-occupancy-smoke-v1/ckpts/"
                "denoiser_ema0.9999_step0000002.pt"
            ),
        },
        "e8-smoke-repeatability": {
            "experimentId": "e8_sparse_decoded_occupancy_step2_screen_v2",
            "evidencePath": (
                "/checkpoints/e8-sparse-decoded-occupancy-smoke-v1/"
                "smoke-evidence.json"
            ),
            "expectedSteps": 2,
            "permissionKey": "incisorTwoStepScreenPermitted",
            "candidateCheckpointPath": (
                "/checkpoints/e8-sparse-decoded-occupancy-smoke-v1/ckpts/"
                "denoiser_ema0.9999_step0000002.pt"
            ),
        },
    }
    if experiment not in contracts:
        raise ValueError("Occupancy experiment is not a sealed contract")
    contract = contracts[experiment]
    experiment_id = contract["experimentId"]
    report_path = dataset_root / f"{experiment_id}.json"
    if report_path.exists():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return {**existing, "resumed": True}
        raise ValueError(f"Incomplete {experiment.upper()} occupancy screen exists")
    evidence_path = Path(contract["evidencePath"])
    if not evidence_path.is_file():
        raise FileNotFoundError(f"Passed {experiment.upper()} canary evidence is required")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not (
        evidence.get("valid")
        and evidence.get("steps") == contract["expectedSteps"]
        and evidence.get(contract["permissionKey"])
        and not evidence.get("fullMeshEvaluationPermitted")
    ):
        raise ValueError(
            f"{experiment.upper()} canary evidence does not authorize occupancy screening"
        )
    checkpoint_path = Path(
        contract.get("candidateCheckpointPath", evidence.get("candidateCheckpointPath", ""))
    )
    if not checkpoint_path.is_file():
        raise FileNotFoundError(checkpoint_path)

    inputs = json.loads(
        (dataset_root / "benchmark_inputs_v1.json").read_text(encoding="utf-8")
    )
    frozen_ids = ("004029_fdi21", "001363_fdi13", "008934_fdi34", "001341_fdi16")
    by_id = {row["id"]: row for row in inputs["cases"]}
    if any(case_id not in by_id for case_id in frozen_ids):
        raise ValueError("A frozen four-family case is missing")
    cases = [by_id[case_id] for case_id in frozen_ids]
    if {row["toothFamily"] for row in cases} != {
        "incisor", "canine", "premolar", "molar"
    }:
        raise ValueError("Frozen four-family benchmark is required")

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    generator = TrellisGenerator()
    generator.load_model()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    params = sampler_params_for_steps(12)["sparse_structure"]

    prepared = {}
    for case in cases:
        image_bytes = (dataset_root / case["inputImage"]).read_bytes()
        if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
            raise ValueError(f"Input image hash drifted: {case['id']}")
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        processed = generator.pipeline.preprocess_image(image)
        prepared[case["id"]] = {
            "case": case,
            "conditioning": generator.pipeline.get_cond([processed], 512),
        }

    def sample(case_id: str) -> np.ndarray:
        case = prepared[case_id]["case"]
        seed = int(case["generationSeed"])
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        with torch.inference_mode():
            coords = generator.pipeline.sample_sparse_structure(
                prepared[case_id]["conditioning"], 32, sampler_params=params
            )
        return coords.detach().cpu().numpy().astype(np.int32, copy=False)

    frozen_root = dataset_root / "frozen_sparse_base_v1"
    frozen_receipt_path = frozen_root / "receipt.json"
    if not frozen_receipt_path.is_file():
        raise FileNotFoundError("Immutable sparse base benchmark is required")
    frozen_receipt = json.loads(frozen_receipt_path.read_text(encoding="utf-8"))
    if not (
        frozen_receipt.get("valid")
        and frozen_receipt.get("caseCount") == 4
        and frozen_receipt.get("exactlyRepeatableEveryFamily")
        and len(frozen_receipt.get("cohortSha256", "")) == 64
    ):
        raise ValueError("Immutable sparse base receipt failed its sealed contract")
    frozen_assets = {asset["id"]: asset for asset in frozen_receipt["assets"]}
    base = {}
    for case in cases:
        asset = frozen_assets.get(case["id"])
        if not asset or asset.get("toothFamily") != case["toothFamily"]:
            raise ValueError(f"Frozen sparse base case mismatch: {case['id']}")
        path = frozen_root / asset["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            raise ValueError(f"Frozen sparse base artifact drifted: {path}")
        base[case["id"]] = np.load(path, allow_pickle=False)
    base_repeatability = frozen_receipt["repeatability"]
    base_exactly_repeatable = True
    checkpoint_receipt = generator.load_sparse_structure_checkpoint(
        str(checkpoint_path)
    )
    candidate_coords = {}
    case_rows = []
    for case in cases:
        coords = sample(case["id"])
        candidate_coords[case["id"]] = coords
        comparison = compare_sparse_occupancies(base[case["id"]], coords, 32)
        checks = {
            "voxelIoUAtLeast0.95": comparison["voxelIoU"] >= 0.95,
            "absoluteVoxelCountChangeAtMost0.02": abs(
                comparison["candidateVoxelCountRelativeChange"]
            ) <= 0.02,
            "centroidShiftFractionAtMost0.01": (
                comparison["centroidShiftFractionResolution"] <= 0.01
            ),
            "singleConnectedComponent": (
                comparison["candidate"]["componentCount6Connected"] == 1
            ),
        }
        case_rows.append({
            "id": case["id"],
            "toothFamily": case["toothFamily"],
            "comparison": comparison,
            "gateChecks": checks,
            "passed": all(checks.values()),
        })

    all_families_passed = all(row["passed"] for row in case_rows)
    candidate_repeatability = []
    for case in cases:
        repeated = sample(case["id"])
        comparison = compare_sparse_occupancies(
            candidate_coords[case["id"]], repeated, 32
        )
        candidate_repeatability.append({
            "id": case["id"],
            "toothFamily": case["toothFamily"],
            "exactlyEqual": comparison["exactlyEqual"],
            "comparison": comparison,
        })
    candidate_exactly_repeatable = all(
        row["exactlyEqual"] for row in candidate_repeatability
    )
    passed = (
        all_families_passed
        and base_exactly_repeatable
        and candidate_exactly_repeatable
    )
    report = {
        "schemaVersion": 1,
        "experimentId": experiment_id,
        "status": "complete",
        "sourceCanaryEvidence": str(evidence_path),
        "candidateCheckpoint": checkpoint_receipt,
        "caseCount": 4,
        "toothFamilies": ["incisor", "canine", "premolar", "molar"],
        "preservationThresholds": {
            "minimumVoxelIoU": 0.95,
            "maximumAbsoluteVoxelCountRelativeChange": 0.02,
            "maximumCentroidShiftFractionResolution": 0.01,
            "requiredComponentCount6Connected": 1,
            "mustPassEveryFamily": True,
            "mustBeExactlyRepeatable": True,
        },
        "cases": case_rows,
        "allFamiliesPassed": all_families_passed,
        "baseRepeatability": base_repeatability,
        "baseExactlyRepeatable": base_exactly_repeatable,
        "frozenBaseCohortSha256": frozen_receipt["cohortSha256"],
        "candidateRepeatability": candidate_repeatability,
        "candidateExactlyRepeatable": candidate_exactly_repeatable,
        "benchmarkValid": base_exactly_repeatable and candidate_exactly_repeatable,
        "passedOccupancyPreservationGate": passed,
        "fullMeshEvaluationPermitted": passed,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return report


@app.function(
    image=trellis_gpu_image,
    volumes={
        "/datasets": dataset_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="A100",
    timeout=2 * 60 * 60,
)
def freeze_sparse_base_benchmark() -> dict:
    """Persist one immutable, repeatable base occupancy per frozen tooth family."""
    import io
    import os
    import random
    import sys

    import numpy as np
    import torch
    from PIL import Image

    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator

    dataset_root = Path("/datasets/dental-anatomy-v1")
    output_root = dataset_root / "frozen_sparse_base_v1"
    receipt_path = output_root / "receipt.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not receipt.get("valid") or receipt.get("caseCount") != 4:
            raise ValueError("Existing frozen sparse base receipt is invalid")
        for asset in receipt.get("assets", []):
            path = output_root / asset["file"]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
                raise ValueError(f"Frozen sparse base artifact drifted: {path}")
        return {**receipt, "resumed": True}
    if output_root.exists():
        raise FileExistsError("Partial frozen sparse base exists; inspect before retrying")

    inputs_path = dataset_root / "benchmark_inputs_v1.json"
    input_bytes = inputs_path.read_bytes()
    inputs = json.loads(input_bytes)
    frozen_ids = ("004029_fdi21", "001363_fdi13", "008934_fdi34", "001341_fdi16")
    by_id = {row["id"]: row for row in inputs["cases"]}
    if any(case_id not in by_id for case_id in frozen_ids):
        raise ValueError("A frozen four-family case is missing")
    cases = [by_id[case_id] for case_id in frozen_ids]
    expected_families = ["incisor", "canine", "premolar", "molar"]
    if [case["toothFamily"] for case in cases] != expected_families:
        raise ValueError("Frozen benchmark family order changed")

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    generator = TrellisGenerator()
    generator.load_model()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    params = sampler_params_for_steps(12)["sparse_structure"]

    prepared = {}
    for case in cases:
        image_bytes = (dataset_root / case["inputImage"]).read_bytes()
        if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
            raise ValueError(f"Input image hash drifted: {case['id']}")
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        processed = generator.pipeline.preprocess_image(image)
        prepared[case["id"]] = generator.pipeline.get_cond([processed], 512)

    def sample(case: dict) -> np.ndarray:
        seed = int(case["generationSeed"])
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        with torch.inference_mode():
            coords = generator.pipeline.sample_sparse_structure(
                prepared[case["id"]], 32, sampler_params=params
            )
        return coords.detach().cpu().numpy().astype(np.int32, copy=False)

    first = {case["id"]: sample(case) for case in cases}
    repeatability = []
    for case in cases:
        comparison = compare_sparse_occupancies(first[case["id"]], sample(case), 32)
        repeatability.append({
            "id": case["id"],
            "toothFamily": case["toothFamily"],
            "exactlyEqual": comparison["exactlyEqual"],
            "comparison": comparison,
        })
    if not all(row["exactlyEqual"] for row in repeatability):
        raise RuntimeError("Base sparse benchmark is not exactly repeatable; nothing persisted")

    output_root.mkdir(parents=True)
    assets = []
    for case in cases:
        filename = f"{case['id']}.npy"
        path = output_root / filename
        np.save(path, first[case["id"]], allow_pickle=False)
        assets.append({
            "id": case["id"],
            "toothFamily": case["toothFamily"],
            "generationSeed": int(case["generationSeed"]),
            "file": filename,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "voxelCount": int(first[case["id"]].shape[0]),
        })
    cohort_sha = hashlib.sha256(
        "\n".join(f"{asset['id']}:{asset['sha256']}" for asset in assets).encode("utf-8")
    ).hexdigest()
    receipt = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "frozen-sparse-base-benchmark-v1",
        "caseCount": 4,
        "resolution": 32,
        "samplerSteps": 12,
        "model": BASE_MODEL_NAME,
        "modelRevision": BASE_MODEL_REVISION,
        "benchmarkInputsSha256": hashlib.sha256(input_bytes).hexdigest(),
        "deterministicControls": {
            "cublasWorkspaceConfig": ":4096:8",
            "tf32": False,
            "cudnnDeterministic": True,
            "torchDeterministicAlgorithms": True,
        },
        "exactlyRepeatableEveryFamily": True,
        "repeatability": repeatability,
        "assets": assets,
        "cohortSha256": cohort_sha,
        "trainingExecuted": False,
        "productionMutationPermitted": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return receipt


@app.function(
    image=training_image,
    volumes={"/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    timeout=30 * 60,
)
def validate_training_runtime() -> dict:
    """Cheap fail-fast audit of source and pinned base checkpoint before H100 use."""
    import importlib.util
    from huggingface_hub import list_repo_files

    train_path = Path(TRELLIS2_PATH) / "train.py"
    config_path = Path(TRELLIS2_PATH) / "configs/gen/slat_flow_img2shape_dit_1_3B_512_bf16.json"
    required = {f"{BASE_SHAPE_FLOW_FILE}.json", f"{BASE_SHAPE_FLOW_FILE}.safetensors"}
    repository_files = set(list_repo_files("microsoft/TRELLIS.2-4B", revision=BASE_MODEL_REVISION))
    checks = {
        "trainSource": train_path.is_file(),
        "baseConfig": config_path.is_file(),
        "trainerImport": importlib.util.find_spec("trellis2.trainers") is not None,
        "baseCheckpointFiles": required <= repository_files,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Training runtime preflight failed: {checks}")
    return {
        "valid": True,
        "checks": checks,
        "trainingCodeCommit": TRAINING_CODE_COMMIT,
        "baseModelRevision": BASE_MODEL_REVISION,
        "baseShapeCheckpoint": BASE_SHAPE_FLOW_FILE,
    }


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100",
    # Modal caps individual calls at 24h. The preprocessing script checkpoints
    # each completed artifact and skips it on the next invocation.
    timeout=24 * 60 * 60,
)
def preprocess_anatomy(dataset_name: str, resolution: int = 512, num_cond_views: int = 24) -> dict:
    """Run one resumable TRELLIS.2 preprocessing pass for an anatomy dataset."""
    import sys
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("TRELLIS preprocessing requires an active CUDA GPU")

    sys.path.insert(0, "/root")
    from scripts.preprocess_anatomy_trellis import preprocess

    dataset_root = Path(f"/datasets/{dataset_name}")
    manifest = dataset_root / "anatomy_manifest.json"
    if not manifest.is_file():
        raise FileNotFoundError(f"Missing anatomy manifest: {manifest}")
    from scripts.validate_anatomy_dataset import validate_dataset
    validate_dataset(manifest, expected_dataset_id=dataset_name, require_files=True)
    status = preprocess(
        manifest,
        dataset_root,
        dataset_root,
        resolution=resolution,
        num_cond_views=num_cond_views,
        trellis_root=Path(TRELLIS2_PATH),
        scripts_root=Path("/root/scripts"),
    )
    dataset_volume.commit()
    return status


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100",
    timeout=24 * 60 * 60,
)
def preprocess_stage1_cohort(
    dataset_name: str = "toothfairy-stage1-v1",
    resolution: int = 512,
    num_cond_views: int = 8,
) -> dict:
    """Run the sealed, resumable small-data Stage-1 preprocessing protocol."""
    import sys
    import torch

    if dataset_name != "toothfairy-stage1-v1" or resolution != 512 or num_cond_views != 8:
        raise ValueError("Stage-1 preprocessing is sealed at toothfairy-stage1-v1, 512/8")
    if not torch.cuda.is_available():
        raise RuntimeError("TRELLIS preprocessing requires an active CUDA GPU")
    sys.path.insert(0, "/root")
    from scripts.anatomy_common import sha256_file
    from scripts.preprocess_anatomy_trellis import preprocess
    from scripts.validate_anatomy_dataset import validate_dataset

    root = Path(f"/datasets/{dataset_name}")
    manifest = root / "anatomy_manifest.json"
    validation = validate_dataset(
        manifest, expected_dataset_id=dataset_name,
        minimum_per_family=32, require_files=True,
    )
    canary_path = root / "stage1_render_canary_receipt.json"
    if not canary_path.is_file():
        raise FileNotFoundError("Stage-1 render canary receipt is required")
    canary = json.loads(canary_path.read_text(encoding="utf-8"))
    if (
        canary.get("manifestSha256") != sha256_file(manifest)
        or canary.get("successfulConditionalRenders") != 8
        or canary.get("numCondViews") != 8
        or canary.get("optimizerExecuted") is not False
    ):
        raise ValueError("Stage-1 render canary receipt does not match the sealed dataset")
    status = preprocess(
        manifest, root, root, resolution=resolution,
        num_cond_views=num_cond_views, trellis_root=Path(TRELLIS2_PATH),
        scripts_root=Path("/root/scripts"),
    )
    receipt = {
        "schemaVersion": 1,
        "stage": "clinical-stage1-preprocessing",
        "datasetId": dataset_name,
        "manifestSha256": sha256_file(manifest),
        "resolution": resolution,
        "numCondViews": num_cond_views,
        "optimizerExecuted": False,
        "validation": validation,
        "status": status,
    }
    (root / "stage1_preprocess_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    dataset_volume.commit()
    return receipt


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    timeout=30 * 60,
)
def diagnose_conditional_render(
    dataset_name: str = "dental-anatomy-v1",
    sample_count: int = 1,
    num_cond_views: int = 4,
    balanced_families: bool = False,
) -> dict:
    """Run a bounded CPU Blender diagnostic and retain its full subprocess output."""
    import shutil
    import sys

    sys.path.insert(0, "/root")
    from scripts.diagnose_conditional_render import run_diagnostic
    from scripts.preprocess_anatomy_trellis import ensure_data_toolkit, install_dataset_module

    if sample_count < 1 or sample_count > 8:
        raise ValueError("sample_count must be between 1 and 8")
    if num_cond_views < 1 or num_cond_views > 24:
        raise ValueError("num_cond_views must be between 1 and 24")
    dataset_root = Path(f"/datasets/{dataset_name}")
    if not (dataset_root / "metadata.csv").is_file():
        raise FileNotFoundError(f"Missing dataset metadata: {dataset_root / 'metadata.csv'}")
    toolkit = ensure_data_toolkit(Path(TRELLIS2_PATH))
    install_dataset_module(Path(TRELLIS2_PATH), Path("/root/scripts"))
    diagnostic_root = Path("/tmp/dentalsculptor-render-diagnostic")
    shutil.rmtree(diagnostic_root, ignore_errors=True)
    diagnostic_root.mkdir(parents=True)
    result = run_diagnostic(
        toolkit=toolkit,
        dataset_root=dataset_root,
        render_root=diagnostic_root,
        subset="DentalAnatomy",
        sample_count=sample_count,
        num_cond_views=num_cond_views,
        balanced_families=balanced_families,
    )
    print(json.dumps(result, indent=2), flush=True)
    return result


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume},
    cpu=4,
    memory=16384,
    timeout=60 * 60,
)
def render_provisional_cohort_canary(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    sample_count: int = 2,
    num_cond_views: int = 8,
) -> dict:
    """Prove the renderer on an explicitly non-clinical cohort before preprocessing."""
    import sys

    if sample_count != 2:
        raise ValueError("The provisional gate is intentionally fixed at two assets")
    if num_cond_views < 4 or num_cond_views > 24:
        raise ValueError("num_cond_views must be between 4 and 24")
    sys.path.insert(0, "/root")
    from scripts.anatomy_common import sha256_file
    from scripts.bootstrap_trellis_metadata import bootstrap
    from scripts.preprocess_anatomy_trellis import (
        ensure_data_toolkit,
        install_dataset_module,
        run_render_canary,
    )

    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("datasetId") != dataset_name
        or manifest.get("trainingPurpose") != "engineering-smoke-only"
        or manifest.get("clinicalClaimPermitted") is not False
        or manifest.get("researchTrainingApproved") is not False
        or manifest.get("assetCount") != 32
    ):
        raise ValueError("Dataset does not match the sealed TF-PW32 provisional contract")
    for asset in manifest["assets"]:
        mesh_path = root / asset["canonicalPath"]
        if not mesh_path.is_file() or sha256_file(mesh_path) != asset["canonicalSha256"]:
            raise ValueError(f"Canonical mesh integrity failed: {asset['id']}")
    toolkit = ensure_data_toolkit(Path(TRELLIS2_PATH))
    install_dataset_module(Path(TRELLIS2_PATH), Path("/root/scripts"))
    bootstrap(manifest_path, root, root, subset="DentalAnatomy")
    result = run_render_canary(
        toolkit, root, sample_count=sample_count, num_cond_views=num_cond_views
    )
    receipt = {
        "schemaVersion": 1,
        "stage": "provisional-render-canary",
        "datasetId": dataset_name,
        "manifestSha256": sha256_file(manifest_path),
        "clinicalClaimPermitted": False,
        **result,
    }
    (root / "provisional_render_canary_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    dataset_volume.commit()
    return receipt


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume},
    cpu=4,
    memory=16384,
    timeout=60 * 60,
)
def render_stage1_cohort_canary(
    dataset_name: str = "toothfairy-stage1-v1",
    sample_count: int = 8,
    num_cond_views: int = 8,
) -> dict:
    """Prove Blender rendering on the sealed clinical Stage-1 dataset without a GPU."""
    import sys
    from collections import Counter

    if sample_count != 8 or num_cond_views != 8:
        raise ValueError("The registered Stage-1 render canary is fixed at 8 assets and 8 views")
    sys.path.insert(0, "/root")
    from scripts.anatomy_common import sha256_file
    from scripts.bootstrap_trellis_metadata import bootstrap
    from scripts.preprocess_anatomy_trellis import (
        ensure_data_toolkit,
        install_dataset_module,
        run_render_canary,
    )

    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_splits = {"train": 128, "validation": 12, "test": 24}
    if (
        manifest.get("datasetId") != dataset_name
        or manifest.get("trainingPurpose") != "registered-stage1"
        or manifest.get("clinicalClaimPermitted") is not True
        or manifest.get("researchTrainingApproved") is not True
        or manifest.get("assetCount") != 164
        or manifest.get("splits") != expected_splits
    ):
        raise ValueError("Dataset does not match the sealed clinical Stage-1 contract")
    train_families = Counter(
        asset["toothFamily"] for asset in manifest["assets"] if asset["split"] == "train"
    )
    if train_families != Counter({family: 32 for family in ("incisor", "canine", "premolar", "molar")}):
        raise ValueError("Stage-1 train family balance changed")
    for asset in manifest["assets"]:
        mesh_path = root / asset["canonicalPath"]
        if not mesh_path.is_file() or sha256_file(mesh_path) != asset["canonicalSha256"]:
            raise ValueError(f"Canonical mesh integrity failed: {asset['id']}")
    toolkit = ensure_data_toolkit(Path(TRELLIS2_PATH))
    install_dataset_module(Path(TRELLIS2_PATH), Path("/root/scripts"))
    bootstrap(manifest_path, root, root, subset="DentalAnatomy")
    result = run_render_canary(
        toolkit, root, sample_count=sample_count, num_cond_views=num_cond_views
    )
    receipt = {
        "schemaVersion": 1,
        "stage": "clinical-stage1-render-canary",
        "datasetId": dataset_name,
        "manifestSha256": sha256_file(manifest_path),
        "clinicalClaimPermitted": True,
        "optimizerExecuted": False,
        **result,
    }
    (root / "stage1_render_canary_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    dataset_volume.commit()
    return receipt


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume},
    cpu=4,
    memory=16384,
    timeout=2 * 60 * 60,
)
def prepare_stage1_validation_inputs(
    dataset_name: str = "toothfairy-stage1-v1",
    num_cond_views: int = 8,
    selected_view: int = 0,
) -> dict:
    """Render and seal the patient-disjoint Stage-1 validation inputs."""
    import shutil
    import sys
    from collections import Counter

    if dataset_name != "toothfairy-stage1-v1" or num_cond_views != 8 or selected_view != 0:
        raise ValueError("Stage-1 validation inputs are sealed at view 0 of 8")
    sys.path.insert(0, "/root")
    from scripts.anatomy_common import sha256_file
    from scripts.preprocess_anatomy_trellis import ensure_data_toolkit, install_dataset_module
    from scripts.render_conditional_batches import render_selected_assets

    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = sorted(
        (asset for asset in manifest.get("assets", []) if asset.get("split") == "validation"),
        key=lambda asset: (asset["toothFamily"], asset["canonicalSha256"]),
    )
    families = Counter(asset["toothFamily"] for asset in validation)
    patients = {asset["groupId"] for asset in validation}
    training_patients = {
        asset["groupId"] for asset in manifest.get("assets", []) if asset.get("split") == "train"
    }
    if (
        len(validation) != 12
        or families != Counter({family: 3 for family in ("incisor", "canine", "premolar", "molar")})
        or len(patients) != 3
        or patients & training_patients
    ):
        raise ValueError("Stage-1 validation split balance or patient isolation changed")
    target = root / "stage1_validation_inputs_v1"
    receipt_path = root / "stage1_validation_inputs_v1.json"
    if receipt_path.is_file():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (
            existing.get("valid")
            and existing.get("manifestSha256") == sha256_file(manifest_path)
            and existing.get("caseCount") == 12
        ):
            return {**existing, "resumed": True}
        raise ValueError("Existing Stage-1 validation input receipt is stale")

    toolkit = ensure_data_toolkit(Path(TRELLIS2_PATH))
    install_dataset_module(Path(TRELLIS2_PATH), Path("/root/scripts"))
    rendered = render_selected_assets(
        toolkit=toolkit,
        dataset_root=root,
        subset="DentalAnatomy",
        rows=[{"sha256": asset["canonicalSha256"]} for asset in validation],
        num_cond_views=num_cond_views,
    )
    if not rendered.get("valid") or rendered.get("successfulCount") != 12:
        dataset_volume.commit()
        raise RuntimeError(f"Stage-1 validation rendering failed: {json.dumps(rendered)}")
    target.mkdir(parents=True, exist_ok=False)
    cases = []
    for index, asset in enumerate(validation):
        digest = asset["canonicalSha256"]
        source = root / "renders_cond" / digest / f"{selected_view:03d}.png"
        destination = target / f"{asset['id']}.png"
        shutil.copy2(source, destination)
        cases.append({
            "id": asset["id"],
            "toothFamily": asset["toothFamily"],
            "fdiNumber": asset.get("fdiNumber"),
            "groupId": asset["groupId"],
            "referenceMesh": asset["canonicalPath"],
            "referenceMeshSha256": digest,
            "inputImage": str(destination.relative_to(root)).replace("\\", "/"),
            "inputImageSha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "viewIndex": selected_view,
            "generationSeed": 1724708096 + index,
            "quality": "standard",
        })
    result = {
        "schemaVersion": 1,
        "stage": "stage1-patient-disjoint-validation-inputs",
        "valid": True,
        "datasetId": dataset_name,
        "manifestSha256": sha256_file(manifest_path),
        "caseCount": len(cases),
        "patientCount": len(patients),
        "familyCounts": dict(families),
        "numCondViews": num_cond_views,
        "selectedView": selected_view,
        "trainingPatientOverlapCount": 0,
        "cases": cases,
        "optimizerExecuted": False,
    }
    receipt_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return result


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100",
    cpu=8,
    memory=32768,
    timeout=6 * 60 * 60,
)
def preprocess_provisional_cohort(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    resolution: int = 512,
    num_cond_views: int = 8,
) -> dict:
    """Preprocess only the sealed TF-PW32 engineering cohort after its render gate."""
    import sys
    import torch

    if resolution != 512 or num_cond_views != 8:
        raise ValueError("The registered TF-PW32 smoke protocol is fixed at 512/8 views")
    if not torch.cuda.is_available():
        raise RuntimeError("TRELLIS preprocessing requires an active CUDA GPU")
    sys.path.insert(0, "/root")
    from scripts.anatomy_common import sha256_file
    from scripts.preprocess_anatomy_trellis import preprocess

    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    canary_path = root / "provisional_render_canary_receipt.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    canary = json.loads(canary_path.read_text(encoding="utf-8"))
    if (
        dataset_name != "toothfairy-tf-pw32-v1"
        or manifest.get("assetCount") != 32
        or manifest.get("trainingPurpose") != "engineering-smoke-only"
        or manifest.get("clinicalClaimPermitted") is not False
        or manifest.get("researchTrainingApproved") is not False
        or canary.get("successfulConditionalRenders") != 2
        or canary.get("numCondViews") != num_cond_views
        or canary.get("manifestSha256") != sha256_file(manifest_path)
    ):
        raise ValueError("TF-PW32 preprocessing gate is not satisfied")
    status = preprocess(
        manifest_path,
        root,
        root,
        resolution=resolution,
        num_cond_views=num_cond_views,
        trellis_root=Path(TRELLIS2_PATH),
        scripts_root=Path("/root/scripts"),
    )
    status["trainingPurpose"] = "engineering-smoke-only"
    status["clinicalClaimPermitted"] = False
    status["sourceCanaryReceipt"] = canary_path.name
    (root / "preprocess_status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    dataset_volume.commit()
    return status


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100",
    timeout=2 * 60 * 60,
)
def prepare_e3_sparse_structure_latents(
    dataset_name: str = "toothfairy-tf-pw32-v1",
) -> dict:
    """Encode and seal all TF-PW32 first-stage sparse latents for E3-B."""
    import sys

    if dataset_name != "toothfairy-tf-pw32-v1":
        raise ValueError("E3 sparse-latent canary is sealed to TF-PW32")
    root = Path(f"/datasets/{dataset_name}")
    manifest = json.loads((root / "anatomy_manifest.json").read_text(encoding="utf-8"))
    status = json.loads((root / "preprocess_status.json").read_text(encoding="utf-8"))
    if (
        manifest.get("assetCount") != 32
        or manifest.get("trainingPurpose") != "engineering-smoke-only"
        or status.get("assetCount") != 32
        or status.get("resolution") != 512
        or status.get("successfulConditionalRenders") != 32
    ):
        raise ValueError("Sealed TF-PW32 preprocessing contract is not satisfied")
    receipt_path = root / "e3_sparse_structure_latent_receipt.json"
    if receipt_path.exists():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("observedCount") == 32:
            return {**existing, "resumed": True}
        raise ValueError("Existing E3 sparse-latent receipt is invalid; do not overwrite it")
    sys.path.insert(0, "/root")
    from scripts.anatomy_common import sha256_file
    from scripts.preprocess_anatomy_trellis import (
        encode_sparse_structure_latents,
        ensure_data_toolkit,
        install_dataset_module,
    )

    toolkit = ensure_data_toolkit(Path(TRELLIS2_PATH))
    install_dataset_module(Path(TRELLIS2_PATH), Path("/root/scripts"))
    evidence = encode_sparse_structure_latents(
        toolkit,
        root,
        shape_latent_name="shape_enc_next_dc_f16c32_fp16_512",
        resolution=64,
    )
    receipt = {
        "schemaVersion": 1,
        "stage": "E3-sparse-structure-latents",
        "datasetId": dataset_name,
        "datasetManifestSha256": sha256_file(root / "anatomy_manifest.json"),
        "shapeLatentName": "shape_enc_next_dc_f16c32_fp16_512",
        "sparseResolution": 64,
        "trainingTarget": "sparse-structure-flow-only",
        "baseSparseFlowCheckpoint": BASE_SPARSE_FLOW_FILE,
        "trellisCommit": TRELLIS_COMMIT,
        "engineeringCanaryOnly": True,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
        **evidence,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return receipt


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100-80GB",
    cpu=8,
    memory=32768,
    timeout=3 * 60 * 60,
)
def evaluate_shape_vae_representation_ceiling(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    max_cases: int = 4,
    resolution: int = 512,
    samples: int = 10000,
) -> dict:
    """Decode frozen encoder latents and measure the shape SC-VAE ceiling (E0).

    The saved latents were produced by the official pinned encoder during the
    sealed preprocessing run.  This job invokes no image conditioner, flow
    sampler, candidate checkpoint, texture model, optimizer, or GLB remesher.
    It therefore isolates information lost by the frozen shape representation.
    TF-PW32 remains an engineering cohort, so this result can diagnose but can
    never authorize a clinical claim or production promotion.
    """
    import sys
    import numpy as np
    import torch
    import trimesh

    if dataset_name != "toothfairy-tf-pw32-v1":
        raise ValueError("E0 is currently sealed to the TF-PW32 engineering cohort")
    if resolution != 512:
        raise ValueError("The sealed TF-PW32 latents use resolution 512")
    if max_cases < 4 or max_cases > 32:
        raise ValueError("max_cases must be between 4 and 32")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh
    from scripts.anatomy_common import sha256_file
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh
    from scripts.representation_ceiling import summarize_representation_ceiling
    from trellis2.modules.sparse import SparseTensor

    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    status_path = root / "preprocess_status.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if (
        manifest.get("datasetId") != dataset_name
        or manifest.get("trainingPurpose") != "engineering-smoke-only"
        or manifest.get("clinicalClaimPermitted") is not False
        or manifest.get("assetCount") != 32
        or status.get("resolution") != resolution
        or status.get("assetCount") != 32
    ):
        raise ValueError("TF-PW32 manifest/preprocessing contract is not satisfied")

    by_family = {family: [] for family in ("incisor", "canine", "premolar", "molar")}
    for asset in manifest["assets"]:
        by_family[asset["toothFamily"]].append(asset)
    selected = []
    while len(selected) < max_cases:
        advanced = False
        for family in by_family:
            if by_family[family] and len(selected) < max_cases:
                selected.append(by_family[family].pop(0))
                advanced = True
        if not advanced:
            break

    latent_dir = root / status["shapeLatentDir"]
    output_dir = root / "representation_ceiling_e0" / "decoded_meshes"
    receipt_dir = root / "representation_ceiling_e0" / "receipts"
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)

    generator = TrellisGenerator()
    generator.load_model()
    runtime = {
        "gpuName": torch.cuda.get_device_name(0),
        "torchVersion": str(torch.__version__),
        "cudaVersion": torch.version.cuda,
        "cudnnVersion": torch.backends.cudnn.version(),
        "tf32MatmulEnabled": bool(torch.backends.cuda.matmul.allow_tf32),
    }
    decoder = generator.pipeline.models["shape_slat_decoder"]
    decoder.set_resolution(resolution)
    decoder.eval()
    cases = []
    for index, asset in enumerate(selected, start=1):
        source_path = root / asset["canonicalPath"]
        if sha256_file(source_path) != asset["canonicalSha256"]:
            raise ValueError(f"Canonical mesh hash drift: {asset['id']}")
        latent_path = latent_dir / f"{asset['canonicalSha256']}.npz"
        if not latent_path.is_file():
            raise FileNotFoundError(latent_path)
        packed = np.load(latent_path)
        feats = torch.from_numpy(packed["feats"]).cuda()
        coords = torch.from_numpy(packed["coords"].astype(np.int32)).cuda()
        coords = torch.cat([torch.zeros_like(coords[:, :1]), coords], dim=1)
        latent = SparseTensor(feats=feats, coords=coords)
        with torch.inference_mode():
            decoded, _ = generator.pipeline.decode_shape_slat(latent, resolution)
        decoded_mesh = decoded[0]
        prediction = trimesh.Trimesh(
            vertices=decoded_mesh.vertices.detach().cpu().numpy(),
            faces=decoded_mesh.faces.detach().cpu().numpy(),
            process=False,
        )
        output_path = output_dir / f"{asset['canonicalSha256']}.ply"
        output_path.write_bytes(prediction.export(file_type="ply"))
        reference = load_mesh(source_path)
        receipt = {
            "schemaVersion": 1,
            "experiment": "E0-frozen-shape-scvae-representation-ceiling",
            "id": asset["id"],
            "toothFamily": asset["toothFamily"],
            "fdiNumber": asset.get("fdiNumber"),
            "groupId": asset.get("groupId"),
            "referenceMesh": asset["canonicalPath"],
            "referenceMeshSha256": asset["canonicalSha256"],
            "artifactDirectory": asset["canonicalSha256"],
            "encodedLatent": str(latent_path.relative_to(root)).replace("\\", "/"),
            "encodedLatentSha256": sha256_file(latent_path),
            "latentTokenCount": int(coords.shape[0]),
            "decodedMesh": str(output_path.relative_to(root)).replace("\\", "/"),
            "decodedMeshSha256": sha256_file(output_path),
            "resolution": resolution,
            "metrics": compare_meshes(
                reference, prediction, samples=samples, seed=1724708096 + index
            ),
            "referenceTopology": analyze_mesh(reference),
            "decodedTopology": analyze_mesh(prediction),
            "flowModelInvoked": False,
            "textureModelInvoked": False,
            "glbPostprocessInvoked": False,
        }
        (receipt_dir / f"{asset['canonicalSha256']}.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        cases.append(receipt)
        dataset_volume.commit()
        print(f"E0 {index}/{len(selected)} complete: {asset['id']}", flush=True)
        del latent, decoded, decoded_mesh, feats, coords
        torch.cuda.empty_cache()

    summary = summarize_representation_ceiling(cases)
    report = {
        "schemaVersion": 1,
        "experiment": "E0-frozen-shape-scvae-representation-ceiling",
        "datasetId": dataset_name,
        "datasetManifestSha256": sha256_file(manifest_path),
        "baseModelName": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trellisInferenceCommit": TRELLIS_COMMIT,
        "trellisPreprocessingCommit": TRAINING_CODE_COMMIT,
        "runtime": runtime,
        "resolution": resolution,
        "samplesPerMesh": samples,
        "selection": "round-robin-family-balanced-manifest-order",
        "engineeringCohortOnly": True,
        "cases": cases,
        **summary,
    }
    report_path = root / "representation_ceiling_e0" / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return {
        "reportPath": str(report_path),
        "reportSha256": sha256_file(report_path),
        "caseCount": len(cases),
        "aggregate": summary["aggregate"],
        "representationCeilingEstablished": False,
        "productionPromotionPermitted": False,
    }


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100-80GB",
    cpu=8,
    memory=32768,
    timeout=3 * 60 * 60,
)
def evaluate_mixed_shape_vae_representation_ceiling(
    resolution: int = 512,
    samples: int = 10000,
) -> dict:
    """Run the frozen shape-representation ceiling on all three data domains."""
    import sys
    from collections import Counter, defaultdict

    import numpy as np
    import torch
    import trimesh

    if resolution != 512 or samples != 10000:
        raise ValueError("The mixed Stage-0 ceiling contract is sealed at 512/10000")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh
    from scripts.anatomy_common import sha256_file
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh
    from trellis2.modules.sparse import SparseTensor

    toothfairy_root = Path("/datasets/toothfairy-tf-pw32-v1")
    crown_root = Path("/datasets/dental-anatomy-v1")
    report_root = crown_root / "mixed_representation_ceiling_v1"
    report_path = report_root / "report.json"
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("status") == "complete" and report.get("caseCount") == 12:
            return {**report, "resumed": True}
        raise ValueError("Existing mixed Stage-0 report is invalid")
    if report_root.exists():
        raise FileExistsError("Partial mixed Stage-0 output exists; inspect before retrying")

    manifests = {
        "toothfairy-tf-pw32-v1": json.loads(
            (toothfairy_root / "anatomy_manifest.json").read_text(encoding="utf-8")
        ),
        "dental-anatomy-v1": json.loads(
            (crown_root / "anatomy_manifest.json").read_text(encoding="utf-8")
        ),
    }
    selected = select_mixed_representation_ceiling_cases(
        manifests["toothfairy-tf-pw32-v1"], manifests["dental-anatomy-v1"]
    )
    report_root.mkdir(parents=True)
    output_dir = report_root / "decoded_meshes"
    receipt_dir = report_root / "receipts"
    output_dir.mkdir()
    receipt_dir.mkdir()

    generator = TrellisGenerator()
    generator.load_model()
    decoder = generator.pipeline.models["shape_slat_decoder"]
    decoder.set_resolution(resolution)
    decoder.eval()
    cases = []
    for index, asset in enumerate(selected, start=1):
        root = Path("/datasets") / asset["ceilingDatasetRoot"]
        source_path = root / asset["canonicalPath"]
        if sha256_file(source_path) != asset["canonicalSha256"]:
            raise ValueError(f"Canonical mesh hash drift: {asset['id']}")
        latent_path = (
            root / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512"
            / f"{asset['canonicalSha256']}.npz"
        )
        if not latent_path.is_file():
            raise FileNotFoundError(latent_path)
        packed = np.load(latent_path, allow_pickle=False)
        feats = torch.from_numpy(packed["feats"]).cuda()
        coords = torch.from_numpy(packed["coords"].astype(np.int32)).cuda()
        coords = torch.cat([torch.zeros_like(coords[:, :1]), coords], dim=1)
        latent = SparseTensor(feats=feats, coords=coords)
        with torch.inference_mode():
            decoded, _ = generator.pipeline.decode_shape_slat(latent, resolution)
        decoded_mesh = decoded[0]
        prediction = trimesh.Trimesh(
            vertices=decoded_mesh.vertices.detach().cpu().numpy(),
            faces=decoded_mesh.faces.detach().cpu().numpy(), process=False,
        )
        output_path = output_dir / f"{asset['canonicalSha256']}.ply"
        output_path.write_bytes(prediction.export(file_type="ply"))
        receipt = {
            "schemaVersion": 1,
            "experiment": "mixed-source-frozen-shape-scvae-ceiling-v1",
            "id": asset["id"], "source": asset["ceilingSource"],
            "representationScope": asset["representationScope"],
            "rootSupervision": asset["rootSupervision"],
            "toothFamily": asset["toothFamily"],
            "fdiNumber": asset.get("fdiNumber"),
            "groupId": asset.get("groupId"),
            "referenceMeshSha256": asset["canonicalSha256"],
            "encodedLatentSha256": sha256_file(latent_path),
            "latentTokenCount": int(coords.shape[0]),
            "decodedMeshSha256": sha256_file(output_path),
            "metrics": compare_meshes(
                load_mesh(source_path), prediction,
                samples=samples, seed=1724708096 + index,
            ),
            "referenceTopology": analyze_mesh(load_mesh(source_path)),
            "decodedTopology": analyze_mesh(prediction),
            "flowModelInvoked": False, "optimizerInvoked": False,
            "candidateCheckpointWritten": False,
        }
        (receipt_dir / f"{asset['canonicalSha256']}.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        cases.append(receipt)
        dataset_volume.commit()
        print(f"Mixed Stage 0 {index}/12 complete: {asset['ceilingSource']} {asset['id']}", flush=True)
        del latent, decoded, decoded_mesh, feats, coords
        torch.cuda.empty_cache()

    grouped = defaultdict(list)
    for case in cases:
        grouped[case["source"]].append(case)
    metrics = (
        "symmetricChamferPercentDiagonal", "hausdorff95PercentDiagonal",
        "sortedExtentRelativeError", "surfaceFscoreAt1Percent", "surfaceFscoreAt2Percent",
    )
    source_summary = {
        source: {
            "caseCount": len(rows),
            "metrics": {
                metric: sum(float(row["metrics"][metric]) for row in rows) / len(rows)
                for metric in metrics
            },
        }
        for source, rows in sorted(grouped.items())
    }
    report = {
        "schemaVersion": 1, "status": "complete",
        "experiment": "mixed-source-frozen-shape-scvae-ceiling-v1",
        "baseModelName": BASE_MODEL_NAME, "baseModelRevision": BASE_MODEL_REVISION,
        "trellisCommit": TRELLIS_COMMIT, "resolution": resolution,
        "samplesPerMesh": samples, "caseCount": len(cases),
        "sourceCounts": dict(Counter(case["source"] for case in cases)),
        "scopeCounts": dict(Counter(case["representationScope"] for case in cases)),
        "selection": "4-family-whole-tooth-plus-4-family-teeth3ds-plus-4-distinct-dtu-fdi16",
        "bySource": source_summary, "cases": cases,
        "trainingExecuted": False, "candidateCheckpointWritten": False,
        "clinicalClaimPermitted": False, "productionPromotionPermitted": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return {**report, "reportPath": str(report_path), "reportSha256": sha256_file(report_path)}


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    cpu=8,
    memory=32768,
    timeout=60 * 60,
)
def qualify_mixed_ceiling_main_components(samples: int = 10000) -> dict:
    """Measure whether decoder debris can be removed without changing anatomy."""
    import sys

    if samples != 10000:
        raise ValueError("The mixed Stage-0 cleanup qualification is sealed at 10000 samples")
    sys.path.insert(0, "/root")
    from scripts.anatomy_common import sha256_file
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    crown_root = Path("/datasets/dental-anatomy-v1")
    toothfairy_root = Path("/datasets/toothfairy-tf-pw32-v1")
    ceiling_root = crown_root / "mixed_representation_ceiling_v1"
    source_report_path = ceiling_root / "report.json"
    output_path = ceiling_root / "main-component-qualification.json"
    if output_path.is_file():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return {**existing, "resumed": True}
        raise ValueError("Existing cleanup qualification is invalid")
    source_report = json.loads(source_report_path.read_text(encoding="utf-8"))
    if source_report.get("status") != "complete" or source_report.get("caseCount") != 12:
        raise ValueError("Complete 12-case mixed Stage-0 report is required")

    combined_manifest = json.loads(
        (crown_root / "anatomy_manifest.json").read_text(encoding="utf-8")
    )
    toothfairy_manifest = json.loads(
        (toothfairy_root / "anatomy_manifest.json").read_text(encoding="utf-8")
    )
    roots = {"toothfairy2": toothfairy_root, "teeth3ds": crown_root, "dtu-fdi16": crown_root}
    by_hash = {
        "toothfairy2": {
            row["canonicalSha256"]: row for row in toothfairy_manifest["assets"]
        },
        "teeth3ds": {row["canonicalSha256"]: row for row in combined_manifest["assets"]},
        "dtu-fdi16": {row["canonicalSha256"]: row for row in combined_manifest["assets"]},
    }
    cleaned_dir = ceiling_root / "main_component_meshes"
    cleaned_dir.mkdir()
    rows = []
    for index, case in enumerate(source_report["cases"], start=1):
        digest = case["referenceMeshSha256"]
        asset = by_hash[case["source"]].get(digest)
        if not asset:
            raise ValueError(f"Cannot resolve Stage-0 source asset {digest}")
        decoded = load_mesh(ceiling_root / "decoded_meshes" / f"{digest}.ply")
        components = decoded.split(only_watertight=False)
        if not components:
            raise ValueError(f"Decoded mesh has no components: {digest}")
        main = max(components, key=lambda component: float(component.area))
        cleaned_path = cleaned_dir / f"{digest}.ply"
        cleaned_path.write_bytes(main.export(file_type="ply"))
        reference = load_mesh(roots[case["source"]] / asset["canonicalPath"])
        cleaned_metrics = compare_meshes(
            reference, main, samples=samples, seed=1724708196 + index
        )
        raw = case["metrics"]
        area_fraction = float(case["decodedTopology"]["largestComponentAreaFraction"])
        row_passed = (
            area_fraction >= 0.99
            and cleaned_metrics["surfaceFscoreAt2Percent"] >= 0.99
            and cleaned_metrics["symmetricChamferPercentDiagonal"]
                <= raw["symmetricChamferPercentDiagonal"] + 0.05
        )
        rows.append({
            "id": case["id"], "source": case["source"],
            "toothFamily": case["toothFamily"],
            "representationScope": case["representationScope"],
            "referenceMeshSha256": digest,
            "rawDecodedComponentCount": case["decodedTopology"]["componentCount"],
            "largestComponentAreaFraction": area_fraction,
            "cleanedMeshSha256": sha256_file(cleaned_path),
            "rawSymmetricChamferPercentDiagonal": raw["symmetricChamferPercentDiagonal"],
            "cleanedMetrics": cleaned_metrics,
            "passedEngineeringCleanupGate": row_passed,
        })
    report = {
        "schemaVersion": 1, "status": "complete",
        "experiment": "mixed-source-main-component-qualification-v1",
        "sourceReportSha256": sha256_file(source_report_path),
        "rules": {
            "minimumLargestComponentAreaFraction": 0.99,
            "minimumCleanedSurfaceFscoreAt2Percent": 0.99,
            "maximumCleanedChamferIncreasePercentagePoints": 0.05,
        },
        "caseCount": len(rows), "cases": rows,
        "allCasesPassed": all(row["passedEngineeringCleanupGate"] for row in rows),
        "cleanupIsEvaluationOnly": True,
        "trainingExecuted": False, "candidateCheckpointWritten": False,
        "clinicalClaimPermitted": False, "productionPromotionPermitted": False,
    }
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return {**report, "reportPath": str(output_path), "reportSha256": sha256_file(output_path)}


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    cpu=8,
    memory=32768,
    timeout=60 * 60,
)
def compare_e1_trial_geometry(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    pipeline_type: str = "512",
    first_trial: str = "strict-deterministic-a",
    second_trial: str = "strict-deterministic-b",
    samples: int = 20000,
) -> dict:
    """Directly compare two immutable E1 trials with sampling-floor calibration."""
    import sys

    if dataset_name != "toothfairy-tf-pw32-v1":
        raise ValueError("E1 comparison is sealed to the TF-PW32 engineering cohort")
    if pipeline_type not in {"512", "1024", "1024_cascade"}:
        raise ValueError("unsupported pipeline_type")
    for value in (first_trial, second_trial):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", value):
            raise ValueError("trial IDs must be lowercase alphanumeric/hyphen")
    if first_trial == second_trial:
        raise ValueError("trial IDs must differ")
    if samples < 5000 or samples > 100000:
        raise ValueError("samples must be between 5000 and 100000")

    sys.path.insert(0, "/root")
    from scripts.anatomy_common import sha256_file
    from scripts.compare_topology_trials import (
        add_direct_geometry_comparison,
        compare_trials,
    )

    trial_root = Path(f"/datasets/{dataset_name}/topology_trace_e1/{pipeline_type}")
    first_root = trial_root / first_trial
    second_root = trial_root / second_trial
    first = json.loads((first_root / "report.json").read_text(encoding="utf-8"))
    second = json.loads((second_root / "report.json").read_text(encoding="utf-8"))
    report = compare_trials(first, second)
    report = add_direct_geometry_comparison(
        report,
        first,
        second,
        first_root,
        second_root,
        samples=samples,
    )
    comparison_dir = trial_root / "comparisons"
    output = comparison_dir / f"{first_trial}--{second_trial}.json"
    if output.exists():
        raise FileExistsError(f"Immutable E1 comparison already exists: {output.name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return {
        "reportPath": str(output),
        "reportSha256": sha256_file(output),
        "byteRepeatable": report["byteRepeatable"],
        "directPairwiseGeometryPassed": report["directPairwiseGeometryPassed"],
        "repeatabilityGatePassed": report["repeatabilityGatePassed"],
        "productionPromotionPermitted": False,
    }


@app.function(
    image=ingestion_image,
    volumes={"/datasets": dataset_volume},
    cpu=8,
    memory=32768,
    timeout=60 * 60,
)
def evaluate_e1_axial_regions(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    trial_id: str = "strict-deterministic-a",
    evaluation_id: str = "axial-proxy-v1",
    samples: int = 20000,
) -> dict:
    """Apply the registered crown/root axial proxies to persisted E1 finals."""
    import sys

    if dataset_name != "toothfairy-tf-pw32-v1":
        raise ValueError("axial E1 evaluation is sealed to TF-PW32")
    for value in (trial_id, evaluation_id):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", value):
            raise ValueError("IDs must be lowercase alphanumeric/hyphen")
    if samples < 5000 or samples > 100000:
        raise ValueError("samples must be between 5000 and 100000")
    sys.path.insert(0, "/root")
    from scripts.anatomy_common import sha256_file
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    root = Path(f"/datasets/{dataset_name}")
    output = root / "topology_trace_e1" / "evaluations" / f"{evaluation_id}.json"
    if output.exists():
        raise FileExistsError(f"Immutable E1 evaluation already exists: {evaluation_id}")
    rows = []
    for index, pipeline_type in enumerate(("512", "1024", "1024_cascade")):
        trial_root = root / "topology_trace_e1" / pipeline_type / trial_id
        trial = json.loads((trial_root / "report.json").read_text(encoding="utf-8"))
        case = trial["cases"][0]
        final_stage = next(stage for stage in case["stages"] if stage["stage"] == "final-glb")
        case_dir = case.get("artifactDirectory", case["referenceMeshSha256"])
        reference = load_mesh(root / case["referenceMesh"])
        prediction = load_mesh(trial_root / case_dir / final_stage["artifact"])
        rows.append({
            "pipelineType": pipeline_type,
            "trialId": trial_id,
            "caseId": case["id"],
            "referenceMeshSha256": case["referenceMeshSha256"],
            "predictionMeshSha256": final_stage["artifactSha256"],
            "metrics": compare_meshes(
                reference, prediction, samples=samples, seed=1724708096 + index
            ),
        })
    report = {
        "schemaVersion": 1,
        "experiment": "E1-canonical-axial-region-proxy",
        "evaluationId": evaluation_id,
        "datasetId": dataset_name,
        "datasetManifestSha256": sha256_file(root / "anatomy_manifest.json"),
        "samplesPerComparison": samples,
        "engineeringProxyOnly": True,
        "clinicalLandmarkClaimPermitted": False,
        "rows": rows,
        "productionPromotionPermitted": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return {
        "reportPath": str(output),
        "reportSha256": sha256_file(output),
        "pipelineCount": len(rows),
        "clinicalLandmarkClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100-80GB",
    cpu=8,
    memory=32768,
    timeout=3 * 60 * 60,
)
def trace_generation_topology_stages(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    pipeline_type: str = "512",
    trial_id: str = "trial-1",
    deterministic: bool = True,
    max_cases: int = 1,
    samples: int = 5000,
) -> dict:
    """Localise geometry/topology changes across decode, remesh and GLB (E1).

    Run this function separately for ``512``, ``1024`` and ``1024_cascade``.
    It uses the unchanged pinned base model and never writes production state.
    """
    import io
    import os
    import sys
    import torch
    import trimesh
    from PIL import Image

    if dataset_name != "toothfairy-tf-pw32-v1":
        raise ValueError("E1 is currently sealed to the TF-PW32 engineering cohort")
    if pipeline_type not in {"512", "1024", "1024_cascade"}:
        raise ValueError("pipeline_type must be 512, 1024, or 1024_cascade")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", trial_id):
        raise ValueError("trial_id must be lowercase alphanumeric/hyphen and at most 32 characters")
    if max_cases < 1 or max_cases > 4:
        raise ValueError("max_cases must be between 1 and 4")
    if MODEL_NAME != BASE_MODEL_NAME or MODEL_REVISION != BASE_MODEL_REVISION:
        raise RuntimeError("E1 requires the unchanged pinned base model")
    sys.path.insert(0, "/root")
    from modal_app.trellis_config import get_quality_preset, sampler_params_for_steps
    from modal_app.workers.trellis_generator import TrellisGenerator
    from o_voxel.postprocess import to_glb
    from scripts.analyze_mesh_topology import analyze_mesh, analyze_mesh_with_weld_control
    from scripts.anatomy_common import sha256_file
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh
    from scripts.topology_stage_trace import (
        build_topology_stage_report,
        mesh_from_arrays,
        remesh_geometry_for_diagnostics,
        write_mesh_stage,
    )

    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("assetCount") != 32
        or manifest.get("trainingPurpose") != "engineering-smoke-only"
        or manifest.get("clinicalClaimPermitted") is not False
    ):
        raise ValueError("TF-PW32 engineering manifest contract is not satisfied")

    # One case per family before any second case, preserving the sealed order.
    selected = []
    for family in ("incisor", "canine", "premolar", "molar"):
        match = next(asset for asset in manifest["assets"] if asset["toothFamily"] == family)
        selected.append(match)
    selected = selected[:max_cases]
    resolution = 512 if pipeline_type == "512" else 1024
    preset = get_quality_preset("preview" if pipeline_type == "512" else "standard")
    sampler_params = sampler_params_for_steps(int(preset["steps"]))
    decimation_target = int(preset["decimation_target"])
    texture_size = int(preset["texture_size"])

    if deterministic:
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True)

    generator = TrellisGenerator()
    generator.load_model()
    # TrellisGenerator applies the service TF32 policy while loading. Reapply
    # the stricter research policy after load so the recorded state is the one
    # actually used for the measured inference.
    if deterministic:
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True)
    runtime = {
        "gpuName": torch.cuda.get_device_name(0),
        "torchVersion": str(torch.__version__),
        "cudaVersion": torch.version.cuda,
        "cudnnVersion": torch.backends.cudnn.version(),
        "tf32MatmulEnabled": bool(torch.backends.cuda.matmul.allow_tf32),
        "tf32CudnnEnabled": bool(torch.backends.cudnn.allow_tf32),
        "cudnnDeterministic": bool(torch.backends.cudnn.deterministic),
        "deterministicAlgorithmsEnabled": bool(torch.are_deterministic_algorithms_enabled()),
        "cublasWorkspaceConfig": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
    }
    runtime["deterministicControlsSatisfied"] = bool(
        not runtime["tf32MatmulEnabled"]
        and not runtime["tf32CudnnEnabled"]
        and runtime["cudnnDeterministic"]
        and runtime["deterministicAlgorithmsEnabled"]
        and runtime["cublasWorkspaceConfig"] == ":4096:8"
    ) if deterministic else None
    if deterministic and not runtime["deterministicControlsSatisfied"]:
        raise RuntimeError(f"Deterministic runtime controls were not applied: {runtime}")
    pipeline = generator.pipeline
    run_root = root / "topology_trace_e1" / pipeline_type / trial_id
    report_path = run_root / "report.json"
    if report_path.exists():
        raise FileExistsError(
            f"Immutable E1 trial already exists: {pipeline_type}/{trial_id}"
        )
    cases = []
    for index, asset in enumerate(selected, start=1):
        input_path = root / "renders_cond" / asset["canonicalSha256"] / "000.png"
        if not input_path.is_file():
            raise FileNotFoundError(input_path)
        image = Image.open(input_path)
        image.load()
        processed = pipeline.preprocess_image(image)
        seed = 1724708096
        with torch.inference_mode():
            generated = pipeline.run(
                processed,
                seed=seed,
                pipeline_type=pipeline_type,
                preprocess_image=False,
                sparse_structure_sampler_params=sampler_params["sparse_structure"],
                shape_slat_sampler_params=sampler_params["shape"],
                tex_slat_sampler_params=sampler_params["texture"],
            )[0]

        case_dir = run_root / asset["canonicalSha256"]
        decoded_cpu = mesh_from_arrays(generated.vertices, generated.faces)
        decoded_stage = write_mesh_stage(
            decoded_cpu, case_dir / "pipeline-decoded.ply", "pipeline-decoded"
        )
        remeshed_cpu = remesh_geometry_for_diagnostics(
            generated.vertices,
            generated.faces,
            resolution=resolution,
            decimation_target=decimation_target,
            remesh_band=1.0,
            remesh_project=0.0,
        )
        remeshed_stage = write_mesh_stage(
            remeshed_cpu, case_dir / "post-remesh.ply", "post-remesh"
        )
        with torch.inference_mode():
            final = to_glb(
                vertices=generated.vertices,
                faces=generated.faces,
                attr_volume=generated.attrs,
                coords=generated.coords,
                attr_layout=generated.layout,
                aabb=torch.tensor(
                    [[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]], device="cuda"
                ),
                voxel_size=generated.voxel_size,
                decimation_target=decimation_target,
                texture_size=texture_size,
                remesh=True,
                remesh_band=1.0,
                remesh_project=0.0,
                verbose=False,
            )
        final_path = case_dir / "final.glb"
        buffer = io.BytesIO()
        final.export(buffer, file_type="glb")
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_bytes(buffer.getvalue())
        final_cpu = load_mesh(final_path)
        final_stage = {
            "stage": "final-glb",
            "artifact": final_path.name,
            "artifactSha256": sha256_file(final_path),
            "topology": analyze_mesh(final_cpu),
            "topologyWeldControl": analyze_mesh_with_weld_control(final_cpu),
        }
        stage_report = build_topology_stage_report(
            [decoded_stage, remeshed_stage, final_stage]
        )
        reference = load_mesh(root / asset["canonicalPath"])
        for stage, mesh in zip(
            stage_report["stages"], (decoded_cpu, remeshed_cpu, final_cpu)
        ):
            stage["referenceMetrics"] = compare_meshes(
                reference, mesh, samples=samples, seed=seed + index
            )
        receipt = {
            "schemaVersion": 1,
            "experiment": "E1-topology-stage-localisation",
            "id": asset["id"],
            "toothFamily": asset["toothFamily"],
            "fdiNumber": asset.get("fdiNumber"),
            "referenceMesh": asset["canonicalPath"],
            "referenceMeshSha256": asset["canonicalSha256"],
            "artifactDirectory": asset["canonicalSha256"],
            "inputImage": str(input_path.relative_to(root)).replace("\\", "/"),
            "inputImageSha256": sha256_file(input_path),
            "baseModelName": BASE_MODEL_NAME,
            "baseModelRevision": BASE_MODEL_REVISION,
            "pipelineType": pipeline_type,
            "trialId": trial_id,
            "resolution": resolution,
            "seed": seed,
            "deterministicRequested": deterministic,
            "runtime": runtime,
            **stage_report,
        }
        (case_dir / "receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        cases.append(receipt)
        dataset_volume.commit()
        print(
            f"E1 {pipeline_type} {index}/{len(selected)} complete: {asset['id']}",
            flush=True,
        )
        del generated, final
        torch.cuda.empty_cache()

    report = {
        "schemaVersion": 1,
        "experiment": "E1-topology-stage-localisation",
        "datasetId": dataset_name,
        "datasetManifestSha256": sha256_file(manifest_path),
        "baseModelName": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trellisCommit": TRELLIS_COMMIT,
        "runtime": runtime,
        "pipelineType": pipeline_type,
        "trialId": trial_id,
        "deterministicRequested": deterministic,
        "caseCount": len(cases),
        "cases": cases,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return {
        "reportPath": str(report_path),
        "reportSha256": sha256_file(report_path),
        "pipelineType": pipeline_type,
        "trialId": trial_id,
        "caseCount": len(cases),
        "firstFragmentationStages": {
            case["id"]: case["firstGeometryFragmentationAmplificationStage"]
            for case in cases
        },
        "productionPromotionPermitted": False,
    }


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100-80GB",
    cpu=8,
    memory=32768,
    timeout=3 * 60 * 60,
)
def trace_same_container_generation_repeatability(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    pipeline_type: str = "512",
    pair_id: str = "same-container-a",
    samples: int = 20000,
) -> dict:
    """Run the frozen generator twice after one model load on one exact GPU.

    This isolates generation repeatability from container scheduling, model-load
    differences, GLB serialization, and cross-device A100 variants.  It is an E1
    engineering diagnostic only and cannot promote a production model.
    """
    import os
    import sys
    import torch
    from PIL import Image

    if dataset_name != "toothfairy-tf-pw32-v1" or pipeline_type != "512":
        raise ValueError("same-container E1 is sealed to TF-PW32 and pipeline 512")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", pair_id):
        raise ValueError("pair_id must be lowercase alphanumeric/hyphen")
    if samples < 5000 or samples > 100000:
        raise ValueError("samples must be between 5000 and 100000")
    if MODEL_NAME != BASE_MODEL_NAME or MODEL_REVISION != BASE_MODEL_REVISION:
        raise RuntimeError("E1 requires the unchanged pinned base model")

    sys.path.insert(0, "/root")
    from modal_app.trellis_config import get_quality_preset, sampler_params_for_steps
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.anatomy_common import sha256_file
    from scripts.compare_topology_trials import calibrated_pairwise_geometry
    from scripts.topology_stage_trace import mesh_from_arrays, write_mesh_stage

    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("assetCount") != 32 or manifest.get("trainingPurpose") != "engineering-smoke-only":
        raise ValueError("TF-PW32 engineering manifest contract is not satisfied")
    asset = next(item for item in manifest["assets"] if item["toothFamily"] == "incisor")
    output_root = root / "topology_trace_e1" / pipeline_type / "same-container" / pair_id
    report_path = output_root / "report.json"
    if report_path.exists():
        raise FileExistsError(f"Immutable same-container pair already exists: {pair_id}")

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    generator = TrellisGenerator()
    generator.load_model()
    # Service initialization changes TF32 policy; the experiment policy wins.
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    runtime = {
        "gpuName": torch.cuda.get_device_name(0),
        "gpuIndex": 0,
        "torchVersion": str(torch.__version__),
        "cudaVersion": torch.version.cuda,
        "cudnnVersion": torch.backends.cudnn.version(),
        "tf32MatmulEnabled": bool(torch.backends.cuda.matmul.allow_tf32),
        "tf32CudnnEnabled": bool(torch.backends.cudnn.allow_tf32),
        "cudnnDeterministic": bool(torch.backends.cudnn.deterministic),
        "deterministicAlgorithmsEnabled": bool(torch.are_deterministic_algorithms_enabled()),
        "cublasWorkspaceConfig": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "singleContainerSingleModelLoad": True,
    }
    runtime["deterministicControlsSatisfied"] = bool(
        not runtime["tf32MatmulEnabled"]
        and not runtime["tf32CudnnEnabled"]
        and runtime["cudnnDeterministic"]
        and runtime["deterministicAlgorithmsEnabled"]
        and runtime["cublasWorkspaceConfig"] == ":4096:8"
    )
    if not runtime["deterministicControlsSatisfied"]:
        raise RuntimeError(f"Deterministic runtime controls were not applied: {runtime}")

    pipeline = generator.pipeline
    preset = get_quality_preset("preview")
    sampler_params = sampler_params_for_steps(int(preset["steps"]))
    input_path = root / "renders_cond" / asset["canonicalSha256"] / "000.png"
    image = Image.open(input_path)
    image.load()
    processed = pipeline.preprocess_image(image)
    seed = 1724708096
    meshes = []
    repetitions = []
    for repetition in (1, 2):
        with torch.inference_mode():
            generated = pipeline.run(
                processed,
                seed=seed,
                pipeline_type=pipeline_type,
                preprocess_image=False,
                sparse_structure_sampler_params=sampler_params["sparse_structure"],
                shape_slat_sampler_params=sampler_params["shape"],
                tex_slat_sampler_params=sampler_params["texture"],
            )[0]
        mesh = mesh_from_arrays(generated.vertices, generated.faces)
        stage = write_mesh_stage(
            mesh, output_root / f"decoded-{repetition}.ply", f"decoded-{repetition}"
        )
        repetitions.append({
            "repetition": repetition,
            "artifact": stage["artifact"],
            "artifactSha256": stage["artifactSha256"],
            "topologyWeldControl": analyze_mesh_with_weld_control(mesh),
        })
        meshes.append(mesh)
        del generated
        torch.cuda.empty_cache()

    direct = calibrated_pairwise_geometry(
        meshes[0], meshes[1], samples=samples, seed=seed
    )
    report = {
        "schemaVersion": 1,
        "experiment": "E1-same-container-fixed-seed-repeatability",
        "datasetId": dataset_name,
        "datasetManifestSha256": sha256_file(manifest_path),
        "baseModelName": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trellisCommit": TRELLIS_COMMIT,
        "pipelineType": pipeline_type,
        "pairId": pair_id,
        "caseId": asset["id"],
        "inputImageSha256": sha256_file(input_path),
        "seed": seed,
        "runtime": runtime,
        "repetitions": repetitions,
        "artifactBytesIdentical": repetitions[0]["artifactSha256"] == repetitions[1]["artifactSha256"],
        "directPairwiseGeometry": direct,
        "repeatabilityGatePassed": bool(
            repetitions[0]["artifactSha256"] == repetitions[1]["artifactSha256"]
            or direct["passed"]
        ),
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return {
        "reportPath": str(report_path),
        "reportSha256": sha256_file(report_path),
        "artifactBytesIdentical": report["artifactBytesIdentical"],
        "directPairwiseGeometryPassed": direct["passed"],
        "repeatabilityGatePassed": report["repeatabilityGatePassed"],
        "runtime": runtime,
        "productionPromotionPermitted": False,
    }


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    timeout=60 * 60,
    max_containers=4,
)
def render_conditional_batch(
    dataset_name: str = "dental-anatomy-v1",
    batch_index: int = 0,
    batch_size: int = 25,
    num_cond_views: int = 24,
) -> dict:
    """Render and durably commit one deterministic train-only batch."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.preprocess_anatomy_trellis import ensure_data_toolkit, install_dataset_module
    from scripts.render_conditional_batches import render_batch

    dataset_root = Path(f"/datasets/{dataset_name}")
    toolkit = ensure_data_toolkit(Path(TRELLIS2_PATH))
    install_dataset_module(Path(TRELLIS2_PATH), Path("/root/scripts"))
    try:
        result = render_batch(
            toolkit=toolkit,
            dataset_root=dataset_root,
            subset="DentalAnatomy",
            batch_index=batch_index,
            batch_size=batch_size,
            num_cond_views=num_cond_views,
        )
    finally:
        # Preserve valid outputs and the receipt even if a later asset fails.
        dataset_volume.commit()
    if not result["valid"]:
        raise RuntimeError(f"Conditional-render batch failed after commit: {json.dumps(result)}")
    print(json.dumps(result, indent=2), flush=True)
    return result


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume},
    timeout=5 * 60,
)
def plan_conditional_render_window(
    dataset_name: str,
    start_batch: int,
    batch_size: int,
    window_size: int,
) -> dict:
    """Read the remote dataset size and clamp a requested render window safely."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.render_conditional_batches import batch_window

    return batch_window(
        Path(f"/datasets/{dataset_name}/metadata.csv"),
        start_batch=start_batch,
        batch_size=batch_size,
        window_size=window_size,
    )


@app.local_entrypoint()
def render_conditional_window(
    dataset_name: str = "dental-anatomy-v1",
    start_batch: int = 0,
    batch_size: int = 25,
    window_size: int = 4,
    num_cond_views: int = 24,
) -> None:
    """Run one bounded window; durable receipts make a later invocation resumable."""
    if start_batch < 0:
        raise ValueError("start_batch must be non-negative")
    if batch_size < 1 or batch_size > 100:
        raise ValueError("batch_size must be between 1 and 100")
    if window_size < 1 or window_size > 4:
        raise ValueError("window_size must be between 1 and 4")
    plan = plan_conditional_render_window.remote(
        dataset_name=dataset_name,
        start_batch=start_batch,
        batch_size=batch_size,
        window_size=window_size,
    )
    calls = [
        render_conditional_batch.spawn(
            dataset_name=dataset_name,
            batch_index=batch_index,
            batch_size=batch_size,
            num_cond_views=num_cond_views,
        )
        for batch_index in plan["batchIndices"]
    ]
    results = modal.FunctionCall.gather(*calls)
    summary = {
        "valid": all(result.get("valid") for result in results),
        "datasetName": dataset_name,
        "batchIndices": [result["batchIndex"] for result in results],
        "successfulCount": sum(result["successfulCount"] for result in results),
        "failedCount": sum(result["failedCount"] for result in results),
        "receiptsCommitted": len(results),
        "nextBatch": plan["nextBatch"],
    }
    print(json.dumps(summary, indent=2), flush=True)


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume},
    timeout=30 * 60,
)
def audit_conditional_batches(
    dataset_name: str = "dental-anatomy-v1",
    batch_size: int = 25,
    num_cond_views: int = 24,
    max_failure_details: int = 20,
) -> dict:
    """Revalidate receipts and every persisted train render from disk."""
    import sys

    sys.path.insert(0, "/root")
    from scripts.render_conditional_batches import audit_receipts

    result = audit_receipts(
        Path(f"/datasets/{dataset_name}"),
        batch_size=batch_size,
        num_cond_views=num_cond_views,
        max_failure_details=max_failure_details,
    )
    print(json.dumps(result, indent=2), flush=True)
    return result


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume},
    timeout=30 * 60,
)
def finalize_stage1_preprocessing(
    dataset_name: str = "toothfairy-stage1-v1",
    resolution: int = 512,
    num_cond_views: int = 8,
    render_batch_size: int = 25,
) -> dict:
    """Seal already-persisted Stage-1 artifacts without rerunning paid preprocessing."""
    import sys
    from collections import Counter

    import numpy as np

    if (
        dataset_name != "toothfairy-stage1-v1"
        or resolution != 512
        or num_cond_views != 8
        or render_batch_size != 25
    ):
        raise ValueError("Stage-1 finalization is sealed at toothfairy-stage1-v1, 512/8, batches of 25")
    sys.path.insert(0, "/root")
    from scripts.anatomy_common import sha256_file
    from scripts.render_conditional_batches import audit_receipts
    from scripts.validate_anatomy_dataset import validate_dataset

    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    validation = validate_dataset(
        manifest_path,
        expected_dataset_id=dataset_name,
        minimum_per_family=32,
        require_files=True,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = manifest.get("assets", [])
    expected_hashes = {asset["canonicalSha256"] for asset in assets}
    split_counts = Counter(asset["split"] for asset in assets)
    if len(assets) != 164 or len(expected_hashes) != 164:
        raise ValueError("Stage-1 manifest must contain 164 unique assets")
    if split_counts != Counter({"train": 128, "validation": 12, "test": 24}):
        raise ValueError(f"Stage-1 split contract changed: {dict(split_counts)}")

    def validate_files(directory: Path, suffix: str) -> dict:
        observed = {path.stem for path in directory.glob(f"*{suffix}") if path.stat().st_size > 0}
        missing = sorted(expected_hashes - observed)
        unexpected = sorted(observed - expected_hashes)
        if missing or unexpected:
            raise ValueError(
                f"Artifact set {directory.name} is not sealed: "
                f"missing={len(missing)}, unexpected={len(unexpected)}"
            )
        return {"expectedCount": len(expected_hashes), "observedCount": len(observed)}

    mesh_dumps = validate_files(root / "mesh_dumps", ".pickle")
    dual_grids = validate_files(root / f"dual_grid_{resolution}", ".vxz")
    latent_dir = root / "shape_latents" / f"shape_enc_next_dc_f16c32_fp16_{resolution}"
    shape_latents = validate_files(latent_dir, ".npz")
    invalid_latents = []
    token_counts = []
    for digest in sorted(expected_hashes):
        try:
            with np.load(latent_dir / f"{digest}.npz") as packed:
                coords = packed["coords"]
                if coords.shape[0] <= 0 or not np.isfinite(coords).all():
                    invalid_latents.append(digest)
                else:
                    token_counts.append(int(coords.shape[0]))
        except (OSError, KeyError, ValueError):
            invalid_latents.append(digest)
    if invalid_latents:
        raise ValueError(f"Invalid Stage-1 shape latents: {invalid_latents[:10]}")
    shape_latents.update({
        "invalidCount": 0,
        "minimumTokenCount": min(token_counts),
        "maximumTokenCount": max(token_counts),
    })

    render_audit = audit_receipts(
        root,
        batch_size=render_batch_size,
        num_cond_views=num_cond_views,
    )
    if (
        not render_audit.get("valid")
        or render_audit.get("trainingAssetCount") != 128
        or render_audit.get("validatedAssetCount") != 128
        or render_audit.get("validReceiptCount") != 6
    ):
        raise ValueError(f"Stage-1 conditional-render audit failed: {json.dumps(render_audit)}")
    canary_path = root / "stage1_render_canary_receipt.json"
    canary = json.loads(canary_path.read_text(encoding="utf-8"))
    if (
        canary.get("manifestSha256") != sha256_file(manifest_path)
        or canary.get("successfulConditionalRenders") != 8
        or canary.get("numCondViews") != num_cond_views
        or canary.get("optimizerExecuted") is not False
    ):
        raise ValueError("Stage-1 render canary receipt is absent, stale, or invalid")

    training_view = prepare_training_metadata_view(root, resolution)
    if training_view.get("trainCount") != 128 or training_view.get("uniqueTrainHashes") != 128:
        raise ValueError("Stage-1 training metadata view is incomplete")
    receipt = {
        "schemaVersion": 1,
        "stage": "clinical-stage1-preprocessing-finalized",
        "valid": True,
        "datasetId": dataset_name,
        "manifestSha256": sha256_file(manifest_path),
        "resolution": resolution,
        "numCondViews": num_cond_views,
        "assetCount": len(assets),
        "splitCounts": dict(split_counts),
        "meshDumps": mesh_dumps,
        "dualGrids": dual_grids,
        "shapeLatents": shape_latents,
        "conditionalRenders": render_audit,
        "trainingView": training_view,
        "validation": validation,
        "renderCanaryReceipt": canary_path.name,
        "optimizerExecuted": False,
    }
    (root / "stage1_preprocess_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    dataset_volume.commit()
    return receipt


def prepare_training_metadata_view(dataset_root: Path, resolution: int = 512) -> dict:
    """Expose only train rows to TRELLIS while retaining held-out preprocessed assets."""
    metadata_path = dataset_root / "metadata.csv"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Missing preprocessed metadata: {metadata_path}")
    with metadata_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        rows = [row for row in reader if row.get("split") == "train"]
    if not fieldnames or not rows:
        raise ValueError("Preprocessed metadata has no training rows.")
    digests = [row.get("sha256", "") for row in rows]
    if any(len(digest) != 64 for digest in digests) or len(set(digests)) != len(digests):
        raise ValueError("Training metadata contains invalid or duplicate hashes.")

    import numpy as np

    latent_name = f"shape_enc_next_dc_f16c32_fp16_{resolution}"
    fieldnames = list(fieldnames)
    for required in ("shape_latent_encoded", "shape_latent_tokens", "cond_rendered"):
        if required not in fieldnames:
            fieldnames.append(required)
    for row in rows:
        digest = row["sha256"]
        latent_path = dataset_root / "shape_latents" / latent_name / f"{digest}.npz"
        render_path = dataset_root / "renders_cond" / digest
        if not latent_path.is_file():
            raise FileNotFoundError(f"Missing training shape latent: {latent_path}")
        if not render_path.is_dir():
            raise FileNotFoundError(f"Missing training conditional render directory: {render_path}")
        with np.load(latent_path) as packed:
            if "coords" not in packed or packed["coords"].shape[0] <= 0:
                raise ValueError(f"Training latent has no coordinate tokens: {latent_path}")
            row["shape_latent_tokens"] = str(int(packed["coords"].shape[0]))
        row["shape_latent_encoded"] = "True"
        row["cond_rendered"] = "True"
    destinations = (
        dataset_root / "training_views" / "train" / "metadata.csv",
        dataset_root / "shape_latents" / latent_name / "metadata.csv",
        dataset_root / "renders_cond" / "metadata.csv",
    )
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    return {
        "trainCount": len(rows),
        "uniqueTrainHashes": len(set(digests)),
        "metadataPaths": [str(path) for path in destinations],
    }


def build_finetune_config(
    base_config: dict,
    base_checkpoint: str,
    *,
    max_steps: int = 20_000,
    save_interval: int = 1_000,
    log_interval: int = 100,
) -> dict:
    """Create a conservative same-resolution shape-flow fine-tuning config."""
    config = json.loads(json.dumps(base_config))
    trainer = config.setdefault("trainer", {}).setdefault("args", {})
    trainer["finetune_ckpt"] = {"denoiser": base_checkpoint}
    trainer["max_steps"] = int(max_steps)
    trainer.setdefault("optimizer", {}).setdefault("args", {})["lr"] = 1e-5
    trainer["i_print"] = int(log_interval)
    trainer["i_log"] = int(log_interval)
    trainer["i_sample"] = 2_000
    trainer["i_save"] = int(save_interval)
    return config


def materialize_trainer_checkpoint(safetensors_path: str, output_path: Path) -> str:
    """Convert a pinned Hugging Face safetensors state dict for TRELLIS.2's torch.load trainer."""
    source = Path(safetensors_path)
    if source.suffix != ".safetensors" or not source.is_file():
        raise FileNotFoundError(f"Pinned safetensors checkpoint is missing: {source}")
    import torch
    from safetensors.torch import load_file

    output_path.parent.mkdir(parents=True, exist_ok=True)
    state_dict = load_file(str(source), device="cpu")
    if not state_dict or not all(isinstance(value, torch.Tensor) for value in state_dict.values()):
        raise ValueError("Pinned safetensors checkpoint did not contain a tensor state dict.")
    torch.save(state_dict, output_path)
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("Failed to materialize the trainer-compatible checkpoint.")
    return str(output_path)


def smoke_training_command(dataset_name: str, run_name: str, resolution: int = 512) -> list[str]:
    smoke = f"/datasets/{dataset_name}/smoke_training_v1"
    data_spec = json.dumps({f"{dataset_name}-smoke": {
        "base": f"{smoke}/base",
        "shape_latent": f"{smoke}/shape_latent",
        "render_cond": f"{smoke}/render_cond",
    }}, separators=(",", ":"))
    return ["python", f"{TRELLIS2_PATH}/train.py", "--config",
            f"/checkpoints/{run_name}/dentalsculptor_smoke_config.json",
            "--output_dir", f"/checkpoints/{run_name}", "--data_dir", data_spec,
            "--auto_retry", "0"]


def sparse_structure_training_command(
    dataset_name: str,
    run_name: str,
    *,
    tryrun: bool = False,
) -> list[str]:
    if not dataset_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("dataset-name contains unsupported characters")
    if not run_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("run-name contains unsupported characters")
    root = f"/datasets/{dataset_name}"
    data_spec = json.dumps({dataset_name: {
        "base": root,
        "ss_latent": f"{root}/ss_latents/ss_enc_conv3d_16l8_fp16_64",
        "render_cond": f"{root}/renders_cond",
    }}, separators=(",", ":"))
    command = [
        "python", f"{TRELLIS2_PATH}/train.py",
        "--config", f"/checkpoints/{run_name}/dentalsculptor_sparse_config.json",
        "--output_dir", f"/checkpoints/{run_name}",
        "--data_dir", data_spec,
        "--auto_retry", "0",
    ]
    if tryrun:
        command.append("--tryrun")
    return command


def sparse_anchor_training_command(dataset_name: str, run_name: str) -> list[str]:
    """Train only against the sealed eight-asset, four-family sparse anchor view."""
    if not dataset_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("dataset-name contains unsupported characters")
    if not run_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("run-name contains unsupported characters")
    anchor = f"/datasets/{dataset_name}/sparse_anchor_v1"
    data_spec = json.dumps({f"{dataset_name}-anchor8": {
        "base": f"{anchor}/base",
        "ss_latent": f"{anchor}/ss_latent",
        "render_cond": f"{anchor}/render_cond",
    }}, separators=(",", ":"))
    return [
        "python", f"{TRELLIS2_PATH}/train.py",
        "--config", f"/checkpoints/{run_name}/dentalsculptor_sparse_config.json",
        "--output_dir", f"/checkpoints/{run_name}",
        "--data_dir", data_spec,
        "--auto_retry", "0",
    ]


def e9_family_diagnostic_command(dataset_name: str, family: str, run_name: str) -> list[str]:
    """Run one sealed family view through the zero-update E9 diagnostic."""
    if family not in ("incisor", "canine", "premolar", "molar"):
        raise ValueError("Unsupported E9 tooth family")
    if not run_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("run-name contains unsupported characters")
    view = f"/datasets/{dataset_name}/e9_gradient_views_v3/{family}"
    data_spec = json.dumps({f"{dataset_name}-e9-{family}": {
        "base": f"{view}/base",
        "ss_latent": f"{view}/ss_latent",
        "render_cond": f"{view}/render_cond",
    }}, separators=(",", ":"))
    return [
        "python", f"{TRELLIS2_PATH}/train.py",
        "--config", f"/checkpoints/{run_name}/dentalsculptor_sparse_config.json",
        "--output_dir", f"/checkpoints/{run_name}",
        "--data_dir", data_spec,
        "--auto_retry", "0",
    ]


def finite_losses_from_log(text: str) -> list[float]:
    """Extract printed loss values and reject NaN/Inf evidence."""
    values = [
        float(match)
        for match in re.findall(r"(?:^|[\s'\"])(?:loss|Loss)[\s'\"]*[:=][\s]*(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)", text)
    ]
    return [value for value in values if math.isfinite(value)]


def finite_losses_from_training_log(text: str) -> list[float]:
    """Read the canonical TRELLIS.2 JSON-lines loss.loss values."""
    losses = []
    for line in text.splitlines():
        if not line.strip():
            continue
        _, separator, payload = line.partition(": ")
        if not separator:
            raise ValueError(f"Malformed TRELLIS.2 training log line: {line[:80]}")
        value = float(json.loads(payload)["loss"]["loss"])
        if not math.isfinite(value):
            raise ValueError("TRELLIS.2 emitted a non-finite canonical loss.")
        losses.append(value)
    return losses


def smoke_trainer_source_without_snapshots(source: str) -> str:
    """Disable only TRELLIS.2's pre/final visualization in the bounded optimizer gate."""
    replacements = {
        "            self.snapshot_dataset(batch_size=self.snapshot_batch_size)": "            pass  # DentalSculptor smoke: no dataset visualization",
        "            self.snapshot(suffix='init', batch_size=self.snapshot_batch_size)": "            pass  # DentalSculptor smoke: no initial visualization",
        "            self.snapshot(suffix=f'resume_step{self.step:07d}', batch_size=self.snapshot_batch_size)": "            pass  # DentalSculptor smoke: no resume visualization",
        "        self.snapshot(suffix='final', batch_size=self.snapshot_batch_size)": "        pass  # DentalSculptor smoke: no final visualization",
    }
    patched = source
    for original, replacement in replacements.items():
        if patched.count(original) != 1:
            raise ValueError(f"Pinned TRELLIS.2 snapshot statement changed: {original.strip()}")
        patched = patched.replace(original, replacement)
    return patched


def training_entry_source_with_experiment_seed(source: str, seed: int) -> str:
    """Offset the pinned TRELLIS rank seed with an explicit experiment seed."""
    if seed < 0 or seed > 2**31 - 1:
        raise ValueError("experiment seed must fit in a signed 32-bit integer")
    original = "    setup_rng(rank)\n"
    replacement = f"    setup_rng(rank + {seed})\n"
    if source.count(original) != 1:
        raise ValueError("Pinned TRELLIS.2 RNG setup changed; refusing seed patch")
    return source.replace(original, replacement)


def sparse_flow_trainer_source_with_derived_rope_buffer(source: str) -> str:
    """Restore only the deterministic RoPE buffer omitted by the official checkpoint.

    The pinned SparseStructureFlowModel registers ``rope_phases`` as a buffer derived
    solely from the model config and voxel coordinates.  The published safetensors
    checkpoint omits it, while BasicTrainer.finetune_from performs a strict load and
    then forwards the checkpoint state to its master-parameter initializer.  Fill the
    one explicitly allowed missing buffer from the freshly constructed official model;
    fail closed for every other missing key or upstream source change.
    """
    original = (
        "                model_ckpts[name] = model_ckpt\n"
        "                model.load_state_dict(model_ckpt)"
    )
    replacement = (
        "                missing_keys = set(model_state_dict) - set(model_ckpt)\n"
        "                if missing_keys != {'rope_phases'}:\n"
        "                    raise RuntimeError(f'Unexpected missing finetune keys: {sorted(missing_keys)}')\n"
        "                model_ckpt['rope_phases'] = model_state_dict['rope_phases']\n"
        "                model_ckpts[name] = model_ckpt\n"
        "                model.load_state_dict(model_ckpt, strict=True)"
    )
    if source.count(original) != 1:
        raise ValueError("Pinned TRELLIS.2 finetune loader changed; refusing compatibility patch")
    return source.replace(original, replacement)


def trust_region_trainer_source(source: str) -> str:
    """Patch the pinned trainer with a full-precision hard L2-SP projection."""
    autocast_original = (
        "        step_log = {'loss': {}, 'status': {}}\n"
        "        amp_context = partial(torch.autocast, device_type='cuda', "
        "dtype=self.mix_precision_dtype) if self.mix_precision_mode == 'amp' else nullcontext\n"
        "        elastic_controller_context = self.elastic_controller.record "
        "if self.elastic_controller_config is not None else nullcontext"
    )
    autocast_replacement = autocast_original.replace(
        "self.mix_precision_mode == 'amp'",
        "self.mix_precision_mode in ('amp', 'inflat_all')",
    )
    if source.count(autocast_original) != 1:
        raise ValueError("Pinned trainer run-step autocast changed; refusing trust-region patch")
    source = source.replace(autocast_original, autocast_replacement)

    init_original = (
        "        elif finetune_ckpt is not None:\n"
        "            self.finetune_from(finetune_ckpt)"
    )
    init_replacement = init_original + (
        "\n\n"
        "        self.dentalsculptor_trust_region_max = float(kwargs.get(\n"
        "            'dentalsculptor_trust_region_max_relative_l2', 0.0\n"
        "        ))\n"
        "        if self.dentalsculptor_trust_region_max <= 0.0:\n"
        "            raise ValueError('DentalSculptor trust-region radius must be positive')\n"
        "        if finetune_ckpt is None:\n"
        "            raise ValueError('DentalSculptor trust region requires a pinned finetune checkpoint')\n"
        "        self.dentalsculptor_anchor_params = [\n"
        "            param.detach().clone() for param in self.master_params\n"
        "        ]"
    )
    if source.count(init_original) != 1:
        raise ValueError("Pinned trainer finetune initialization changed; refusing trust-region patch")
    source = source.replace(init_original, init_replacement)

    step_original = "        ## adjust learning rate"
    step_replacement = (
        "        ## DentalSculptor full-precision L2-SP hard projection\n"
        "        with torch.no_grad():\n"
        "            anchor_sq = sum(\n"
        "                anchor.float().square().sum()\n"
        "                for anchor in self.dentalsculptor_anchor_params\n"
        "            )\n"
        "            update_sq = sum(\n"
        "                param.float().sub(anchor.float()).square().sum()\n"
        "                for param, anchor in zip(\n"
        "                    self.master_params, self.dentalsculptor_anchor_params\n"
        "                )\n"
        "            )\n"
        "            relative_before = torch.sqrt(update_sq / anchor_sq.clamp_min(1e-30))\n"
        "            if relative_before > self.dentalsculptor_trust_region_max:\n"
        "                scale = self.dentalsculptor_trust_region_max / relative_before\n"
        "                for param, anchor in zip(\n"
        "                    self.master_params, self.dentalsculptor_anchor_params\n"
        "                ):\n"
        "                    param.copy_(anchor + (param - anchor) * scale)\n"
        "                if self.mix_precision_mode == 'inflat_all':\n"
        "                    master_params_to_model_params(self.model_params, self.master_params)\n"
        "            update_sq_after = sum(\n"
        "                param.float().sub(anchor.float()).square().sum()\n"
        "                for param, anchor in zip(\n"
        "                    self.master_params, self.dentalsculptor_anchor_params\n"
        "                )\n"
        "            )\n"
        "            relative_after = torch.sqrt(update_sq_after / anchor_sq.clamp_min(1e-30))\n"
        "            statuses[-1]['trust_region_relative_l2_before'] = relative_before.item()\n"
        "            statuses[-1]['trust_region_relative_l2_after'] = relative_after.item()\n"
        "            statuses[-1]['trust_region_projected'] = float(\n"
        "                relative_before > self.dentalsculptor_trust_region_max\n"
        "            )\n"
        "\n"
        + step_original
    )
    if source.count(step_original) != 1:
        raise ValueError("Pinned trainer optimizer step changed; refusing trust-region patch")
    return source.replace(step_original, step_replacement)


def teacher_consistency_flow_source(source: str) -> str:
    """Add a frozen base teacher and an explicit output-consistency loss."""
    init_original = "        super().__init__(*args, **kwargs)\n        self.t_schedule = t_schedule"
    init_replacement = (
        "        super().__init__(*args, **kwargs)\n"
        "        self.dentalsculptor_teacher_consistency_weight = float(kwargs.get(\n"
        "            'dentalsculptor_teacher_consistency_weight', 0.0\n"
        "        ))\n"
        "        if self.dentalsculptor_teacher_consistency_weight <= 0.0:\n"
        "            raise ValueError('DentalSculptor teacher consistency weight must be positive')\n"
        "        self.dentalsculptor_teacher = copy.deepcopy(\n"
        "            self.models['denoiser']\n"
        "        ).eval().requires_grad_(False)\n"
        "        self.t_schedule = t_schedule"
    )
    if source.count(init_original) != 1:
        raise ValueError("Pinned flow trainer initialization changed; refusing teacher patch")
    source = source.replace(init_original, init_replacement)

    pred_original = (
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        assert pred.shape == noise.shape == x_0.shape"
    )
    pred_replacement = (
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        with torch.no_grad():\n"
        "            teacher_pred = self.dentalsculptor_teacher(\n"
        "                x_t, t * 1000, cond, **kwargs\n"
        "            )\n"
        "        assert pred.shape == teacher_pred.shape == noise.shape == x_0.shape"
    )
    if source.count(pred_original) != 1:
        raise ValueError("Pinned flow prediction path changed; refusing teacher patch")
    source = source.replace(pred_original, pred_replacement)

    loss_original = (
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"loss\"] = terms[\"mse\"]"
    )
    loss_replacement = (
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"teacher_consistency_mse\"] = F.mse_loss(\n"
        "            pred, teacher_pred\n"
        "        )\n"
        "        terms[\"loss\"] = terms[\"mse\"] + (\n"
        "            self.dentalsculptor_teacher_consistency_weight\n"
        "            * terms[\"teacher_consistency_mse\"]\n"
        "        )"
    )
    if source.count(loss_original) != 1:
        raise ValueError("Pinned flow loss path changed; refusing teacher patch")
    return source.replace(loss_original, loss_replacement)


def calibrated_teacher_consistency_flow_source(source: str) -> str:
    """Add a frozen teacher whose detached loss scale targets a bounded objective share.

    The scale is computed from the current supervised and consistency losses, but is
    detached before multiplication.  It therefore changes the gradient magnitude,
    not the gradient direction, and cannot backpropagate through the calibration.
    """
    init_original = "        super().__init__(*args, **kwargs)\n        self.t_schedule = t_schedule"
    init_replacement = (
        "        super().__init__(*args, **kwargs)\n"
        "        self.dentalsculptor_consistency_target_ratio = float(kwargs.get(\n"
        "            'dentalsculptor_consistency_target_ratio', 0.0\n"
        "        ))\n"
        "        self.dentalsculptor_consistency_scale_min = float(kwargs.get(\n"
        "            'dentalsculptor_consistency_scale_min', 1.0\n"
        "        ))\n"
        "        self.dentalsculptor_consistency_scale_max = float(kwargs.get(\n"
        "            'dentalsculptor_consistency_scale_max', 250.0\n"
        "        ))\n"
        "        if not 0.0 < self.dentalsculptor_consistency_target_ratio <= 0.25:\n"
        "            raise ValueError('DentalSculptor consistency target ratio must be in (0, 0.25]')\n"
        "        if not 0.0 < self.dentalsculptor_consistency_scale_min <= self.dentalsculptor_consistency_scale_max:\n"
        "            raise ValueError('DentalSculptor consistency scale bounds are invalid')\n"
        "        self.dentalsculptor_teacher = copy.deepcopy(\n"
        "            self.models['denoiser']\n"
        "        ).eval().requires_grad_(False)\n"
        "        self.t_schedule = t_schedule"
    )
    if source.count(init_original) != 1:
        raise ValueError("Pinned flow trainer initialization changed; refusing calibrated teacher patch")
    source = source.replace(init_original, init_replacement)

    pred_original = (
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        assert pred.shape == noise.shape == x_0.shape"
    )
    pred_replacement = (
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        with torch.no_grad():\n"
        "            teacher_pred = self.dentalsculptor_teacher(\n"
        "                x_t, t * 1000, cond, **kwargs\n"
        "            )\n"
        "        assert pred.shape == teacher_pred.shape == noise.shape == x_0.shape"
    )
    if source.count(pred_original) != 1:
        raise ValueError("Pinned flow prediction path changed; refusing calibrated teacher patch")
    source = source.replace(pred_original, pred_replacement)

    loss_original = (
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"loss\"] = terms[\"mse\"]"
    )
    loss_replacement = (
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"teacher_consistency_mse\"] = F.mse_loss(pred, teacher_pred)\n"
        "        desired = (\n"
        "            self.dentalsculptor_consistency_target_ratio * terms[\"mse\"].detach()\n"
        "        )\n"
        "        raw_scale = desired / terms[\"teacher_consistency_mse\"].detach().clamp_min(1e-12)\n"
        "        consistency_scale = raw_scale.clamp(\n"
        "            min=self.dentalsculptor_consistency_scale_min,\n"
        "            max=self.dentalsculptor_consistency_scale_max,\n"
        "        )\n"
        "        terms[\"teacher_consistency_scale\"] = consistency_scale\n"
        "        terms[\"teacher_consistency_contribution\"] = (\n"
        "            consistency_scale * terms[\"teacher_consistency_mse\"]\n"
        "        )\n"
        "        terms[\"teacher_consistency_share\"] = (\n"
        "            terms[\"teacher_consistency_contribution\"]\n"
        "            / terms[\"mse\"].detach().clamp_min(1e-12)\n"
        "        )\n"
        "        terms[\"loss\"] = terms[\"mse\"] + terms[\"teacher_consistency_contribution\"]"
    )
    if source.count(loss_original) != 1:
        raise ValueError("Pinned flow loss path changed; refusing calibrated teacher patch")
    return source.replace(loss_original, loss_replacement)


def axial_band_balanced_teacher_shape_flow_source(source: str) -> str:
    """Balance shape supervision across four principal-axis token bands."""
    init_original = "        super().__init__(*args, **kwargs)\n        self.t_schedule = t_schedule"
    init_replacement = (
        "        super().__init__(*args, **kwargs)\n"
        "        self.dentalsculptor_axial_band_count = int(kwargs.get(\n"
        "            'dentalsculptor_axial_band_count', 0\n"
        "        ))\n"
        "        self.dentalsculptor_teacher_target_ratio = float(kwargs.get(\n"
        "            'dentalsculptor_teacher_target_ratio', 0.0\n"
        "        ))\n"
        "        if self.dentalsculptor_axial_band_count != 4:\n"
        "            raise ValueError('DentalSculptor axial objective requires four bands')\n"
        "        if self.dentalsculptor_teacher_target_ratio != 0.05:\n"
        "            raise ValueError('DentalSculptor teacher ratio is sealed at 0.05')\n"
        "        self.dentalsculptor_teacher = copy.deepcopy(\n"
        "            self.models['denoiser']\n"
        "        ).eval().requires_grad_(False)\n"
        "        self.t_schedule = t_schedule"
    )
    if source.count(init_original) != 1:
        raise ValueError("Pinned shape-flow initialization changed; refusing axial patch")
    source = source.replace(init_original, init_replacement)
    pred_original = (
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        assert pred.shape == noise.shape == x_0.shape"
    )
    pred_replacement = (
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        with torch.no_grad():\n"
        "            teacher_pred = self.dentalsculptor_teacher(\n"
        "                x_t, t * 1000, cond, **kwargs\n"
        "            )\n"
        "        assert pred.shape == teacher_pred.shape == noise.shape == x_0.shape\n"
        "        if not torch.equal(pred.coords, target.coords):\n"
        "            raise RuntimeError('DentalSculptor target coordinates drifted')\n"
        "        if not torch.equal(pred.coords, teacher_pred.coords):\n"
        "            raise RuntimeError('DentalSculptor teacher coordinates drifted')"
    )
    if source.count(pred_original) != 1:
        raise ValueError("Pinned shape-flow prediction path changed; refusing axial patch")
    source = source.replace(pred_original, pred_replacement)
    loss_original = (
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"loss\"] = terms[\"mse\"]"
    )
    loss_replacement = (
        "        token_error = (pred.feats.float() - target.feats.float()).square().mean(dim=1)\n"
        "        coords = pred.coords\n"
        "        batch_ids = coords[:, 0].long()\n"
        "        sample_losses = []\n"
        "        for batch_id in torch.unique(batch_ids, sorted=True):\n"
        "            sample_mask = batch_ids == batch_id\n"
        "            sample_coords = coords[sample_mask, 1:4].float()\n"
        "            spans = sample_coords.amax(dim=0) - sample_coords.amin(dim=0)\n"
        "            principal_axis = int(torch.argmax(spans).item())\n"
        "            axial = sample_coords[:, principal_axis]\n"
        "            axial_min, axial_max = axial.amin(), axial.amax()\n"
        "            normalized = (axial - axial_min) / (axial_max - axial_min).clamp_min(1.0)\n"
        "            bands = torch.clamp(\n"
        "                (normalized * self.dentalsculptor_axial_band_count).long(),\n"
        "                max=self.dentalsculptor_axial_band_count - 1,\n"
        "            )\n"
        "            sample_error = token_error[sample_mask]\n"
        "            band_losses = [\n"
        "                sample_error[bands == band].mean()\n"
        "                for band in range(self.dentalsculptor_axial_band_count)\n"
        "                if torch.any(bands == band)\n"
        "            ]\n"
        "            if len(band_losses) != self.dentalsculptor_axial_band_count:\n"
        "                raise RuntimeError('DentalSculptor tooth does not occupy all axial bands')\n"
        "            sample_losses.append(torch.stack(band_losses).mean())\n"
        "        axial_mse = torch.stack(sample_losses).mean()\n"
        "        teacher_mse = F.mse_loss(pred.feats.float(), teacher_pred.feats.float())\n"
        "        desired = axial_mse.detach() * self.dentalsculptor_teacher_target_ratio\n"
        "        teacher_scale = desired / teacher_mse.detach().clamp_min(1e-12)\n"
        "        teacher_contribution = teacher_scale * teacher_mse\n"
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"axial_band_balanced_mse\"] = axial_mse\n"
        "        terms[\"teacher_consistency_mse\"] = teacher_mse\n"
        "        terms[\"teacher_consistency_scale\"] = teacher_scale\n"
        "        terms[\"teacher_consistency_contribution\"] = teacher_contribution\n"
        "        terms[\"loss\"] = axial_mse + teacher_contribution\n"
        "        receipt_path = __import__('os').environ.get('DENTALSCULPTOR_E10_OBJECTIVE_RECEIPT')\n"
        "        if receipt_path:\n"
        "            receipt = {\n"
        "                'mse': float(terms['mse'].detach().item()),\n"
        "                'axial_band_balanced_mse': float(axial_mse.detach().item()),\n"
        "                'teacher_consistency_mse': float(teacher_mse.detach().item()),\n"
        "                'teacher_consistency_scale': float(teacher_scale.detach().item()),\n"
        "                'teacher_consistency_contribution': float(teacher_contribution.detach().item()),\n"
        "                'loss': float(terms['loss'].detach().item()),\n"
        "                'teacherFrozen': not any(p.requires_grad for p in self.dentalsculptor_teacher.parameters()),\n"
        "                'populatedAxialBands': self.dentalsculptor_axial_band_count,\n"
        "            }\n"
        "            with open(receipt_path, 'a', encoding='utf-8') as receipt_stream:\n"
        "                receipt_stream.write(__import__('json').dumps(receipt, sort_keys=True) + '\\n')"
    )
    if source.count(loss_original) != 1:
        raise ValueError("Pinned shape-flow loss changed; refusing axial patch")
    return source.replace(loss_original, loss_replacement)


def e10_teacher_init_flow_source(source: str) -> str:
    """Install only E10's frozen teacher on the effective sparse trainer's parent."""
    original = "        super().__init__(*args, **kwargs)\n        self.t_schedule = t_schedule"
    replacement = (
        "        super().__init__(*args, **kwargs)\n"
        "        self.dentalsculptor_axial_band_count = int(kwargs.get('dentalsculptor_axial_band_count', 0))\n"
        "        self.dentalsculptor_teacher_target_ratio = float(kwargs.get('dentalsculptor_teacher_target_ratio', 0.0))\n"
        "        if self.dentalsculptor_axial_band_count != 4:\n"
        "            raise ValueError('DentalSculptor axial objective requires four bands')\n"
        "        if self.dentalsculptor_teacher_target_ratio != 0.05:\n"
        "            raise ValueError('DentalSculptor teacher ratio is sealed at 0.05')\n"
        "        self.dentalsculptor_teacher = copy.deepcopy(self.models['denoiser']).eval().requires_grad_(False)\n"
        "        self.t_schedule = t_schedule"
    )
    if source.count(original) != 1:
        raise ValueError("Pinned flow initialization changed; refusing E10 teacher patch")
    return source.replace(original, replacement)


def e10_axial_sparse_flow_source(source: str) -> str:
    """Patch the SparseFlowMatchingTrainer loss that the configured trainer resolves."""
    pred_original = (
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        assert pred.shape == noise.shape == x_0.shape\n"
        "        target = self.get_v(x_0, noise, t)"
    )
    pred_replacement = (
        "        pred = self.training_models['denoiser'](x_t, t * 1000, cond, **kwargs)\n"
        "        with torch.no_grad():\n"
        "            teacher_pred = self.dentalsculptor_teacher(x_t, t * 1000, cond, **kwargs)\n"
        "        assert pred.shape == teacher_pred.shape == noise.shape == x_0.shape\n"
        "        target = self.get_v(x_0, noise, t)\n"
        "        if not torch.equal(pred.coords, target.coords) or not torch.equal(pred.coords, teacher_pred.coords):\n"
        "            raise RuntimeError('DentalSculptor sparse coordinates drifted')"
    )
    if source.count(pred_original) != 1:
        raise ValueError("Pinned sparse prediction path changed; refusing E10 patch")
    source = source.replace(pred_original, pred_replacement)
    loss_original = (
        "        terms[\"mse\"] = F.mse_loss(pred.feats, target.feats)\n"
        "        terms[\"loss\"] = terms[\"mse\"]"
    )
    loss_replacement = (
        "        token_error = (pred.feats.float() - target.feats.float()).square().mean(dim=1)\n"
        "        batch_ids = pred.coords[:, 0].long()\n"
        "        sample_losses = []\n"
        "        for batch_id in torch.unique(batch_ids, sorted=True):\n"
        "            sample_mask = batch_ids == batch_id\n"
        "            sample_coords = pred.coords[sample_mask, 1:4].float()\n"
        "            spans = sample_coords.amax(dim=0) - sample_coords.amin(dim=0)\n"
        "            principal_axis = int(torch.argmax(spans).item())\n"
        "            axial = sample_coords[:, principal_axis]\n"
        "            normalized = (axial - axial.amin()) / (axial.amax() - axial.amin()).clamp_min(1.0)\n"
        "            bands = torch.clamp((normalized * self.dentalsculptor_axial_band_count).long(), max=self.dentalsculptor_axial_band_count - 1)\n"
        "            sample_error = token_error[sample_mask]\n"
        "            band_losses = [sample_error[bands == band].mean() for band in range(self.dentalsculptor_axial_band_count) if torch.any(bands == band)]\n"
        "            if len(band_losses) != self.dentalsculptor_axial_band_count:\n"
        "                raise RuntimeError('DentalSculptor tooth does not occupy all axial bands')\n"
        "            sample_losses.append(torch.stack(band_losses).mean())\n"
        "        axial_mse = torch.stack(sample_losses).mean()\n"
        "        teacher_mse = F.mse_loss(pred.feats.float(), teacher_pred.feats.float())\n"
        "        teacher_scale = (axial_mse.detach() * self.dentalsculptor_teacher_target_ratio) / teacher_mse.detach().clamp_min(1e-12)\n"
        "        teacher_contribution = teacher_scale * teacher_mse\n"
        "        terms[\"mse\"] = F.mse_loss(pred.feats, target.feats)\n"
        "        terms[\"axial_band_balanced_mse\"] = axial_mse\n"
        "        terms[\"teacher_consistency_mse\"] = teacher_mse\n"
        "        terms[\"teacher_consistency_scale\"] = teacher_scale\n"
        "        terms[\"teacher_consistency_contribution\"] = teacher_contribution\n"
        "        terms[\"loss\"] = axial_mse + teacher_contribution\n"
        "        receipt_path = os.environ.get('DENTALSCULPTOR_E10_OBJECTIVE_RECEIPT')\n"
        "        if receipt_path:\n"
        "            import json\n"
        "            receipt = {\n"
        "                'mse': float(terms['mse'].detach().item()),\n"
        "                'axial_band_balanced_mse': float(axial_mse.detach().item()),\n"
        "                'teacher_consistency_mse': float(teacher_mse.detach().item()),\n"
        "                'teacher_consistency_scale': float(teacher_scale.detach().item()),\n"
        "                'teacher_consistency_contribution': float(teacher_contribution.detach().item()),\n"
        "                'loss': float(terms['loss'].detach().item()),\n"
        "                'teacherFrozen': not any(p.requires_grad for p in self.dentalsculptor_teacher.parameters()),\n"
        "                'populatedAxialBands': self.dentalsculptor_axial_band_count,\n"
        "                'effectiveTrainerModule': type(self).__module__,\n"
        "                'effectiveTrainerClass': type(self).__name__,\n"
        "                'phase': getattr(self, 'dentalsculptor_receipt_phase', 'pre_update'),\n"
        "            }\n"
        "            with open(receipt_path, 'a', encoding='utf-8') as stream:\n"
        "                stream.write(json.dumps(receipt, sort_keys=True) + '\\n')"
    )
    if source.count(loss_original) != 1:
        raise ValueError("Pinned sparse loss changed; refusing E10 patch")
    return source.replace(loss_original, loss_replacement)


def e11_bandwise_teacher_sparse_flow_source(source: str) -> str:
    """E11: balance preservation across every axial region, not all tokens.

    E10 balanced the supervised target by axial band but calibrated its frozen
    teacher on a global token mean. Dense crown/body tokens could therefore
    dominate preservation while a root or terminal band drifted. E11 applies
    the same per-sample, per-band averaging to teacher consistency before the
    detached 5% calibration. It remains orientation independent.
    """
    patched = e10_axial_sparse_flow_source(source)
    original = (
        "        teacher_mse = F.mse_loss(pred.feats.float(), teacher_pred.feats.float())\n"
        "        teacher_scale = (axial_mse.detach() * self.dentalsculptor_teacher_target_ratio) / teacher_mse.detach().clamp_min(1e-12)\n"
        "        teacher_contribution = teacher_scale * teacher_mse"
    )
    replacement = (
        "        teacher_token_error = (pred.feats.float() - teacher_pred.feats.float()).square().mean(dim=1)\n"
        "        teacher_sample_losses = []\n"
        "        teacher_band_mses = []\n"
        "        for batch_id in torch.unique(batch_ids, sorted=True):\n"
        "            sample_mask = batch_ids == batch_id\n"
        "            sample_coords = pred.coords[sample_mask, 1:4].float()\n"
        "            spans = sample_coords.amax(dim=0) - sample_coords.amin(dim=0)\n"
        "            principal_axis = int(torch.argmax(spans).item())\n"
        "            axial = sample_coords[:, principal_axis]\n"
        "            normalized = (axial - axial.amin()) / (axial.amax() - axial.amin()).clamp_min(1.0)\n"
        "            bands = torch.clamp((normalized * self.dentalsculptor_axial_band_count).long(), max=self.dentalsculptor_axial_band_count - 1)\n"
        "            sample_teacher_error = teacher_token_error[sample_mask]\n"
        "            band_teacher_losses = [sample_teacher_error[bands == band].mean() for band in range(self.dentalsculptor_axial_band_count) if torch.any(bands == band)]\n"
        "            if len(band_teacher_losses) != self.dentalsculptor_axial_band_count:\n"
        "                raise RuntimeError('DentalSculptor teacher preservation lacks an axial band')\n"
        "            teacher_band_mses.extend(band_teacher_losses)\n"
        "            teacher_sample_losses.append(torch.stack(band_teacher_losses).mean())\n"
        "        teacher_mse = torch.stack(teacher_sample_losses).mean()\n"
        "        teacher_scale = (axial_mse.detach() * self.dentalsculptor_teacher_target_ratio) / teacher_mse.detach().clamp_min(1e-12)\n"
        "        teacher_contribution = teacher_scale * teacher_mse"
    )
    if patched.count(original) != 1:
        raise ValueError("E10 teacher block changed; refusing E11 regional patch")
    patched = patched.replace(original, replacement)
    receipt_anchor = (
        "                'populatedAxialBands': self.dentalsculptor_axial_band_count,\n"
        "                'effectiveTrainerModule': type(self).__module__,"
    )
    receipt_replacement = (
        "                'populatedAxialBands': self.dentalsculptor_axial_band_count,\n"
        "                'teacherConsistencyMode': 'equal-per-sample-per-axial-band',\n"
        "                'teacherBandMseMin': float(torch.stack(teacher_band_mses).amin().detach().item()),\n"
        "                'teacherBandMseMax': float(torch.stack(teacher_band_mses).amax().detach().item()),\n"
        "                'effectiveTrainerModule': type(self).__module__,"
    )
    if patched.count(receipt_anchor) != 1:
        raise ValueError("E10 receipt block changed; refusing E11 regional patch")
    return patched.replace(receipt_anchor, receipt_replacement)


def e12_decoder_only_shape_vae_source(source: str) -> str:
    """E12: adapt only the native geometry decoder with official surface losses."""
    init_anchor = (
        "    ):\n"
        "        super().__init__(*args, **kwargs)\n"
        "        self.lambda_subdiv = lambda_subdiv"
    )
    init_replacement = (
        "    ):\n"
        "        models = args[0] if args else kwargs.get('models')\n"
        "        if not isinstance(models, dict) or set(models) != {'encoder', 'decoder'}:\n"
        "            raise ValueError('DentalSculptor E12 requires exactly encoder and decoder models')\n"
        "        if kwargs.get('dentalsculptor_e12_objective') != 'decoder-only-native-geometry-v1':\n"
        "            raise ValueError('DentalSculptor E12 objective contract is not sealed')\n"
        "        models['encoder'].train().requires_grad_(False)\n"
        "        if not any(p.requires_grad for p in models['decoder'].parameters()):\n"
        "            raise ValueError('DentalSculptor E12 decoder has no trainable parameters')\n"
        "        super().__init__(*args, **kwargs)\n"
        "        if any(p.requires_grad for p in self.models['encoder'].parameters()):\n"
        "            raise RuntimeError('DentalSculptor E12 encoder is not frozen')\n"
        "        encoder_ids = {id(p) for p in self.models['encoder'].parameters()}\n"
        "        if any(id(p) in encoder_ids for p in self.model_params):\n"
        "            raise RuntimeError('DentalSculptor E12 optimizer contains encoder parameters')\n"
        "        self.dentalsculptor_e12_trainable_parameters = sum(p.numel() for p in self.models['decoder'].parameters() if p.requires_grad)\n"
        "        self.lambda_subdiv = lambda_subdiv"
    )
    if source.count(init_anchor) != 1:
        raise ValueError("Pinned ShapeVaeTrainer initialization changed; refusing E12 patch")
    patched = source.replace(init_anchor, init_replacement)

    latent_anchor = (
        "        z, mean, logvar = self.training_models['encoder'](vertices, intersected, sample_posterior=True, return_raw=True)\n"
        "        recon, pred_vertice, pred_intersected, subs_gt, subs = self.training_models['decoder'](z, intersected)"
    )
    latent_replacement = (
        "        z, mean, logvar = self.training_models['encoder'](vertices, intersected, sample_posterior=True, return_raw=True)\n"
        "        # Frozen encoder boundary: preserve spatial caches, but make decoder input a grad-enabled leaf.\n"
        "        z = z.replace(z.feats.detach().requires_grad_(True))\n"
        "        # Do not reuse inference-only FlexGEMM caches created by the frozen encoder.\n"
        "        retained_spatial_cache = {}\n"
        "        removed_neighbor_caches = 0\n"
        "        for scale, entries in z._spatial_cache.items():\n"
        "            retained = {}\n"
        "            for key, value in entries.items():\n"
        "                if key.startswith('SubMConv3d_neighbor_cache_'):\n"
        "                    removed_neighbor_caches += 1\n"
        "                else:\n"
        "                    retained[key] = value\n"
        "            retained_spatial_cache[scale] = retained\n"
        "        z._spatial_cache = retained_spatial_cache\n"
        "        if not z.feats.is_leaf or not z.feats.requires_grad:\n"
        "            raise RuntimeError('DentalSculptor E12 decoder latent is not a gradient-enabled leaf')\n"
        "        self.dentalsculptor_e12_latent_leaf_grad_enabled = True\n"
        "        self.dentalsculptor_e12_removed_inference_neighbor_caches = removed_neighbor_caches\n"
        "        recon, pred_vertice, pred_intersected, subs_gt, subs = self.training_models['decoder'](z, intersected)"
    )
    if patched.count(latent_anchor) != 1:
        raise ValueError("Pinned ShapeVaeTrainer latent boundary changed; refusing E12 patch")
    patched = patched.replace(latent_anchor, latent_replacement)

    subdivision_anchor = (
        "        # subdivision prediction loss\n"
        "        for i, (sub_gt, sub) in enumerate(zip(subs_gt, subs)):\n"
    )
    subdivision_replacement = (
        "        # DentalSculptor E12 zero-step native-target contract\n"
        "        missing_subdivision_targets = [i for i, target in enumerate(subs_gt) if target is None]\n"
        "        if missing_subdivision_targets or len(subs_gt) != len(subs):\n"
        "            raise RuntimeError(f'DentalSculptor E12 subdivision target contract failed: missing={missing_subdivision_targets}, targets={len(subs_gt)}, predictions={len(subs)}')\n"
        "        self.dentalsculptor_e12_subdivision_target_levels = len(subs_gt)\n"
        "        # subdivision prediction loss\n"
        "        for i, (sub_gt, sub) in enumerate(zip(subs_gt, subs)):\n"
    )
    if patched.count(subdivision_anchor) != 1:
        raise ValueError("Pinned ShapeVaeTrainer subdivision boundary changed; refusing E12 patch")
    patched = patched.replace(subdivision_anchor, subdivision_replacement)

    loss_anchor = (
        "        terms[\"loss\"] = terms[\"loss\"] + self.lambda_kl * terms[\"kl\"]\n"
        "            \n"
        "        return terms, {}"
    )
    loss_replacement = (
        "        terms[\"loss\"] = terms[\"loss\"] + self.lambda_kl * terms[\"kl\"]\n"
        "        receipt_path = os.environ.get('DENTALSCULPTOR_E12_OBJECTIVE_RECEIPT')\n"
        "        if receipt_path:\n"
        "            required = ['direct/intersected', 'direct/vertice', 'render/mask', 'render/depth', 'render/normal/l1', 'render/normal/ssim', 'render/normal/lpips', 'kl']\n"
        "            missing = [name for name in required if name not in terms]\n"
        "            subdiv = sorted(name for name in terms if name.startswith('bce_sub'))\n"
        "            if missing or not subdiv:\n"
        "                raise RuntimeError(f'DentalSculptor E12 native geometry terms missing: {missing}, subdivision={subdiv}')\n"
        "            values = {name: float(terms[name].detach().item()) for name in required + subdiv}\n"
        "            if not all(__import__('math').isfinite(value) for value in values.values()):\n"
        "                raise RuntimeError('DentalSculptor E12 produced non-finite geometry loss')\n"
        "            receipt = {\n"
        "                'objective': 'decoder-only-native-geometry-v1',\n"
        "                'encoderFrozen': not any(p.requires_grad for p in self.models['encoder'].parameters()),\n"
        "                'decoderTrainableParameters': self.dentalsculptor_e12_trainable_parameters,\n"
        "                'optimizerParameterCount': sum(p.numel() for p in self.model_params),\n"
        "                'subdivisionTargetLevels': self.dentalsculptor_e12_subdivision_target_levels,\n"
        "                'latentLeafGradEnabled': self.dentalsculptor_e12_latent_leaf_grad_enabled,\n"
        "                'removedInferenceNeighborCaches': self.dentalsculptor_e12_removed_inference_neighbor_caches,\n"
        "                'nativeGeometryTerms': values,\n"
        "                'loss': float(terms['loss'].detach().item()),\n"
        "            }\n"
        "            with open(receipt_path, 'a', encoding='utf-8') as stream:\n"
        "                stream.write(__import__('json').dumps(receipt, sort_keys=True) + '\\n')\n"
        "            \n"
        "        return terms, {}"
    )
    if patched.count(loss_anchor) != 1:
        raise ValueError("Pinned ShapeVaeTrainer loss boundary changed; refusing E12 patch")
    return patched.replace(loss_anchor, loss_replacement)


def e15_regional_decoder_zero_step_source(source: str) -> str:
    """Qualify a crown-targeted late-decoder objective without updating weights.

    The official direct decoder targets remain the crown supervision.  A frozen
    copy of the base decoder is the teacher for the cervical/root proxy bands.
    This is deliberately an engineering axial proxy gate, not a claim that the
    bands are reviewed enamel/CEJ/root annotations.
    """
    patched = e12_decoder_only_shape_vae_source(source)
    init_anchor = (
        "        self.dentalsculptor_e12_trainable_parameters = sum(p.numel() for p in self.models['decoder'].parameters() if p.requires_grad)\n"
        "        self.lambda_subdiv = lambda_subdiv"
    )
    init_replacement = (
        "        late_prefixes = ('blocks.3.', 'output_layer.')\n"
        "        for name, parameter in self.models['decoder'].named_parameters():\n"
        "            parameter.requires_grad_(any(name.startswith(prefix) for prefix in late_prefixes))\n"
        "        self.dentalsculptor_e15_teacher = __import__('copy').deepcopy(self.models['decoder']).eval().requires_grad_(False)\n"
        "        self.dentalsculptor_e15_teacher.to(self.device)\n"
        "        self.model_params = [parameter for parameter in self.models['decoder'].parameters() if parameter.requires_grad]\n"
        "        self.master_params = self.model_params\n"
        "        self.dentalsculptor_e12_trainable_parameters = sum(p.numel() for p in self.model_params)\n"
        "        self.dentalsculptor_e15_trainable_names = [name for name, parameter in self.models['decoder'].named_parameters() if parameter.requires_grad]\n"
        "        if not self.dentalsculptor_e15_trainable_names or any(not any(name.startswith(prefix) for prefix in late_prefixes) for name in self.dentalsculptor_e15_trainable_names):\n"
        "            raise RuntimeError('DentalSculptor E15 late-decoder parameter boundary failed')\n"
        "        self.lambda_subdiv = lambda_subdiv"
    )
    if patched.count(init_anchor) != 1:
        raise ValueError("E12 decoder initialization changed; refusing E15 patch")
    patched = patched.replace(init_anchor, init_replacement)

    forward_anchor = "        recon, pred_vertice, pred_intersected, subs_gt, subs = self.training_models['decoder'](z, intersected)"
    forward_replacement = (
        "        recon, pred_vertice, pred_intersected, subs_gt, subs = self.training_models['decoder'](z, intersected)\n"
        "        teacher_z = z.replace(z.feats.detach())\n"
        "        teacher_z._spatial_cache = {scale: {key: value for key, value in entries.items() if not key.startswith('SubMConv3d_neighbor_cache_')} for scale, entries in z._spatial_cache.items()}\n"
        "        with torch.no_grad():\n"
        "            _, teacher_vertice, teacher_intersected, _, _ = self.dentalsculptor_e15_teacher(teacher_z, intersected)\n"
        "        if not torch.equal(pred_intersected.coords, intersected.coords) or not torch.equal(pred_vertice.coords, vertices.coords):\n"
        "            raise RuntimeError('DentalSculptor E15 candidate/target sparse coordinates do not align')\n"
        "        if not torch.equal(teacher_intersected.coords, pred_intersected.coords) or not torch.equal(teacher_vertice.coords, pred_vertice.coords):\n"
        "            raise RuntimeError('DentalSculptor E15 teacher/candidate sparse coordinates do not align')\n"
        "        coords = intersected.coords[:, 1:4].float()\n"
        "        occupied = intersected.feats.flatten().bool()\n"
        "        spans = coords.amax(dim=0) - coords.amin(dim=0)\n"
        "        principal_axis = int(torch.argmax(spans).item())\n"
        "        axial = coords[:, principal_axis]\n"
        "        normalized = (axial - axial.amin()) / (axial.amax() - axial.amin()).clamp_min(1.0)\n"
        "        lower_terminal = normalized <= 0.30\n"
        "        upper_terminal = normalized >= 0.70\n"
        "        crown_is_upper = int((occupied & upper_terminal).sum().item()) >= int((occupied & lower_terminal).sum().item())\n"
        "        crown_mask = upper_terminal if crown_is_upper else lower_terminal\n"
        "        cervical_mask = ((normalized >= 0.30) & (normalized < 0.48)) if crown_is_upper else ((normalized > 0.52) & (normalized <= 0.70))\n"
        "        protected_mask = ~crown_mask\n"
        "        root_mask = protected_mask & ~cervical_mask\n"
        "        if not crown_mask.any() or not cervical_mask.any() or not root_mask.any():\n"
        "            raise RuntimeError('DentalSculptor E15 regional proxy mask is empty')"
    )
    if patched.count(forward_anchor) != 1:
        raise ValueError("E12 decoder forward boundary changed; refusing E15 patch")
    patched = patched.replace(forward_anchor, forward_replacement)

    loss_anchor = (
        "        terms[\"loss\"] = terms[\"loss\"] + self.lambda_kl * terms[\"kl\"]\n"
        "        receipt_path = os.environ.get('DENTALSCULPTOR_E12_OBJECTIVE_RECEIPT')"
    )
    loss_replacement = (
        "        terms[\"loss\"] = terms[\"loss\"] + self.lambda_kl * terms[\"kl\"]\n"
        "        crown_intersected = F.binary_cross_entropy_with_logits(pred_intersected.feats.flatten()[crown_mask], intersected.feats.flatten().float()[crown_mask])\n"
        "        crown_vertice = F.mse_loss(pred_vertice.feats[crown_mask], vertices.feats[crown_mask])\n"
        "        cervical_intersected_teacher = F.mse_loss(pred_intersected.feats.flatten()[cervical_mask], teacher_intersected.feats.flatten()[cervical_mask])\n"
        "        cervical_vertice_teacher = F.mse_loss(pred_vertice.feats[cervical_mask], teacher_vertice.feats[cervical_mask])\n"
        "        root_intersected_teacher = F.mse_loss(pred_intersected.feats.flatten()[root_mask], teacher_intersected.feats.flatten()[root_mask])\n"
        "        root_vertice_teacher = F.mse_loss(pred_vertice.feats[root_mask], teacher_vertice.feats[root_mask])\n"
        "        protected_teacher = 2.0 * (cervical_intersected_teacher + cervical_vertice_teacher) + root_intersected_teacher + root_vertice_teacher\n"
        "        protected_probe = 2.0 * (F.mse_loss(pred_intersected.feats.flatten()[cervical_mask] + 1e-3, teacher_intersected.feats.flatten()[cervical_mask]) + F.mse_loss(pred_vertice.feats[cervical_mask] + 1e-3, teacher_vertice.feats[cervical_mask])) + F.mse_loss(pred_intersected.feats.flatten()[root_mask] + 1e-3, teacher_intersected.feats.flatten()[root_mask]) + F.mse_loss(pred_vertice.feats[root_mask] + 1e-3, teacher_vertice.feats[root_mask])\n"
        "        crown_objective = crown_intersected + 0.1 * crown_vertice\n"
        "        terms['loss'] = crown_objective + 0.25 * protected_teacher\n"
        "        receipt_path_e15 = os.environ.get('DENTALSCULPTOR_E15_ZERO_STEP_RECEIPT')\n"
        "        if receipt_path_e15:\n"
        "            named_params = [(name, parameter) for name, parameter in self.models['decoder'].named_parameters() if parameter.requires_grad]\n"
        "            components = [('crownObjective', crown_objective), ('protectedTeacher', protected_teacher), ('protectedProbe', protected_probe), ('totalLoss', terms['loss'])]\n"
        "            component_receipts = []\n"
        "            for index, (component_name, component) in enumerate(components):\n"
        "                gradients = torch.autograd.grad(component, [parameter for _, parameter in named_params], retain_graph=index < len(components) - 1, allow_unused=True)\n"
        "                component_receipts.append({'name': component_name, 'value': float(component.detach().item()), 'missingGradientNames': [name for (name, _), gradient in zip(named_params, gradients) if gradient is None], 'nonfiniteGradientNames': [name for (name, _), gradient in zip(named_params, gradients) if gradient is not None and not gradient.isfinite().all()], 'nonzeroGradientTensorCount': sum(bool(gradient is not None and gradient.isfinite().all() and torch.count_nonzero(gradient).item()) for gradient in gradients)})\n"
        "            receipt = {'schemaVersion': 1, 'valid': True, 'objective': 'late-decoder-crown-detail-with-root-teacher-v1', 'optimizerSteps': 0, 'engineeringMaskOnly': True, 'principalAxis': principal_axis, 'crownDirection': 'upper' if crown_is_upper else 'lower', 'regionCounts': {'crown': int(crown_mask.sum().item()), 'cervical': int(cervical_mask.sum().item()), 'root': int(root_mask.sum().item())}, 'trainableParameterNames': self.dentalsculptor_e15_trainable_names, 'trainableParameterTensorCount': len(named_params), 'components': component_receipts}\n"
        "            with open(receipt_path_e15, 'w', encoding='utf-8') as stream:\n"
        "                stream.write(__import__('json').dumps(receipt, sort_keys=True) + '\\n')\n"
        "            raise RuntimeError('DENTALSCULPTOR_E15_REGIONAL_DECODER_ZERO_STEP_COMPLETE')\n"
        "        receipt_path = os.environ.get('DENTALSCULPTOR_E12_OBJECTIVE_RECEIPT')"
    )
    if patched.count(loss_anchor) != 1:
        raise ValueError("E12 decoder loss boundary changed; refusing E15 patch")
    return patched.replace(loss_anchor, loss_replacement)


def e12_basic_trainer_gradient_gate_source(source: str) -> str:
    """Require complete finite decoder gradients before the first optimizer step."""
    anchor = "        ## gradient clip\n        if self.grad_clip is not None:"
    replacement = (
        "        ## DentalSculptor E12 pre-optimizer decoder-gradient gate\n"
        "        gradient_receipt_path = os.environ.get('DENTALSCULPTOR_E12_GRADIENT_RECEIPT')\n"
        "        if gradient_receipt_path:\n"
        "            missing_gradients = [i for i, p in enumerate(self.model_params) if p.grad is None]\n"
        "            nonfinite_gradients = [i for i, p in enumerate(self.model_params) if p.grad is not None and not p.grad.isfinite().all()]\n"
        "            if missing_gradients or nonfinite_gradients:\n"
        "                raise RuntimeError(f'DentalSculptor E12 decoder gradient contract failed: missing={missing_gradients[:16]}, nonfinite={nonfinite_gradients[:16]}')\n"
        "            all_zero_gradients = [i for i, p in enumerate(self.model_params) if p.grad is not None and p.grad.isfinite().all() and not bool(torch.count_nonzero(p.grad).item())]\n"
        "            if all_zero_gradients:\n"
        "                raise RuntimeError(f'DentalSculptor E12 decoder zero-gradient contract failed: all_zero={all_zero_gradients[:16]}')\n"
        "            gradient_receipt = {'valid': True, 'parameterTensorCount': len(self.model_params), 'missingGradientCount': 0, 'nonfiniteGradientCount': 0, 'allZeroGradientCount': 0, 'logScale': float(self.log_scale), 'lossScale': float(2 ** self.log_scale)}\n"
        "            with open(gradient_receipt_path, 'w', encoding='utf-8') as stream:\n"
        "                stream.write(__import__('json').dumps(gradient_receipt, sort_keys=True) + '\\n')\n"
        "        ## gradient clip\n"
        "        if self.grad_clip is not None:"
    )
    if source.count(anchor) != 1:
        raise ValueError("Pinned BasicTrainer gradient boundary changed; refusing E12 patch")
    return source.replace(anchor, replacement)


def e12_initial_log_scale_source(source: str, log_scale: int = 12) -> str:
    """Set the preregistered safe initial inflat_all scale for E12."""
    if log_scale != 12:
        raise ValueError("E12 initial log scale is sealed to 12")
    anchor = "                self.log_scale = 20.0"
    replacement = (
        "                self.log_scale = 12.0\n"
        "                self.dentalsculptor_e12_initial_log_scale = 12.0"
    )
    if source.count(anchor) != 1:
        raise ValueError("Pinned inflat_all scale initialization changed; refusing E12 scale patch")
    return source.replace(anchor, replacement)


def compare_e12_encoder_states(base_state: dict, saved_state: dict) -> dict:
    """Classify exact, dtype-only, and genuine tensor changes fail-closed."""
    import numpy as np

    base_keys = set(base_state)
    saved_keys = set(saved_state)
    missing = sorted(base_keys - saved_keys)
    unexpected = sorted(saved_keys - base_keys)
    dtype_changed = []
    raw_changed = []
    canonical_changed = []
    first_differences = []
    maximum_absolute_difference = 0.0
    for key in sorted(base_keys & saved_keys):
        base_value = base_state[key]
        saved_value = saved_state[key]
        base = (
            base_value.detach().cpu().contiguous().numpy()
            if hasattr(base_value, "detach") else np.ascontiguousarray(base_value)
        )
        saved = (
            saved_value.detach().cpu().contiguous().numpy()
            if hasattr(saved_value, "detach") else np.ascontiguousarray(saved_value)
        )
        if tuple(base.shape) != tuple(saved.shape):
            canonical_changed.append(key)
            first_differences.append({
                "name": key, "reason": "shape",
                "baseShape": list(base.shape), "savedShape": list(saved.shape),
            })
            continue
        if base.dtype != saved.dtype:
            dtype_changed.append(key)
        raw_equal = base.dtype == saved.dtype and np.array_equal(base, saved)
        if not raw_equal:
            raw_changed.append(key)
        canonical_equal = np.array_equal(base.astype(saved.dtype, copy=False), saved)
        if np.issubdtype(base.dtype, np.floating) or np.issubdtype(saved.dtype, np.floating):
            maximum_absolute_difference = max(
                maximum_absolute_difference,
                float(np.max(np.abs(base.astype(np.float32) - saved.astype(np.float32)))) if base.size else 0.0,
            )
        if not canonical_equal:
            canonical_changed.append(key)
            if len(first_differences) < 32:
                first_differences.append({
                    "name": key, "reason": "value",
                    "baseDtype": str(base.dtype), "savedDtype": str(saved.dtype),
                    "maxAbsDifference": (
                        float(np.max(np.abs(base.astype(np.float32) - saved.astype(np.float32))))
                        if base.size and (np.issubdtype(base.dtype, np.floating) or np.issubdtype(saved.dtype, np.floating))
                        else None
                    ),
                })
    canonical_equivalent = not missing and not unexpected and not canonical_changed
    return {
        "schemaVersion": 1,
        "tensorCount": len(base_keys & saved_keys),
        "missingKeyCount": len(missing), "missingKeys": missing[:32],
        "unexpectedKeyCount": len(unexpected), "unexpectedKeys": unexpected[:32],
        "dtypeChangedTensorCount": len(dtype_changed),
        "rawChangedTensorCount": len(raw_changed),
        "canonicalChangedTensorCount": len(canonical_changed),
        "firstCanonicalDifferences": first_differences,
        "maximumAbsoluteDifference": maximum_absolute_difference,
        "rawByteEquivalent": not missing and not unexpected and not raw_changed,
        "canonicalRuntimeEquivalent": canonical_equivalent,
        "classification": (
            "identical" if canonical_equivalent and not raw_changed
            else "dtype-or-serialization-only" if canonical_equivalent
            else "genuine-state-change"
        ),
    }


def summarize_e12_decoder_update_groups(base_state: dict, candidate_state: dict) -> dict:
    """Measure one-step decoder deltas by architectural stage after dtype canonicalization."""
    import numpy as np

    def group_for(key: str) -> str:
        if key.startswith("from_latent."):
            return "from_latent"
        for index in range(4):
            if key.startswith(f"blocks.{index}."):
                return f"blocks.{index}"
        if key.startswith("output_layer.") or key.startswith("out_layer."):
            return "output_layer"
        return "other"

    if set(base_state) != set(candidate_state) or not base_state:
        raise ValueError("E12 decoder localization requires identical non-empty state keys")
    groups: dict[str, dict] = {}
    changed_keys = []
    for key in sorted(base_state):
        base_value, candidate_value = base_state[key], candidate_state[key]
        base = (
            base_value.detach().cpu().contiguous().numpy()
            if hasattr(base_value, "detach") else np.ascontiguousarray(base_value)
        )
        candidate = (
            candidate_value.detach().cpu().contiguous().numpy()
            if hasattr(candidate_value, "detach") else np.ascontiguousarray(candidate_value)
        )
        if base.shape != candidate.shape:
            raise ValueError(f"E12 decoder shape drift for {key}")
        canonical_base = base.astype(candidate.dtype, copy=False)
        delta = candidate.astype(np.float64) - canonical_base.astype(np.float64)
        changed = bool(np.any(delta != 0))
        group = group_for(key)
        row = groups.setdefault(group, {
            "tensorCount": 0, "parameterCount": 0, "changedTensorCount": 0,
            "changedParameterCount": 0, "squaredL2Delta": 0.0,
            "maximumAbsoluteDelta": 0.0,
        })
        row["tensorCount"] += 1
        row["parameterCount"] += int(candidate.size)
        if changed:
            changed_keys.append(key)
            row["changedTensorCount"] += 1
            row["changedParameterCount"] += int(np.count_nonzero(delta))
            row["squaredL2Delta"] += float(np.sum(delta * delta))
            row["maximumAbsoluteDelta"] = max(
                row["maximumAbsoluteDelta"], float(np.max(np.abs(delta)))
            )
    for row in groups.values():
        row["l2Delta"] = float(np.sqrt(row.pop("squaredL2Delta")))
    recognized = {"from_latent", "blocks.0", "blocks.1", "blocks.2", "blocks.3", "output_layer"}
    changed_groups = sorted(group for group, row in groups.items() if row["changedTensorCount"])
    unknown_changed = groups.get("other", {}).get("changedTensorCount", 0)
    late_changed = sum(
        groups.get(group, {}).get("changedTensorCount", 0)
        for group in ("blocks.3", "output_layer")
    )
    return {
        "schemaVersion": 1,
        "tensorCount": len(base_state),
        "changedTensorCount": len(changed_keys),
        "changedGroups": changed_groups,
        "groups": groups,
        "firstChangedKeys": changed_keys[:32],
        "allChangedGroupsRecognized": all(group in recognized for group in changed_groups),
        "lateStageChangedTensorCount": late_changed,
        "lateDeltaHybridAuthorized": bool(
            changed_keys and late_changed and not unknown_changed
        ),
    }


def build_e12_late_delta_hybrid_state(
    base_state: dict,
    candidate_state: dict,
    candidate_prefixes: tuple[str, ...] = ("blocks.3.", "output_layer."),
) -> tuple[dict, list[str]]:
    """Keep the base decoder except for explicitly sealed candidate stages."""
    if set(base_state) != set(candidate_state) or not base_state:
        raise ValueError("E12 late-delta hybrid requires identical non-empty state keys")
    late_keys = sorted(
        key for key in base_state
        if any(key.startswith(prefix) for prefix in candidate_prefixes)
    )
    if not late_keys:
        raise ValueError("E12 late-delta hybrid found no late-stage tensors")
    late_key_set = set(late_keys)
    return {
        key: candidate_state[key] if key in late_key_set else base_state[key]
        for key in base_state
    }, late_keys


def e12_component_gradient_diagnostic_source(source: str) -> str:
    """Measure each native E12 term without populating .grad or stepping."""
    anchor = "            \n        return terms, {}"
    replacement = (
        "        diagnostic_path = os.environ.get('DENTALSCULPTOR_E12_COMPONENT_GRADIENT_RECEIPT')\n"
        "        if diagnostic_path:\n"
        "            named_params = [(name, p) for name, p in self.models['decoder'].named_parameters() if p.requires_grad]\n"
        "            component_names = ['direct/intersected', 'direct/vertice', 'render/mask', 'render/depth', 'render/normal/l1', 'render/normal/ssim', 'render/normal/lpips', 'kl']\n"
        "            component_names += sorted(name for name in terms if name.startswith('bce_sub'))\n"
        "            component_names += ['loss']\n"
        "            component_receipts = []\n"
        "            for component_index, component_name in enumerate(component_names):\n"
        "                value = terms[component_name]\n"
        "                gradients = torch.autograd.grad(value, [p for _, p in named_params], retain_graph=component_index < len(component_names) - 1, allow_unused=True) if value.requires_grad else tuple(None for _ in named_params)\n"
        "                missing = [name for (name, _), grad in zip(named_params, gradients) if grad is None]\n"
        "                nonfinite = [name for (name, _), grad in zip(named_params, gradients) if grad is not None and not grad.isfinite().all()]\n"
        "                finite_max_abs = [float(grad.detach().abs().amax().item()) for grad in gradients if grad is not None and grad.isfinite().all()]\n"
        "                component_receipts.append({\n"
        "                    'component': component_name,\n"
        "                    'value': float(value.detach().item()),\n"
        "                    'requiresGrad': bool(value.requires_grad),\n"
        "                    'missingGradientCount': len(missing),\n"
        "                    'missingGradientNames': missing[:32],\n"
        "                    'nonfiniteGradientCount': len(nonfinite),\n"
        "                    'nonfiniteGradientNames': nonfinite[:32],\n"
        "                    'finiteGradientMaxAbs': max(finite_max_abs) if finite_max_abs else None,\n"
        "                })\n"
        "                del gradients\n"
        "            diagnostic = {\n"
        "                'schemaVersion': 1,\n"
        "                'valid': True,\n"
        "                'mode': 'zero-step-unscaled-component-autograd',\n"
        "                'optimizerSteps': 0,\n"
        "                'parameterTensorCount': len(named_params),\n"
        "                'parameterNames': [name for name, _ in named_params],\n"
        "                'components': component_receipts,\n"
        "            }\n"
        "            with open(diagnostic_path, 'w', encoding='utf-8') as stream:\n"
        "                stream.write(__import__('json').dumps(diagnostic, sort_keys=True) + '\\n')\n"
        "            raise RuntimeError('DENTALSCULPTOR_E12_COMPONENT_DIAGNOSTIC_COMPLETE_ZERO_STEP')\n"
        "            \n"
        "        return terms, {}"
    )
    if source.count(anchor) != 1:
        raise ValueError("Pinned E12 return boundary changed; refusing diagnostic patch")
    return source.replace(anchor, replacement)


def e12_controlled_scale_zero_step_source(source: str, log_scale: int = 12) -> str:
    """Run normal inflat_all backward at one sealed scale, then stop pre-step."""
    if log_scale != 12:
        raise ValueError("E12 controlled-scale probe is sealed to log_scale 12")
    patched = e12_initial_log_scale_source(source, log_scale=log_scale)
    gradient_anchor = "        ## gradient clip\n        if self.grad_clip is not None:"
    gradient_replacement = (
        "        ## DentalSculptor E12 controlled-scale zero-step receipt\n"
        "        controlled_receipt_path = os.environ.get('DENTALSCULPTOR_E12_CONTROLLED_SCALE_RECEIPT')\n"
        "        if controlled_receipt_path:\n"
        "            named_params = sum([[(model_name, name, p) for name, p in model.named_parameters() if p.requires_grad] for model_name, model in self.models.items()], [])\n"
        "            missing = [f'{model_name}.{name}' for model_name, name, p in named_params if p.grad is None]\n"
        "            nonfinite = [f'{model_name}.{name}' for model_name, name, p in named_params if p.grad is not None and not p.grad.isfinite().all()]\n"
        "            all_zero = [f'{model_name}.{name}' for model_name, name, p in named_params if p.grad is not None and p.grad.isfinite().all() and not bool(torch.count_nonzero(p.grad).item())]\n"
        "            finite_max_abs = [float(p.grad.detach().abs().amax().item()) for _, _, p in named_params if p.grad is not None and p.grad.isfinite().all()]\n"
        "            finite_nonzero_min_abs = [float(p.grad.detach().abs()[p.grad.detach() != 0].amin().item()) for _, _, p in named_params if p.grad is not None and p.grad.isfinite().all() and bool(torch.count_nonzero(p.grad).item())]\n"
        "            receipt = {\n"
        "                'schemaVersion': 1, 'valid': True, 'optimizerSteps': 0,\n"
        "                'mode': 'normal-inflat-all-backward-controlled-scale',\n"
        "                'logScale': float(self.log_scale), 'lossScale': float(2 ** self.log_scale),\n"
        "                'parameterTensorCount': len(named_params),\n"
        "                'missingGradientCount': len(missing), 'missingGradientNames': missing[:32],\n"
        "                'nonfiniteGradientCount': len(nonfinite), 'nonfiniteGradientNames': nonfinite[:32],\n"
        "                'allZeroGradientCount': len(all_zero), 'allZeroGradientNames': all_zero[:32],\n"
        "                'finiteGradientMaxAbsScaled': max(finite_max_abs) if finite_max_abs else None,\n"
        "                'finiteNonzeroGradientMinAbsScaled': min(finite_nonzero_min_abs) if finite_nonzero_min_abs else None,\n"
        "            }\n"
        "            with open(controlled_receipt_path, 'w', encoding='utf-8') as stream:\n"
        "                stream.write(__import__('json').dumps(receipt, sort_keys=True) + '\\n')\n"
        "            raise RuntimeError('DENTALSCULPTOR_E12_CONTROLLED_SCALE_COMPLETE_ZERO_STEP')\n"
        "        ## gradient clip\n"
        "        if self.grad_clip is not None:"
    )
    if patched.count(gradient_anchor) != 1:
        raise ValueError("Pinned BasicTrainer gradient boundary changed; refusing E12 scale patch")
    return patched.replace(gradient_anchor, gradient_replacement)


def e10_post_update_probe_trainer_source(source: str) -> str:
    """Add one read-only loss probe after the sole G1 optimizer update."""
    original = (
        "        ## adjust learning rate\n"
        "        if self.lr_scheduler_config is not None:"
    )
    replacement = (
        "        ## DentalSculptor read-only post-update probe (no backward or optimizer step)\n"
        "        if os.environ.get('DENTALSCULPTOR_E10_POST_UPDATE_PROBE') == '1':\n"
        "            if len(data_list) != 1:\n"
        "                raise RuntimeError('E10 G1 post-update probe requires one microbatch')\n"
        "            self.dentalsculptor_receipt_phase = 'post_update_probe'\n"
        "            with torch.no_grad():\n"
        "                with amp_context():\n"
        "                    self.training_losses(**data_list[0])\n"
        "            self.dentalsculptor_receipt_phase = 'pre_update'\n"
        "        ## adjust learning rate\n"
        "        if self.lr_scheduler_config is not None:"
    )
    if source.count(original) != 1:
        raise ValueError("Pinned optimizer boundary changed; refusing E10 probe patch")
    return source.replace(original, replacement)


@app.function(
    image=training_image,
    volumes={"/checkpoints": checkpoint_volume},
    cpu=2,
    memory=8192,
    timeout=10 * 60,
)
def diagnose_e10_training_route(
    run_name: str = "stage1-e10-route-canary-v2",
) -> dict:
    """Prove worker persistence and identify the effective E10 loss method without training."""
    import os
    import subprocess

    if run_name != "stage1-e10-route-canary-v2":
        raise ValueError("E10 route canary name is sealed")
    root = Path(f"/checkpoints/{run_name}")
    evidence_path = root / "route-evidence.json"
    if evidence_path.is_file():
        return json.loads(evidence_path.read_text(encoding="utf-8"))
    if root.exists():
        raise FileExistsError("Partial E10 route canary exists")
    root.mkdir(parents=True, exist_ok=False)

    worker_script = root / "worker_canary.py"
    child_receipt = root / "distributed-child-receipt.json"
    worker_script.write_text(
        "import hashlib, json, os\n"
        "from pathlib import Path\n"
        "target = Path(os.environ['DENTALSCULPTOR_ROUTE_RECEIPT'])\n"
        "payload = {'rank': int(os.environ.get('RANK', '-1')), "
        "'localRank': int(os.environ.get('LOCAL_RANK', '-1')), "
        "'worldSize': int(os.environ.get('WORLD_SIZE', '-1')), "
        "'pid': os.getpid(), 'sentinel': 'e10-route-canary-v2'}\n"
        "target.write_text(json.dumps(payload, sort_keys=True) + '\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["DENTALSCULPTOR_ROUTE_RECEIPT"] = str(child_receipt)
    worker = subprocess.run(
        ["python", "-m", "torch.distributed.run", "--standalone", "--nproc_per_node=1", str(worker_script)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
    )
    if worker.returncode or not child_receipt.is_file():
        checkpoint_volume.commit()
        raise RuntimeError(f"E10 distributed persistence canary failed: {worker.stdout}")
    child = json.loads(child_receipt.read_text(encoding="utf-8"))
    if child.get("rank") != 0 or child.get("worldSize") != 1:
        raise RuntimeError(f"Unexpected distributed receipt: {child}")

    trellis_root = Path(TRELLIS2_PATH)
    definitions = []
    for path in sorted((trellis_root / "trellis2/trainers").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "ImageConditionedSparseFlowMatchingCFGTrainer" in source or "def training_losses" in source:
            definitions.append({
                "path": str(path.relative_to(trellis_root)),
                "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                "definesConfiguredTrainer": "class ImageConditionedSparseFlowMatchingCFGTrainer" in source,
                "trainingLossDefinitions": source.count("def training_losses"),
                "hasAxialReceiptHook": "DENTALSCULPTOR_E10_OBJECTIVE_RECEIPT" in source,
            })
    flow_path = trellis_root / "trellis2/trainers/flow_matching/flow_matching.py"
    sparse_path = trellis_root / "trellis2/trainers/flow_matching/sparse_flow_matching.py"
    original = flow_path.read_text(encoding="utf-8")
    sparse_original = sparse_path.read_text(encoding="utf-8")
    patched = e10_teacher_init_flow_source(original)
    sparse_patched = e10_axial_sparse_flow_source(sparse_original)
    patch_contract = {
        "target": str(flow_path.relative_to(trellis_root)),
        "originalSha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
        "patchedSha256": hashlib.sha256(patched.encode("utf-8")).hexdigest(),
        "changed": patched != original,
        "sparseTarget": str(sparse_path.relative_to(trellis_root)),
        "sparseOriginalSha256": hashlib.sha256(sparse_original.encode("utf-8")).hexdigest(),
        "sparsePatchedSha256": hashlib.sha256(sparse_patched.encode("utf-8")).hexdigest(),
        "sparseChanged": sparse_patched != sparse_original,
        "receiptHooks": sparse_patched.count("DENTALSCULPTOR_E10_OBJECTIVE_RECEIPT"),
        "effectiveOverridePatched": "class SparseFlowMatchingTrainer" in sparse_patched,
    }
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E10-route-and-persistence-canary",
        "runName": run_name,
        "distributedChildReceipt": child,
        "distributedChildReceiptSha256": hashlib.sha256(child_receipt.read_bytes()).hexdigest(),
        "patchContract": patch_contract,
        "trainerDefinitions": definitions,
        "optimizerSteps": 0,
        "gpuRequired": False,
        "g1Authorized": bool(patch_contract["changed"] and patch_contract["sparseChanged"] and patch_contract["receiptHooks"] == 1 and patch_contract["effectiveOverridePatched"]),
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=trellis_gpu_image,
    volumes={"/datasets": dataset_volume},
    cpu=8,
    memory=32768,
    timeout=30 * 60,
)
def audit_e14_g2_alignment_and_crown_masks(
    dataset_name: str = "toothfairy-stage1-v1",
    audit_name: str = "stage1-e14-g2-alignment-mask-audit-v2",
) -> dict:
    """Audit cached supervision alignment and crown-mask coverage without training."""
    import numpy as np
    import torch
    from collections import Counter, defaultdict

    if dataset_name != "toothfairy-stage1-v1" or audit_name != "stage1-e14-g2-alignment-mask-audit-v2":
        raise ValueError("E14 G2 alignment/mask audit is sealed")
    root = Path(f"/datasets/{dataset_name}")
    cache_path = root / "stage1-e14-g2-frozen-base-support-v1/cache-evidence.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if not (
        cache.get("valid") is True
        and cache.get("caseCount") == 76
        and cache.get("trainCaseCount") == 64
        and cache.get("validationCaseCount") == 12
    ):
        raise ValueError("E14 alignment audit requires the sealed 76-case base cache")
    audit_root = root / audit_name
    evidence_path = audit_root / "audit-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True and existing.get("caseCount") == 76:
            return {**existing, "resumed": True}
        raise ValueError("Existing E14 alignment/mask audit is invalid")
    if audit_root.exists():
        raise FileExistsError("Partial E14 alignment/mask audit exists; inspect before versioning")
    audit_root.mkdir(parents=True, exist_ok=False)

    def dense(coords: np.ndarray) -> torch.Tensor:
        values = np.asarray(coords, dtype=np.int64)
        output = torch.zeros((1, 1, 32, 32, 32), dtype=torch.bool)
        output[0, 0, values[:, 0], values[:, 1], values[:, 2]] = True
        return output

    cases = []
    for row in sorted(cache["cases"], key=lambda item: item["id"]):
        artifact = root / row["artifact"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != row["artifactSha256"]:
            raise ValueError(f"E14 audit artifact hash drift: {row['id']}")
        packed = np.load(artifact)
        base_coords = np.asarray(packed["base_coords"], dtype=np.int16)
        reference_coords = np.asarray(packed["reference_coords"], dtype=np.int16)
        alignment = align_sparse_support_integer_translation(
            reference_coords, base_coords, resolution=32, maximum_shift=6
        )
        base = dense(base_coords)
        weights, _ = build_crown_transition_weights_from_occupancy(base)
        crown_mask = weights[0, 0].numpy() > 0
        root_mask = ~crown_mask
        reference = dense(reference_coords)[0, 0].numpy()
        base_binary = base[0, 0].numpy()
        inverse_shift = [-int(value) for value in alignment["bestTranslationXYZ"]]
        aligned_reference_coords = reference_coords + np.asarray(inverse_shift, dtype=np.int16)
        in_bounds = np.all((aligned_reference_coords >= 0) & (aligned_reference_coords < 32), axis=1)
        aligned_reference = dense(aligned_reference_coords[in_bounds])[0, 0].numpy()
        reference_count = max(int(reference.sum()), 1)
        aligned_reference_count = max(int(aligned_reference.sum()), 1)
        cases.append({
            "id": row["id"], "groupId": row["groupId"], "split": row["split"],
            "toothFamily": row["toothFamily"], "fdiNumber": row["fdiNumber"],
            "baseCoordsSha256": row["baseCoordsSha256"],
            "referenceCoordsSha256": row["referenceCoordsSha256"],
            "bestBaseToReferenceTranslationXYZ": alignment["bestTranslationXYZ"],
            "referenceToBaseTranslationXYZ": inverse_shift,
            "translationMagnitudeVoxels": alignment["bestTranslationMagnitudeVoxels"],
            "rawGlobalVoxelIoU": alignment["raw"]["global"]["voxelIoU"],
            "alignedGlobalVoxelIoU": alignment["aligned"]["global"]["voxelIoU"],
            "globalIoUErrorFractionClosed": alignment["globalIoUErrorFractionClosed"],
            "rawCrownVoxelIoU": alignment["raw"]["bands"]["crownProxy"]["voxelIoU"],
            "alignedCrownVoxelIoU": alignment["aligned"]["bands"]["crownProxy"]["voxelIoU"],
            "crownIoUErrorFractionClosed": alignment["crownIoUErrorFractionClosed"],
            "rawReferenceFractionInsideCrownMask": float((reference & crown_mask).sum() / reference_count),
            "alignedReferenceFractionInsideCrownMask": float((aligned_reference & crown_mask).sum() / aligned_reference_count),
            "rawReferenceFractionInsideRootMask": float((reference & root_mask).sum() / reference_count),
            "alignedReferenceFractionInsideRootMask": float((aligned_reference & root_mask).sum() / aligned_reference_count),
            "baseFractionInsideCrownMask": float((base_binary & crown_mask).sum() / max(int(base_binary.sum()), 1)),
        })

    by_family = defaultdict(list)
    for case in cases:
        by_family[case["toothFamily"]].append(case)
    metric_names = (
        "translationMagnitudeVoxels", "globalIoUErrorFractionClosed", "crownIoUErrorFractionClosed",
        "rawGlobalVoxelIoU", "alignedGlobalVoxelIoU", "rawCrownVoxelIoU", "alignedCrownVoxelIoU",
        "rawReferenceFractionInsideCrownMask", "alignedReferenceFractionInsideCrownMask",
    )
    family_summary = {
        family: {name: float(np.median([case[name] for case in rows])) for name in metric_names}
        for family, rows in sorted(by_family.items())
    }
    median_crown_closure = float(np.median([case["crownIoUErrorFractionClosed"] for case in cases]))
    median_shift = float(np.median([case["translationMagnitudeVoxels"] for case in cases]))
    cases_nonzero = sum(case["translationMagnitudeVoxels"] > 0 for case in cases)
    median_global_closure = float(np.median([case["globalIoUErrorFractionClosed"] for case in cases]))
    # A non-zero translation is not evidence that registration dominates. It
    # must close a material fraction of the measured occupancy error.
    alignment_dominant = bool(median_crown_closure >= 0.25 or median_global_closure >= 0.25)
    passed = bool(
        len(cases) == 76
        and Counter(case["split"] for case in cases) == Counter({"train": 64, "validation": 12})
        and len({case["id"] for case in cases}) == 76
        and all(np.isfinite(case[name]) for case in cases for name in metric_names)
    )
    evidence = {
        "schemaVersion": 1, "valid": passed,
        "stage": "E14-G2-alignment-and-crown-mask-audit-v1", "optimizerSteps": 0,
        "caseCount": len(cases), "trainCaseCount": 64, "validationCaseCount": 12,
        "cacheEvidenceSha256": hashlib.sha256(cache_path.read_bytes()).hexdigest(),
        "maximumShiftVoxelsPerAxis": 6, "casesWithNonzeroTranslation": cases_nonzero,
        "medianTranslationMagnitudeVoxels": median_shift,
        "medianGlobalIoUErrorFractionClosed": median_global_closure,
        "medianCrownIoUErrorFractionClosed": median_crown_closure,
        "alignmentDominant": alignment_dominant,
        "familySummary": family_summary, "cases": cases,
        "nextTrainingDesignAuthorized": passed,
        "requiredNextDesign": (
            "align-reference-to-frozen-base-before-supervision-and-use-family-specific-heads"
            if alignment_dominant else "use-family-specific-heads-with-base-trust-region"
        ),
        "clinicalClaimPermitted": False, "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    if not passed:
        raise RuntimeError("E14 G2 alignment/mask audit failed its evidence gate")
    return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    gpu="T4",
    cpu=8,
    memory=32768,
    timeout=30 * 60,
)
def run_e14_g2b_family_trust_region_gate(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2b-family-trust-region-v1",
) -> dict:
    """Run one isolated optimizer step per family before a response screen."""
    import numpy as np
    import torch
    import torch.nn.functional as F

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2b-family-trust-region-v1":
        raise ValueError("E14 G2B family trust-region gate is sealed")
    dataset_root = Path(f"/datasets/{dataset_name}")
    cache_path = dataset_root / "stage1-e14-g2-frozen-base-support-v1/cache-evidence.json"
    audit_path = dataset_root / "stage1-e14-g2-alignment-mask-audit-v2/audit-evidence.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if not (
        cache.get("valid") is True and cache.get("caseCount") == 76
        and audit.get("valid") is True and audit.get("optimizerSteps") == 0
        and audit.get("alignmentDominant") is False
        and audit.get("requiredNextDesign") == "use-family-specific-heads-with-base-trust-region"
    ):
        raise ValueError("E14 G2B requires the sealed cache and corrected v2 audit")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "g2b-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Existing E14 G2B evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E14 G2B output exists; inspect before versioning")
    run_root.mkdir(parents=True, exist_ok=False)

    torch.manual_seed(20260923)
    torch.cuda.manual_seed_all(20260923)
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    family_order = ("incisor", "canine", "premolar", "molar")

    class FamilyHead(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.net = torch.nn.Sequential(
                torch.nn.Conv3d(4, 12, 3, padding=1), torch.nn.SiLU(),
                torch.nn.Conv3d(12, 12, 3, padding=1), torch.nn.SiLU(),
                torch.nn.Conv3d(12, 1, 1),
            )
            torch.nn.init.zeros_(self.net[-1].weight)
            torch.nn.init.zeros_(self.net[-1].bias)

        def forward(self, base_logits: torch.Tensor) -> torch.Tensor:
            batch, _, depth, height, width = base_logits.shape
            axes = [torch.linspace(-1, 1, size, device=base_logits.device, dtype=base_logits.dtype)
                    for size in (depth, height, width)]
            grid = torch.stack(torch.meshgrid(*axes, indexing="ij"), dim=0).expand(batch, -1, -1, -1, -1)
            return 1.0 * torch.tanh(self.net(torch.cat((torch.sigmoid(base_logits), grid), dim=1)))

    class FamilyRefiner(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.heads = torch.nn.ModuleList([FamilyHead() for _ in family_order])

        def forward(self, base_logits: torch.Tensor, family_index: int) -> torch.Tensor:
            return self.heads[family_index](base_logits)

    def dense(coords: np.ndarray) -> torch.Tensor:
        values = np.asarray(coords, dtype=np.int64)
        output = torch.zeros((1, 1, 32, 32, 32), dtype=torch.bool, device=device)
        output[0, 0, values[:, 0], values[:, 1], values[:, 2]] = True
        return output

    def load_case(row: dict) -> dict:
        artifact = dataset_root / row["artifact"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != row["artifactSha256"]:
            raise ValueError(f"E14 G2B artifact hash drift: {row['id']}")
        packed = np.load(artifact)
        return {"receipt": row, "base": dense(packed["base_coords"]), "reference": dense(packed["reference_coords"])}

    selected = {}
    for family in family_order:
        rows = sorted(
            (row for row in cache["cases"] if row["split"] == "train" and row["toothFamily"] == family),
            key=lambda row: row["id"],
        )
        if not rows:
            raise RuntimeError(f"No E14 G2B training case for {family}")
        selected[family] = load_case(rows[0])

    model = FamilyRefiner().to(device)
    receipts = []
    for family_index, family in enumerate(family_order):
        case = selected[family]
        base = case["base"]
        target = case["reference"].float()
        weights, _ = build_crown_transition_weights_from_occupancy(base)
        weights = weights.to(device)
        base_logits = torch.where(base, torch.tensor(0.25, device=device), torch.tensor(-0.25, device=device))
        supervised = weights > 0
        agreement = supervised & (base == case["reference"])
        disagreement = supervised & (base != case["reference"])
        if not bool(agreement.any()) or not bool(disagreement.any()):
            raise RuntimeError(f"E14 G2B requires agreement and disagreement voxels for {family}")
        before = {name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()}
        optimizer = torch.optim.AdamW(model.heads[family_index].parameters(), lr=0.0001, weight_decay=0.0)
        residual = model(base_logits, family_index)
        candidate = compose_crown_residual_logits(base_logits, residual, weights)
        correction = F.binary_cross_entropy_with_logits(candidate[disagreement], target[disagreement])
        preservation = F.mse_loss(candidate[agreement], base_logits[agreement])
        residual_penalty = torch.mean((residual[supervised] * weights[supervised]) ** 2)
        loss = correction + 8.0 * preservation + 0.25 * residual_penalty
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        gradients_finite = all(
            parameter.grad is not None and torch.isfinite(parameter.grad).all()
            for parameter in model.heads[family_index].parameters()
        )
        if not bool(torch.isfinite(loss)) or not gradients_finite:
            raise RuntimeError(f"E14 G2B finite-gradient gate failed for {family}")
        optimizer.step()
        changed = [
            name for name, tensor in model.state_dict().items()
            if not torch.equal(before[name], tensor.detach().cpu())
        ]
        expected_prefix = f"heads.{family_index}."
        isolated = bool(changed) and all(name.startswith(expected_prefix) for name in changed)
        with torch.no_grad():
            post_residual = model(base_logits, family_index)
            post_candidate = compose_crown_residual_logits(base_logits, post_residual, weights)
            repeated = compose_crown_residual_logits(base_logits, model(base_logits, family_index), weights)
        root_mask = weights == 0
        root_identical = torch.equal(post_candidate[root_mask], base_logits[root_mask])
        repeat_exact = torch.equal(post_candidate, repeated)
        receipts.append({
            "family": family, "caseId": case["receipt"]["id"], "optimizerSteps": 1,
            "loss": float(loss.detach().item()), "correctionLoss": float(correction.detach().item()),
            "preservationLoss": float(preservation.detach().item()),
            "residualPenalty": float(residual_penalty.detach().item()),
            "agreementVoxelCount": int(agreement.sum().item()),
            "disagreementVoxelCount": int(disagreement.sum().item()),
            "gradientsFinite": gradients_finite, "changedParameterTensors": changed,
            "onlySelectedFamilyHeadChanged": isolated,
            "rootLogitsByteIdentical": root_identical, "rawDecodeExactRepeat": repeat_exact,
        })

    checkpoint_path = run_root / "family-refiner-four-step.pt"
    torch.save({"state_dict": model.state_dict(), "familyOrder": family_order, "optimizerSteps": 4}, checkpoint_path)
    verification = FamilyRefiner().to(device)
    strict = verification.load_state_dict(torch.load(checkpoint_path, map_location=device, weights_only=True)["state_dict"], strict=True)
    strict_reload = not strict.missing_keys and not strict.unexpected_keys
    passed = bool(
        len(receipts) == 4 and sum(row["optimizerSteps"] for row in receipts) == 4
        and all(row["gradientsFinite"] and row["onlySelectedFamilyHeadChanged"] for row in receipts)
        and all(row["rootLogitsByteIdentical"] and row["rawDecodeExactRepeat"] for row in receipts)
        and strict_reload
    )
    evidence = {
        "schemaVersion": 1, "valid": passed,
        "stage": "E14-G2B-family-specific-trust-region-integration-v1",
        "optimizerSteps": 4, "optimizerStepsPerFamily": 1, "learningRate": 0.0001,
        "trustRegionWeight": 8.0, "residualPenaltyWeight": 0.25,
        "cacheEvidenceSha256": hashlib.sha256(cache_path.read_bytes()).hexdigest(),
        "auditEvidenceSha256": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
        "receipts": receipts, "checkpointReloadedStrict": strict_reload,
        "checkpointArtifact": str(checkpoint_path),
        "checkpointSha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "g2cResponseAuthorized": passed, "g3Authorized": False,
        "clinicalClaimPermitted": False, "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    if not passed:
        raise RuntimeError("E14 G2B family trust-region integration gate failed")
    return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    gpu="T4", cpu=8, memory=32768, timeout=45 * 60,
)
def run_e14_g2c_family_response_screen(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2c-family-response-v1",
) -> dict:
    """Run a sealed 40-step, equally sampled, family-specific response screen."""
    import numpy as np
    import torch
    import torch.nn.functional as F
    from collections import defaultdict
    from scipy import ndimage
    from scipy.spatial import cKDTree

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2c-family-response-v1":
        raise ValueError("E14 G2C response screen is sealed")
    dataset_root = Path(f"/datasets/{dataset_name}")
    cache_path = dataset_root / "stage1-e14-g2-frozen-base-support-v1/cache-evidence.json"
    g2b_path = Path("/checkpoints/stage1-e14-g2b-family-trust-region-v1/g2b-evidence.json")
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    g2b = json.loads(g2b_path.read_text(encoding="utf-8"))
    if not (cache.get("valid") is True and g2b.get("valid") is True
            and g2b.get("g2cResponseAuthorized") is True and g2b.get("optimizerSteps") == 4):
        raise ValueError("E14 G2C requires the sealed passing G2B gate")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "g2c-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Existing E14 G2C evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E14 G2C output exists; inspect before versioning")
    run_root.mkdir(parents=True, exist_ok=False)
    torch.manual_seed(20260924); torch.cuda.manual_seed_all(20260924)
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    family_order = ("incisor", "canine", "premolar", "molar")

    class FamilyHead(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.net = torch.nn.Sequential(
                torch.nn.Conv3d(4, 12, 3, padding=1), torch.nn.SiLU(),
                torch.nn.Conv3d(12, 12, 3, padding=1), torch.nn.SiLU(),
                torch.nn.Conv3d(12, 1, 1),
            )
        def forward(self, base_logits: torch.Tensor) -> torch.Tensor:
            batch, _, depth, height, width = base_logits.shape
            axes = [torch.linspace(-1, 1, size, device=base_logits.device, dtype=base_logits.dtype)
                    for size in (depth, height, width)]
            grid = torch.stack(torch.meshgrid(*axes, indexing="ij"), dim=0).expand(batch, -1, -1, -1, -1)
            return torch.tanh(self.net(torch.cat((torch.sigmoid(base_logits), grid), dim=1)))
    class FamilyRefiner(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__(); self.heads = torch.nn.ModuleList([FamilyHead() for _ in family_order])
        def forward(self, base_logits: torch.Tensor, family_index: int) -> torch.Tensor:
            return self.heads[family_index](base_logits)

    def dense(coords: np.ndarray) -> torch.Tensor:
        values = np.asarray(coords, dtype=np.int64)
        output = torch.zeros((1, 1, 32, 32, 32), dtype=torch.bool, device=device)
        output[0, 0, values[:, 0], values[:, 1], values[:, 2]] = True
        return output
    def load_case(row: dict) -> dict:
        artifact = dataset_root / row["artifact"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != row["artifactSha256"]:
            raise ValueError(f"E14 G2C artifact hash drift: {row['id']}")
        packed = np.load(artifact)
        return {"receipt": row, "base": dense(packed["base_coords"]), "reference": dense(packed["reference_coords"])}
    training = defaultdict(list); validation = []
    for row in cache["cases"]:
        case = load_case(row)
        (training[row["toothFamily"]] if row["split"] == "train" else validation).append(case)
    if len(validation) != 12 or any(not training[family] for family in family_order):
        raise RuntimeError("E14 G2C cohort drift")

    model = FamilyRefiner().to(device)
    checkpoint_path = Path(g2b["checkpointArtifact"])
    if hashlib.sha256(checkpoint_path.read_bytes()).hexdigest() != g2b["checkpointSha256"]:
        raise ValueError("E14 G2B checkpoint hash drift")
    strict = model.load_state_dict(torch.load(checkpoint_path, map_location=device, weights_only=True)["state_dict"], strict=True)
    if strict.missing_keys or strict.unexpected_keys:
        raise RuntimeError("E14 G2C could not strict-load G2B")
    optimizers = [torch.optim.AdamW(head.parameters(), lr=0.0001, weight_decay=0.0) for head in model.heads]

    def logits_weights(case: dict):
        weights, _ = build_crown_transition_weights_from_occupancy(case["base"])
        logits = torch.where(case["base"], torch.tensor(0.25, device=device), torch.tensor(-0.25, device=device))
        return logits, weights.to(device)
    def chamfer(reference, prediction, region):
        structure = np.ones((3, 3, 3), dtype=bool)
        rs = reference & ~ndimage.binary_erosion(reference, structure=structure, border_value=0)
        ps = prediction & ~ndimage.binary_erosion(prediction, structure=structure, border_value=0)
        rp, pp = np.argwhere(rs & region), np.argwhere(ps & region)
        if not len(rp) or not len(pp): return float("inf")
        rt, pt = cKDTree(rp), cKDTree(pp)
        return float((pt.query(rp)[0].mean() + rt.query(pp)[0].mean()) / 2)
    def topology(binary):
        labels, count = ndimage.label(binary, structure=ndimage.generate_binary_structure(3, 1))
        sizes = np.bincount(labels.ravel())[1:]; total = int(binary.sum())
        return int(count), float(sizes.max() / total) if total and len(sizes) else 0.0
    def evaluate(step: int) -> dict:
        model.eval(); rows = []
        with torch.no_grad():
            for case in validation:
                family = case["receipt"]["toothFamily"]; index = family_order.index(family)
                base_logits, weights = logits_weights(case)
                candidate = compose_crown_residual_logits(base_logits, model(base_logits, index), weights)
                repeated = compose_crown_residual_logits(base_logits, model(base_logits, index), weights)
                base = case["base"][0, 0].cpu().numpy(); ref = case["reference"][0, 0].cpu().numpy()
                pred = (candidate[0, 0] >= 0).cpu().numpy(); region = (weights[0, 0] > 0).cpu().numpy()
                bc, cc = chamfer(ref, base, region), chamfer(ref, pred, region)
                bt, ct = topology(base), topology(pred)
                rows.append({"id": case["receipt"]["id"], "toothFamily": family,
                    "baseCrownChamferVoxels": bc, "candidateCrownChamferVoxels": cc,
                    "crownChamferRelativeImprovement": (bc-cc)/max(bc,1e-8),
                    "rootLogitsByteIdentical": torch.equal(candidate[weights == 0], base_logits[weights == 0]),
                    "rawDecodeExactRepeat": torch.equal(candidate, repeated),
                    "topologyPassed": ct[0] <= bt[0] and ct[1] >= bt[1]-0.01})
        families = {family: float(np.median([r["crownChamferRelativeImprovement"] for r in rows if r["toothFamily"] == family])) for family in family_order}
        return {"step": step, "cases": rows,
            "medianCrownChamferRelativeImprovement": float(np.median([r["crownChamferRelativeImprovement"] for r in rows])),
            "familyMedianCrownChamferRelativeImprovement": families,
            "allRootLogitsByteIdentical": all(r["rootLogitsByteIdentical"] for r in rows),
            "allRawDecodesExactRepeat": all(r["rawDecodeExactRepeat"] for r in rows),
            "allTopologyPassed": all(r["topologyPassed"] for r in rows)}

    evaluations = [evaluate(0)]; losses = []
    for step in range(1, 41):
        index = (step - 1) % 4; family = family_order[index]
        case = training[family][((step - 1) // 4) % len(training[family])]
        base_logits, weights = logits_weights(case); target = case["reference"].float()
        supervised = weights > 0; agreement = supervised & (case["base"] == case["reference"])
        disagreement = supervised & (case["base"] != case["reference"])
        residual = model(base_logits, index); candidate = compose_crown_residual_logits(base_logits, residual, weights)
        correction = F.binary_cross_entropy_with_logits(candidate[disagreement], target[disagreement])
        preservation = F.mse_loss(candidate[agreement], base_logits[agreement])
        penalty = torch.mean((residual[supervised] * weights[supervised]) ** 2)
        loss = correction + 8.0*preservation + 0.25*penalty
        optimizers[index].zero_grad(set_to_none=True); loss.backward()
        if not bool(torch.isfinite(loss)) or not all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.heads[index].parameters()):
            raise RuntimeError(f"E14 G2C finite gate failed at step {step}")
        optimizers[index].step(); losses.append({"step": step, "family": family, "loss": float(loss.detach())})
        if step in (10, 20, 40): evaluations.append(evaluate(step))
    final = evaluations[-1]; fm = final["familyMedianCrownChamferRelativeImprovement"]
    passed = bool(final["medianCrownChamferRelativeImprovement"] > 0 and fm["premolar"] > 0 and fm["molar"] > 0
                  and all(v >= -0.005 for v in fm.values()) and final["allRootLogitsByteIdentical"]
                  and final["allRawDecodesExactRepeat"] and final["allTopologyPassed"])
    candidate_path = run_root / "family-refiner-step-44.pt"
    torch.save({"state_dict": model.state_dict(), "familyOrder": family_order, "optimizerSteps": 44}, candidate_path)
    verification = FamilyRefiner().to(device)
    reload_result = verification.load_state_dict(torch.load(candidate_path, map_location=device, weights_only=True)["state_dict"], strict=True)
    strict_reload = not reload_result.missing_keys and not reload_result.unexpected_keys; passed = passed and strict_reload
    evidence = {"schemaVersion": 1, "valid": True, "stage": "E14-G2C-family-response-v1",
        "optimizerSteps": 40, "cumulativeOptimizerSteps": 44, "stepsPerFamily": 10,
        "evaluationSteps": [e["step"] for e in evaluations], "losses": losses, "evaluations": evaluations,
        "checkpointReloadedStrict": strict_reload, "checkpointArtifact": str(candidate_path),
        "checkpointSha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        "summaryPassed": passed, "g3Authorized": passed,
        "clinicalClaimPermitted": False, "productionMutationPermitted": False}
    evidence_path.write_text(json.dumps(evidence, indent=2)+"\n", encoding="utf-8"); checkpoint_volume.commit()
    return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    cpu=8, memory=32768, timeout=30 * 60,
)
def diagnose_e14_g2d_response_margin(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2d-response-margin-v1",
) -> dict:
    """Measure learned residual direction and counterfactual scale response without training."""
    import numpy as np
    import torch
    from collections import defaultdict
    from scipy import ndimage
    from scipy.spatial import cKDTree

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2d-response-margin-v1":
        raise ValueError("E14 G2D response-margin diagnostic is sealed")
    dataset_root = Path(f"/datasets/{dataset_name}")
    cache_path = dataset_root / "stage1-e14-g2-frozen-base-support-v1/cache-evidence.json"
    g2c_path = Path("/checkpoints/stage1-e14-g2c-family-response-v1/g2c-evidence.json")
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    g2c = json.loads(g2c_path.read_text(encoding="utf-8"))
    if not (cache.get("valid") is True and g2c.get("valid") is True
            and g2c.get("optimizerSteps") == 40 and g2c.get("summaryPassed") is False):
        raise ValueError("E14 G2D requires the sealed rejected G2C response")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "g2d-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True: return {**existing, "resumed": True}
        raise ValueError("Existing E14 G2D evidence is invalid")
    if run_root.exists(): raise FileExistsError("Partial E14 G2D output exists")
    run_root.mkdir(parents=True, exist_ok=False)
    torch.manual_seed(20260925); torch.use_deterministic_algorithms(True)
    family_order = ("incisor", "canine", "premolar", "molar")

    class FamilyHead(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.net = torch.nn.Sequential(
                torch.nn.Conv3d(4,12,3,padding=1), torch.nn.SiLU(),
                torch.nn.Conv3d(12,12,3,padding=1), torch.nn.SiLU(), torch.nn.Conv3d(12,1,1))
        def forward(self, logits):
            b,_,d,h,w=logits.shape
            axes=[torch.linspace(-1,1,s,dtype=logits.dtype) for s in (d,h,w)]
            grid=torch.stack(torch.meshgrid(*axes,indexing="ij"),dim=0).expand(b,-1,-1,-1,-1)
            return torch.tanh(self.net(torch.cat((torch.sigmoid(logits),grid),dim=1)))
    class FamilyRefiner(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.heads=torch.nn.ModuleList([FamilyHead() for _ in family_order])
        def forward(self, logits, index): return self.heads[index](logits)

    def dense(coords):
        values=np.asarray(coords,dtype=np.int64); out=torch.zeros((1,1,32,32,32),dtype=torch.bool)
        out[0,0,values[:,0],values[:,1],values[:,2]]=True; return out
    validation=[]
    for row in cache["cases"]:
        if row["split"] != "validation": continue
        artifact=dataset_root/row["artifact"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest()!=row["artifactSha256"]: raise ValueError("G2D artifact drift")
        packed=np.load(artifact); validation.append({"receipt":row,"base":dense(packed["base_coords"]),"reference":dense(packed["reference_coords"])})
    if len(validation)!=12: raise RuntimeError("E14 G2D requires 12 validation cases")
    model=FamilyRefiner()
    checkpoint=Path(g2c["checkpointArtifact"])
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=g2c["checkpointSha256"]: raise ValueError("G2C checkpoint drift")
    strict=model.load_state_dict(torch.load(checkpoint,map_location="cpu",weights_only=True)["state_dict"],strict=True)
    if strict.missing_keys or strict.unexpected_keys: raise RuntimeError("G2D strict load failed")
    model.eval()

    def chamfer(reference,prediction,region):
        structure=np.ones((3,3,3),dtype=bool)
        rs=reference & ~ndimage.binary_erosion(reference,structure=structure,border_value=0)
        ps=prediction & ~ndimage.binary_erosion(prediction,structure=structure,border_value=0)
        rp,pp=np.argwhere(rs&region),np.argwhere(ps&region)
        if not len(rp) or not len(pp): return float("inf")
        rt,pt=cKDTree(rp),cKDTree(pp)
        return float((pt.query(rp)[0].mean()+rt.query(pp)[0].mean())/2)

    scales=(1.0,2.0,4.0,8.0,16.0); scale_rows=[]
    with torch.no_grad():
        cached=[]
        for case in validation:
            family=case["receipt"]["toothFamily"]; index=family_order.index(family)
            weights,_=build_crown_transition_weights_from_occupancy(case["base"])
            base_logits=torch.where(case["base"],torch.tensor(0.25),torch.tensor(-0.25))
            residual=model(base_logits,index); target=case["reference"]
            supervised=weights>0; disagreement=supervised & (case["base"]!=target)
            direction=torch.where(target,torch.tensor(1.0),torch.tensor(-1.0))
            directional=(residual[disagreement]*direction[disagreement])>0
            cached.append((case,family,base_logits,weights,residual,disagreement,float(directional.float().mean()),float(residual[supervised].abs().max()),float(residual[supervised].abs().median())))
        for scale in scales:
            cases=[]
            for case,family,base_logits,weights,residual,disagreement,directional,max_abs,median_abs in cached:
                candidate=compose_crown_residual_logits(base_logits,scale*residual,weights)
                base=case["base"][0,0].numpy(); ref=case["reference"][0,0].numpy(); pred=(candidate[0,0]>=0).numpy()
                region=(weights[0,0]>0).numpy(); bc=chamfer(ref,base,region); cc=chamfer(ref,pred,region)
                root_equal=torch.equal(candidate[weights==0],base_logits[weights==0])
                cases.append({"id":case["receipt"]["id"],"toothFamily":family,
                    "directionalAgreement":directional,"maximumAbsoluteResidual":max_abs,"medianAbsoluteResidual":median_abs,
                    "occupancyCrossingCount":int(np.count_nonzero(pred!=base)),
                    "crownChamferRelativeImprovement":(bc-cc)/max(bc,1e-8),"rootLogitsByteIdentical":root_equal})
            fm={f:float(np.median([r["crownChamferRelativeImprovement"] for r in cases if r["toothFamily"]==f])) for f in family_order}
            scale_rows.append({"scale":scale,"cases":cases,"familyMedianCrownChamferRelativeImprovement":fm,
                "medianCrownChamferRelativeImprovement":float(np.median([r["crownChamferRelativeImprovement"] for r in cases])),
                "medianDirectionalAgreement":float(np.median([r["directionalAgreement"] for r in cases])),
                "totalOccupancyCrossingCount":sum(r["occupancyCrossingCount"] for r in cases),
                "allRootLogitsByteIdentical":all(r["rootLogitsByteIdentical"] for r in cases)})
    eligible=[r for r in scale_rows if r["familyMedianCrownChamferRelativeImprovement"]["premolar"]>0
              and r["familyMedianCrownChamferRelativeImprovement"]["molar"]>0
              and all(v>=-0.005 for v in r["familyMedianCrownChamferRelativeImprovement"].values())
              and r["allRootLogitsByteIdentical"]]
    selected=min(eligible,key=lambda row:row["scale"]) if eligible else None
    evidence={"schemaVersion":1,"valid":True,"stage":"E14-G2D-response-margin-diagnostic-v1","optimizerSteps":0,
        "scales":list(scales),"scaleResults":scale_rows,"selectedScale":selected["scale"] if selected else None,
        "scaledCanaryAuthorized":selected is not None,"objectiveRedesignRequired":selected is None,
        "g3Authorized":False,"clinicalClaimPermitted":False,"productionMutationPermitted":False}
    evidence_path.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit(); return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    cpu=8, memory=32768, timeout=20 * 60,
)
def diagnose_e14_g2f_signed_margin_gain(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2f-signed-margin-gain-v1",
) -> dict:
    """Measure the minimum zero-update residual gain that changes crown geometry safely."""
    import numpy as np
    import torch
    from scipy import ndimage
    from scipy.spatial import cKDTree

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2f-signed-margin-gain-v1":
        raise ValueError("E14 G2F signed-margin gain diagnostic is sealed")
    dataset_root=Path(f"/datasets/{dataset_name}")
    cache_path=dataset_root/"stage1-e14-g2-frozen-base-support-v1/cache-evidence.json"
    g2e_path=Path("/checkpoints/stage1-e14-g2e-signed-margin-canary-v2/g2e-evidence.json")
    cache=json.loads(cache_path.read_text(encoding="utf-8")); g2e=json.loads(g2e_path.read_text(encoding="utf-8"))
    if not (cache.get("valid") is True and g2e.get("valid") is True
            and g2e.get("optimizerSteps") == 20 and g2e.get("g2fAuthorized") is False
            and all(row.get("rootLogitsByteIdentical") and row.get("rawDecodeExactRepeat") for row in g2e.get("receipts", []))):
        raise ValueError("E14 G2F requires sealed, safe but non-responsive G2E v2 evidence")
    run_root=Path(f"/checkpoints/{run_name}"); evidence_path=run_root/"g2f-evidence.json"
    if evidence_path.is_file():
        existing=json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True: return {**existing,"resumed":True}
        raise ValueError("Existing G2F evidence is invalid")
    if run_root.exists(): raise FileExistsError("Partial G2F output exists")
    run_root.mkdir(parents=True,exist_ok=False)
    torch.manual_seed(20260927); torch.use_deterministic_algorithms(True)
    family_order=("incisor","canine","premolar","molar")

    class FamilyHead(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.net=torch.nn.Sequential(torch.nn.Conv3d(4,12,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(12,12,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(12,1,1))
        def forward(self,logits):
            b,_,d,h,w=logits.shape; axes=[torch.linspace(-1,1,s,dtype=logits.dtype) for s in (d,h,w)]
            grid=torch.stack(torch.meshgrid(*axes,indexing="ij"),dim=0).expand(b,-1,-1,-1,-1)
            return torch.tanh(self.net(torch.cat((torch.sigmoid(logits),grid),dim=1)))
    class FamilyRefiner(torch.nn.Module):
        def __init__(self): super().__init__(); self.heads=torch.nn.ModuleList([FamilyHead() for _ in family_order])
        def forward(self,logits,index): return self.heads[index](logits)
    def dense(coords):
        values=np.asarray(coords,dtype=np.int64); out=torch.zeros((1,1,32,32,32),dtype=torch.bool)
        out[0,0,values[:,0],values[:,1],values[:,2]]=True; return out
    def chamfer(reference,prediction,region):
        structure=np.ones((3,3,3),dtype=bool)
        rs=reference & ~ndimage.binary_erosion(reference,structure=structure,border_value=0)
        ps=prediction & ~ndimage.binary_erosion(prediction,structure=structure,border_value=0)
        rp,pp=np.argwhere(rs&region),np.argwhere(ps&region)
        if not len(rp) or not len(pp): return float("inf")
        rt,pt=cKDTree(rp),cKDTree(pp)
        return float((pt.query(rp)[0].mean()+rt.query(pp)[0].mean())/2)

    validation=[]
    for row in cache["cases"]:
        if row["split"]!="validation": continue
        artifact=dataset_root/row["artifact"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest()!=row["artifactSha256"]: raise ValueError("G2F artifact drift")
        packed=np.load(artifact); validation.append({"receipt":row,"base":dense(packed["base_coords"]),"reference":dense(packed["reference_coords"])})
    if len(validation)!=12 or {row["receipt"]["toothFamily"] for row in validation}!=set(family_order):
        raise RuntimeError("E14 G2F requires the sealed balanced 12-case validation cohort")
    model=FamilyRefiner(); checkpoint=Path(g2e["checkpointArtifact"])
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=g2e["checkpointSha256"]: raise ValueError("G2E checkpoint drift")
    strict=model.load_state_dict(torch.load(checkpoint,map_location="cpu",weights_only=True)["state_dict"],strict=True)
    if strict.missing_keys or strict.unexpected_keys: raise RuntimeError("G2F strict load failed")
    model.eval(); cached=[]
    with torch.no_grad():
        for case in validation:
            family=case["receipt"]["toothFamily"]; index=family_order.index(family)
            weights,_=build_crown_transition_weights_from_occupancy(case["base"])
            base_logits=torch.where(case["base"],torch.tensor(0.25),torch.tensor(-0.25)); residual=model(base_logits,index)
            cached.append((case,family,base_logits,weights,residual))
        gain_results=[]
        for gain in (1.0,2.0,4.0,6.0,8.0,12.0,16.0):
            cases=[]
            for case,family,base_logits,weights,residual in cached:
                candidate=compose_crown_residual_logits(base_logits,gain*residual,weights); repeated=compose_crown_residual_logits(base_logits,gain*model(base_logits,family_order.index(family)),weights)
                base=case["base"][0,0].numpy(); ref=case["reference"][0,0].numpy(); pred=(candidate[0,0]>=0).numpy(); region=(weights[0,0]>0).numpy()
                bc,cc=chamfer(ref,base,region),chamfer(ref,pred,region); _,base_components=ndimage.label(base); _,candidate_components=ndimage.label(pred)
                cases.append({"id":case["receipt"]["id"],"toothFamily":family,"gain":gain,
                    "occupancyCrossingCount":int(np.count_nonzero(pred!=base)),"baseCrownChamfer":bc,"candidateCrownChamfer":cc,
                    "crownChamferRelativeImprovement":(bc-cc)/max(bc,1e-8),"candidateOccupiedVoxelCount":int(np.count_nonzero(pred)),
                    "rootLogitsByteIdentical":torch.equal(candidate[weights==0],base_logits[weights==0]),"rawDecodeExactRepeat":torch.equal(candidate,repeated),
                    "topologyPassed":int(np.count_nonzero(pred))>0 and 0<int(candidate_components)<=int(base_components)})
            family_medians={f:float(np.median([r["crownChamferRelativeImprovement"] for r in cases if r["toothFamily"]==f])) for f in family_order}
            gain_results.append({"gain":gain,"cases":cases,"totalOccupancyCrossings":sum(r["occupancyCrossingCount"] for r in cases),
                "medianCrownChamferRelativeImprovement":float(np.median([r["crownChamferRelativeImprovement"] for r in cases])),
                "familyMedianCrownChamferRelativeImprovement":family_medians,
                "allRootLogitsByteIdentical":all(r["rootLogitsByteIdentical"] for r in cases),"allRawDecodesExactRepeat":all(r["rawDecodeExactRepeat"] for r in cases),
                "allTopologyPassed":all(r["topologyPassed"] for r in cases)})
    eligible=[row for row in gain_results if row["totalOccupancyCrossings"]>0 and row["familyMedianCrownChamferRelativeImprovement"]["premolar"]>0
              and row["familyMedianCrownChamferRelativeImprovement"]["molar"]>0 and all(v>=-0.005 for v in row["familyMedianCrownChamferRelativeImprovement"].values())
              and row["allRootLogitsByteIdentical"] and row["allRawDecodesExactRepeat"] and row["allTopologyPassed"]]
    selected=min(eligible,key=lambda row:row["gain"]) if eligible else None
    evidence={"schemaVersion":1,"valid":True,"stage":"E14-G2F-signed-margin-gain-v1","optimizerSteps":0,"sourceCheckpointSha256":g2e["checkpointSha256"],
        "gainResults":gain_results,"selectedGain":selected["gain"] if selected else None,"boundedTrainingAuthorized":selected is not None,
        "g3Authorized":False,"clinicalClaimPermitted":False,"productionMutationPermitted":False}
    evidence_path.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit(); return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    gpu="L4", cpu=8, memory=32768, timeout=45 * 60,
)
def run_e14_g2g_class_balanced_family_response(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2g-class-balanced-family-response-v1",
) -> dict:
    """Train a bounded crown response without letting removal dominate addition."""
    import copy
    import numpy as np
    import torch
    import torch.nn.functional as F
    from collections import defaultdict
    from scipy import ndimage
    from scipy.spatial import cKDTree

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2g-class-balanced-family-response-v1":
        raise ValueError("E14 G2G class-balanced response is sealed")
    dataset_root=Path(f"/datasets/{dataset_name}")
    cache_path=dataset_root/"stage1-e14-g2-frozen-base-support-v1/cache-evidence.json"
    g2b_path=Path("/checkpoints/stage1-e14-g2b-family-trust-region-v1/g2b-evidence.json")
    g2f_path=Path("/checkpoints/stage1-e14-g2f-signed-margin-gain-v1/g2f-evidence.json")
    cache=json.loads(cache_path.read_text(encoding="utf-8")); g2b=json.loads(g2b_path.read_text(encoding="utf-8")); g2f=json.loads(g2f_path.read_text(encoding="utf-8"))
    if not (cache.get("valid") is True and g2b.get("g2cResponseAuthorized") is True
            and g2f.get("valid") is True and g2f.get("boundedTrainingAuthorized") is False
            and g2f.get("selectedGain") is None):
        raise ValueError("E14 G2G requires the sealed safe G2B boundary and rejected G2F gain screen")
    run_root=Path(f"/checkpoints/{run_name}"); evidence_path=run_root/"g2g-evidence.json"
    if evidence_path.is_file():
        existing=json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True: return {**existing,"resumed":True}
        raise ValueError("Existing G2G evidence is invalid")
    if run_root.exists(): raise FileExistsError("Partial G2G output exists")
    run_root.mkdir(parents=True,exist_ok=False)
    torch.manual_seed(20260928); torch.cuda.manual_seed_all(20260928); torch.use_deterministic_algorithms(True)
    device=torch.device("cuda"); family_order=("incisor","canine","premolar","molar")

    class FamilyHead(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.net=torch.nn.Sequential(torch.nn.Conv3d(4,12,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(12,12,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(12,1,1))
        def forward(self,logits):
            b,_,d,h,w=logits.shape; axes=[torch.linspace(-1,1,s,device=logits.device,dtype=logits.dtype) for s in (d,h,w)]
            grid=torch.stack(torch.meshgrid(*axes,indexing="ij"),dim=0).expand(b,-1,-1,-1,-1)
            return torch.tanh(self.net(torch.cat((torch.sigmoid(logits),grid),dim=1)))
    class FamilyRefiner(torch.nn.Module):
        def __init__(self): super().__init__(); self.heads=torch.nn.ModuleList([FamilyHead() for _ in family_order])
        def forward(self,logits,index): return self.heads[index](logits)
    def dense(coords):
        values=np.asarray(coords,dtype=np.int64); out=torch.zeros((1,1,32,32,32),dtype=torch.bool,device=device)
        if values.ndim!=2 or values.shape[1]!=3 or not len(values) or values.min()<0 or values.max()>=32: raise ValueError("Invalid G2G coordinates")
        out[0,0,values[:,0],values[:,1],values[:,2]]=True; return out
    def load(row):
        artifact=dataset_root/row["artifact"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest()!=row["artifactSha256"]: raise ValueError("G2G artifact drift")
        packed=np.load(artifact); return {"receipt":row,"base":dense(packed["base_coords"]),"reference":dense(packed["reference_coords"])}
    def logits_weights(case):
        weights,_=build_crown_transition_weights_from_occupancy(case["base"])
        return torch.where(case["base"],torch.tensor(0.25,device=device),torch.tensor(-0.25,device=device)),weights.to(device)
    def chamfer(reference,prediction,region):
        structure=np.ones((3,3,3),dtype=bool); rs=reference&~ndimage.binary_erosion(reference,structure=structure,border_value=0); ps=prediction&~ndimage.binary_erosion(prediction,structure=structure,border_value=0)
        rp,pp=np.argwhere(rs&region),np.argwhere(ps&region)
        if not len(rp) or not len(pp): return float("inf")
        rt,pt=cKDTree(rp),cKDTree(pp); return float((pt.query(rp)[0].mean()+rt.query(pp)[0].mean())/2)

    training=defaultdict(list); validation=[]
    for row in cache["cases"]:
        case=load(row); (training[row["toothFamily"]] if row["split"]=="train" else validation).append(case)
    if len(validation)!=12 or any(not training[f] for f in family_order): raise RuntimeError("G2G cohort drift")
    model=FamilyRefiner().to(device); source_checkpoint=Path(g2b["checkpointArtifact"])
    if hashlib.sha256(source_checkpoint.read_bytes()).hexdigest()!=g2b["checkpointSha256"]: raise ValueError("G2B checkpoint drift")
    strict=model.load_state_dict(torch.load(source_checkpoint,map_location=device,weights_only=True)["state_dict"],strict=True)
    if strict.missing_keys or strict.unexpected_keys: raise RuntimeError("G2G strict source load failed")
    optimizers=[torch.optim.AdamW(head.parameters(),lr=0.001,weight_decay=0.0) for head in model.heads]

    def evaluate(step):
        model.eval(); cases=[]
        with torch.no_grad():
            for case in validation:
                family=case["receipt"]["toothFamily"]; index=family_order.index(family); base_logits,weights=logits_weights(case)
                residual=model(base_logits,index); candidate=compose_crown_residual_logits(base_logits,residual,weights); repeated=compose_crown_residual_logits(base_logits,model(base_logits,index),weights)
                base=case["base"][0,0].cpu().numpy(); ref=case["reference"][0,0].cpu().numpy(); pred=(candidate[0,0]>=0).cpu().numpy(); region=(weights[0,0]>0).cpu().numpy()
                bc,cc=chamfer(ref,base,region),chamfer(ref,pred,region); _,base_components=ndimage.label(base); _,candidate_components=ndimage.label(pred)
                cases.append({"id":case["receipt"]["id"],"toothFamily":family,"baseCrownChamfer":bc,"candidateCrownChamfer":cc,
                    "crownChamferRelativeImprovement":(bc-cc)/max(bc,1e-8),"occupancyCrossingCount":int(np.count_nonzero(pred!=base)),
                    "rootLogitsByteIdentical":torch.equal(candidate[weights==0],base_logits[weights==0]),"rawDecodeExactRepeat":torch.equal(candidate,repeated),
                    "topologyPassed":int(np.count_nonzero(pred))>0 and 0<int(candidate_components)<=int(base_components)})
        fm={f:float(np.median([r["crownChamferRelativeImprovement"] for r in cases if r["toothFamily"]==f])) for f in family_order}
        return {"step":step,"cases":cases,"medianCrownChamferRelativeImprovement":float(np.median([r["crownChamferRelativeImprovement"] for r in cases])),
            "familyMedianCrownChamferRelativeImprovement":fm,"totalOccupancyCrossings":sum(r["occupancyCrossingCount"] for r in cases),
            "allRootLogitsByteIdentical":all(r["rootLogitsByteIdentical"] for r in cases),"allRawDecodesExactRepeat":all(r["rawDecodeExactRepeat"] for r in cases),
            "allTopologyPassed":all(r["topologyPassed"] for r in cases)}

    evaluation_steps=(0,40,80,160,240,400); evaluations=[]; checkpoints={}; losses=[]
    initial=evaluate(0); evaluations.append(initial); checkpoints[0]=copy.deepcopy(model.state_dict())
    for step in range(1,401):
        index=(step-1)%4; family=family_order[index]; case=training[family][((step-1)//4)%len(training[family])]; base_logits,weights=logits_weights(case); target=case["reference"]
        supervised=weights>0; missing=supervised&(~case["base"])&target; extra=supervised&case["base"]&(~target); agreement=supervised&(case["base"]==target)
        if not bool(missing.any()) or not bool(extra.any()) or not bool(agreement.any()): raise RuntimeError(f"G2G incomplete supervision at step {step}")
        residual=model(base_logits,index); candidate=compose_crown_residual_logits(base_logits,residual,weights)
        missing_loss=F.relu(0.10-candidate[missing]).mean(); extra_loss=F.relu(0.10+candidate[extra]).mean(); preservation=F.mse_loss(candidate[agreement],base_logits[agreement]); magnitude=torch.mean((residual[supervised]*weights[supervised])**2)
        loss=0.5*missing_loss+0.5*extra_loss+8.0*preservation+0.10*magnitude
        optimizers[index].zero_grad(set_to_none=True); loss.backward()
        if not bool(torch.isfinite(loss)) or not all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.heads[index].parameters()): raise RuntimeError(f"G2G finite gate failed at step {step}")
        torch.nn.utils.clip_grad_norm_(model.heads[index].parameters(),1.0); optimizers[index].step()
        losses.append({"step":step,"family":family,"loss":float(loss.detach()),"missingMargin":float(missing_loss.detach()),"extraMargin":float(extra_loss.detach()),"preservation":float(preservation.detach())})
        if step in evaluation_steps[1:]: evaluations.append(evaluate(step)); checkpoints[step]=copy.deepcopy(model.state_dict())
    def eligible(row):
        fm=row["familyMedianCrownChamferRelativeImprovement"]
        return row["totalOccupancyCrossings"]>0 and fm["premolar"]>0 and fm["molar"]>0 and all(v>=-0.005 for v in fm.values()) and row["allRootLogitsByteIdentical"] and row["allRawDecodesExactRepeat"] and row["allTopologyPassed"]
    eligible_rows=[row for row in evaluations if eligible(row)]
    selected=max(eligible_rows,key=lambda row:(row["medianCrownChamferRelativeImprovement"],min(row["familyMedianCrownChamferRelativeImprovement"].values()))) if eligible_rows else None
    selected_step=selected["step"] if selected else max(evaluations,key=lambda row:row["medianCrownChamferRelativeImprovement"])["step"]
    checkpoint_path=run_root/f"class-balanced-step-{selected_step:03d}.pt"; torch.save({"state_dict":checkpoints[selected_step],"familyOrder":family_order,"optimizerSteps":selected_step},checkpoint_path)
    verification=FamilyRefiner().to(device); reload_result=verification.load_state_dict(torch.load(checkpoint_path,map_location=device,weights_only=True)["state_dict"],strict=True); strict_reload=not reload_result.missing_keys and not reload_result.unexpected_keys
    passed=selected is not None and strict_reload
    evidence={"schemaVersion":1,"valid":True,"stage":"E14-G2G-class-balanced-family-response-v1","optimizerSteps":400,"stepsPerFamily":100,"learningRate":0.001,
        "evaluationSteps":list(evaluation_steps),"objective":{"missingWeight":0.5,"extraWeight":0.5,"signedMargin":0.10,"preservationWeight":8.0,"magnitudeWeight":0.10},
        "losses":losses,"evaluations":evaluations,"selectedStep":selected_step,"selectedEvaluation":selected,"checkpointReloadedStrict":strict_reload,
        "checkpointArtifact":str(checkpoint_path),"checkpointSha256":hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "expertReviewPackAuthorized":passed,"g3Authorized":False,"clinicalClaimPermitted":False,"productionMutationPermitted":False}
    evidence_path.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit(); return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    gpu="L4", cpu=8, memory=32768, timeout=60 * 60,
)
def run_e14_g2h_image_conditioned_crown_adapter(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2h-image-conditioned-crown-adapter-v1",
) -> dict:
    """Fit a bounded image-conditioned crown adapter while copying roots exactly."""
    import copy
    import io
    import numpy as np
    import torch
    import torch.nn.functional as F
    from collections import defaultdict
    from PIL import Image
    from scipy import ndimage
    from scipy.spatial import cKDTree

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2h-image-conditioned-crown-adapter-v1":
        raise ValueError("E14 G2H image-conditioned crown adapter is sealed")
    dataset_root=Path(f"/datasets/{dataset_name}")
    cache_path=dataset_root/"stage1-e14-g2-frozen-base-support-v1/cache-evidence.json"
    g2g_path=Path("/checkpoints/stage1-e14-g2g-class-balanced-family-response-v1/g2g-evidence.json")
    cache=json.loads(cache_path.read_text(encoding="utf-8")); g2g=json.loads(g2g_path.read_text(encoding="utf-8"))
    if not (cache.get("valid") is True and g2g.get("valid") is True and g2g.get("optimizerSteps")==400
            and g2g.get("expertReviewPackAuthorized") is False and g2g.get("selectedStep")==0):
        raise ValueError("E14 G2H requires the sealed non-responsive G2G result")
    run_root=Path(f"/checkpoints/{run_name}"); evidence_path=run_root/"g2h-evidence.json"
    if evidence_path.is_file():
        existing=json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True: return {**existing,"resumed":True}
        raise ValueError("Existing G2H evidence is invalid")
    if run_root.exists(): raise FileExistsError("Partial G2H output exists")
    run_root.mkdir(parents=True,exist_ok=False)
    torch.manual_seed(20260929); torch.cuda.manual_seed_all(20260929); torch.use_deterministic_algorithms(True)
    device=torch.device("cuda"); family_order=("incisor","canine","premolar","molar")

    class ImageFamilyHead(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.image=torch.nn.Sequential(torch.nn.Conv2d(3,8,3,padding=1),torch.nn.SiLU(),torch.nn.Conv2d(8,8,3,padding=1),torch.nn.SiLU())
            self.volume=torch.nn.Sequential(torch.nn.Conv3d(28,24,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(24,16,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(16,1,1))
            torch.nn.init.zeros_(self.volume[-1].weight); torch.nn.init.zeros_(self.volume[-1].bias)
        def forward(self,logits,image):
            b,_,d,h,w=logits.shape; features=self.image(image)
            yz=features.unsqueeze(2).expand(-1,-1,d,-1,-1)
            xz=features.unsqueeze(3).expand(-1,-1,-1,h,-1)
            xy=features.unsqueeze(4).expand(-1,-1,-1,-1,w)
            axes=[torch.linspace(-1,1,s,device=logits.device,dtype=logits.dtype) for s in (d,h,w)]
            grid=torch.stack(torch.meshgrid(*axes,indexing="ij"),dim=0).expand(b,-1,-1,-1,-1)
            return 0.5*torch.tanh(self.volume(torch.cat((torch.sigmoid(logits),grid,yz,xz,xy),dim=1)))
    class ImageFamilyRefiner(torch.nn.Module):
        def __init__(self): super().__init__(); self.heads=torch.nn.ModuleList([ImageFamilyHead() for _ in family_order])
        def forward(self,logits,image,index): return self.heads[index](logits,image)
    def dense(coords):
        values=np.asarray(coords,dtype=np.int64); out=torch.zeros((1,1,32,32,32),dtype=torch.bool,device=device)
        if values.ndim!=2 or values.shape[1]!=3 or not len(values) or values.min()<0 or values.max()>=32: raise ValueError("Invalid G2H coordinates")
        out[0,0,values[:,0],values[:,1],values[:,2]]=True; return out
    def image_tensor(row):
        path=dataset_root/row["inputImage"]; payload=path.read_bytes()
        if hashlib.sha256(payload).hexdigest()!=row["inputImageSha256"]: raise ValueError("G2H image hash drift")
        image=Image.open(io.BytesIO(payload)).convert("RGB").resize((32,32),Image.Resampling.BILINEAR)
        array=np.asarray(image,dtype=np.float32)/255.0
        return torch.from_numpy(array).permute(2,0,1).unsqueeze(0).contiguous().to(device)
    def load(row):
        artifact=dataset_root/row["artifact"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest()!=row["artifactSha256"]: raise ValueError("G2H artifact drift")
        packed=np.load(artifact); return {"receipt":row,"base":dense(packed["base_coords"]),"reference":dense(packed["reference_coords"]),"image":image_tensor(row)}
    def logits_weights(case):
        weights,_=build_crown_transition_weights_from_occupancy(case["base"])
        return torch.where(case["base"],torch.tensor(0.25,device=device),torch.tensor(-0.25,device=device)),weights.to(device)
    def chamfer(reference,prediction,region):
        structure=np.ones((3,3,3),dtype=bool); rs=reference&~ndimage.binary_erosion(reference,structure=structure,border_value=0); ps=prediction&~ndimage.binary_erosion(prediction,structure=structure,border_value=0)
        rp,pp=np.argwhere(rs&region),np.argwhere(ps&region)
        if not len(rp) or not len(pp): return float("inf")
        rt,pt=cKDTree(rp),cKDTree(pp); return float((pt.query(rp)[0].mean()+rt.query(pp)[0].mean())/2)

    training=defaultdict(list); validation=[]
    for row in cache["cases"]:
        case=load(row); (training[row["toothFamily"]] if row["split"]=="train" else validation).append(case)
    if sum(len(v) for v in training.values())!=64 or len(validation)!=12: raise RuntimeError("G2H cohort drift")
    model=ImageFamilyRefiner().to(device); optimizers=[torch.optim.AdamW(head.parameters(),lr=0.002,weight_decay=0.0) for head in model.heads]

    def evaluate(step):
        model.eval(); cases=[]
        with torch.no_grad():
            for case in validation:
                family=case["receipt"]["toothFamily"]; index=family_order.index(family); base_logits,weights=logits_weights(case)
                residual=model(base_logits,case["image"],index); candidate=compose_crown_residual_logits(base_logits,residual,weights); repeated=compose_crown_residual_logits(base_logits,model(base_logits,case["image"],index),weights)
                base=case["base"][0,0].cpu().numpy(); ref=case["reference"][0,0].cpu().numpy(); pred=(candidate[0,0]>=0).cpu().numpy(); region=(weights[0,0]>0).cpu().numpy()
                bc,cc=chamfer(ref,base,region),chamfer(ref,pred,region); _,base_components=ndimage.label(base); _,candidate_components=ndimage.label(pred)
                cases.append({"id":case["receipt"]["id"],"toothFamily":family,"baseCrownChamfer":bc,"candidateCrownChamfer":cc,
                    "crownChamferRelativeImprovement":(bc-cc)/max(bc,1e-8),"occupancyCrossingCount":int(np.count_nonzero(pred!=base)),
                    "maximumAbsoluteResidual":float(residual.abs().max()),"rootLogitsByteIdentical":torch.equal(candidate[weights==0],base_logits[weights==0]),
                    "rawDecodeExactRepeat":torch.equal(candidate,repeated),"topologyPassed":int(np.count_nonzero(pred))>0 and 0<int(candidate_components)<=int(base_components)})
        fm={f:float(np.median([r["crownChamferRelativeImprovement"] for r in cases if r["toothFamily"]==f])) for f in family_order}
        return {"step":step,"cases":cases,"medianCrownChamferRelativeImprovement":float(np.median([r["crownChamferRelativeImprovement"] for r in cases])),
            "familyMedianCrownChamferRelativeImprovement":fm,"totalOccupancyCrossings":sum(r["occupancyCrossingCount"] for r in cases),
            "allRootLogitsByteIdentical":all(r["rootLogitsByteIdentical"] for r in cases),"allRawDecodesExactRepeat":all(r["rawDecodeExactRepeat"] for r in cases),"allTopologyPassed":all(r["topologyPassed"] for r in cases)}

    evaluation_steps=(0,100,200,400,600,800); evaluations=[]; checkpoint_paths={}; losses=[]
    evaluations.append(evaluate(0)); initial_path=run_root/"adapter-step-000.pt"; torch.save({"state_dict":model.state_dict(),"optimizerSteps":0},initial_path); checkpoint_paths[0]=initial_path
    for step in range(1,801):
        index=(step-1)%4; family=family_order[index]; case=training[family][((step-1)//4)%len(training[family])]; base_logits,weights=logits_weights(case); target=case["reference"]
        supervised=weights>0; missing=supervised&(~case["base"])&target; extra=supervised&case["base"]&(~target); agreement=supervised&(case["base"]==target)
        if not bool(missing.any()) or not bool(extra.any()) or not bool(agreement.any()): raise RuntimeError(f"G2H incomplete supervision at step {step}")
        residual=model(base_logits,case["image"],index); candidate=compose_crown_residual_logits(base_logits,residual,weights)
        missing_loss=F.relu(0.05-candidate[missing]).mean(); extra_loss=F.relu(0.05+candidate[extra]).mean(); preservation=F.mse_loss(candidate[agreement],base_logits[agreement]); magnitude=torch.mean((residual[supervised]*weights[supervised])**2)
        loss=0.5*missing_loss+0.5*extra_loss+4.0*preservation+0.02*magnitude
        optimizers[index].zero_grad(set_to_none=True); loss.backward()
        if not bool(torch.isfinite(loss)) or not all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.heads[index].parameters()): raise RuntimeError(f"G2H finite gate failed at step {step}")
        torch.nn.utils.clip_grad_norm_(model.heads[index].parameters(),1.0); optimizers[index].step()
        losses.append({"step":step,"family":family,"loss":float(loss.detach()),"missingMargin":float(missing_loss.detach()),"extraMargin":float(extra_loss.detach()),"preservation":float(preservation.detach())})
        if step in evaluation_steps[1:]:
            evaluations.append(evaluate(step)); path=run_root/f"adapter-step-{step:03d}.pt"; torch.save({"state_dict":model.state_dict(),"optimizerSteps":step},path); checkpoint_paths[step]=path; checkpoint_volume.commit()
    def eligible(row):
        fm=row["familyMedianCrownChamferRelativeImprovement"]
        return row["totalOccupancyCrossings"]>0 and fm["premolar"]>0 and fm["molar"]>0 and all(v>=-0.005 for v in fm.values()) and row["allRootLogitsByteIdentical"] and row["allRawDecodesExactRepeat"] and row["allTopologyPassed"]
    eligible_rows=[row for row in evaluations if eligible(row)]
    selected=max(eligible_rows,key=lambda row:(row["medianCrownChamferRelativeImprovement"],min(row["familyMedianCrownChamferRelativeImprovement"].values()))) if eligible_rows else None
    selected_step=selected["step"] if selected else 0; checkpoint_path=checkpoint_paths[selected_step]
    verification=ImageFamilyRefiner().to(device); reload_result=verification.load_state_dict(torch.load(checkpoint_path,map_location=device,weights_only=True)["state_dict"],strict=True); strict_reload=not reload_result.missing_keys and not reload_result.unexpected_keys
    passed=selected is not None and strict_reload
    evidence={"schemaVersion":1,"valid":True,"stage":"E14-G2H-image-conditioned-crown-adapter-v1","optimizerSteps":800,"stepsPerFamily":200,"learningRate":0.002,
        "imageConditioning":{"input":"hashed source render","resize":[32,32],"featureChannels":8,"projection":"three orthogonal feature planes"},
        "evaluationSteps":list(evaluation_steps),"objective":{"missingWeight":0.5,"extraWeight":0.5,"signedMargin":0.05,"preservationWeight":4.0,"magnitudeWeight":0.02},
        "losses":losses,"evaluations":evaluations,"selectedStep":selected_step,"selectedEvaluation":selected,"checkpointReloadedStrict":strict_reload,
        "checkpointArtifact":str(checkpoint_path),"checkpointSha256":hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "expertReviewPackAuthorized":passed,"g3Authorized":False,"clinicalClaimPermitted":False,"productionMutationPermitted":False}
    evidence_path.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit(); return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    gpu="L4", cpu=8, memory=32768, timeout=60 * 60,
)
def run_e14_g2i_surface_band_crown_adapter(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2i-surface-band-crown-adapter-v1",
) -> dict:
    """Refine only near crown surfaces and project detached crown fragments away."""
    import io
    import numpy as np
    import torch
    import torch.nn.functional as F
    from collections import defaultdict
    from PIL import Image
    from scipy import ndimage
    from scipy.spatial import cKDTree

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2i-surface-band-crown-adapter-v1": raise ValueError("E14 G2I is sealed")
    root=Path(f"/datasets/{dataset_name}"); cache_path=root/"stage1-e14-g2-frozen-base-support-v1/cache-evidence.json"
    g2h_path=Path("/checkpoints/stage1-e14-g2h-image-conditioned-crown-adapter-v1/g2h-evidence.json")
    cache=json.loads(cache_path.read_text(encoding="utf-8")); g2h=json.loads(g2h_path.read_text(encoding="utf-8"))
    source_path=Path("/checkpoints/stage1-e14-g2h-image-conditioned-crown-adapter-v1/adapter-step-400.pt")
    if not (cache.get("valid") is True and g2h.get("valid") is True and g2h.get("expertReviewPackAuthorized") is False and source_path.is_file()): raise ValueError("E14 G2I requires sealed G2H failure evidence and step-400 adapter")
    run_root=Path(f"/checkpoints/{run_name}"); evidence_path=run_root/"g2i-evidence.json"
    if evidence_path.is_file():
        existing=json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True: return {**existing,"resumed":True}
        raise ValueError("Existing G2I evidence is invalid")
    if run_root.exists(): raise FileExistsError("Partial G2I output exists")
    run_root.mkdir(parents=True,exist_ok=False); torch.manual_seed(20260930); torch.cuda.manual_seed_all(20260930); torch.use_deterministic_algorithms(True)
    device=torch.device("cuda"); families=("incisor","canine","premolar","molar")

    class Head(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.image=torch.nn.Sequential(torch.nn.Conv2d(3,8,3,padding=1),torch.nn.SiLU(),torch.nn.Conv2d(8,8,3,padding=1),torch.nn.SiLU()); self.volume=torch.nn.Sequential(torch.nn.Conv3d(28,24,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(24,16,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(16,1,1))
        def forward(self,logits,image):
            b,_,d,h,w=logits.shape; feat=self.image(image); yz=feat.unsqueeze(2).expand(-1,-1,d,-1,-1); xz=feat.unsqueeze(3).expand(-1,-1,-1,h,-1); xy=feat.unsqueeze(4).expand(-1,-1,-1,-1,w)
            axes=[torch.linspace(-1,1,s,device=logits.device,dtype=logits.dtype) for s in (d,h,w)]; grid=torch.stack(torch.meshgrid(*axes,indexing="ij"),dim=0).expand(b,-1,-1,-1,-1)
            return 0.5*torch.tanh(self.volume(torch.cat((torch.sigmoid(logits),grid,yz,xz,xy),dim=1)))
    class Refiner(torch.nn.Module):
        def __init__(self): super().__init__(); self.heads=torch.nn.ModuleList([Head() for _ in families])
        def forward(self,logits,image,index): return self.heads[index](logits,image)
    def dense(coords):
        values=np.asarray(coords,dtype=np.int64); out=torch.zeros((1,1,32,32,32),dtype=torch.bool,device=device); out[0,0,values[:,0],values[:,1],values[:,2]]=True; return out
    def image_tensor(row):
        path=root/row["inputImage"]; payload=path.read_bytes()
        if hashlib.sha256(payload).hexdigest()!=row["inputImageSha256"]: raise ValueError("G2I image drift")
        arr=np.asarray(Image.open(io.BytesIO(payload)).convert("RGB").resize((32,32),Image.Resampling.BILINEAR),dtype=np.float32)/255.0
        return torch.from_numpy(arr).permute(2,0,1).unsqueeze(0).contiguous().to(device)
    def load(row):
        artifact=root/row["artifact"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest()!=row["artifactSha256"]: raise ValueError("G2I artifact drift")
        packed=np.load(artifact); base=dense(packed["base_coords"]); reference=dense(packed["reference_coords"])
        base_np=base[0,0].cpu().numpy(); ref_np=reference[0,0].cpu().numpy(); structure=np.ones((3,3,3),dtype=bool)
        surface=(base_np&~ndimage.binary_erosion(base_np,structure=structure,border_value=0))|(ref_np&~ndimage.binary_erosion(ref_np,structure=structure,border_value=0))
        band=torch.from_numpy(ndimage.distance_transform_edt(~surface)<=2.0).view(1,1,32,32,32).to(device)
        return {"receipt":row,"base":base,"reference":reference,"image":image_tensor(row),"surfaceBand":band}
    def logits_weights(case):
        weights,_=build_crown_transition_weights_from_occupancy(case["base"]); return torch.where(case["base"],torch.tensor(0.25,device=device),torch.tensor(-0.25,device=device)),weights.to(device)
    def project(candidate,base,weights):
        binary=(candidate[0,0]>=0).detach().cpu().numpy(); labels,count=ndimage.label(binary,structure=ndimage.generate_binary_structure(3,1))
        if count<=1: return candidate.clone(),0,count
        root_anchor=((weights[0,0]==0)&base[0,0]).detach().cpu().numpy(); scores=[int(np.count_nonzero(root_anchor&(labels==label))) for label in range(1,count+1)]
        keep=int(np.argmax(scores))+1 if max(scores)>0 else int(np.argmax(np.bincount(labels.ravel())[1:]))+1; remove=torch.from_numpy((labels!=0)&(labels!=keep)).to(device)&(weights[0,0]>0)
        output=candidate.clone(); output[0,0][remove]=-0.25; return output,int(remove.sum().item()),count
    def chamfer(reference,prediction,region):
        structure=np.ones((3,3,3),dtype=bool); rs=reference&~ndimage.binary_erosion(reference,structure=structure,border_value=0); ps=prediction&~ndimage.binary_erosion(prediction,structure=structure,border_value=0); rp,pp=np.argwhere(rs&region),np.argwhere(ps&region)
        if not len(rp) or not len(pp): return float("inf")
        rt,pt=cKDTree(rp),cKDTree(pp); return float((pt.query(rp)[0].mean()+rt.query(pp)[0].mean())/2)

    training=defaultdict(list); validation=[]
    for row in cache["cases"]:
        case=load(row); (training[row["toothFamily"]] if row["split"]=="train" else validation).append(case)
    model=Refiner().to(device); strict=model.load_state_dict(torch.load(source_path,map_location=device,weights_only=True)["state_dict"],strict=True)
    if strict.missing_keys or strict.unexpected_keys: raise RuntimeError("G2I strict source reload failed")
    optimizers=[torch.optim.AdamW(head.parameters(),lr=0.0005,weight_decay=0.0) for head in model.heads]
    def evaluate(step):
        model.eval(); cases=[]
        with torch.no_grad():
            for case in validation:
                family=case["receipt"]["toothFamily"]; index=families.index(family); base_logits,weights=logits_weights(case); raw=compose_crown_residual_logits(base_logits,model(base_logits,case["image"],index),weights); candidate,removed,raw_components=project(raw,case["base"],weights); repeated,_removed,_components=project(compose_crown_residual_logits(base_logits,model(base_logits,case["image"],index),weights),case["base"],weights)
                base=case["base"][0,0].cpu().numpy(); ref=case["reference"][0,0].cpu().numpy(); pred=(candidate[0,0]>=0).cpu().numpy(); region=(weights[0,0]>0).cpu().numpy(); bc,cc=chamfer(ref,base,region),chamfer(ref,pred,region); _,projected_components=ndimage.label(pred)
                cases.append({"id":case["receipt"]["id"],"toothFamily":family,"crownChamferRelativeImprovement":(bc-cc)/max(bc,1e-8),"occupancyCrossingCount":int(np.count_nonzero(pred!=base)),"rawComponentCount":int(raw_components),"projectedComponentCount":int(projected_components),"projectedVoxelRemovalCount":removed,"rootLogitsByteIdentical":torch.equal(candidate[weights==0],base_logits[weights==0]),"rawDecodeExactRepeat":torch.equal(candidate,repeated),"topologyPassed":int(projected_components)==1})
        fm={f:float(np.median([r["crownChamferRelativeImprovement"] for r in cases if r["toothFamily"]==f])) for f in families}
        return {"step":step,"cases":cases,"medianCrownChamferRelativeImprovement":float(np.median([r["crownChamferRelativeImprovement"] for r in cases])),"familyMedianCrownChamferRelativeImprovement":fm,"totalOccupancyCrossings":sum(r["occupancyCrossingCount"] for r in cases),"allRootLogitsByteIdentical":all(r["rootLogitsByteIdentical"] for r in cases),"allRawDecodesExactRepeat":all(r["rawDecodeExactRepeat"] for r in cases),"allTopologyPassed":all(r["topologyPassed"] for r in cases)}
    evaluation_steps=(0,100,200,300,400,600); evaluations=[evaluate(0)]; checkpoint_paths={0:source_path}; losses=[]
    for step in range(1,601):
        index=(step-1)%4; family=families[index]; case=training[family][((step-1)//4)%len(training[family])]; base_logits,weights=logits_weights(case); supervised=(weights>0)&case["surfaceBand"]; target=case["reference"]; missing=supervised&(~case["base"])&target; extra=supervised&case["base"]&(~target); preserve=(weights>0)&(~case["surfaceBand"])
        if not bool(missing.any()) or not bool(extra.any()) or not bool(preserve.any()): raise RuntimeError(f"G2I incomplete surface supervision at {step}")
        residual=model(base_logits,case["image"],index); candidate=compose_crown_residual_logits(base_logits,residual,weights); add=F.relu(0.05-candidate[missing]).mean(); remove=F.relu(0.05+candidate[extra]).mean(); preservation=F.mse_loss(candidate[preserve],base_logits[preserve]); loss=0.5*add+0.5*remove+12.0*preservation+0.02*torch.mean((residual[supervised]*weights[supervised])**2)
        optimizers[index].zero_grad(set_to_none=True); loss.backward()
        if not bool(torch.isfinite(loss)) or not all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.heads[index].parameters()): raise RuntimeError(f"G2I finite gate failed at {step}")
        torch.nn.utils.clip_grad_norm_(model.heads[index].parameters(),1.0); optimizers[index].step(); losses.append({"step":step,"family":family,"loss":float(loss.detach()),"add":float(add.detach()),"remove":float(remove.detach()),"preservation":float(preservation.detach())})
        if step in evaluation_steps[1:]: evaluations.append(evaluate(step)); path=run_root/f"surface-band-step-{step:03d}.pt"; torch.save({"state_dict":model.state_dict(),"optimizerSteps":step},path); checkpoint_paths[step]=path; checkpoint_volume.commit()
    def eligible(row):
        fm=row["familyMedianCrownChamferRelativeImprovement"]; return row["totalOccupancyCrossings"]>0 and fm["premolar"]>0 and fm["molar"]>0 and all(v>=-0.005 for v in fm.values()) and row["allRootLogitsByteIdentical"] and row["allRawDecodesExactRepeat"] and row["allTopologyPassed"]
    eligible_rows=[row for row in evaluations if eligible(row)]; selected=max(eligible_rows,key=lambda row:row["medianCrownChamferRelativeImprovement"]) if eligible_rows else None; selected_step=selected["step"] if selected else 0; checkpoint_path=checkpoint_paths[selected_step]
    evidence={"schemaVersion":1,"valid":True,"stage":"E14-G2I-surface-band-crown-adapter-v1","optimizerSteps":600,"stepsPerFamily":150,"learningRate":0.0005,"surfaceBandVoxels":2.0,"projection":"retain component connected to unchanged root anchor","evaluationSteps":list(evaluation_steps),"evaluations":evaluations,"losses":losses,"selectedStep":selected_step,"selectedEvaluation":selected,"checkpointArtifact":str(checkpoint_path),"checkpointSha256":hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),"expertReviewPackAuthorized":selected is not None,"g3Authorized":False,"clinicalClaimPermitted":False,"productionMutationPermitted":False}
    evidence_path.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit(); return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret], gpu="H100", cpu=8, memory=65536, timeout=2 * 60 * 60,
)
def qualify_e14_g2j_molar_adapter_through_decoder(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2j-molar-decoder-qualification-v3",
) -> dict:
    """Decode the bounded molar-only signal and gate crown gain/root preservation."""
    import io
    import random
    import sys
    import numpy as np
    import torch
    import trimesh
    from PIL import Image
    from scipy import ndimage

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2j-molar-decoder-qualification-v3": raise ValueError("E14 G2J is sealed")
    sys.path.insert(0,"/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh
    from scripts.regional_anatomy_gate import evaluate_regional_non_regression

    root=Path(f"/datasets/{dataset_name}"); cache_path=root/"stage1-e14-g2-frozen-base-support-v1/cache-evidence.json"; manifest_path=root/"anatomy_manifest.json"
    g2h_path=Path("/checkpoints/stage1-e14-g2h-image-conditioned-crown-adapter-v1/g2h-evidence.json"); source_path=Path("/checkpoints/stage1-e14-g2h-image-conditioned-crown-adapter-v1/adapter-step-800.pt")
    cache=json.loads(cache_path.read_text(encoding="utf-8")); g2h=json.loads(g2h_path.read_text(encoding="utf-8")); manifest=json.loads(manifest_path.read_text(encoding="utf-8")); assets={row["id"]:row for row in manifest["assets"]}
    if not (cache.get("valid") is True and g2h.get("valid") is True and g2h.get("expertReviewPackAuthorized") is False and source_path.is_file()): raise ValueError("G2J requires sealed G2H evidence")
    molar_rows=[row for row in cache["cases"] if row["split"]=="validation" and row["toothFamily"]=="molar"]
    if len(molar_rows)!=3: raise RuntimeError("G2J requires exactly three held-out molars")
    run_root=Path(f"/checkpoints/{run_name}"); evidence_path=run_root/"g2j-evidence.json"
    if evidence_path.is_file():
        existing=json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True: return {**existing,"resumed":True}
        raise ValueError("Existing G2J evidence is invalid")
    if run_root.exists(): raise FileExistsError("Partial G2J output exists")
    run_root.mkdir(parents=True,exist_ok=False)
    run_receipt={"schemaVersion":1,"stage":"E14-G2J-molar-decoder-qualification-v3","status":"started","optimizerSteps":0,"caseIds":[row["id"] for row in molar_rows],"sourceAdapterSha256":hashlib.sha256(source_path.read_bytes()).hexdigest(),"sparseCoordinateContiguityGuard":"decoder-upsample-input","productionMutationPermitted":False}
    (run_root/"run-receipt.json").write_text(json.dumps(run_receipt,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit()
    device=torch.device("cuda"); families=("incisor","canine","premolar","molar")

    class Head(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.image=torch.nn.Sequential(torch.nn.Conv2d(3,8,3,padding=1),torch.nn.SiLU(),torch.nn.Conv2d(8,8,3,padding=1),torch.nn.SiLU()); self.volume=torch.nn.Sequential(torch.nn.Conv3d(28,24,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(24,16,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(16,1,1))
        def forward(self,logits,image):
            b,_,d,h,w=logits.shape; feat=self.image(image); yz=feat.unsqueeze(2).expand(-1,-1,d,-1,-1); xz=feat.unsqueeze(3).expand(-1,-1,-1,h,-1); xy=feat.unsqueeze(4).expand(-1,-1,-1,-1,w); axes=[torch.linspace(-1,1,s,device=logits.device,dtype=logits.dtype) for s in (d,h,w)]; grid=torch.stack(torch.meshgrid(*axes,indexing="ij"),dim=0).expand(b,-1,-1,-1,-1); return 0.5*torch.tanh(self.volume(torch.cat((torch.sigmoid(logits),grid,yz,xz,xy),dim=1)))
    class Refiner(torch.nn.Module):
        def __init__(self): super().__init__(); self.heads=torch.nn.ModuleList([Head() for _ in families])
        def forward(self,logits,image,index): return self.heads[index](logits,image)
    model=Refiner().to(device).eval(); strict=model.load_state_dict(torch.load(source_path,map_location=device,weights_only=True)["state_dict"],strict=True)
    if strict.missing_keys or strict.unexpected_keys: raise RuntimeError("G2J adapter strict load failed")
    generator=TrellisGenerator(); generator.load_model(); params=sampler_params_for_steps(12); results=[]
    def support(row):
        artifact=root/row["artifact"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest()!=row["artifactSha256"]: raise ValueError("G2J support drift")
        packed=np.load(artifact); coords=np.asarray(packed["base_coords"],dtype=np.int64); base=torch.zeros((1,1,32,32,32),dtype=torch.bool,device=device); base[0,0,coords[:,0],coords[:,1],coords[:,2]]=True
        payload=(root/row["inputImage"]).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=row["inputImageSha256"]: raise ValueError("G2J image drift")
        image=Image.open(io.BytesIO(payload)); image.load(); small=np.asarray(image.convert("RGB").resize((32,32),Image.Resampling.BILINEAR),dtype=np.float32)/255.0; image_tensor=torch.from_numpy(small).permute(2,0,1).unsqueeze(0).contiguous().to(device)
        weights,_=build_crown_transition_weights_from_occupancy(base); weights=weights.to(device); logits=torch.where(base,torch.tensor(0.25,device=device),torch.tensor(-0.25,device=device)); candidate=compose_crown_residual_logits(logits,model(logits,image_tensor,3),weights); binary=(candidate[0,0]>=0).detach().cpu().numpy(); labels,count=ndimage.label(binary,structure=ndimage.generate_binary_structure(3,1)); root_anchor=((weights[0,0]==0)&base[0,0]).detach().cpu().numpy()
        if count>1:
            scores=[int(np.count_nonzero(root_anchor&(labels==label))) for label in range(1,count+1)]; keep=int(np.argmax(scores))+1 if max(scores)>0 else int(np.argmax(np.bincount(labels.ravel())[1:]))+1; binary=(labels==keep)
        candidate_coords=np.argwhere(binary).astype(np.int32); base_coords=coords.astype(np.int32)
        def batched(values): return torch.from_numpy(np.concatenate((np.zeros((len(values),1),dtype=np.int32),values),axis=1)).to(device).contiguous()
        return payload,image,batched(base_coords),batched(candidate_coords),weights,logits,candidate
    def decode(role,row,image,coords):
        seed=int(row["generationSeed"]); random.seed(seed); np.random.seed(seed%(2**32)); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
        processed=generator.pipeline.preprocess_image(image); cond512=generator.pipeline.get_cond([processed],512); cond1024=generator.pipeline.get_cond([processed],1024)
        decoder=generator.pipeline.models["shape_slat_decoder"]; original_upsample=decoder.upsample; guard={"calls":0,"nonContiguousInputs":0}
        def contiguous_upsample(slat,*args,**kwargs):
            guard["calls"]+=1
            if not slat.coords.is_contiguous(): guard["nonContiguousInputs"]+=1
            guarded=slat.replace(slat.feats,slat.coords.contiguous())
            if not guarded.coords.is_contiguous(): raise RuntimeError("G2J sparse-coordinate contiguity guard failed")
            return original_upsample(guarded,*args,**kwargs)
        decoder.upsample=contiguous_upsample
        try:
            with torch.inference_mode():
                slat,resolution=generator.pipeline.sample_shape_slat_cascade(cond512,cond1024,generator.pipeline.models["shape_slat_flow_model_512"],generator.pipeline.models["shape_slat_flow_model_1024"],512,1024,coords.contiguous(),params["shape"]); meshes,_=generator.pipeline.decode_shape_slat(slat.replace(slat.feats,slat.coords.contiguous()),resolution)
        finally:
            decoder.upsample=original_upsample
        if len(meshes)!=1: raise RuntimeError("G2J expected one decoded mesh")
        if guard["calls"]<1: raise RuntimeError("G2J sparse-coordinate contiguity guard was not exercised")
        raw=meshes[0]; mesh=trimesh.Trimesh(vertices=raw.vertices.detach().cpu().numpy(),faces=raw.faces.detach().cpu().numpy(),process=False); path=run_root/f"{row['id']}-{role}.ply"; mesh.export(path); return mesh,path,{"vertices":int(len(mesh.vertices)),"faces":int(len(mesh.faces)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"resolution":int(resolution),"upsampleGuardCalls":guard["calls"],"nonContiguousUpsampleInputsRepaired":guard["nonContiguousInputs"]}
    for row in molar_rows:
        payload,image,base_coords,candidate_coords,weights,base_logits,candidate_logits=support(row); base_mesh,base_path,base_receipt=decode("base",row,image,base_coords); candidate_mesh,candidate_path,candidate_receipt=decode("candidate",row,image,candidate_coords); reference=load_mesh(root/assets[row["id"]]["canonicalPath"]); base_metrics=compare_meshes(reference,base_mesh,samples=5000,seed=int(row["generationSeed"])); candidate_metrics=compare_meshes(reference,candidate_mesh,samples=5000,seed=int(row["generationSeed"])); regional=evaluate_regional_non_regression(base_metrics,candidate_metrics)
        base_crown=base_metrics["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]["symmetricChamferPercentDiagonal"]; candidate_crown=candidate_metrics["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]["symmetricChamferPercentDiagonal"]
        results.append({"id":row["id"],"baseMesh":str(base_path),"candidateMesh":str(candidate_path),"baseReceipt":base_receipt,"candidateReceipt":candidate_receipt,"baseMetrics":base_metrics,"candidateMetrics":candidate_metrics,"crownChamferRelativeImprovement":(base_crown-candidate_crown)/max(base_crown,1e-8),"regionalNonRegression":regional,"supportRootLogitsByteIdentical":torch.equal(candidate_logits[weights==0],base_logits[weights==0])}); checkpoint_volume.commit()
    improvements=[row["crownChamferRelativeImprovement"] for row in results]; passed=bool(float(np.median(improvements))>=0.05 and sum(value>0 for value in improvements)>=2 and all(row["regionalNonRegression"]["passed"] and row["supportRootLogitsByteIdentical"] for row in results))
    evidence={"schemaVersion":1,"valid":True,"stage":"E14-G2J-molar-decoder-qualification-v3","optimizerSteps":0,"caseCount":3,"shapeSamplerSteps":12,"sourceAdapterSha256":hashlib.sha256(source_path.read_bytes()).hexdigest(),"cases":results,"medianDecodedCrownChamferRelativeImprovement":float(np.median(improvements)),"casesImproved":sum(value>0 for value in improvements),"allRegionalNonRegressionPassed":all(row["regionalNonRegression"]["passed"] for row in results),"allSparseCoordinateGuardsExercised":all(row[role]["upsampleGuardCalls"]>=1 for row in results for role in ("baseReceipt","candidateReceipt")),"expertReviewPackAuthorized":passed,"g3Authorized":False,"clinicalClaimPermitted":False,"productionMutationPermitted":False}
    evidence_path.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit(); return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    cpu=16, memory=65536, timeout=60 * 60,
)
def qualify_e14_g2k_topology_preserving_crown_composition(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2k-topology-preserving-crown-composition-v1",
) -> dict:
    """Preserve baseline root/connectivity while transferring the G2J crown signal."""
    import numpy as np
    import trimesh

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2k-topology-preserving-crown-composition-v1":
        raise ValueError("E14 G2K is sealed")
    from scripts.crown_mesh_composition import compose_candidate_crown_onto_baseline
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh
    from scripts.regional_anatomy_gate import evaluate_regional_non_regression

    dataset_root=Path(f"/datasets/{dataset_name}")
    manifest=json.loads((dataset_root/"anatomy_manifest.json").read_text(encoding="utf-8"))
    assets={row["id"]:row for row in manifest["assets"]}
    source_root=Path("/checkpoints/stage1-e14-g2j-molar-decoder-qualification-v3")
    source_path=source_root/"g2j-evidence.json"
    source=json.loads(source_path.read_text(encoding="utf-8"))
    if not (source.get("valid") is True and source.get("caseCount")==3 and source.get("optimizerSteps")==0 and source.get("expertReviewPackAuthorized") is False):
        raise ValueError("G2K requires sealed rejected G2J v3 evidence")
    run_root=Path(f"/checkpoints/{run_name}"); evidence_path=run_root/"g2k-evidence.json"
    if evidence_path.is_file():
        existing=json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True: return {**existing,"resumed":True}
        raise ValueError("Existing G2K evidence is invalid")
    if run_root.exists(): raise FileExistsError("Partial G2K output exists")
    run_root.mkdir(parents=True,exist_ok=False)
    receipt={"schemaVersion":1,"stage":"E14-G2K-topology-preserving-crown-composition-v1","status":"started","optimizerSteps":0,"sourceEvidenceSha256":hashlib.sha256(source_path.read_bytes()).hexdigest(),"preregisteredComposition":{"protectedHeight":0.72,"fullTransferHeight":0.82,"maximumDisplacementFraction":0.05},"productionMutationPermitted":False}
    (run_root/"run-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit()

    results=[]
    for row in source["cases"]:
        case_id=row["id"]
        baseline=load_mesh(Path(row["baseMesh"])); candidate=load_mesh(Path(row["candidateMesh"]))
        reference=load_mesh(dataset_root/assets[case_id]["canonicalPath"])
        composed,composition=compose_candidate_crown_onto_baseline(baseline,candidate,protected_height=0.72,full_transfer_height=0.82,maximum_displacement_fraction=0.05)
        output=run_root/f"{case_id}-composed.ply"; composed.export(output)
        reloaded=trimesh.load(output,force="mesh",process=False)
        if not np.array_equal(np.asarray(reloaded.faces),np.asarray(baseline.faces)):
            raise RuntimeError("G2K exported connectivity drifted")
        seed=int(assets[case_id].get("generationSeed",20260924))
        base_metrics=compare_meshes(reference,baseline,samples=10000,seed=seed)
        composed_metrics=compare_meshes(reference,reloaded,samples=10000,seed=seed)
        base_crown=base_metrics["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]["symmetricChamferPercentDiagonal"]
        composed_crown=composed_metrics["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]["symmetricChamferPercentDiagonal"]
        results.append({"id":case_id,"baseMesh":row["baseMesh"],"candidateMesh":row["candidateMesh"],"composedMesh":str(output),"composedMeshSha256":hashlib.sha256(output.read_bytes()).hexdigest(),"composedVertexCount":int(len(reloaded.vertices)),"composedFaceCount":int(len(reloaded.faces)),"compositionReceipt":composition,"baseMetrics":base_metrics,"composedMetrics":composed_metrics,"crownChamferRelativeImprovement":(base_crown-composed_crown)/max(base_crown,1e-8),"legacyIndependentAlignmentRegionalGate":evaluate_regional_non_regression(base_metrics,composed_metrics),"structuralRootCervicalPreservationPassed":composition["protectedVerticesByteIdentical"] and composition["facesByteIdentical"]}); checkpoint_volume.commit()

    improvements=[row["crownChamferRelativeImprovement"] for row in results]
    structural=all(row["structuralRootCervicalPreservationPassed"] for row in results)
    positive=all(row["composedVertexCount"]>0 and row["composedFaceCount"]>0 for row in results)
    passed=bool(float(np.median(improvements))>=0.05 and sum(value>0 for value in improvements)>=2 and structural and positive)
    evidence={"schemaVersion":1,"valid":True,"stage":"E14-G2K-topology-preserving-crown-composition-v1","optimizerSteps":0,"caseCount":3,"sourceEvidenceSha256":receipt["sourceEvidenceSha256"],"composition":receipt["preregisteredComposition"],"cases":results,"medianComposedCrownChamferRelativeImprovement":float(np.median(improvements)),"casesImproved":sum(value>0 for value in improvements),"allStructuralRootCervicalPreservationPassed":structural,"allComposedMeshesPositive":positive,"legacyIndependentAlignmentRegionalGatesPassed":all(row["legacyIndependentAlignmentRegionalGate"]["passed"] for row in results),"expertEngineeringReviewPackAuthorized":passed,"clinicalClaimPermitted":False,"productionMutationPermitted":False}
    evidence_path.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit(); return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    cpu=16, memory=65536, timeout=60 * 60,
)
def qualify_e14_g2l_root_registered_crown_composition(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2l-root-registered-crown-composition-v1",
) -> dict:
    """Root-register the candidate before the fixed topology-preserving transfer."""
    import numpy as np
    import trimesh

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2l-root-registered-crown-composition-v1":
        raise ValueError("E14 G2L is sealed")
    from scripts.crown_mesh_composition import align_candidate_to_baseline_root, compose_candidate_crown_onto_baseline
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh
    from scripts.regional_anatomy_gate import evaluate_regional_non_regression

    dataset_root=Path(f"/datasets/{dataset_name}")
    manifest=json.loads((dataset_root/"anatomy_manifest.json").read_text(encoding="utf-8")); assets={row["id"]:row for row in manifest["assets"]}
    source_root=Path("/checkpoints/stage1-e14-g2j-molar-decoder-qualification-v3"); source_path=source_root/"g2j-evidence.json"; source=json.loads(source_path.read_text(encoding="utf-8"))
    g2k_path=Path("/checkpoints/stage1-e14-g2k-topology-preserving-crown-composition-v1/g2k-evidence.json"); g2k=json.loads(g2k_path.read_text(encoding="utf-8"))
    if not (source.get("valid") is True and source.get("caseCount")==3 and g2k.get("valid") is True and g2k.get("expertEngineeringReviewPackAuthorized") is False):
        raise ValueError("G2L requires sealed G2J and rejected G2K evidence")
    run_root=Path(f"/checkpoints/{run_name}"); evidence_path=run_root/"g2l-evidence.json"
    if evidence_path.is_file():
        existing=json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True: return {**existing,"resumed":True}
        raise ValueError("Existing G2L evidence is invalid")
    if run_root.exists(): raise FileExistsError("Partial G2L output exists")
    run_root.mkdir(parents=True,exist_ok=False)
    rule={"protectedHeight":0.72,"fullTransferHeight":0.82,"maximumDisplacementFraction":0.05,"registration":"rigid ICP on candidate/baseline vertices at or below protectedHeight","scaleApplied":False}
    receipt={"schemaVersion":1,"stage":"E14-G2L-root-registered-crown-composition-v1","status":"started","optimizerSteps":0,"sourceEvidenceSha256":hashlib.sha256(source_path.read_bytes()).hexdigest(),"rejectedG2kEvidenceSha256":hashlib.sha256(g2k_path.read_bytes()).hexdigest(),"preregisteredRule":rule,"productionMutationPermitted":False}
    (run_root/"run-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit()
    results=[]
    for row in source["cases"]:
        case_id=row["id"]; baseline=load_mesh(Path(row["baseMesh"])); candidate=load_mesh(Path(row["candidateMesh"])); reference=load_mesh(dataset_root/assets[case_id]["canonicalPath"])
        aligned,registration=align_candidate_to_baseline_root(baseline,candidate,protected_height=0.72,iterations=30,maximum_points=100000)
        composed,composition=compose_candidate_crown_onto_baseline(baseline,aligned,protected_height=0.72,full_transfer_height=0.82,maximum_displacement_fraction=0.05)
        output=run_root/f"{case_id}-root-registered-composed.ply"; composed.export(output); reloaded=trimesh.load(output,force="mesh",process=False)
        if not np.array_equal(np.asarray(reloaded.faces),np.asarray(baseline.faces)): raise RuntimeError("G2L exported connectivity drifted")
        seed=int(assets[case_id].get("generationSeed",20260924)); base_metrics=compare_meshes(reference,baseline,samples=10000,seed=seed); composed_metrics=compare_meshes(reference,reloaded,samples=10000,seed=seed)
        base_crown=base_metrics["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]["symmetricChamferPercentDiagonal"]; composed_crown=composed_metrics["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]["symmetricChamferPercentDiagonal"]
        results.append({"id":case_id,"baseMesh":row["baseMesh"],"candidateMesh":row["candidateMesh"],"composedMesh":str(output),"composedMeshSha256":hashlib.sha256(output.read_bytes()).hexdigest(),"composedVertexCount":int(len(reloaded.vertices)),"composedFaceCount":int(len(reloaded.faces)),"registrationReceipt":registration,"compositionReceipt":composition,"baseMetrics":base_metrics,"composedMetrics":composed_metrics,"crownChamferRelativeImprovement":(base_crown-composed_crown)/max(base_crown,1e-8),"legacyIndependentAlignmentRegionalGate":evaluate_regional_non_regression(base_metrics,composed_metrics),"structuralRootCervicalPreservationPassed":composition["protectedVerticesByteIdentical"] and composition["facesByteIdentical"]}); checkpoint_volume.commit()
    improvements=[row["crownChamferRelativeImprovement"] for row in results]; structural=all(row["structuralRootCervicalPreservationPassed"] for row in results); positive=all(row["composedVertexCount"]>0 and row["composedFaceCount"]>0 for row in results); passed=bool(float(np.median(improvements))>=0.05 and sum(value>0 for value in improvements)>=2 and structural and positive)
    evidence={"schemaVersion":1,"valid":True,"stage":"E14-G2L-root-registered-crown-composition-v1","optimizerSteps":0,"caseCount":3,"rule":rule,"cases":results,"medianComposedCrownChamferRelativeImprovement":float(np.median(improvements)),"casesImproved":sum(value>0 for value in improvements),"allStructuralRootCervicalPreservationPassed":structural,"allComposedMeshesPositive":positive,"legacyIndependentAlignmentRegionalGatesPassed":all(row["legacyIndependentAlignmentRegionalGate"]["passed"] for row in results),"expertEngineeringReviewPackAuthorized":passed,"clinicalClaimPermitted":False,"productionMutationPermitted":False}
    evidence_path.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit(); return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    cpu=16, memory=65536, timeout=60 * 60,
)
def qualify_e14_g2m_cut_stitch_crown_graft(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2m-cut-stitch-crown-graft-v2",
) -> dict:
    """Graft the actual root-registered candidate crown onto the baseline root."""
    import numpy as np
    import trimesh

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2m-cut-stitch-crown-graft-v2": raise ValueError("E14 G2M is sealed")
    from scripts.crown_mesh_composition import align_candidate_to_baseline_root
    from scripts.crown_mesh_graft import graft_candidate_crown
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh
    from scripts.regional_anatomy_gate import evaluate_regional_non_regression

    dataset_root=Path(f"/datasets/{dataset_name}"); manifest=json.loads((dataset_root/"anatomy_manifest.json").read_text(encoding="utf-8")); assets={row["id"]:row for row in manifest["assets"]}
    source_root=Path("/checkpoints/stage1-e14-g2j-molar-decoder-qualification-v3"); source_path=source_root/"g2j-evidence.json"; source=json.loads(source_path.read_text(encoding="utf-8"))
    g2l_path=Path("/checkpoints/stage1-e14-g2l-root-registered-crown-composition-v1/g2l-evidence.json"); g2l=json.loads(g2l_path.read_text(encoding="utf-8"))
    if not (source.get("valid") is True and source.get("caseCount")==3 and g2l.get("valid") is True and g2l.get("expertEngineeringReviewPackAuthorized") is False): raise ValueError("G2M requires sealed G2J and rejected G2L evidence")
    run_root=Path(f"/checkpoints/{run_name}"); evidence_path=run_root/"g2m-evidence.json"
    if evidence_path.is_file():
        existing=json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True: return {**existing,"resumed":True}
        raise ValueError("Existing G2M evidence is invalid")
    if run_root.exists(): raise FileExistsError("Partial G2M output exists")
    run_root.mkdir(parents=True,exist_ok=False)
    rule={"cutHeight":0.72,"registration":"rigid ICP on candidate/baseline protected root vertices","scaleApplied":False,"rootSource":"baseline geometry below cut","crownSource":"candidate geometry above cut","seam":"single-plane zipper stitch"}
    receipt={"schemaVersion":1,"stage":"E14-G2M-cut-stitch-crown-graft-v2","status":"started","optimizerSteps":0,"sourceEvidenceSha256":hashlib.sha256(source_path.read_bytes()).hexdigest(),"rejectedG2lEvidenceSha256":hashlib.sha256(g2l_path.read_bytes()).hexdigest(),"cutSurfaceConsolidation":"merge at 6 decimal digits; remove degenerate and duplicate faces","preregisteredRule":rule,"productionMutationPermitted":False}
    (run_root/"run-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit(); results=[]
    for row in source["cases"]:
        case_id=row["id"]; baseline=load_mesh(Path(row["baseMesh"])); candidate=load_mesh(Path(row["candidateMesh"])); reference=load_mesh(dataset_root/assets[case_id]["canonicalPath"])
        aligned,registration=align_candidate_to_baseline_root(baseline,candidate,protected_height=0.72,iterations=30,maximum_points=100000)
        graft,graft_receipt=graft_candidate_crown(baseline,aligned,cut_height=0.72)
        output=run_root/f"{case_id}-grafted.ply"; graft.export(output); reloaded=trimesh.load(output,force="mesh",process=False)
        seed=int(assets[case_id].get("generationSeed",20260924)); base_metrics=compare_meshes(reference,baseline,samples=10000,seed=seed); graft_metrics=compare_meshes(reference,reloaded,samples=10000,seed=seed)
        base_crown=base_metrics["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]["symmetricChamferPercentDiagonal"]; graft_crown=graft_metrics["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"]["symmetricChamferPercentDiagonal"]
        seam_passed=graft_receipt["boundaryEdgeCount"]==0 and graft_receipt["nonManifoldEdgeCount"]==0 and graft_receipt["watertight"]
        results.append({"id":case_id,"baseMesh":row["baseMesh"],"candidateMesh":row["candidateMesh"],"graftedMesh":str(output),"graftedMeshSha256":hashlib.sha256(output.read_bytes()).hexdigest(),"graftedVertexCount":int(len(reloaded.vertices)),"graftedFaceCount":int(len(reloaded.faces)),"registrationReceipt":registration,"graftReceipt":graft_receipt,"baseMetrics":base_metrics,"graftMetrics":graft_metrics,"crownChamferRelativeImprovement":(base_crown-graft_crown)/max(base_crown,1e-8),"regionalNonRegression":evaluate_regional_non_regression(base_metrics,graft_metrics),"seamTopologyPassed":seam_passed}); checkpoint_volume.commit()
    improvements=[row["crownChamferRelativeImprovement"] for row in results]; positive=all(row["graftedVertexCount"]>0 and row["graftedFaceCount"]>0 for row in results); seams=all(row["seamTopologyPassed"] for row in results); passed=bool(float(np.median(improvements))>=0.05 and sum(value>0 for value in improvements)>=2 and positive and seams)
    evidence={"schemaVersion":1,"valid":True,"stage":"E14-G2M-cut-stitch-crown-graft-v2","optimizerSteps":0,"caseCount":3,"rule":rule,"cases":results,"medianGraftedCrownChamferRelativeImprovement":float(np.median(improvements)),"casesImproved":sum(value>0 for value in improvements),"allGraftedMeshesPositive":positive,"allSeamTopologyPassed":seams,"allRegionalNonRegressionPassed":all(row["regionalNonRegression"]["passed"] for row in results),"expertEngineeringReviewPackAuthorized":passed,"clinicalClaimPermitted":False,"productionMutationPermitted":False}
    evidence_path.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit(); return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    gpu="L4", cpu=8, memory=32768, timeout=30 * 60,
)
def run_e14_g2e_signed_margin_canary(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2e-signed-margin-canary-v2",
) -> dict:
    """Run five signed-margin updates per family and measure real occupancy response."""
    import numpy as np
    import torch
    import torch.nn.functional as F
    from collections import defaultdict
    from scipy import ndimage

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2e-signed-margin-canary-v2":
        raise ValueError("E14 G2E signed-margin canary is sealed")
    dataset_root=Path(f"/datasets/{dataset_name}")
    cache_path=dataset_root/"stage1-e14-g2-frozen-base-support-v1/cache-evidence.json"
    g2b_path=Path("/checkpoints/stage1-e14-g2b-family-trust-region-v1/g2b-evidence.json")
    g2d_path=Path("/checkpoints/stage1-e14-g2d-response-margin-v1/g2d-evidence.json")
    cache=json.loads(cache_path.read_text(encoding="utf-8")); g2b=json.loads(g2b_path.read_text(encoding="utf-8")); g2d=json.loads(g2d_path.read_text(encoding="utf-8"))
    if not (cache.get("valid") is True and g2b.get("g2cResponseAuthorized") is True
            and g2d.get("objectiveRedesignRequired") is True and g2d.get("scaledCanaryAuthorized") is False):
        raise ValueError("E14 G2E requires sealed G2B and G2D evidence")
    run_root=Path(f"/checkpoints/{run_name}"); evidence_path=run_root/"g2e-evidence.json"
    if evidence_path.is_file():
        existing=json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True: return {**existing,"resumed":True}
        raise ValueError("Existing G2E evidence is invalid")
    if run_root.exists(): raise FileExistsError("Partial G2E output exists")
    run_root.mkdir(parents=True,exist_ok=False)
    torch.manual_seed(20260926); torch.cuda.manual_seed_all(20260926); torch.use_deterministic_algorithms(True)
    device=torch.device("cuda"); family_order=("incisor","canine","premolar","molar")

    class FamilyHead(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.net=torch.nn.Sequential(torch.nn.Conv3d(4,12,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(12,12,3,padding=1),torch.nn.SiLU(),torch.nn.Conv3d(12,1,1))
        def forward(self,logits):
            b,_,d,h,w=logits.shape; axes=[torch.linspace(-1,1,s,device=logits.device,dtype=logits.dtype) for s in (d,h,w)]
            grid=torch.stack(torch.meshgrid(*axes,indexing="ij"),dim=0).expand(b,-1,-1,-1,-1)
            return torch.tanh(self.net(torch.cat((torch.sigmoid(logits),grid),dim=1)))
    class FamilyRefiner(torch.nn.Module):
        def __init__(self): super().__init__(); self.heads=torch.nn.ModuleList([FamilyHead() for _ in family_order])
        def forward(self,logits,index): return self.heads[index](logits)
    def dense(coords):
        values=np.asarray(coords,dtype=np.int64); out=torch.zeros((1,1,32,32,32),dtype=torch.bool,device=device); out[0,0,values[:,0],values[:,1],values[:,2]]=True; return out
    def load(row):
        artifact=dataset_root/row["artifact"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest()!=row["artifactSha256"]: raise ValueError("G2E artifact drift")
        packed=np.load(artifact); return {"receipt":row,"base":dense(packed["base_coords"]),"reference":dense(packed["reference_coords"])}
    training=defaultdict(list); validation=[]
    for row in cache["cases"]:
        case=load(row); (training[row["toothFamily"]] if row["split"]=="train" else validation).append(case)
    model=FamilyRefiner().to(device); checkpoint=Path(g2b["checkpointArtifact"])
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=g2b["checkpointSha256"]: raise ValueError("G2B checkpoint drift")
    strict=model.load_state_dict(torch.load(checkpoint,map_location=device,weights_only=True)["state_dict"],strict=True)
    if strict.missing_keys or strict.unexpected_keys: raise RuntimeError("G2E strict load failed")
    optimizers=[torch.optim.AdamW(head.parameters(),lr=0.005,weight_decay=0.0) for head in model.heads]
    def logits_weights(case):
        weights,_=build_crown_transition_weights_from_occupancy(case["base"]); logits=torch.where(case["base"],torch.tensor(0.25,device=device),torch.tensor(-0.25,device=device)); return logits,weights.to(device)
    losses=[]
    for step in range(1,21):
        index=(step-1)%4; family=family_order[index]; case=training[family][((step-1)//4)%len(training[family])]
        base_logits,weights=logits_weights(case); target=case["reference"]; supervised=weights>0
        agreement=supervised&(case["base"]==target); disagreement=supervised&(case["base"]!=target)
        if not bool(disagreement.any()):
            raise RuntimeError(f"G2E has no signed-margin disagreements for {family} at step {step}")
        if not bool(agreement.any()):
            raise RuntimeError(f"G2E has no trust-region agreement voxels for {family} at step {step}")
        residual=model(base_logits,index); candidate=compose_crown_residual_logits(base_logits,residual,weights)
        target_sign=torch.where(target,torch.tensor(1.0,device=device),torch.tensor(-1.0,device=device))
        signed_margin=F.relu(0.10-target_sign[disagreement]*candidate[disagreement]).mean()
        preservation=F.mse_loss(candidate[agreement],base_logits[agreement]); penalty=torch.mean((residual[supervised]*weights[supervised])**2)
        loss=signed_margin+8.0*preservation+0.25*penalty; optimizers[index].zero_grad(set_to_none=True); loss.backward()
        if not bool(torch.isfinite(loss)) or not all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.heads[index].parameters()): raise RuntimeError(f"G2E finite gate failed at {step}")
        optimizers[index].step(); losses.append({"step":step,"family":family,"loss":float(loss.detach()),"signedMargin":float(signed_margin.detach()),"preservation":float(preservation.detach())})
    model.eval(); receipts=[]
    with torch.no_grad():
        for case in validation:
            family=case["receipt"]["toothFamily"]; index=family_order.index(family); base_logits,weights=logits_weights(case); target=case["reference"]
            residual=model(base_logits,index); candidate=compose_crown_residual_logits(base_logits,residual,weights); repeated=compose_crown_residual_logits(base_logits,model(base_logits,index),weights)
            supervised=weights>0; disagreement=supervised&(case["base"]!=target); sign=torch.where(target,torch.tensor(1.0,device=device),torch.tensor(-1.0,device=device))
            if not bool(disagreement.any()):
                raise RuntimeError(f"G2E validation case {case['receipt']['id']} has no supervised disagreements")
            base_binary=case["base"][0,0].cpu().numpy(); candidate_binary=(candidate[0,0]>=0).cpu().numpy(); labels,count=ndimage.label(candidate_binary,structure=ndimage.generate_binary_structure(3,1))
            base_labels,base_count=ndimage.label(base_binary,structure=ndimage.generate_binary_structure(3,1))
            receipts.append({"id":case["receipt"]["id"],"toothFamily":family,
                "directionalAgreement":float(((residual[disagreement]*sign[disagreement])>0).float().mean()),
                "occupancyCrossingCount":int(np.count_nonzero(candidate_binary!=base_binary)),
                "maximumAbsoluteResidual":float(residual[supervised].abs().max()),
                "rootLogitsByteIdentical":torch.equal(candidate[weights==0],base_logits[weights==0]),
                "rawDecodeExactRepeat":torch.equal(candidate,repeated),
                "candidateOccupiedVoxelCount":int(np.count_nonzero(candidate_binary)),
                "candidateComponentCount":int(count),
                "baseComponentCount":int(base_count),
                "topologyPassed":int(np.count_nonzero(candidate_binary))>0 and 0<int(count)<=int(base_count)})
    family_summary={f:{"medianDirectionalAgreement":float(np.median([r["directionalAgreement"] for r in receipts if r["toothFamily"]==f])),"totalOccupancyCrossings":sum(r["occupancyCrossingCount"] for r in receipts if r["toothFamily"]==f)} for f in family_order}
    passed=bool(family_summary["premolar"]["medianDirectionalAgreement"]>=0.65 and family_summary["molar"]["medianDirectionalAgreement"]>=0.60
                and family_summary["premolar"]["totalOccupancyCrossings"]>0 and family_summary["molar"]["totalOccupancyCrossings"]>0
                and all(r["rootLogitsByteIdentical"] and r["rawDecodeExactRepeat"] and r["topologyPassed"] for r in receipts))
    candidate_path=run_root/"signed-margin-step-20.pt"; torch.save({"state_dict":model.state_dict(),"familyOrder":family_order,"optimizerSteps":20},candidate_path)
    verification=FamilyRefiner().to(device); reload_result=verification.load_state_dict(torch.load(candidate_path,map_location=device,weights_only=True)["state_dict"],strict=True); strict_reload=not reload_result.missing_keys and not reload_result.unexpected_keys; passed=passed and strict_reload
    evidence={"schemaVersion":1,"valid":True,"stage":"E14-G2E-signed-margin-canary-v2","optimizerSteps":20,"stepsPerFamily":5,"learningRate":0.005,"signedMargin":0.10,"trustRegionWeight":8.0,"gpuClass":"L4","losses":losses,"receipts":receipts,"familySummary":family_summary,"checkpointReloadedStrict":strict_reload,"checkpointArtifact":str(candidate_path),"checkpointSha256":hashlib.sha256(candidate_path.read_bytes()).hexdigest(),"g2fAuthorized":passed,"g3Authorized":False,"clinicalClaimPermitted":False,"productionMutationPermitted":False}
    evidence_path.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8"); checkpoint_volume.commit(); return evidence


@app.function(
    image=e12_training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def run_e12_v7_late_delta_hybrid_screen(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e12-g1-one-tooth-v7",
    samples: int = 5000,
    candidate_scope: str = "late",
) -> dict:
    """Screen a sealed subset of the rejected v7 delta without training."""
    import sys
    import numpy as np
    import torch
    import trimesh

    if (
        (dataset_name, run_name, samples) !=
        ("toothfairy-stage1-v1", "stage1-e12-g1-one-tooth-v7", 5000)
        or candidate_scope not in {"late", "output-only", "block3-only"}
    ):
        raise ValueError("E12 late-delta hybrid screen is sealed")
    root = Path(f"/datasets/{dataset_name}")
    run_root = Path(f"/checkpoints/{run_name}")
    scope_contract = {
        "late": {
            "prefixes": ("blocks.3.", "output_layer."),
            "tensorCount": 42,
            "outputDirectory": "late-delta-hybrid-screen-v1",
            "evidenceFile": "late-delta-hybrid-evidence-v1.json",
            "stage": "E12-v7-late-delta-hybrid-screen-v1",
            "role": "base-plus-v7-late-delta",
        },
        "output-only": {
            "prefixes": ("output_layer.",),
            "tensorCount": 2,
            "outputDirectory": "output-only-delta-screen-v1",
            "evidenceFile": "output-only-delta-evidence-v1.json",
            "stage": "E12-v7-output-only-delta-screen-v1",
            "role": "base-plus-v7-output-only-delta",
        },
        "block3-only": {
            "prefixes": ("blocks.3.",),
            "tensorCount": 40,
            "outputDirectory": "block3-only-delta-screen-v1",
            "evidenceFile": "block3-only-delta-evidence-v1.json",
            "stage": "E12-v7-block3-only-delta-screen-v1",
            "role": "base-plus-v7-block3-only-delta",
        },
    }[candidate_scope]
    evidence_path = run_root / scope_contract["evidenceFile"]
    if evidence_path.is_file():
        return {**json.loads(evidence_path.read_text(encoding="utf-8")), "resumed": True}
    localization = json.loads(
        (run_root / "decoder-update-localization-v1.json").read_text(encoding="utf-8")
    )
    rejected_g2 = json.loads((run_root / "g2-evidence-v2.json").read_text(encoding="utf-8"))
    if (
        localization.get("lateDeltaHybridAuthorized") is not True
        or localization.get("optimizerSteps") != 0
        or rejected_g2.get("e13Authorized") is not False
        or rejected_g2.get("summary", {}).get("passed") is not False
    ):
        raise ValueError("E12 late-delta hybrid requires sealed localization and rejected G2")
    if candidate_scope == "output-only":
        late_evidence = json.loads(
            (run_root / "late-delta-hybrid-evidence-v1.json").read_text(encoding="utf-8")
        )
        if (
            late_evidence.get("optimizerSteps") != 0
            or late_evidence.get("e13Authorized") is not False
            or late_evidence.get("summary", {}).get("passed") is not False
        ):
            raise ValueError("E12 output-only screen requires the sealed rejected late hybrid")
    if candidate_scope == "block3-only":
        output_evidence = json.loads(
            (run_root / "output-only-delta-evidence-v1.json").read_text(encoding="utf-8")
        )
        if (
            output_evidence.get("optimizerSteps") != 0
            or output_evidence.get("e13Authorized") is not False
            or output_evidence.get("summary", {}).get("passed") is not False
        ):
            raise ValueError("E12 block3-only screen requires rejected output-only evidence")
    base_path = run_root / "base-decoder.pt"
    candidate_path = run_root / "ckpts/decoder_ema0.9999_step0000001.pt"
    if any(not path.is_file() or path.stat().st_size == 0 for path in (base_path, candidate_path)):
        raise FileNotFoundError("E12 late-delta hybrid checkpoint is missing")
    if hashlib.sha256(base_path.read_bytes()).hexdigest() != localization["baseDecoderSha256"]:
        raise RuntimeError("E12 late-delta base checkpoint hash drifted")
    if hashlib.sha256(candidate_path.read_bytes()).hexdigest() != localization["candidateDecoderSha256"]:
        raise RuntimeError("E12 late-delta candidate checkpoint hash drifted")
    baseline = rejected_g2.get("baseline", [])
    if len(baseline) != 4:
        raise ValueError("E12 late-delta hybrid requires four sealed base receipts")
    manifest = json.loads((root / "anatomy_manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((root / "stage1_validation_inputs_v1.json").read_text(encoding="utf-8"))
    cases = resolve_e12_g2_validation_cases(
        validation, manifest, ("incisor", "canine", "premolar", "molar")
    )

    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh
    from trellis2.modules.sparse import SparseTensor

    generator = TrellisGenerator()
    generator.load_model()
    decoder = generator.pipeline.models["shape_slat_decoder"]
    decoder.set_resolution(512)
    base_state = torch.load(base_path, map_location="cpu", weights_only=True)
    candidate_state = torch.load(candidate_path, map_location="cpu", weights_only=True)
    hybrid_state, late_keys = build_e12_late_delta_hybrid_state(
        base_state, candidate_state, scope_contract["prefixes"]
    )
    if len(late_keys) != scope_contract["tensorCount"]:
        raise RuntimeError(
            f"E12 {candidate_scope} expected {scope_contract['tensorCount']} "
            f"candidate tensors, found {len(late_keys)}"
        )
    decoder.load_state_dict(hybrid_state, strict=True)
    decoder.eval()

    def tensor_hash(tensor: torch.Tensor) -> str:
        return hashlib.sha256(tensor.detach().cpu().contiguous().numpy().tobytes()).hexdigest()

    def load_latent(case: dict) -> tuple[torch.Tensor, torch.Tensor, str]:
        latent_path = root / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512" / f"{case['canonicalSha256']}.npz"
        packed = np.load(latent_path)
        feats = torch.from_numpy(packed["feats"]).cuda()
        coords = torch.from_numpy(packed["coords"].astype(np.int32)).cuda()
        coords = torch.cat([torch.zeros_like(coords[:, :1]), coords], dim=1)
        return feats, coords, hashlib.sha256(latent_path.read_bytes()).hexdigest()

    def decode_once(feats: torch.Tensor, coords: torch.Tensor) -> tuple[trimesh.Trimesh, dict]:
        latent = SparseTensor(feats=feats, coords=coords)
        with torch.inference_mode():
            meshes, _ = generator.pipeline.decode_shape_slat(latent, 512)
        raw = meshes[0]
        boundary = {
            "inputLatentSha256": hashlib.sha256(
                feats.detach().cpu().contiguous().numpy().tobytes()
                + coords.detach().cpu().contiguous().numpy().tobytes()
            ).hexdigest(),
            "rawVerticesSha256": tensor_hash(raw.vertices),
            "rawFacesSha256": tensor_hash(raw.faces),
        }
        mesh = trimesh.Trimesh(
            vertices=raw.vertices.detach().cpu().numpy(),
            faces=raw.faces.detach().cpu().numpy(), process=False,
        )
        if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
            raise RuntimeError("E12 late-delta hybrid decoded an empty mesh")
        del meshes, raw, latent
        torch.cuda.empty_cache()
        return mesh, boundary

    output_root = run_root / scope_contract["outputDirectory"]
    output_root.mkdir(exist_ok=False)
    receipts = []
    for case in cases:
        feats, coords, latent_file_hash = load_latent(case)
        input_hash = hashlib.sha256(
            feats.detach().cpu().contiguous().numpy().tobytes()
            + coords.detach().cpu().contiguous().numpy().tobytes()
        ).hexdigest()
        mesh, boundary = decode_once(feats, coords)
        _, repeated = decode_once(feats, coords)
        if boundary != repeated:
            raise RuntimeError(f"E12 late-delta repeatability failed for {case['id']}")
        mesh_path = output_root / f"{case['id']}.ply"
        mesh_path.write_bytes(mesh.export(file_type="ply", encoding="binary"))
        reference = load_mesh(root / case["referenceMesh"])
        receipt = {
            "schemaVersion": 1, "id": case["id"],
            "toothFamily": case["toothFamily"], "groupId": case["groupId"],
            "modelRole": scope_contract["role"],
            "frozenLatentSha256": input_hash, "latentArtifactSha256": latent_file_hash,
            "boundary": boundary, "repeatability": {"rawShapeExact": True},
            "metrics": compare_meshes(
                reference, mesh, samples=samples, seed=int(case["generationSeed"])
            ),
            "topology": analyze_mesh_with_weld_control(mesh),
            "meshArtifact": str(mesh_path),
            "meshArtifactSha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
            "vertexCount": int(len(mesh.vertices)), "faceCount": int(len(mesh.faces)),
        }
        (output_root / f"{case['id']}.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        receipts.append(receipt)
        checkpoint_volume.commit()
        del feats, coords, mesh, reference
        torch.cuda.empty_cache()

    summary = summarize_e12_g2_decoder_screen(baseline, receipts)
    evidence = {
        "schemaVersion": 1, "valid": True,
        "stage": scope_contract["stage"],
        "runName": run_name, "optimizerSteps": 0,
        "baseDecoderSha256": localization["baseDecoderSha256"],
        "sourceCandidateDecoderSha256": localization["candidateDecoderSha256"],
        "hybridTensorCount": len(hybrid_state), "candidateLateTensorCount": len(late_keys),
        "candidateScope": candidate_scope,
        "candidateLatePrefixes": [f"{prefix}*" for prefix in scope_contract["prefixes"]],
        "baseline": baseline, "candidate": receipts, "summary": summary,
        "e13Authorized": summary["e13Authorized"],
        "clinicalClaimPermitted": False, "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


def decoded_occupancy_flow_source(source: str) -> str:
    """Add a frozen inference-decoder occupancy surrogate to the pinned flow loss."""
    import_original = "from ...utils.general_utils import dict_reduce"
    import_replacement = import_original + "\nfrom ... import models"
    if source.count(import_original) != 1:
        raise ValueError("Pinned flow imports changed; refusing occupancy patch")
    source = source.replace(import_original, import_replacement)

    init_original = "        super().__init__(*args, **kwargs)\n        self.t_schedule = t_schedule"
    init_replacement = (
        "        super().__init__(*args, **kwargs)\n"
        "        self.dentalsculptor_occupancy_target_ratio = float(kwargs.get(\n"
        "            'dentalsculptor_occupancy_target_ratio', 0.0\n"
        "        ))\n"
        "        self.dentalsculptor_occupancy_scale_min = float(kwargs.get(\n"
        "            'dentalsculptor_occupancy_scale_min', 1e-4\n"
        "        ))\n"
        "        self.dentalsculptor_occupancy_scale_max = float(kwargs.get(\n"
        "            'dentalsculptor_occupancy_scale_max', 100.0\n"
        "        ))\n"
        "        self.dentalsculptor_occupancy_temperature = float(kwargs.get(\n"
        "            'dentalsculptor_occupancy_temperature', 1.0\n"
        "        ))\n"
        "        decoder_name = kwargs.get('dentalsculptor_occupancy_decoder')\n"
        "        if not 0.0 < self.dentalsculptor_occupancy_target_ratio <= 0.25:\n"
        "            raise ValueError('DentalSculptor occupancy target ratio must be in (0, 0.25]')\n"
        "        if not 0.0 < self.dentalsculptor_occupancy_scale_min <= self.dentalsculptor_occupancy_scale_max:\n"
        "            raise ValueError('DentalSculptor occupancy scale bounds are invalid')\n"
        "        if self.dentalsculptor_occupancy_temperature <= 0.0:\n"
        "            raise ValueError('DentalSculptor occupancy temperature must be positive')\n"
        "        if not decoder_name:\n"
        "            raise ValueError('DentalSculptor occupancy decoder must be pinned')\n"
        "        self.dentalsculptor_occupancy_decoder = models.from_pretrained(\n"
        "            decoder_name\n"
        "        ).cuda().eval().requires_grad_(False)\n"
        "        self.t_schedule = t_schedule"
    )
    if source.count(init_original) != 1:
        raise ValueError("Pinned flow trainer initialization changed; refusing occupancy patch")
    source = source.replace(init_original, init_replacement)

    loss_original = (
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"loss\"] = terms[\"mse\"]"
    )
    loss_replacement = (
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        student_x0 = (1 - self.sigma_min) * noise - pred\n"
        "        student_logits = self.dentalsculptor_occupancy_decoder(student_x0)\n"
        "        with torch.no_grad():\n"
        "            target_logits = self.dentalsculptor_occupancy_decoder(x_0)\n"
        "            target_occupancy = (target_logits > 0).float()\n"
        "        temperature = self.dentalsculptor_occupancy_temperature\n"
        "        logits_fp32 = student_logits.float() / temperature\n"
        "        probabilities = torch.sigmoid(logits_fp32)\n"
        "        occupancy_bce = F.binary_cross_entropy_with_logits(\n"
        "            logits_fp32, target_occupancy\n"
        "        )\n"
        "        spatial_dims = tuple(range(1, probabilities.ndim))\n"
        "        intersection = (probabilities * target_occupancy).sum(dim=spatial_dims)\n"
        "        denominator = (probabilities + target_occupancy).sum(dim=spatial_dims)\n"
        "        occupancy_dice = ((2 * intersection + 1.0) / (denominator + 1.0)).mean()\n"
        "        occupancy_raw = occupancy_bce + (1.0 - occupancy_dice)\n"
        "        desired = self.dentalsculptor_occupancy_target_ratio * terms[\"mse\"].detach()\n"
        "        occupancy_scale = (desired / occupancy_raw.detach().clamp_min(1e-12)).clamp(\n"
        "            min=self.dentalsculptor_occupancy_scale_min,\n"
        "            max=self.dentalsculptor_occupancy_scale_max,\n"
        "        )\n"
        "        terms[\"occupancy_bce\"] = occupancy_bce\n"
        "        terms[\"occupancy_dice\"] = occupancy_dice\n"
        "        terms[\"occupancy_raw\"] = occupancy_raw\n"
        "        terms[\"occupancy_scale\"] = occupancy_scale\n"
        "        terms[\"occupancy_contribution\"] = occupancy_scale * occupancy_raw\n"
        "        terms[\"occupancy_share\"] = (\n"
        "            terms[\"occupancy_contribution\"] / terms[\"mse\"].detach().clamp_min(1e-12)\n"
        "        )\n"
        "        terms[\"loss\"] = terms[\"mse\"] + terms[\"occupancy_contribution\"]"
    )
    if source.count(loss_original) != 1:
        raise ValueError("Pinned flow loss path changed; refusing occupancy patch")
    return source.replace(loss_original, loss_replacement)


def e9_gradient_diagnostic_flow_source(source: str) -> str:
    """Instrument the pinned loss for zero-update occupancy-gradient diagnostics."""
    import_original = "from ...utils.general_utils import dict_reduce"
    if source.count(import_original) != 1:
        raise ValueError("Pinned flow imports changed; refusing E9 diagnostic patch")
    source = source.replace(import_original, import_original + "\nfrom ... import models")

    init_original = "        super().__init__(*args, **kwargs)\n        self.t_schedule = t_schedule"
    init_replacement = (
        "        super().__init__(*args, **kwargs)\n"
        "        diagnostic_timesteps = kwargs.get('dentalsculptor_diagnostic_timesteps')\n"
        "        decoder_name = kwargs.get('dentalsculptor_occupancy_decoder')\n"
        "        expected = [0.05, 0.25, 0.5, 0.75, 0.95]\n"
        "        if diagnostic_timesteps != expected:\n"
        "            raise ValueError('DentalSculptor E9 timesteps must match the sealed contract')\n"
        "        if not decoder_name:\n"
        "            raise ValueError('DentalSculptor E9 decoder must be pinned')\n"
        "        self.dentalsculptor_diagnostic_timesteps = diagnostic_timesteps\n"
        "        self.dentalsculptor_diagnostic_index = 0\n"
        "        self.dentalsculptor_occupancy_decoder = models.from_pretrained(\n"
        "            decoder_name\n"
        "        ).cuda().eval().requires_grad_(False)\n"
        "        self.t_schedule = t_schedule"
    )
    if source.count(init_original) != 1:
        raise ValueError("Pinned flow initialization changed; refusing E9 diagnostic patch")
    source = source.replace(init_original, init_replacement)

    time_original = "        t = self.sample_t(x_0.shape[0]).to(x_0.device).float()"
    time_replacement = (
        "        diagnostic_index = self.dentalsculptor_diagnostic_index\n"
        "        if diagnostic_index >= len(self.dentalsculptor_diagnostic_timesteps):\n"
        "            raise RuntimeError('DentalSculptor E9 received more steps than registered')\n"
        "        diagnostic_t = self.dentalsculptor_diagnostic_timesteps[diagnostic_index]\n"
        "        self.dentalsculptor_diagnostic_index += 1\n"
        "        t = torch.full(\n"
        "            (x_0.shape[0],), diagnostic_t, device=x_0.device, dtype=torch.float32\n"
        "        )"
    )
    if source.count(time_original) != 1:
        raise ValueError("Pinned flow timestep sampling changed; refusing E9 diagnostic patch")
    source = source.replace(time_original, time_replacement)

    loss_original = (
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        terms[\"loss\"] = terms[\"mse\"]"
    )
    loss_replacement = (
        "        terms[\"mse\"] = F.mse_loss(pred, target)\n"
        "        student_x0 = (1 - self.sigma_min) * noise - pred\n"
        "        student_logits = self.dentalsculptor_occupancy_decoder(student_x0)\n"
        "        with torch.no_grad():\n"
        "            target_logits = self.dentalsculptor_occupancy_decoder(x_0)\n"
        "            target_occupancy = (target_logits > 0).float()\n"
        "        logits_fp32 = student_logits.float()\n"
        "        probabilities = torch.sigmoid(logits_fp32)\n"
        "        occupancy_bce = F.binary_cross_entropy_with_logits(logits_fp32, target_occupancy)\n"
        "        spatial_dims = tuple(range(1, probabilities.ndim))\n"
        "        intersection = (probabilities * target_occupancy).sum(dim=spatial_dims)\n"
        "        denominator = (probabilities + target_occupancy).sum(dim=spatial_dims)\n"
        "        occupancy_dice = ((2 * intersection + 1.0) / (denominator + 1.0)).mean()\n"
        "        occupancy_raw = occupancy_bce + (1.0 - occupancy_dice)\n"
        "        mse_gradient = torch.autograd.grad(\n"
        "            terms[\"mse\"], pred, retain_graph=True, create_graph=False\n"
        "        )[0].detach().float()\n"
        "        occupancy_gradient = torch.autograd.grad(\n"
        "            occupancy_raw, pred, retain_graph=True, create_graph=False\n"
        "        )[0].detach().float()\n"
        "        mse_norm = torch.linalg.vector_norm(mse_gradient).clamp_min(1e-12)\n"
        "        occupancy_norm = torch.linalg.vector_norm(occupancy_gradient).clamp_min(1e-12)\n"
        "        gradient_cosine = torch.sum(mse_gradient * occupancy_gradient) / (mse_norm * occupancy_norm)\n"
        "        terms[\"diagnostic_t\"] = torch.tensor(\n"
        "            diagnostic_t, device=pred.device, dtype=torch.float32\n"
        "        )\n"
        "        terms[\"occupancy_bce\"] = occupancy_bce.detach()\n"
        "        terms[\"occupancy_dice\"] = occupancy_dice.detach()\n"
        "        terms[\"occupancy_raw\"] = occupancy_raw.detach()\n"
        "        terms[\"mse_gradient_norm\"] = mse_norm\n"
        "        terms[\"occupancy_gradient_norm\"] = occupancy_norm\n"
        "        terms[\"occupancy_to_mse_gradient_norm_ratio\"] = occupancy_norm / mse_norm\n"
        "        terms[\"gradient_cosine_similarity\"] = gradient_cosine\n"
        "        terms[\"loss\"] = terms[\"mse\"]"
    )
    if source.count(loss_original) != 1:
        raise ValueError("Pinned flow loss changed; refusing E9 diagnostic patch")
    return source.replace(loss_original, loss_replacement)


def checkpoint_relative_l2(base_path: Path, candidate_path: Path) -> float:
    """Measure candidate parameter displacement from base using mmap checkpoints."""
    import torch

    base = torch.load(base_path, map_location="cpu", weights_only=True, mmap=True)
    candidate = torch.load(candidate_path, map_location="cpu", weights_only=True, mmap=True)
    missing = set(base) - set(candidate)
    extra = set(candidate) - set(base)
    if missing or extra - {"rope_phases"}:
        raise ValueError(f"Checkpoint schema mismatch: missing={missing}, extra={extra}")
    anchor_sq = 0.0
    update_sq = 0.0
    for key in base:
        if not base[key].is_floating_point():
            if not base[key].equal(candidate[key]):
                raise ValueError(f"Non-floating checkpoint entry changed: {key}")
            continue
        anchor = base[key].float()
        changed = candidate[key].float()
        anchor_sq += float(anchor.square().sum().item())
        update_sq += float(changed.sub(anchor).square().sum().item())
    if anchor_sq <= 0.0:
        raise ValueError("Base checkpoint has zero floating-point norm")
    return math.sqrt(update_sq / anchor_sq)


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    timeout=60 * 60,
)
def prepare_training_smoke_inputs(
    dataset_name: str = "dental-anatomy-v1",
    per_family: int = 2,
    num_cond_views: int = 24,
) -> dict:
    """Seal and persist the minimum four-family dataset used by the H100 gate."""
    import shutil
    import sys
    import numpy as np

    sys.path.insert(0, "/root")
    from scripts.diagnose_conditional_render import select_family_canary_assets
    from scripts.preprocess_anatomy_trellis import ensure_data_toolkit, install_dataset_module
    from scripts.render_conditional_batches import render_selected_assets, validate_selected

    if per_family != 2:
        raise ValueError("The v1 smoke contract requires exactly two assets per family (8 total).")
    root = Path(f"/datasets/{dataset_name}")
    selected = select_family_canary_assets(
        root / "metadata.csv", per_family=per_family, required_split="train"
    )
    passed, failed = validate_selected(root, selected, num_cond_views)
    if not failed and len(passed) == len(selected):
        rendered = {
            "valid": True, "successfulCount": len(passed), "failedCount": 0,
            "assets": passed, "failures": [], "processError": None,
            "reusedPersistedRenders": True,
        }
    else:
        toolkit = ensure_data_toolkit(Path(TRELLIS2_PATH))
        install_dataset_module(Path(TRELLIS2_PATH), Path("/root/scripts"))
        rendered = render_selected_assets(
            toolkit=toolkit, dataset_root=root, subset="DentalAnatomy",
            rows=selected, num_cond_views=num_cond_views,
        )
    if not rendered["valid"]:
        dataset_volume.commit()
        raise RuntimeError(f"Smoke render selection failed: {json.dumps(rendered)}")

    smoke = root / "smoke_training_v1"
    if smoke.exists():
        shutil.rmtree(smoke)
    base = smoke / "base"
    latent = smoke / "shape_latent"
    render = smoke / "render_cond"
    for folder in (base, latent, render):
        folder.mkdir(parents=True, exist_ok=True)
    fieldnames = list(selected[0])
    for required in ("shape_latent_encoded", "shape_latent_tokens", "cond_rendered"):
        if required not in fieldnames:
            fieldnames.append(required)
    for row in selected:
        row["shape_latent_encoded"] = "True"
        row["cond_rendered"] = "True"
        digest = row["sha256"]
        source_latent = root / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512" / f"{digest}.npz"
        if not source_latent.is_file():
            raise FileNotFoundError(f"Missing smoke latent: {source_latent}")
        with np.load(source_latent) as packed_latent:
            if "coords" not in packed_latent:
                raise ValueError(f"Smoke latent has no coords array: {source_latent}")
            token_count = int(packed_latent["coords"].shape[0])
        if token_count <= 0:
            raise ValueError(f"Smoke latent has no tokens: {source_latent}")
        row["shape_latent_tokens"] = str(token_count)
        shutil.copy2(source_latent, latent / source_latent.name)
        shutil.copytree(root / "renders_cond" / digest, render / digest)
    for folder in (base, latent, render):
        with (folder / "metadata.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(selected)
    if any(row.get("split") != "train" for row in selected):
        raise ValueError("Smoke cohort contains a non-training asset.")
    receipt = {
        "schemaVersion": 1, "valid": True, "assetCount": len(selected),
        "perFamily": per_family, "numCondViews": num_cond_views,
        "reusedPersistedRenders": rendered.get("reusedPersistedRenders", False),
        "assets": [{
            "sha256": row["sha256"],
            "family": row["caption"].split()[-1].lower(),
            "split": row["split"],
            "shapeLatentTokens": int(row["shape_latent_tokens"]),
        } for row in selected],
    }
    (smoke / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return receipt


@app.function(
    image=preprocess_image,
    volumes={"/datasets": dataset_volume},
    timeout=30 * 60,
)
def prepare_e7_sparse_anchor_inputs(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    per_family: int = 2,
) -> dict:
    """Materialize an immutable two-per-family sparse anchor cohort for E7."""
    import shutil
    import sys

    sys.path.insert(0, "/root")
    from scripts.diagnose_conditional_render import select_family_canary_assets

    if dataset_name != "toothfairy-tf-pw32-v1" or per_family != 2:
        raise ValueError("The E7 anchor contract is sealed at TF-PW32 with two assets per family")
    root = Path(f"/datasets/{dataset_name}")
    sparse_receipt_path = root / "e3_sparse_structure_latent_receipt.json"
    if not sparse_receipt_path.is_file():
        raise FileNotFoundError("Validated sparse-latent receipt is required")
    sparse_receipt = json.loads(sparse_receipt_path.read_text(encoding="utf-8"))
    if not sparse_receipt.get("valid") or sparse_receipt.get("observedCount") != 32:
        raise ValueError("E7 requires the validated 32/32 sparse-latent cohort")

    selected = select_family_canary_assets(
        root / "metadata.csv", per_family=per_family, required_split="train"
    )
    anchor = root / "sparse_anchor_v1"
    receipt_path = anchor / "receipt.json"
    if receipt_path.is_file():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("assetCount") == 8:
            return {**existing, "resumed": True}
        raise ValueError("Existing E7 sparse anchor receipt is invalid; do not overwrite")
    if anchor.exists():
        raise FileExistsError("Partial E7 sparse anchor exists; inspect before retrying")

    base = anchor / "base"
    latent = anchor / "ss_latent"
    render = anchor / "render_cond"
    for folder in (base, latent, render):
        folder.mkdir(parents=True, exist_ok=False)
    fieldnames = list(selected[0])
    for required in ("ss_latent_encoded", "cond_rendered"):
        if required not in fieldnames:
            fieldnames.append(required)
    assets = []
    for row in selected:
        digest = row["sha256"]
        source_latent = root / "ss_latents" / "ss_enc_conv3d_16l8_fp16_64" / f"{digest}.npz"
        source_render = root / "renders_cond" / digest
        if not source_latent.is_file() or source_latent.stat().st_size == 0:
            raise FileNotFoundError(f"Missing E7 sparse anchor latent: {source_latent}")
        if not source_render.is_dir() or not (source_render / "transforms.json").is_file():
            raise FileNotFoundError(f"Missing E7 sparse anchor render: {source_render}")
        row["ss_latent_encoded"] = "True"
        row["cond_rendered"] = "True"
        shutil.copy2(source_latent, latent / source_latent.name)
        shutil.copytree(source_render, render / digest)
        assets.append({
            "sha256": digest,
            "family": row["caption"].split()[-1].lower(),
            "split": row["split"],
            "sparseLatentSha256": hashlib.sha256(source_latent.read_bytes()).hexdigest(),
        })
    for folder in (base, latent, render):
        with (folder / "metadata.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(selected)
    family_counts = {
        family: sum(asset["family"] == family for asset in assets)
        for family in ("incisor", "canine", "premolar", "molar")
    }
    if family_counts != {family: 2 for family in family_counts}:
        raise ValueError(f"E7 anchor family balance failed: {family_counts}")
    cohort_digest = hashlib.sha256(
        "\n".join(f"{item['sha256']}:{item['sparseLatentSha256']}" for item in assets).encode()
    ).hexdigest()
    receipt = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E7-frozen-family-balanced-sparse-anchor",
        "datasetName": dataset_name,
        "assetCount": 8,
        "perFamily": per_family,
        "familyCounts": family_counts,
        "selectionOrder": ["incisor", "canine", "premolar", "molar"],
        "cohortSha256": cohort_digest,
        "assets": assets,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return receipt


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    timeout=60 * 60,
)
def validate_e3_sparse_training_runtime(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "e3-sparse-runtime-v2",
) -> dict:
    """Run the official sparse-flow trainer in tryrun mode; no optimizer step."""
    if dataset_name != "toothfairy-tf-pw32-v1" or run_name != "e3-sparse-runtime-v2":
        raise ValueError("The E3 sparse runtime contract is sealed")
    root = Path(f"/datasets/{dataset_name}")
    sparse_receipt = root / "e3_sparse_structure_latent_receipt.json"
    if not sparse_receipt.is_file():
        raise FileNotFoundError("Run prepare_e3_sparse_structure_latents first")
    sparse = json.loads(sparse_receipt.read_text(encoding="utf-8"))
    if not sparse.get("valid") or sparse.get("observedCount") != 32:
        raise ValueError("Sparse-latent receipt does not satisfy the 32/32 contract")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "runtime-evidence.json"
    if evidence_path.exists():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid"):
            return {**existing, "resumed": True}
        raise ValueError("Existing E3 runtime evidence is invalid; do not overwrite")
    if run_root.exists():
        raise FileExistsError("Partial E3 runtime directory exists; use a new version")

    from huggingface_hub import hf_hub_download
    files = {
        suffix: hf_hub_download(
            "microsoft/TRELLIS.2-4B",
            f"{BASE_SPARSE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    base_config = json.loads(official.read_text(encoding="utf-8"))
    if (
        base_config.get("models", {}).get("denoiser", {}).get("name")
        != "SparseStructureFlowModel"
        or base_config.get("dataset", {}).get("name")
        != "ImageConditionedSparseStructureLatent"
    ):
        raise ValueError("Pinned official sparse-flow config contract changed")
    run_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    config = build_finetune_config(
        base_config,
        trainer_checkpoint,
        max_steps=2,
        save_interval=1,
        log_interval=1,
    )
    config["trainer"]["args"]["i_sample"] = 102
    config_path = run_root / "dentalsculptor_sparse_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    command = sparse_structure_training_command(dataset_name, run_name, tryrun=True)
    trainer_source = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    original_trainer_source = trainer_source.read_text(encoding="utf-8")
    patched_trainer_source = sparse_flow_trainer_source_with_derived_rope_buffer(
        original_trainer_source
    )
    trainer_source.write_text(patched_trainer_source, encoding="utf-8")
    try:
        result = subprocess.run(
            command,
            cwd=TRELLIS2_PATH,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original_trainer_source, encoding="utf-8")
    print(result.stdout, flush=True)
    (run_root / "tryrun.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"Sparse-flow tryrun exited with code {result.returncode}")
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E3-B-sparse-flow-runtime-tryrun",
        "datasetName": dataset_name,
        "datasetManifestSha256": sparse["datasetManifestSha256"],
        "assetCount": sparse["observedCount"],
        "baseModelRevision": BASE_MODEL_REVISION,
        "baseSparseFlowCheckpoint": BASE_SPARSE_FLOW_FILE,
        "trainingCodeCommit": TRAINING_CODE_COMMIT,
        "officialConfig": str(official),
        "modelClass": "SparseStructureFlowModel",
        "datasetClass": "ImageConditionedSparseStructureLatent",
        "checkpointCompatibility": {
            "restoredDerivedBuffer": "rope_phases",
            "source": "fresh official SparseStructureFlowModel state_dict",
            "strictLoadAfterRestore": True,
            "allOtherMissingKeysRejected": True,
        },
        "tryrun": True,
        "optimizerStepExecuted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=4 * 60 * 60,
)
def run_e10_g2_four_family_screen(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e10-g2-four-family-v1",
    max_steps: int = 2,
    experiment_seed: int = 20260920,
    samples: int = 5000,
    objective: str = "e10",
) -> dict:
    """Train E10/E11 for two steps and run the sealed four-family safety gate."""
    import io
    import os
    import random
    import shutil
    import sys

    import numpy as np
    import torch
    import trimesh
    from PIL import Image
    from huggingface_hub import hf_hub_download

    sealed_runs = {
        "e10": "stage1-e10-g2-four-family-v1",
        "e11": "stage1-e11-g2-four-family-v1",
    }
    if (
        dataset_name != "toothfairy-stage1-v1"
        or sealed_runs.get(objective) != run_name
        or max_steps != 2
        or experiment_seed != 20260920
        or samples != 5000
    ):
        raise ValueError("E10/E11 G2 contract is sealed")
    root = Path(f"/datasets/{dataset_name}")
    g1_run = (
        "stage1-e11-g1-one-tooth-v1" if objective == "e11"
        else "stage1-e10-g1-one-tooth-v4"
    )
    g1 = json.loads(
        Path(f"/checkpoints/{g1_run}/g1-evidence.json").read_text(encoding="utf-8")
    )
    if g1.get("g2Authorized") is not True or g1.get("rawDecodeExactRepeat") is not True:
        raise ValueError("E10 G2 requires sealed passing G1 evidence")
    manifest_path = root / "anatomy_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("assetCount") != 164 or manifest.get("splits") != {
        "train": 128, "validation": 12, "test": 24
    }:
        raise ValueError("E10 G2 requires the sealed Stage-1 cohort")

    families = ("incisor", "canine", "premolar", "molar")
    view = root / "e10_g2_four_family_v1"
    view_receipt_path = view / "receipt.json"
    latent_name = "shape_enc_next_dc_f16c32_fp16_512"
    if view_receipt_path.is_file():
        view_receipt = json.loads(view_receipt_path.read_text(encoding="utf-8"))
        if not view_receipt.get("valid") or view_receipt.get("familyCount") != 4:
            raise ValueError("Existing E10 G2 training view is invalid")
    else:
        if view.exists():
            raise FileExistsError("Partial E10 G2 view exists")
        source_metadata = root / "training_views" / "train" / "metadata.csv"
        with source_metadata.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            fieldnames, rows = reader.fieldnames, list(reader)
        if not fieldnames or len(rows) != 128:
            raise ValueError("E10 G2 requires the sealed 128-row training metadata")
        family_by_digest = {
            asset["canonicalSha256"]: asset["toothFamily"]
            for asset in manifest["assets"] if asset.get("split") == "train"
        }
        if len(family_by_digest) != 128:
            raise ValueError("E10 G2 manifest training-family map is incomplete")
        selected = []
        for family in families:
            matches = sorted(
                (row for row in rows if family_by_digest.get(row["sha256"]) == family),
                key=lambda row: row["sha256"],
            )
            if not matches:
                raise ValueError(f"No E10 G2 training tooth for {family}")
            selected.append({**matches[0], "toothFamily": family})
        if "toothFamily" not in fieldnames:
            fieldnames = [*fieldnames, "toothFamily"]
        for name in ("base", "shape_latent", "render_cond"):
            (view / name).mkdir(parents=True, exist_ok=False)
        for row in selected:
            digest = row["sha256"]
            latent = root / "shape_latents" / latent_name / f"{digest}.npz"
            renders = root / "renders_cond" / digest
            if not latent.is_file() or not renders.is_dir():
                raise FileNotFoundError(f"Missing E10 G2 inputs for {digest}")
            shutil.copy2(latent, view / "shape_latent" / latent.name)
            shutil.copytree(renders, view / "render_cond" / digest)
        for name in ("base", "shape_latent", "render_cond"):
            with (view / name / "metadata.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(selected)
        view_receipt = {
            "schemaVersion": 1, "valid": True, "familyCount": 4,
            "selection": "lexicographically-first-training-sha256-per-family",
            "teeth": [
                {"toothFamily": row["toothFamily"], "sha256": row["sha256"]}
                for row in selected
            ],
        }
        view_receipt_path.write_text(json.dumps(view_receipt, indent=2) + "\n", encoding="utf-8")
        dataset_volume.commit()

    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "g2-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid"):
            return {**existing, "resumed": True}
        raise ValueError("Existing E10 G2 evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E10 G2 run exists; diagnose before versioning")

    base_files = {
        suffix: hf_hub_download(
            BASE_MODEL_NAME, f"{BASE_SHAPE_FLOW_FILE}.{suffix}", revision=BASE_MODEL_REVISION
        ) for suffix in ("json", "safetensors")
    }
    run_root.mkdir(parents=True, exist_ok=False)
    trainer_checkpoint = materialize_trainer_checkpoint(
        base_files["safetensors"], run_root / "base-denoiser.pt"
    )
    official = Path(TRELLIS2_PATH) / "configs/gen/slat_flow_img2shape_dit_1_3B_512_bf16.json"
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")), trainer_checkpoint,
        max_steps=2, save_interval=2, log_interval=1,
    )
    args = config["trainer"]["args"]
    args["batch_size_per_gpu"] = 1
    args["batch_split"] = 1
    args["optimizer"]["args"]["lr"] = 1e-6
    args["dentalsculptor_axial_band_count"] = 4
    args["dentalsculptor_teacher_target_ratio"] = 0.05
    args["i_sample"] = 101
    config["experimentSeed"] = experiment_seed
    (run_root / "dentalsculptor_finetune_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    command = e10_four_family_training_command(dataset_name, run_name)
    trainer_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    sparse_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/sparse_flow_matching.py"
    entry_path = Path(TRELLIS2_PATH) / "train.py"
    originals = {path: path.read_text(encoding="utf-8") for path in (
        trainer_path, flow_path, sparse_path, entry_path
    )}

    def install_sources() -> None:
        trainer_path.write_text(smoke_trainer_source_without_snapshots(originals[trainer_path]), encoding="utf-8")
        flow_path.write_text(e10_teacher_init_flow_source(originals[flow_path]), encoding="utf-8")
        sparse_path.write_text(
            (
                e11_bandwise_teacher_sparse_flow_source(originals[sparse_path])
                if objective == "e11"
                else e10_axial_sparse_flow_source(originals[sparse_path])
            ),
            encoding="utf-8",
        )
        entry_path.write_text(training_entry_source_with_experiment_seed(originals[entry_path], experiment_seed), encoding="utf-8")

    def restore_sources() -> None:
        for path, source in originals.items():
            path.write_text(source, encoding="utf-8")

    objective_path = run_root / "objective-receipt.jsonl"
    install_sources()
    try:
        env = os.environ.copy()
        env["DENTALSCULPTOR_E10_OBJECTIVE_RECEIPT"] = str(objective_path)
        process = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
        )
    finally:
        restore_sources()
    (run_root / "training.log").write_text(process.stdout, encoding="utf-8")
    print(process.stdout, flush=True)
    if process.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"E10 G2 trainer exited with code {process.returncode}")
    records = [json.loads(line) for line in objective_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(records) != 2:
        raise RuntimeError(f"E10 G2 requires exactly two objective receipts, found {len(records)}")
    required = ("loss", "mse", "axial_band_balanced_mse", "teacher_consistency_mse", "teacher_consistency_contribution")
    for index, record in enumerate(records):
        if any(not math.isfinite(float(record[name])) or float(record[name]) < 0 for name in required):
            raise RuntimeError(f"E10 G2 invalid objective receipt {index}: {record}")
        if record.get("teacherFrozen") is not True or record.get("populatedAxialBands") != 4:
            raise RuntimeError(f"E10 G2 objective contract failed: {record}")
    if records[0]["teacher_consistency_mse"] != 0.0:
        raise RuntimeError("E10 G2 first update did not begin at student/teacher identity")
    ratio = float(records[1]["teacher_consistency_contribution"]) / max(
        float(records[1]["axial_band_balanced_mse"]), 1e-12
    )
    if abs(ratio - 0.05) > 1e-4:
        raise RuntimeError(f"E10 G2 second-step teacher ratio drifted: {ratio}")
    if objective == "e11":
        for index, record in enumerate(records):
            if record.get("teacherConsistencyMode") != "equal-per-sample-per-axial-band":
                raise RuntimeError(f"E11 G2 receipt {index} did not execute bandwise preservation")
            bounds = (float(record["teacherBandMseMin"]), float(record["teacherBandMseMax"]))
            if any(not math.isfinite(value) or value < 0 for value in bounds):
                raise RuntimeError(f"E11 G2 receipt {index} has invalid band bounds: {bounds}")

    ckpt_dir = run_root / "ckpts"
    model_ckpt = ckpt_dir / "denoiser_step0000002.pt"
    ema_ckpt = ckpt_dir / "denoiser_ema0.9999_step0000002.pt"
    misc_ckpt = ckpt_dir / "misc_step0000002.pt"
    if any(not path.is_file() or path.stat().st_size == 0 for path in (model_ckpt, ema_ckpt, misc_ckpt)):
        raise RuntimeError("E10 G2 checkpoint contract failed")
    install_sources()
    try:
        reload_result = subprocess.run(
            [*command, "--load_dir", str(run_root), "--ckpt", "2", "--tryrun"],
            cwd=TRELLIS2_PATH, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        restore_sources()
    (run_root / "reload.log").write_text(reload_result.stdout, encoding="utf-8")
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout:
        raise RuntimeError("E10 G2 checkpoint failed strict reload")

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    validation = json.loads((root / "stage1_validation_inputs_v1.json").read_text(encoding="utf-8"))
    if not validation.get("valid") or validation.get("trainingPatientOverlapCount") != 0:
        raise ValueError("E10 G2 requires patient-disjoint sealed validation inputs")
    cases = []
    for family in families:
        match = sorted(
            (case for case in validation["cases"] if case["toothFamily"] == family),
            key=lambda case: case["id"],
        )[0]
        cases.append(match)
    frozen_root = root / "stage1_seed_a_raw_validation_v2_outputs" / "frozen_sparse_conditions"
    generator = TrellisGenerator()
    generator.load_model()
    params = sampler_params_for_steps(int(get_quality_preset("standard")["steps"]))

    def tensor_hash(tensor: torch.Tensor) -> str:
        return hashlib.sha256(tensor.detach().cpu().contiguous().numpy().tobytes()).hexdigest()

    def decode(case: dict, coords_cpu: torch.Tensor) -> tuple[trimesh.Trimesh, dict]:
        seed = int(case["generationSeed"])
        random.seed(seed); np.random.seed(seed % (2**32)); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
        image_bytes = (root / case["inputImage"]).read_bytes()
        if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
            raise ValueError(f"E10 G2 image hash drift for {case['id']}")
        image = Image.open(io.BytesIO(image_bytes)); image.load()
        processed = generator.pipeline.preprocess_image(image)
        cond_512 = generator.pipeline.get_cond([processed], 512)
        cond_1024 = generator.pipeline.get_cond([processed], 1024)
        coords = coords_cpu.to(torch.device("cuda", torch.cuda.current_device()))
        with torch.inference_mode():
            slat, resolution = generator.pipeline.sample_shape_slat_cascade(
                cond_512, cond_1024,
                generator.pipeline.models["shape_slat_flow_model_512"],
                generator.pipeline.models["shape_slat_flow_model_1024"],
                512, 1024, coords, params["shape"],
            )
            meshes, _ = generator.pipeline.decode_shape_slat(slat, resolution)
        torch.cuda.synchronize()
        raw = meshes[0]
        boundary = {
            "sparseCoordsSha256": tensor_hash(coords),
            "shapeLatentCoordsSha256": tensor_hash(slat.coords),
            "shapeLatentFeaturesSha256": tensor_hash(slat.feats),
            "rawVerticesSha256": tensor_hash(raw.vertices),
            "rawFacesSha256": tensor_hash(raw.faces),
        }
        mesh = trimesh.Trimesh(
            vertices=raw.vertices.detach().cpu().numpy(),
            faces=raw.faces.detach().cpu().numpy(), process=False,
        )
        del meshes, raw, slat, coords, cond_512, cond_1024
        torch.cuda.empty_cache()
        return mesh, boundary

    output_root = run_root / "g2-raw-screen"
    output_root.mkdir()

    def evaluate_role(role: str) -> list[dict]:
        role_root = output_root / role
        role_root.mkdir()
        receipts = []
        for case in cases:
            coords_path = frozen_root / f"{case['id']}.pt"
            frozen_receipt = json.loads((frozen_root / f"{case['id']}.json").read_text(encoding="utf-8"))
            coords_cpu = torch.load(coords_path, map_location="cpu", weights_only=True)
            if tensor_hash(coords_cpu) != frozen_receipt["coordsSha256"]:
                raise ValueError(f"E10 G2 frozen condition drift for {case['id']}")
            mesh, boundary = decode(case, coords_cpu)
            _, repeated = decode(case, coords_cpu)
            exact = boundary == repeated
            if not exact:
                raise RuntimeError(f"E10 G2 raw repeatability failed for {role}:{case['id']}")
            mesh_path = role_root / f"{case['id']}.ply"
            mesh_path.write_bytes(mesh.export(file_type="ply", encoding="binary"))
            reference = load_mesh(root / case["referenceMesh"])
            receipt = {
                "schemaVersion": 1, "id": case["id"], "toothFamily": case["toothFamily"],
                "groupId": case["groupId"], "modelRole": role,
                "frozenSparseCondition": frozen_receipt, "boundary": boundary,
                "repeatability": {"rawShapeExact": True, "boundaryEquality": {
                    key: boundary[key] == repeated[key] for key in boundary
                }},
                "metrics": compare_meshes(reference, mesh, samples=samples, seed=int(case["generationSeed"])),
                "topology": analyze_mesh_with_weld_control(mesh),
                "meshArtifact": str(mesh_path),
                "meshArtifactSha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
            }
            (role_root / f"{case['id']}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            receipts.append(receipt)
            checkpoint_volume.commit()
        return receipts

    baseline = evaluate_role("unchanged-base")
    candidate_checkpoint = generator.load_shape_checkpoint(str(ema_ckpt))
    candidate = evaluate_role("e10-g2-candidate")
    summary = summarize_e10_g2_screen(baseline, candidate)
    evidence = {
        "schemaVersion": 1, "valid": True,
        "stage": f"{objective.upper()}-G2-four-family-two-step-screen",
        "objective": objective,
        "runName": run_name, "optimizerSteps": 2, "experimentSeed": experiment_seed,
        "trainingView": view_receipt, "objectiveReceipts": records,
        "observedSecondStepTeacherContributionRatio": ratio,
        "teacherFrozen": True, "checkpointReloaded": True,
        "candidateCheckpoint": candidate_checkpoint,
        "baseline": baseline, "candidate": candidate, "summary": summary,
        "g3Authorized": summary["g3Authorized"],
        "clinicalClaimPermitted": False, "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    timeout=2 * 60 * 60,
)
def smoke_train_e3_sparse_structure(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "e3-sparse-smoke-v1",
    max_steps: int = 2,
) -> dict:
    """Run exactly two sparse-flow optimizer steps and prove checkpoint reload."""
    if (
        dataset_name != "toothfairy-tf-pw32-v1"
        or run_name != "e3-sparse-smoke-v1"
        or max_steps != 2
    ):
        raise ValueError("The E3 sparse smoke contract is sealed at TF-PW32 and two steps")
    root = Path(f"/datasets/{dataset_name}")
    sparse_path = root / "e3_sparse_structure_latent_receipt.json"
    if not sparse_path.is_file():
        raise FileNotFoundError("Run prepare_e3_sparse_structure_latents first")
    sparse = json.loads(sparse_path.read_text(encoding="utf-8"))
    if not sparse.get("valid") or sparse.get("observedCount") != 32:
        raise ValueError("Sparse-latent receipt does not satisfy the sealed 32/32 contract")

    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "smoke-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("steps") == 2:
            return {**existing, "resumed": True}
        raise ValueError("Existing sparse smoke evidence is invalid; do not overwrite")
    if run_root.exists():
        raise FileExistsError("Partial sparse smoke directory exists; use a new version")

    from huggingface_hub import hf_hub_download
    files = {
        suffix: hf_hub_download(
            "microsoft/TRELLIS.2-4B",
            f"{BASE_SPARSE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    run_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")),
        trainer_checkpoint,
        max_steps=max_steps,
        save_interval=1,
        log_interval=1,
    )
    config["trainer"]["args"]["i_sample"] = max_steps + 100
    config_path = run_root / "dentalsculptor_sparse_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    command = sparse_structure_training_command(dataset_name, run_name)

    trainer_source = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    original = trainer_source.read_text(encoding="utf-8")
    patched = smoke_trainer_source_without_snapshots(
        sparse_flow_trainer_source_with_derived_rope_buffer(original)
    )
    trainer_source.write_text(patched, encoding="utf-8")
    try:
        result = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original, encoding="utf-8")
    print(result.stdout, flush=True)
    (run_root / "smoke-training.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"Sparse-flow smoke trainer exited with code {result.returncode}")

    log_path = run_root / "log.txt"
    losses = finite_losses_from_training_log(log_path.read_text(encoding="utf-8"))
    if len(losses) != max_steps or any(not math.isfinite(value) for value in losses):
        checkpoint_volume.commit()
        raise RuntimeError(f"Expected exactly {max_steps} finite sparse-flow losses")
    ckpt_dir = run_root / "ckpts"
    required = [
        ckpt_dir / f"denoiser_step{max_steps:07d}.pt",
        ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt",
        ckpt_dir / f"misc_step{max_steps:07d}.pt",
    ]
    missing = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        checkpoint_volume.commit()
        raise RuntimeError(f"Sparse smoke checkpoint contract failed: {missing}")

    reload_command = [*command, "--load_dir", str(run_root), "--ckpt", str(max_steps), "--tryrun"]
    trainer_source.write_text(smoke_trainer_source_without_snapshots(original), encoding="utf-8")
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original, encoding="utf-8")
    print(reload_result.stdout, flush=True)
    if (
        reload_result.returncode
        or "Loading checkpoint" not in reload_result.stdout
        or "Done." not in reload_result.stdout
    ):
        checkpoint_volume.commit()
        raise RuntimeError("Sparse-flow checkpoint failed strict pinned-trainer reload")
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E3-B-sparse-flow-two-step-smoke",
        "datasetName": dataset_name,
        "datasetManifestSha256": sparse["datasetManifestSha256"],
        "assetCount": 32,
        "runName": run_name,
        "steps": max_steps,
        "finiteLosses": losses,
        "checkpointFiles": [
            {"path": str(path), "bytes": path.stat().st_size} for path in required
        ],
        "checkpointReloaded": True,
        "baseModelRevision": BASE_MODEL_REVISION,
        "baseSparseFlowCheckpoint": BASE_SPARSE_FLOW_FILE,
        "trainingCodeCommit": TRAINING_CODE_COMMIT,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def smoke_train_e6_sparse_teacher_consistency(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "e6-sparse-teacher-consistency-smoke-v1",
    max_steps: int = 2,
) -> dict:
    """Qualify frozen-base output consistency in exactly two optimizer steps."""
    consistency_weight = 1.0
    learning_rate = 1e-6
    if (
        dataset_name != "toothfairy-tf-pw32-v1"
        or run_name != "e6-sparse-teacher-consistency-smoke-v1"
        or max_steps != 2
    ):
        raise ValueError("The E6 smoke contract is sealed")
    root = Path(f"/datasets/{dataset_name}")
    sparse = json.loads(
        (root / "e3_sparse_structure_latent_receipt.json").read_text(encoding="utf-8")
    )
    if not sparse.get("valid") or sparse.get("observedCount") != 32:
        raise ValueError("Validated 32/32 sparse latents are required")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "smoke-evidence.json"
    if evidence_path.exists():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("steps") == max_steps:
            return {**existing, "resumed": True}
        raise ValueError("Existing E6 smoke evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E6 smoke directory exists; use a new version")

    from huggingface_hub import hf_hub_download

    files = {
        suffix: hf_hub_download(
            BASE_MODEL_NAME,
            f"{BASE_SPARSE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    run_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")),
        trainer_checkpoint,
        max_steps=max_steps,
        save_interval=1,
        log_interval=1,
    )
    trainer_args = config["trainer"]["args"]
    trainer_args["mix_precision_mode"] = "amp"
    trainer_args["mix_precision_dtype"] = "bfloat16"
    trainer_args["optimizer"]["args"]["lr"] = learning_rate
    trainer_args["dentalsculptor_teacher_consistency_weight"] = consistency_weight
    trainer_args["i_sample"] = max_steps + 100
    config_path = run_root / "dentalsculptor_sparse_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    command = sparse_structure_training_command(dataset_name, run_name)

    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    basic_original = basic_path.read_text(encoding="utf-8")
    flow_original = flow_path.read_text(encoding="utf-8")
    basic_path.write_text(
        smoke_trainer_source_without_snapshots(
            sparse_flow_trainer_source_with_derived_rope_buffer(basic_original)
        ),
        encoding="utf-8",
    )
    flow_path.write_text(
        teacher_consistency_flow_source(flow_original), encoding="utf-8"
    )
    try:
        result = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
        flow_path.write_text(flow_original, encoding="utf-8")
    print(result.stdout, flush=True)
    (run_root / "smoke-training.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"E6 teacher-consistency smoke exited with code {result.returncode}")

    records = [
        json.loads(line.partition(": ")[2])
        for line in (run_root / "log.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    supervised_losses = [float(row["loss"]["mse"]) for row in records]
    consistency_losses = [
        float(row["loss"]["teacher_consistency_mse"]) for row in records
    ]
    total_losses = [float(row["loss"]["loss"]) for row in records]
    all_losses = supervised_losses + consistency_losses + total_losses
    if (
        len(records) != max_steps
        or any(not math.isfinite(value) or value < 0.0 for value in all_losses)
        or not any(value > 0.0 for value in consistency_losses[1:])
    ):
        checkpoint_volume.commit()
        raise RuntimeError("E6 teacher-consistency loss contract failed")
    ckpt_dir = run_root / "ckpts"
    model_checkpoint = ckpt_dir / f"denoiser_step{max_steps:07d}.pt"
    ema_checkpoint = ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt"
    misc_checkpoint = ckpt_dir / f"misc_step{max_steps:07d}.pt"
    if any(
        not path.is_file() or path.stat().st_size == 0
        for path in (model_checkpoint, ema_checkpoint, misc_checkpoint)
    ):
        checkpoint_volume.commit()
        raise RuntimeError("E6 smoke checkpoints are incomplete")
    model_drift = checkpoint_relative_l2(Path(trainer_checkpoint), model_checkpoint)
    ema_drift = checkpoint_relative_l2(Path(trainer_checkpoint), ema_checkpoint)

    reload_command = [
        *command, "--load_dir", str(run_root), "--ckpt", str(max_steps), "--tryrun"
    ]
    basic_path.write_text(
        smoke_trainer_source_without_snapshots(basic_original), encoding="utf-8"
    )
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout:
        checkpoint_volume.commit()
        raise RuntimeError("E6 smoke checkpoint failed strict reload")
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E6-sparse-frozen-base-output-consistency-two-step-smoke",
        "datasetName": dataset_name,
        "runName": run_name,
        "steps": max_steps,
        "learningRate": learning_rate,
        "teacherConsistencyWeight": consistency_weight,
        "supervisedMse": supervised_losses,
        "teacherConsistencyMse": consistency_losses,
        "totalLoss": total_losses,
        "measuredModelCheckpointRelativeL2": model_drift,
        "measuredEmaCheckpointRelativeL2": ema_drift,
        "teacherFrozen": True,
        "teacherExcludedFromOptimizerEmaAndCheckpoint": True,
        "sameNoiseTimestepAndCondition": True,
        "checkpointReloaded": True,
        "tenStepCanaryPermitted": True,
        "fullMeshEvaluationPermitted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def smoke_train_e7_calibrated_anchor_consistency(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "e7-sparse-calibrated-anchor-smoke-v1",
    max_steps: int = 2,
) -> dict:
    """Qualify bounded loss-scale calibration on the sealed four-family anchor."""
    target_ratio = 0.10
    scale_min = 1.0
    scale_max = 250.0
    learning_rate = 1e-6
    if (
        dataset_name != "toothfairy-tf-pw32-v1"
        or run_name != "e7-sparse-calibrated-anchor-smoke-v1"
        or max_steps != 2
    ):
        raise ValueError("The E7 smoke contract is sealed")
    root = Path(f"/datasets/{dataset_name}")
    anchor_path = root / "sparse_anchor_v1" / "receipt.json"
    if not anchor_path.is_file():
        raise FileNotFoundError("Run prepare_e7_sparse_anchor_inputs first")
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    if not (
        anchor.get("valid")
        and anchor.get("assetCount") == 8
        and anchor.get("familyCounts") == {
            "incisor": 2, "canine": 2, "premolar": 2, "molar": 2
        }
        and len(anchor.get("cohortSha256", "")) == 64
    ):
        raise ValueError("The E7 sparse anchor receipt failed its sealed contract")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "smoke-evidence.json"
    if evidence_path.exists():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("steps") == max_steps:
            return {**existing, "resumed": True}
        raise ValueError("Existing E7 smoke evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E7 smoke directory exists; use a new version")

    from huggingface_hub import hf_hub_download

    files = {
        suffix: hf_hub_download(
            BASE_MODEL_NAME,
            f"{BASE_SPARSE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    run_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")),
        trainer_checkpoint,
        max_steps=max_steps,
        save_interval=1,
        log_interval=1,
    )
    trainer_args = config["trainer"]["args"]
    trainer_args["mix_precision_mode"] = "amp"
    trainer_args["mix_precision_dtype"] = "bfloat16"
    trainer_args["optimizer"]["args"]["lr"] = learning_rate
    trainer_args["dentalsculptor_consistency_target_ratio"] = target_ratio
    trainer_args["dentalsculptor_consistency_scale_min"] = scale_min
    trainer_args["dentalsculptor_consistency_scale_max"] = scale_max
    trainer_args["i_sample"] = max_steps + 100
    config_path = run_root / "dentalsculptor_sparse_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    command = sparse_anchor_training_command(dataset_name, run_name)

    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    basic_original = basic_path.read_text(encoding="utf-8")
    flow_original = flow_path.read_text(encoding="utf-8")
    basic_path.write_text(
        smoke_trainer_source_without_snapshots(
            sparse_flow_trainer_source_with_derived_rope_buffer(basic_original)
        ), encoding="utf-8"
    )
    flow_path.write_text(
        calibrated_teacher_consistency_flow_source(flow_original), encoding="utf-8"
    )
    try:
        result = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
        flow_path.write_text(flow_original, encoding="utf-8")
    print(result.stdout, flush=True)
    (run_root / "smoke-training.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"E7 calibrated-anchor smoke exited with code {result.returncode}")

    records = [
        json.loads(line.partition(": ")[2])
        for line in (run_root / "log.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    names = (
        "mse", "teacher_consistency_mse", "teacher_consistency_scale",
        "teacher_consistency_contribution", "teacher_consistency_share", "loss",
    )
    series = {name: [float(row["loss"][name]) for row in records] for name in names}
    all_values = [value for values in series.values() for value in values]
    observed_shares = series["teacher_consistency_share"][1:]
    if (
        len(records) != max_steps
        or any(not math.isfinite(value) or value < 0.0 for value in all_values)
        or not observed_shares
        or not all(0.08 <= value <= 0.12 for value in observed_shares)
        or not all(scale_min <= value <= scale_max for value in series["teacher_consistency_scale"])
    ):
        checkpoint_volume.commit()
        raise RuntimeError(f"E7 calibrated loss-share contract failed: {series}")

    ckpt_dir = run_root / "ckpts"
    model_checkpoint = ckpt_dir / f"denoiser_step{max_steps:07d}.pt"
    ema_checkpoint = ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt"
    misc_checkpoint = ckpt_dir / f"misc_step{max_steps:07d}.pt"
    if any(not path.is_file() or path.stat().st_size == 0 for path in (
        model_checkpoint, ema_checkpoint, misc_checkpoint
    )):
        checkpoint_volume.commit()
        raise RuntimeError("E7 smoke checkpoints are incomplete")
    model_drift = checkpoint_relative_l2(Path(trainer_checkpoint), model_checkpoint)
    ema_drift = checkpoint_relative_l2(Path(trainer_checkpoint), ema_checkpoint)

    reload_command = [
        *command, "--load_dir", str(run_root), "--ckpt", str(max_steps), "--tryrun"
    ]
    basic_path.write_text(smoke_trainer_source_without_snapshots(basic_original), encoding="utf-8")
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout:
        checkpoint_volume.commit()
        raise RuntimeError("E7 smoke checkpoint failed strict reload")
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E7-calibrated-consistency-frozen-anchor-two-step-smoke",
        "datasetName": dataset_name,
        "anchorCohortSha256": anchor["cohortSha256"],
        "anchorFamilyCounts": anchor["familyCounts"],
        "runName": run_name,
        "steps": max_steps,
        "learningRate": learning_rate,
        "targetConsistencyShare": target_ratio,
        "consistencyScaleBounds": [scale_min, scale_max],
        "lossSeries": series,
        "measuredModelCheckpointRelativeL2": model_drift,
        "measuredEmaCheckpointRelativeL2": ema_drift,
        "teacherFrozen": True,
        "calibrationDetached": True,
        "checkpointReloaded": True,
        "tenStepCanaryPermitted": True,
        "fullMeshEvaluationPermitted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=3 * 60 * 60,
)
def train_e7_calibrated_anchor_canary(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "e7-sparse-calibrated-anchor-step10-v1",
    max_steps: int = 10,
) -> dict:
    """Run the smoke-authorized E7 canary; never promote without geometry gates."""
    target_ratio, scale_min, scale_max, learning_rate = 0.10, 1.0, 250.0, 1e-6
    if (
        dataset_name != "toothfairy-tf-pw32-v1"
        or run_name != "e7-sparse-calibrated-anchor-step10-v1"
        or max_steps != 10
    ):
        raise ValueError("The E7 canary contract is sealed")
    smoke_path = Path(
        "/checkpoints/e7-sparse-calibrated-anchor-smoke-v1/smoke-evidence.json"
    )
    if not smoke_path.is_file():
        raise FileNotFoundError("Passed E7 smoke evidence is required")
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    if not (
        smoke.get("valid")
        and smoke.get("tenStepCanaryPermitted")
        and smoke.get("checkpointReloaded")
        and smoke.get("targetConsistencyShare") == target_ratio
        and smoke.get("consistencyScaleBounds") == [scale_min, scale_max]
    ):
        raise ValueError("E7 smoke evidence does not authorize the canary")
    anchor_path = Path(f"/datasets/{dataset_name}/sparse_anchor_v1/receipt.json")
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    if anchor.get("cohortSha256") != smoke.get("anchorCohortSha256"):
        raise ValueError("E7 anchor changed after smoke qualification")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "canary-evidence.json"
    if evidence_path.exists():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("steps") == max_steps:
            return {**existing, "resumed": True}
        raise ValueError("Existing E7 canary evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E7 canary directory exists; use a new version")

    from huggingface_hub import hf_hub_download
    files = {
        suffix: hf_hub_download(
            BASE_MODEL_NAME, f"{BASE_SPARSE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    run_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")), trainer_checkpoint,
        max_steps=max_steps, save_interval=max_steps, log_interval=1,
    )
    args = config["trainer"]["args"]
    args["mix_precision_mode"] = "amp"
    args["mix_precision_dtype"] = "bfloat16"
    args["optimizer"]["args"]["lr"] = learning_rate
    args["dentalsculptor_consistency_target_ratio"] = target_ratio
    args["dentalsculptor_consistency_scale_min"] = scale_min
    args["dentalsculptor_consistency_scale_max"] = scale_max
    args["i_sample"] = max_steps + 100
    (run_root / "dentalsculptor_sparse_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    command = sparse_anchor_training_command(dataset_name, run_name)
    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    basic_original = basic_path.read_text(encoding="utf-8")
    flow_original = flow_path.read_text(encoding="utf-8")
    basic_path.write_text(smoke_trainer_source_without_snapshots(
        sparse_flow_trainer_source_with_derived_rope_buffer(basic_original)
    ), encoding="utf-8")
    flow_path.write_text(
        calibrated_teacher_consistency_flow_source(flow_original), encoding="utf-8"
    )
    try:
        result = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
        flow_path.write_text(flow_original, encoding="utf-8")
    print(result.stdout, flush=True)
    (run_root / "canary-training.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"E7 canary exited with code {result.returncode}")
    records = [
        json.loads(line.partition(": ")[2])
        for line in (run_root / "log.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    names = (
        "mse", "teacher_consistency_mse", "teacher_consistency_scale",
        "teacher_consistency_contribution", "teacher_consistency_share", "loss",
    )
    series = {name: [float(row["loss"][name]) for row in records] for name in names}
    all_values = [value for values in series.values() for value in values]
    active_shares = series["teacher_consistency_share"][1:]
    if (
        len(records) != max_steps
        or any(not math.isfinite(value) or value < 0.0 for value in all_values)
        or not active_shares
        or not all(0.08 <= value <= 0.12 for value in active_shares)
        or not all(scale_min <= value <= scale_max for value in series["teacher_consistency_scale"])
    ):
        checkpoint_volume.commit()
        raise RuntimeError(f"E7 canary loss-share contract failed: {series}")
    ckpt_dir = run_root / "ckpts"
    model_checkpoint = ckpt_dir / f"denoiser_step{max_steps:07d}.pt"
    ema_checkpoint = ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt"
    misc_checkpoint = ckpt_dir / f"misc_step{max_steps:07d}.pt"
    if any(not path.is_file() or path.stat().st_size == 0 for path in (
        model_checkpoint, ema_checkpoint, misc_checkpoint
    )):
        checkpoint_volume.commit()
        raise RuntimeError("E7 canary checkpoints are incomplete")
    model_drift = checkpoint_relative_l2(Path(trainer_checkpoint), model_checkpoint)
    ema_drift = checkpoint_relative_l2(Path(trainer_checkpoint), ema_checkpoint)
    reload_command = [
        *command, "--load_dir", str(run_root), "--ckpt", str(max_steps), "--tryrun"
    ]
    basic_path.write_text(smoke_trainer_source_without_snapshots(basic_original), encoding="utf-8")
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout:
        checkpoint_volume.commit()
        raise RuntimeError("E7 canary checkpoint failed strict reload")
    evidence = {
        "schemaVersion": 1, "valid": True,
        "stage": "E7-calibrated-consistency-frozen-anchor-ten-step-canary",
        "datasetName": dataset_name, "anchorCohortSha256": anchor["cohortSha256"],
        "anchorFamilyCounts": anchor["familyCounts"], "runName": run_name,
        "steps": max_steps, "learningRate": learning_rate,
        "targetConsistencyShare": target_ratio,
        "consistencyScaleBounds": [scale_min, scale_max], "lossSeries": series,
        "measuredModelCheckpointRelativeL2": model_drift,
        "measuredEmaCheckpointRelativeL2": ema_drift,
        "candidateCheckpointPath": str(ema_checkpoint),
        "teacherFrozen": True, "calibrationDetached": True,
        "checkpointReloaded": True, "fourFamilyOccupancyScreenPermitted": True,
        "fullMeshEvaluationPermitted": False, "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def smoke_train_e8_decoded_occupancy(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "e8-sparse-decoded-occupancy-smoke-v1",
    max_steps: int = 2,
) -> dict:
    """Qualify direct decoded-occupancy supervision in exactly two steps."""
    target_ratio, scale_min, scale_max = 0.10, 1e-4, 100.0
    temperature, learning_rate = 1.0, 1e-6
    decoder_name = "microsoft/TRELLIS-image-large/ckpts/ss_dec_conv3d_16l8_fp16"
    if (
        dataset_name != "toothfairy-tf-pw32-v1"
        or run_name != "e8-sparse-decoded-occupancy-smoke-v1"
        or max_steps != 2
    ):
        raise ValueError("The E8 smoke contract is sealed")
    anchor_path = Path(f"/datasets/{dataset_name}/sparse_anchor_v1/receipt.json")
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    if not (
        anchor.get("valid") and anchor.get("assetCount") == 8
        and anchor.get("familyCounts") == {
            "incisor": 2, "canine": 2, "premolar": 2, "molar": 2
        }
        and len(anchor.get("cohortSha256", "")) == 64
    ):
        raise ValueError("The sealed E8 anchor contract is not satisfied")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "smoke-evidence.json"
    if evidence_path.exists():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("steps") == max_steps:
            return {**existing, "resumed": True}
        raise ValueError("Existing E8 smoke evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E8 smoke directory exists; use a new version")

    from huggingface_hub import hf_hub_download
    files = {
        suffix: hf_hub_download(
            BASE_MODEL_NAME, f"{BASE_SPARSE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    run_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")), trainer_checkpoint,
        max_steps=max_steps, save_interval=1, log_interval=1,
    )
    args = config["trainer"]["args"]
    args["mix_precision_mode"] = "amp"
    args["mix_precision_dtype"] = "bfloat16"
    args["optimizer"]["args"]["lr"] = learning_rate
    args["dentalsculptor_occupancy_target_ratio"] = target_ratio
    args["dentalsculptor_occupancy_scale_min"] = scale_min
    args["dentalsculptor_occupancy_scale_max"] = scale_max
    args["dentalsculptor_occupancy_temperature"] = temperature
    args["dentalsculptor_occupancy_decoder"] = decoder_name
    args["i_sample"] = max_steps + 100
    (run_root / "dentalsculptor_sparse_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    command = sparse_anchor_training_command(dataset_name, run_name)
    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    basic_original = basic_path.read_text(encoding="utf-8")
    flow_original = flow_path.read_text(encoding="utf-8")
    basic_path.write_text(smoke_trainer_source_without_snapshots(
        sparse_flow_trainer_source_with_derived_rope_buffer(basic_original)
    ), encoding="utf-8")
    flow_path.write_text(decoded_occupancy_flow_source(flow_original), encoding="utf-8")
    try:
        result = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
        flow_path.write_text(flow_original, encoding="utf-8")
    print(result.stdout, flush=True)
    (run_root / "smoke-training.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"E8 decoded-occupancy smoke exited with code {result.returncode}")
    records = [
        json.loads(line.partition(": ")[2])
        for line in (run_root / "log.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    names = (
        "mse", "occupancy_bce", "occupancy_dice", "occupancy_raw",
        "occupancy_scale", "occupancy_contribution", "occupancy_share", "loss",
    )
    series = {name: [float(row["loss"][name]) for row in records] for name in names}
    all_values = [value for values in series.values() for value in values]
    if (
        len(records) != max_steps
        or any(not math.isfinite(value) or value < 0.0 for value in all_values)
        or not all(0.08 <= value <= 0.12 for value in series["occupancy_share"])
        or not all(scale_min <= value <= scale_max for value in series["occupancy_scale"])
        or not all(0.0 <= value <= 1.0 for value in series["occupancy_dice"])
    ):
        checkpoint_volume.commit()
        raise RuntimeError(f"E8 decoded-occupancy loss contract failed: {series}")
    ckpt_dir = run_root / "ckpts"
    model_checkpoint = ckpt_dir / f"denoiser_step{max_steps:07d}.pt"
    ema_checkpoint = ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt"
    misc_checkpoint = ckpt_dir / f"misc_step{max_steps:07d}.pt"
    if any(not path.is_file() or path.stat().st_size == 0 for path in (
        model_checkpoint, ema_checkpoint, misc_checkpoint
    )):
        checkpoint_volume.commit()
        raise RuntimeError("E8 smoke checkpoints are incomplete")
    model_drift = checkpoint_relative_l2(Path(trainer_checkpoint), model_checkpoint)
    ema_drift = checkpoint_relative_l2(Path(trainer_checkpoint), ema_checkpoint)
    reload_command = [
        *command, "--load_dir", str(run_root), "--ckpt", str(max_steps), "--tryrun"
    ]
    basic_path.write_text(smoke_trainer_source_without_snapshots(basic_original), encoding="utf-8")
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout:
        checkpoint_volume.commit()
        raise RuntimeError("E8 smoke checkpoint failed strict reload")
    evidence = {
        "schemaVersion": 1, "valid": True,
        "stage": "E8-decoded-occupancy-two-step-smoke",
        "datasetName": dataset_name, "anchorCohortSha256": anchor["cohortSha256"],
        "runName": run_name, "steps": max_steps, "learningRate": learning_rate,
        "occupancyDecoder": decoder_name, "occupancyTemperature": temperature,
        "targetOccupancyShare": target_ratio,
        "occupancyScaleBounds": [scale_min, scale_max], "lossSeries": series,
        "predictedCleanLatentFormula": "(1-sigma_min)*noise-predicted_velocity",
        "groundTruthOccupancyThreshold": "frozen_decoder(x_0)>0",
        "measuredModelCheckpointRelativeL2": model_drift,
        "measuredEmaCheckpointRelativeL2": ema_drift,
        "decoderFrozen": True, "calibrationDetached": True,
        "checkpointReloaded": True, "incisorTwoStepScreenPermitted": True,
        "tenStepCanaryPermitted": False, "fullMeshEvaluationPermitted": False,
        "clinicalClaimPermitted": False, "productionPromotionPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=3 * 60 * 60,
)
def diagnose_e9_occupancy_gradients(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    experiment_name: str = "e9-occupancy-gradient-diagnostic-v3",
) -> dict:
    """Measure family-by-timestep gradient alignment without changing weights."""
    import shutil
    from huggingface_hub import hf_hub_download

    families = ("incisor", "canine", "premolar", "molar")
    timesteps = [0.05, 0.25, 0.5, 0.75, 0.95]
    decoder_name = "microsoft/TRELLIS-image-large/ckpts/ss_dec_conv3d_16l8_fp16"
    target_ratio = 0.10
    if dataset_name != "toothfairy-tf-pw32-v1" or experiment_name != "e9-occupancy-gradient-diagnostic-v3":
        raise ValueError("The E9 diagnostic contract is sealed")
    experiment_root = Path(f"/checkpoints/{experiment_name}")
    report_path = experiment_root / "diagnostic-report.json"
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("status") == "complete":
            return {**report, "resumed": True}
        raise ValueError("Existing E9 diagnostic report is invalid")
    if experiment_root.exists():
        raise FileExistsError("Partial E9 diagnostic exists; inspect before retrying")

    dataset_root = Path(f"/datasets/{dataset_name}")
    anchor_root = dataset_root / "sparse_anchor_v1"
    anchor_receipt = json.loads((anchor_root / "receipt.json").read_text(encoding="utf-8"))
    if not (
        anchor_receipt.get("valid")
        and anchor_receipt.get("familyCounts") == {family: 2 for family in families}
        and len(anchor_receipt.get("cohortSha256", "")) == 64
    ):
        raise ValueError("The sealed four-family anchor is required for E9")
    with (anchor_root / "base" / "metadata.csv").open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise ValueError("E9 anchor metadata has no fields")
    rows_by_sha = {row["sha256"]: row for row in rows}
    selected = {}
    for family in families:
        asset = next((item for item in anchor_receipt["assets"] if item["family"] == family), None)
        if not asset or asset["sha256"] not in rows_by_sha:
            raise ValueError(f"E9 anchor is missing {family}")
        selected[family] = {**asset, "row": rows_by_sha[asset["sha256"]]}

    views_root = dataset_root / "e9_gradient_views_v3"
    if views_root.exists():
        raise FileExistsError("Partial E9 family views exist; inspect before retrying")
    for family, asset in selected.items():
        view = views_root / family
        for name in ("base", "ss_latent", "render_cond"):
            (view / name).mkdir(parents=True, exist_ok=True)
        digest = asset["sha256"]
        shutil.copy2(anchor_root / "ss_latent" / f"{digest}.npz", view / "ss_latent" / f"{digest}.npz")
        shutil.copytree(anchor_root / "render_cond" / digest, view / "render_cond" / digest)
        for name in ("base", "ss_latent", "render_cond"):
            with (view / name / "metadata.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(asset["row"])
    dataset_volume.commit()

    base_files = {
        suffix: hf_hub_download(
            BASE_MODEL_NAME, f"{BASE_SPARSE_FLOW_FILE}.{suffix}", revision=BASE_MODEL_REVISION
        ) for suffix in ("json", "safetensors")
    }
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    experiment_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        base_files["safetensors"], experiment_root / "base-denoiser.pt"
    )
    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    basic_original = basic_path.read_text(encoding="utf-8")
    flow_original = flow_path.read_text(encoding="utf-8")
    family_results = {}
    try:
        basic_path.write_text(smoke_trainer_source_without_snapshots(
            sparse_flow_trainer_source_with_derived_rope_buffer(basic_original)
        ), encoding="utf-8")
        flow_path.write_text(e9_gradient_diagnostic_flow_source(flow_original), encoding="utf-8")
        for family in families:
            run_name = f"{experiment_name}-{family}"
            run_root = Path(f"/checkpoints/{run_name}")
            run_root.mkdir(parents=True)
            config = build_finetune_config(
                json.loads(official.read_text(encoding="utf-8")), trainer_checkpoint,
                max_steps=len(timesteps), save_interval=100, log_interval=1,
            )
            args = config["trainer"]["args"]
            args["mix_precision_mode"] = "amp"
            args["mix_precision_dtype"] = "bfloat16"
            args["batch_size_per_gpu"] = 1
            args["batch_split"] = 1
            args["optimizer"]["args"]["lr"] = 0.0
            args["dentalsculptor_diagnostic_timesteps"] = timesteps
            args["dentalsculptor_occupancy_decoder"] = decoder_name
            args["i_sample"] = 100
            args["i_save"] = 100
            (run_root / "dentalsculptor_sparse_config.json").write_text(
                json.dumps(config, indent=2) + "\n", encoding="utf-8"
            )
            command = e9_family_diagnostic_command(dataset_name, family, run_name)
            result = subprocess.run(
                command, cwd=TRELLIS2_PATH, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            (run_root / "diagnostic.log").write_text(result.stdout, encoding="utf-8")
            print(result.stdout, flush=True)
            if result.returncode:
                checkpoint_volume.commit()
                raise RuntimeError(f"E9 {family} diagnostic exited with code {result.returncode}")
            records = [
                json.loads(line.partition(": ")[2])
                for line in (run_root / "log.txt").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if len(records) != len(timesteps):
                raise RuntimeError(f"E9 {family} emitted {len(records)} diagnostic rows")
            rows_out = []
            for expected_t, record in zip(timesteps, records):
                loss = record["loss"]
                observed_t = float(loss["diagnostic_t"])
                mse = float(loss["mse"])
                raw = float(loss["occupancy_raw"])
                cosine = float(loss["gradient_cosine_similarity"])
                raw_ratio = float(loss["occupancy_to_mse_gradient_norm_ratio"])
                scale = target_ratio * mse / max(raw, 1e-12)
                calibrated_ratio = scale * raw_ratio
                values = [observed_t, mse, raw, cosine, raw_ratio, calibrated_ratio]
                if any(not math.isfinite(value) for value in values) or abs(observed_t - expected_t) > 1e-5:
                    raise RuntimeError(
                        f"E9 {family} emitted invalid diagnostic values at t={expected_t}: {values}"
                    )
                rows_out.append({
                    "timestep": observed_t,
                    "mse": mse,
                    "occupancyBce": float(loss["occupancy_bce"]),
                    "occupancyDice": float(loss["occupancy_dice"]),
                    "occupancyRaw": raw,
                    "gradientCosineSimilarity": cosine,
                    "rawOccupancyToMseGradientNormRatio": raw_ratio,
                    "calibratedOccupancyToMseGradientNormRatio": calibrated_ratio,
                    "safe": cosine > 0.0 and calibrated_ratio <= 0.25,
                })
            if list((run_root / "ckpts").glob("*.pt")):
                raise RuntimeError("E9 diagnostic unexpectedly wrote a candidate checkpoint")
            family_results[family] = rows_out
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
        flow_path.write_text(flow_original, encoding="utf-8")

    timestep_results = []
    for index, timestep in enumerate(timesteps):
        per_family = {family: family_results[family][index] for family in families}
        timestep_results.append({
            "timestep": timestep,
            "perFamily": per_family,
            "safeEveryFamily": all(row["safe"] for row in per_family.values()),
        })
    safe_indices = [index for index, row in enumerate(timestep_results) if row["safeEveryFamily"]]
    adjacent_safe_pair = any(right == left + 1 for left, right in zip(safe_indices, safe_indices[1:]))
    report = {
        "schemaVersion": 1,
        "status": "complete",
        "experimentId": experiment_name,
        "datasetName": dataset_name,
        "anchorCohortSha256": anchor_receipt["cohortSha256"],
        "families": list(families),
        "timesteps": timesteps,
        "acceptanceRules": {
            "gradientCosineStrictlyPositiveEveryFamily": True,
            "maximumCalibratedOccupancyToMseGradientNormRatio": 0.25,
            "minimumAdjacentSafeTimesteps": 2,
        },
        "timestepResults": timestep_results,
        "safeTimesteps": [timesteps[index] for index in safe_indices],
        "adjacentSafePair": adjacent_safe_pair,
        "twoStepE9TrainingPermitted": adjacent_safe_pair,
        "trainingExecuted": False,
        "optimizerLearningRate": 0.0,
        "candidateCheckpointWritten": False,
        "productionMutationPermitted": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return report


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=3 * 60 * 60,
)
def train_e6_sparse_teacher_consistency_canary(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "e6-sparse-teacher-consistency-step10-v1",
    max_steps: int = 10,
) -> dict:
    """Run the smoke-authorized E6 output-consistency canary."""
    consistency_weight = 1.0
    learning_rate = 1e-6
    if (
        dataset_name != "toothfairy-tf-pw32-v1"
        or run_name != "e6-sparse-teacher-consistency-step10-v1"
        or max_steps != 10
    ):
        raise ValueError("The E6 10-step canary contract is sealed")
    smoke_path = Path(
        "/checkpoints/e6-sparse-teacher-consistency-smoke-v1/smoke-evidence.json"
    )
    if not smoke_path.is_file():
        raise FileNotFoundError("Passed E6 smoke evidence is required")
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    if not (
        smoke.get("valid")
        and smoke.get("tenStepCanaryPermitted")
        and smoke.get("teacherFrozen")
        and smoke.get("sameNoiseTimestepAndCondition")
        and smoke.get("teacherConsistencyWeight") == consistency_weight
    ):
        raise ValueError("E6 smoke evidence does not authorize the canary")
    root = Path(f"/datasets/{dataset_name}")
    sparse = json.loads(
        (root / "e3_sparse_structure_latent_receipt.json").read_text(encoding="utf-8")
    )
    if not sparse.get("valid") or sparse.get("observedCount") != 32:
        raise ValueError("Validated 32/32 sparse latents are required")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "canary-evidence.json"
    if evidence_path.exists():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("steps") == max_steps:
            return {**existing, "resumed": True}
        raise ValueError("Existing E6 canary evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E6 canary directory exists; use a new version")

    from huggingface_hub import hf_hub_download

    files = {
        suffix: hf_hub_download(
            BASE_MODEL_NAME,
            f"{BASE_SPARSE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    run_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")),
        trainer_checkpoint,
        max_steps=max_steps,
        save_interval=max_steps,
        log_interval=1,
    )
    trainer_args = config["trainer"]["args"]
    trainer_args["mix_precision_mode"] = "amp"
    trainer_args["mix_precision_dtype"] = "bfloat16"
    trainer_args["optimizer"]["args"]["lr"] = learning_rate
    trainer_args["dentalsculptor_teacher_consistency_weight"] = consistency_weight
    trainer_args["i_sample"] = max_steps + 100
    config_path = run_root / "dentalsculptor_sparse_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    command = sparse_structure_training_command(dataset_name, run_name)

    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    basic_original = basic_path.read_text(encoding="utf-8")
    flow_original = flow_path.read_text(encoding="utf-8")
    basic_path.write_text(
        smoke_trainer_source_without_snapshots(
            sparse_flow_trainer_source_with_derived_rope_buffer(basic_original)
        ), encoding="utf-8"
    )
    flow_path.write_text(
        teacher_consistency_flow_source(flow_original), encoding="utf-8"
    )
    try:
        result = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
        flow_path.write_text(flow_original, encoding="utf-8")
    print(result.stdout, flush=True)
    (run_root / "canary-training.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"E6 teacher-consistency canary exited with code {result.returncode}")

    records = [
        json.loads(line.partition(": ")[2])
        for line in (run_root / "log.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    supervised_losses = [float(row["loss"]["mse"]) for row in records]
    consistency_losses = [
        float(row["loss"]["teacher_consistency_mse"]) for row in records
    ]
    total_losses = [float(row["loss"]["loss"]) for row in records]
    all_losses = supervised_losses + consistency_losses + total_losses
    if (
        len(records) != max_steps
        or any(not math.isfinite(value) or value < 0.0 for value in all_losses)
        or not any(value > 0.0 for value in consistency_losses[1:])
    ):
        checkpoint_volume.commit()
        raise RuntimeError("E6 canary teacher-consistency loss contract failed")
    ckpt_dir = run_root / "ckpts"
    model_checkpoint = ckpt_dir / f"denoiser_step{max_steps:07d}.pt"
    ema_checkpoint = ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt"
    misc_checkpoint = ckpt_dir / f"misc_step{max_steps:07d}.pt"
    if any(
        not path.is_file() or path.stat().st_size == 0
        for path in (model_checkpoint, ema_checkpoint, misc_checkpoint)
    ):
        checkpoint_volume.commit()
        raise RuntimeError("E6 canary checkpoints are incomplete")
    model_drift = checkpoint_relative_l2(Path(trainer_checkpoint), model_checkpoint)
    ema_drift = checkpoint_relative_l2(Path(trainer_checkpoint), ema_checkpoint)

    reload_command = [
        *command, "--load_dir", str(run_root), "--ckpt", str(max_steps), "--tryrun"
    ]
    basic_path.write_text(
        smoke_trainer_source_without_snapshots(basic_original), encoding="utf-8"
    )
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout:
        checkpoint_volume.commit()
        raise RuntimeError("E6 canary checkpoint failed strict reload")
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E6-sparse-frozen-base-output-consistency-ten-step-canary",
        "datasetName": dataset_name,
        "runName": run_name,
        "steps": max_steps,
        "learningRate": learning_rate,
        "teacherConsistencyWeight": consistency_weight,
        "supervisedMse": supervised_losses,
        "teacherConsistencyMse": consistency_losses,
        "totalLoss": total_losses,
        "measuredModelCheckpointRelativeL2": model_drift,
        "measuredEmaCheckpointRelativeL2": ema_drift,
        "candidateCheckpointPath": str(ema_checkpoint),
        "teacherFrozen": True,
        "teacherExcludedFromOptimizerEmaAndCheckpoint": True,
        "sameNoiseTimestepAndCondition": True,
        "checkpointReloaded": True,
        "fourFamilyOccupancyScreenPermitted": True,
        "fullMeshEvaluationPermitted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def smoke_train_e5_sparse_trust_region(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "e5-sparse-trust-region-smoke-v2",
    max_steps: int = 2,
) -> dict:
    """Qualify full-precision training-time projection in exactly two steps."""
    radius = 1e-5
    learning_rate = 1e-6
    if (
        dataset_name != "toothfairy-tf-pw32-v1"
        or run_name != "e5-sparse-trust-region-smoke-v2"
        or max_steps != 2
    ):
        raise ValueError("The E5 smoke contract is sealed")
    root = Path(f"/datasets/{dataset_name}")
    sparse = json.loads(
        (root / "e3_sparse_structure_latent_receipt.json").read_text(encoding="utf-8")
    )
    if not sparse.get("valid") or sparse.get("observedCount") != 32:
        raise ValueError("Validated 32/32 sparse latents are required")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "smoke-evidence.json"
    if evidence_path.exists():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("steps") == 2:
            return {**existing, "resumed": True}
        raise ValueError("Existing E5 smoke evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E5 smoke directory exists; use a new version")

    from huggingface_hub import hf_hub_download

    files = {
        suffix: hf_hub_download(
            BASE_MODEL_NAME,
            f"{BASE_SPARSE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    run_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")),
        trainer_checkpoint,
        max_steps=max_steps,
        save_interval=1,
        log_interval=1,
    )
    trainer_args = config["trainer"]["args"]
    # The trust region must operate on FP32 optimizer/master parameters.  The
    # pinned trainer's default AMP path may retain BF16 parameters, which made
    # post-hoc task-vector scaling discontinuous in E4.  ``inflat_all`` keeps
    # an FP32 master copy and explicitly synchronizes it back to the model.
    trainer_args["mix_precision_mode"] = "inflat_all"
    trainer_args["mix_precision_dtype"] = "bfloat16"
    trainer_args["optimizer"]["args"]["lr"] = learning_rate
    trainer_args["dentalsculptor_trust_region_max_relative_l2"] = radius
    trainer_args["i_sample"] = max_steps + 100
    config_path = run_root / "dentalsculptor_sparse_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    command = sparse_structure_training_command(dataset_name, run_name)

    trainer_source = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    original = trainer_source.read_text(encoding="utf-8")
    patched = smoke_trainer_source_without_snapshots(
        trust_region_trainer_source(
            sparse_flow_trainer_source_with_derived_rope_buffer(original)
        )
    )
    trainer_source.write_text(patched, encoding="utf-8")
    try:
        result = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original, encoding="utf-8")
    print(result.stdout, flush=True)
    (run_root / "smoke-training.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"E5 trust-region smoke exited with code {result.returncode}")

    log_lines = (run_root / "log.txt").read_text(encoding="utf-8").splitlines()
    records = [json.loads(line.partition(": ")[2]) for line in log_lines if line.strip()]
    losses = [float(row["loss"]["loss"]) for row in records]
    drift_after = [float(row["status"]["trust_region_relative_l2_after"]) for row in records]
    projected = [bool(row["status"]["trust_region_projected"]) for row in records]
    if (
        len(records) != max_steps
        or any(not math.isfinite(value) for value in losses + drift_after)
        or any(value > radius * 1.001 for value in drift_after)
    ):
        checkpoint_volume.commit()
        raise RuntimeError("E5 logged trust-region contract failed")
    ckpt_dir = run_root / "ckpts"
    model_checkpoint = ckpt_dir / f"denoiser_step{max_steps:07d}.pt"
    ema_checkpoint = ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt"
    misc_checkpoint = ckpt_dir / f"misc_step{max_steps:07d}.pt"
    required = [model_checkpoint, ema_checkpoint, misc_checkpoint]
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        checkpoint_volume.commit()
        raise RuntimeError("E5 smoke checkpoints are incomplete")
    measured_model_drift = checkpoint_relative_l2(
        Path(trainer_checkpoint), model_checkpoint
    )
    measured_ema_drift = checkpoint_relative_l2(
        Path(trainer_checkpoint), ema_checkpoint
    )
    if measured_model_drift > radius * 1.001 or measured_ema_drift > radius * 1.001:
        checkpoint_volume.commit()
        raise RuntimeError("Persisted E5 checkpoint escaped the trust region")

    reload_command = [*command, "--load_dir", str(run_root), "--ckpt", str(max_steps), "--tryrun"]
    trainer_source.write_text(smoke_trainer_source_without_snapshots(original), encoding="utf-8")
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original, encoding="utf-8")
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout:
        checkpoint_volume.commit()
        raise RuntimeError("E5 smoke checkpoint failed strict reload")
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E5-sparse-training-time-trust-region-two-step-smoke",
        "datasetName": dataset_name,
        "runName": run_name,
        "steps": max_steps,
        "learningRate": learning_rate,
        "maximumRelativeL2Radius": radius,
        "finiteLosses": losses,
        "loggedRelativeL2After": drift_after,
        "projectionActivated": projected,
        "measuredModelCheckpointRelativeL2": measured_model_drift,
        "measuredEmaCheckpointRelativeL2": measured_ema_drift,
        "checkpointReloaded": True,
        "fullPrecisionMasterWeightConstraint": True,
        "mixedPrecisionMode": trainer_args["mix_precision_mode"],
        "mixedPrecisionDtype": trainer_args["mix_precision_dtype"],
        "tenStepCanaryPermitted": True,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=3 * 60 * 60,
)
def train_e5_sparse_trust_region_canary(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "e5-sparse-trust-region-step10-v1",
    max_steps: int = 10,
) -> dict:
    """Run the sealed 10-step E5 canary only after the FP32 smoke passes."""
    radius = 1e-5
    learning_rate = 1e-6
    if (
        dataset_name != "toothfairy-tf-pw32-v1"
        or run_name != "e5-sparse-trust-region-step10-v1"
        or max_steps != 10
    ):
        raise ValueError("The E5 10-step canary contract is sealed")
    smoke_path = Path(
        "/checkpoints/e5-sparse-trust-region-smoke-v2/smoke-evidence.json"
    )
    if not smoke_path.is_file():
        raise FileNotFoundError("Passed E5 smoke evidence is required")
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    if not (
        smoke.get("valid")
        and smoke.get("tenStepCanaryPermitted")
        and smoke.get("fullPrecisionMasterWeightConstraint")
        and smoke.get("mixedPrecisionMode") == "inflat_all"
        and smoke.get("steps") == 2
    ):
        raise ValueError("E5 smoke evidence does not authorize the canary")
    root = Path(f"/datasets/{dataset_name}")
    sparse = json.loads(
        (root / "e3_sparse_structure_latent_receipt.json").read_text(encoding="utf-8")
    )
    if not sparse.get("valid") or sparse.get("observedCount") != 32:
        raise ValueError("Validated 32/32 sparse latents are required")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "canary-evidence.json"
    if evidence_path.exists():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("steps") == max_steps:
            return {**existing, "resumed": True}
        raise ValueError("Existing E5 canary evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E5 canary directory exists; use a new version")

    from huggingface_hub import hf_hub_download

    files = {
        suffix: hf_hub_download(
            BASE_MODEL_NAME,
            f"{BASE_SPARSE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    run_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")),
        trainer_checkpoint,
        max_steps=max_steps,
        save_interval=max_steps,
        log_interval=1,
    )
    trainer_args = config["trainer"]["args"]
    trainer_args["mix_precision_mode"] = "inflat_all"
    trainer_args["mix_precision_dtype"] = "bfloat16"
    trainer_args["optimizer"]["args"]["lr"] = learning_rate
    trainer_args["dentalsculptor_trust_region_max_relative_l2"] = radius
    trainer_args["i_sample"] = max_steps + 100
    config_path = run_root / "dentalsculptor_sparse_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    command = sparse_structure_training_command(dataset_name, run_name)

    trainer_source = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    original = trainer_source.read_text(encoding="utf-8")
    patched = smoke_trainer_source_without_snapshots(
        trust_region_trainer_source(
            sparse_flow_trainer_source_with_derived_rope_buffer(original)
        )
    )
    trainer_source.write_text(patched, encoding="utf-8")
    try:
        result = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original, encoding="utf-8")
    print(result.stdout, flush=True)
    (run_root / "canary-training.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"E5 trust-region canary exited with code {result.returncode}")

    records = [
        json.loads(line.partition(": ")[2])
        for line in (run_root / "log.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    losses = [float(row["loss"]["loss"]) for row in records]
    drift_after = [
        float(row["status"]["trust_region_relative_l2_after"])
        for row in records
    ]
    projected = [bool(row["status"]["trust_region_projected"]) for row in records]
    if (
        len(records) != max_steps
        or any(not math.isfinite(value) for value in losses + drift_after)
        or any(value > radius * 1.001 for value in drift_after)
    ):
        checkpoint_volume.commit()
        raise RuntimeError("E5 canary logged trust-region contract failed")
    ckpt_dir = run_root / "ckpts"
    model_checkpoint = ckpt_dir / f"denoiser_step{max_steps:07d}.pt"
    ema_checkpoint = ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt"
    misc_checkpoint = ckpt_dir / f"misc_step{max_steps:07d}.pt"
    if any(
        not path.is_file() or path.stat().st_size == 0
        for path in (model_checkpoint, ema_checkpoint, misc_checkpoint)
    ):
        checkpoint_volume.commit()
        raise RuntimeError("E5 canary checkpoints are incomplete")
    measured_model_drift = checkpoint_relative_l2(
        Path(trainer_checkpoint), model_checkpoint
    )
    measured_ema_drift = checkpoint_relative_l2(
        Path(trainer_checkpoint), ema_checkpoint
    )
    if measured_model_drift > radius * 1.001 or measured_ema_drift > radius * 1.001:
        checkpoint_volume.commit()
        raise RuntimeError("Persisted E5 canary checkpoint escaped the trust region")

    reload_command = [
        *command, "--load_dir", str(run_root), "--ckpt", str(max_steps), "--tryrun"
    ]
    trainer_source.write_text(
        smoke_trainer_source_without_snapshots(original), encoding="utf-8"
    )
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original, encoding="utf-8")
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout:
        checkpoint_volume.commit()
        raise RuntimeError("E5 canary checkpoint failed strict reload")
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E5-sparse-training-time-trust-region-ten-step-canary",
        "datasetName": dataset_name,
        "runName": run_name,
        "steps": max_steps,
        "learningRate": learning_rate,
        "maximumRelativeL2Radius": radius,
        "finiteLosses": losses,
        "loggedRelativeL2After": drift_after,
        "projectionActivated": projected,
        "measuredModelCheckpointRelativeL2": measured_model_drift,
        "measuredEmaCheckpointRelativeL2": measured_ema_drift,
        "candidateCheckpointPath": str(ema_checkpoint),
        "checkpointReloaded": True,
        "fullPrecisionMasterWeightConstraint": True,
        "mixedPrecisionMode": trainer_args["mix_precision_mode"],
        "mixedPrecisionDtype": trainer_args["mix_precision_dtype"],
        "fourFamilyOccupancyScreenPermitted": True,
        "fullMeshEvaluationPermitted": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    timeout=3 * 60 * 60,
)
def train_e3_sparse_tf_pw32(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "e3-sparse-tf-pw32-step50-v1",
    max_steps: int = 50,
) -> dict:
    """Run the registered E3-B 50-step engineering canary; never deploy it."""
    if (
        dataset_name != "toothfairy-tf-pw32-v1"
        or run_name != "e3-sparse-tf-pw32-step50-v1"
        or max_steps != 50
    ):
        raise ValueError("The E3-B canary contract is fixed at TF-PW32 and 50 steps")
    root = Path(f"/datasets/{dataset_name}")
    sparse_path = root / "e3_sparse_structure_latent_receipt.json"
    smoke_path = Path("/checkpoints/e3-sparse-smoke-v1/smoke-evidence.json")
    if not sparse_path.is_file() or not smoke_path.is_file():
        raise FileNotFoundError("Validated sparse latents and passed two-step smoke are required")
    sparse = json.loads(sparse_path.read_text(encoding="utf-8"))
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    if (
        not sparse.get("valid") or sparse.get("observedCount") != 32
        or not smoke.get("valid") or not smoke.get("checkpointReloaded")
        or smoke.get("steps") != 2
    ):
        raise ValueError("E3-B prerequisite receipts failed their sealed contracts")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "training-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("steps") == max_steps:
            return {**existing, "resumed": True}
        raise ValueError("Existing E3-B evidence is invalid; do not overwrite")
    if run_root.exists():
        raise FileExistsError("Partial E3-B run exists; use a new registered version")

    from huggingface_hub import hf_hub_download
    files = {
        suffix: hf_hub_download(
            "microsoft/TRELLIS.2-4B",
            f"{BASE_SPARSE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    run_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")), trainer_checkpoint,
        max_steps=max_steps, save_interval=max_steps, log_interval=1,
    )
    config["trainer"]["args"]["i_sample"] = max_steps + 100
    config_path = run_root / "dentalsculptor_sparse_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    command = sparse_structure_training_command(dataset_name, run_name)
    trainer_source = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    original = trainer_source.read_text(encoding="utf-8")
    patched = smoke_trainer_source_without_snapshots(
        sparse_flow_trainer_source_with_derived_rope_buffer(original)
    )
    trainer_source.write_text(patched, encoding="utf-8")
    try:
        result = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original, encoding="utf-8")
    print(result.stdout, flush=True)
    (run_root / "training.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"E3-B trainer exited with code {result.returncode}")
    losses = finite_losses_from_training_log(
        (run_root / "log.txt").read_text(encoding="utf-8")
    )
    if len(losses) != max_steps or any(not math.isfinite(value) for value in losses):
        checkpoint_volume.commit()
        raise RuntimeError(f"Expected exactly {max_steps} finite E3-B losses")
    ckpt_dir = run_root / "ckpts"
    required = [
        ckpt_dir / f"denoiser_step{max_steps:07d}.pt",
        ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt",
        ckpt_dir / f"misc_step{max_steps:07d}.pt",
    ]
    missing = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        checkpoint_volume.commit()
        raise RuntimeError(f"E3-B checkpoint contract failed: {missing}")
    reload_command = [*command, "--load_dir", str(run_root), "--ckpt", str(max_steps), "--tryrun"]
    trainer_source.write_text(smoke_trainer_source_without_snapshots(original), encoding="utf-8")
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original, encoding="utf-8")
    if (
        reload_result.returncode or "Loading checkpoint" not in reload_result.stdout
        or "Done." not in reload_result.stdout
    ):
        checkpoint_volume.commit()
        raise RuntimeError("E3-B step-50 checkpoint failed strict reload")
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E3-B-sparse-flow-step50-engineering-canary",
        "datasetName": dataset_name,
        "datasetManifestSha256": sparse["datasetManifestSha256"],
        "assetCount": 32,
        "runName": run_name,
        "steps": max_steps,
        "finiteLossCount": len(losses),
        "firstLoss": losses[0],
        "lastLoss": losses[-1],
        "checkpointFiles": [
            {"path": str(path), "bytes": path.stat().st_size} for path in required
        ],
        "checkpointReloaded": True,
        "baseModelRevision": BASE_MODEL_REVISION,
        "baseSparseFlowCheckpoint": BASE_SPARSE_FLOW_FILE,
        "trainingCodeCommit": TRAINING_CODE_COMMIT,
        "evaluationRequiredBeforeAdvance": True,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    timeout=2 * 60 * 60,
)
def smoke_train(
    dataset_name: str = "dental-anatomy-v1",
    run_name: str = "dental-anatomy-smoke-v1",
    max_steps: int = 2,
) -> dict:
    """Run two optimizer steps, save, and force a real checkpoint reload."""
    if max_steps < 2 or max_steps > 10:
        raise ValueError("Smoke training is restricted to 2-10 steps.")
    smoke_root = Path(f"/datasets/{dataset_name}/smoke_training_v1")
    receipt_path = smoke_root / "receipt.json"
    if not receipt_path.is_file():
        raise FileNotFoundError("Run prepare_training_smoke_inputs first.")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    families = [item["family"] for item in receipt.get("assets", [])]
    if (
        not receipt.get("valid") or receipt.get("assetCount") != 8
        or any(families.count(name) != 2 for name in ("incisor", "canine", "premolar", "molar"))
        or any(item.get("split") != "train" for item in receipt.get("assets", []))
    ):
        raise ValueError("Smoke receipt is not the sealed two-per-family cohort.")

    from huggingface_hub import hf_hub_download
    files = {
        suffix: hf_hub_download(
            "microsoft/TRELLIS.2-4B", f"{BASE_SHAPE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    base_prefix = str(Path(files["json"]).with_suffix(""))
    if Path(files["safetensors"]).with_suffix("") != Path(base_prefix):
        raise ValueError("Pinned smoke base checkpoint files do not share a prefix.")
    official = Path(TRELLIS2_PATH) / "configs/gen/slat_flow_img2shape_dit_1_3B_512_bf16.json"
    run_root = Path(f"/checkpoints/{run_name}")
    if run_root.exists():
        import shutil
        shutil.rmtree(run_root)
    run_root.mkdir(parents=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")), trainer_checkpoint,
        max_steps=max_steps, save_interval=1, log_interval=1,
    )
    config["trainer"]["args"]["i_sample"] = max_steps + 100
    config_path = run_root / "dentalsculptor_smoke_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    command = smoke_training_command(dataset_name, run_name)
    trainer_source = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    original_trainer_source = trainer_source.read_text(encoding="utf-8")
    trainer_source.write_text(
        smoke_trainer_source_without_snapshots(original_trainer_source), encoding="utf-8"
    )
    lines = []
    try:
        process = subprocess.Popen(
            command, cwd=TRELLIS2_PATH, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            lines.append(line)
        return_code = process.wait()
    finally:
        trainer_source.write_text(original_trainer_source, encoding="utf-8")
    log = "".join(lines)
    (run_root / "smoke-training.log").write_text(log, encoding="utf-8")
    if return_code:
        checkpoint_volume.commit()
        raise RuntimeError(f"Smoke trainer exited with code {return_code}.")
    canonical_log_path = run_root / "log.txt"
    canonical_log = canonical_log_path.read_text(encoding="utf-8") if canonical_log_path.is_file() else ""
    losses = finite_losses_from_training_log(canonical_log)
    if not losses or any(not math.isfinite(value) for value in losses):
        checkpoint_volume.commit()
        raise RuntimeError("Smoke training did not emit a finite loss value.")

    ckpt_dir = run_root / "ckpts"
    required = [
        ckpt_dir / f"denoiser_step{max_steps:07d}.pt",
        ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt",
        ckpt_dir / f"misc_step{max_steps:07d}.pt",
    ]
    missing = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        checkpoint_volume.commit()
        raise RuntimeError(f"Smoke checkpoint contract failed: {missing}")

    reload_command = [*command, "--load_dir", str(run_root), "--ckpt", str(max_steps)]
    trainer_source.write_text(
        smoke_trainer_source_without_snapshots(original_trainer_source), encoding="utf-8"
    )
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original_trainer_source, encoding="utf-8")
    print(reload_result.stdout, flush=True)
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout or "Done." not in reload_result.stdout:
        checkpoint_volume.commit()
        raise RuntimeError("Saved checkpoint could not be reloaded by the pinned TRELLIS trainer.")
    evidence = {
        "schemaVersion": 1, "valid": True, "datasetName": dataset_name,
        "runName": run_name, "steps": max_steps, "finiteLosses": losses,
        "checkpointFiles": [{"path": str(path), "bytes": path.stat().st_size} for path in required],
        "checkpointReloaded": True, "baseModelRevision": BASE_MODEL_REVISION,
        "trainingCodeCommit": TRAINING_CODE_COMMIT,
    }
    (run_root / "smoke-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    timeout=60 * 60,
)
def verify_smoke_checkpoint(
    dataset_name: str = "dental-anatomy-v1",
    run_name: str = "dental-anatomy-smoke-v1",
    max_steps: int = 2,
) -> dict:
    """Verify already-completed smoke losses/checkpoints and reload without another optimizer step."""
    run_root = Path(f"/checkpoints/{run_name}")
    config_path = run_root / "dentalsculptor_smoke_config.json"
    log_path = run_root / "log.txt"
    if not config_path.is_file() or not log_path.is_file():
        raise FileNotFoundError("Completed smoke config/log are missing; do not infer success.")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("trainer", {}).get("args", {}).get("max_steps") != max_steps:
        raise ValueError("Persisted smoke config does not match the requested step count.")
    losses = finite_losses_from_training_log(log_path.read_text(encoding="utf-8"))
    if len(losses) != max_steps:
        raise ValueError(f"Expected {max_steps} canonical losses; found {len(losses)}.")
    ckpt_dir = run_root / "ckpts"
    required = [
        ckpt_dir / f"denoiser_step{max_steps:07d}.pt",
        ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt",
        ckpt_dir / f"misc_step{max_steps:07d}.pt",
    ]
    missing = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError(f"Smoke checkpoint contract failed: {missing}")
    command = smoke_training_command(dataset_name, run_name)
    reload_command = [*command, "--load_dir", str(run_root), "--ckpt", str(max_steps)]
    trainer_source = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    original = trainer_source.read_text(encoding="utf-8")
    trainer_source.write_text(smoke_trainer_source_without_snapshots(original), encoding="utf-8")
    try:
        result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original, encoding="utf-8")
    print(result.stdout, flush=True)
    if result.returncode or "Loading checkpoint" not in result.stdout or "Done." not in result.stdout:
        raise RuntimeError("Saved checkpoint could not be reloaded by the pinned TRELLIS trainer.")
    evidence = {
        "schemaVersion": 1, "valid": True, "datasetName": dataset_name,
        "runName": run_name, "steps": max_steps, "finiteLosses": losses,
        "checkpointFiles": [{"path": str(path), "bytes": path.stat().st_size} for path in required],
        "checkpointReloaded": True, "baseModelRevision": BASE_MODEL_REVISION,
        "trainingCodeCommit": TRAINING_CODE_COMMIT,
    }
    (run_root / "smoke-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    timeout=2 * 60 * 60,
)
def train_provisional_tf_pw32(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "toothfairy-tf-pw32-step50-v2",
    max_steps: int = 50,
) -> dict:
    """Run the registered, bounded TF-PW32 learning screen; never deploy it."""
    if (
        dataset_name != "toothfairy-tf-pw32-v1"
        or run_name != "toothfairy-tf-pw32-step50-v2"
        or max_steps != 50
    ):
        raise ValueError("The provisional v1 learning contract is fixed at TF-PW32 and 50 steps")
    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    status_path = root / "preprocess_status.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    family_counts = {
        family: sum(asset.get("toothFamily") == family for asset in manifest.get("assets", []))
        for family in ("incisor", "canine", "premolar", "molar")
    }
    if (
        manifest.get("assetCount") != 32
        or family_counts != {family: 8 for family in family_counts}
        or manifest.get("trainingPurpose") != "engineering-smoke-only"
        or manifest.get("clinicalClaimPermitted") is not False
        or status.get("stage") != "trellis-preprocessed"
        or status.get("assetCount") != 32
        or status.get("successfulConditionalRenders") != 32
        or status.get("resolution") != 512
    ):
        raise ValueError("The sealed TF-PW32 dataset/preprocessing contract is not satisfied")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "provisional-training-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("steps") == max_steps:
            return {**existing, "resumed": True}
        raise ValueError("Existing provisional run is incomplete; use a new versioned run name")

    training_view = prepare_training_metadata_view(root, 512)
    if training_view["trainCount"] != 32:
        raise ValueError("TF-PW32 training metadata must contain exactly 32 assets")
    from huggingface_hub import hf_hub_download

    files = {
        suffix: hf_hub_download(
            "microsoft/TRELLIS.2-4B", f"{BASE_SHAPE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        ) for suffix in ("json", "safetensors")
    }
    run_root.mkdir(parents=True, exist_ok=False)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    official = Path(TRELLIS2_PATH) / "configs/gen/slat_flow_img2shape_dit_1_3B_512_bf16.json"
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")),
        trainer_checkpoint,
        max_steps=max_steps,
        save_interval=max_steps,
        log_interval=5,
    )
    config["trainer"]["args"]["i_sample"] = max_steps + 100
    config_path = run_root / "dentalsculptor_finetune_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    command = training_command(dataset_name, run_name, 512)
    trainer_source = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    original = trainer_source.read_text(encoding="utf-8")
    trainer_source.write_text(smoke_trainer_source_without_snapshots(original), encoding="utf-8")
    try:
        process = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original, encoding="utf-8")
    print(process.stdout, flush=True)
    (run_root / "training.log").write_text(process.stdout, encoding="utf-8")
    if process.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"TF-PW32 trainer exited with code {process.returncode}")
    canonical_log = (run_root / "log.txt").read_text(encoding="utf-8")
    losses = finite_losses_from_training_log(canonical_log)
    if not losses or any(not math.isfinite(value) for value in losses):
        checkpoint_volume.commit()
        raise RuntimeError("TF-PW32 training did not emit finite canonical losses")
    ckpt_dir = run_root / "ckpts"
    required = [
        ckpt_dir / f"denoiser_step{max_steps:07d}.pt",
        ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt",
        ckpt_dir / f"misc_step{max_steps:07d}.pt",
    ]
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        checkpoint_volume.commit()
        raise RuntimeError("TF-PW32 final checkpoint contract failed")
    reload_command = [*command, "--load_dir", str(run_root), "--ckpt", str(max_steps)]
    trainer_source.write_text(smoke_trainer_source_without_snapshots(original), encoding="utf-8")
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        trainer_source.write_text(original, encoding="utf-8")
    if (
        reload_result.returncode
        or "Loading checkpoint" not in reload_result.stdout
        or "Done." not in reload_result.stdout
    ):
        checkpoint_volume.commit()
        raise RuntimeError("TF-PW32 step-50 checkpoint could not be reloaded")
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "claimScope": "engineering-learning-screen-only",
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
        "datasetName": dataset_name,
        "datasetAssetCount": 32,
        "familyCounts": family_counts,
        "runName": run_name,
        "steps": max_steps,
        "learningRate": 1e-5,
        "finiteLosses": losses,
        "checkpointFiles": [
            {"path": str(path), "bytes": path.stat().st_size} for path in required
        ],
        "checkpointReloaded": True,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trainingCodeCommit": TRAINING_CODE_COMMIT,
        "trainingMetadata": training_view,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    timeout=2 * 60 * 60,
)
def train_stage1_whole_tooth_canary(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "toothfairy-stage1-shape-step50-seed1724708096-v1",
    max_steps: int = 50,
    experiment_seed: int = 1724708096,
) -> dict:
    """Run one registered Stage-1 learning canary; evaluation is still mandatory."""
    expected_run = "toothfairy-stage1-shape-step50-seed1724708096-v1"
    if (
        dataset_name != "toothfairy-stage1-v1"
        or run_name != expected_run
        or max_steps != 50
        or experiment_seed != 1724708096
    ):
        raise ValueError("Stage-1 canary A is sealed at 50 steps and seed 1724708096")
    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    receipt_path = root / "stage1_preprocess_receipt.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    train_family_counts = {
        family: sum(
            asset.get("split") == "train" and asset.get("toothFamily") == family
            for asset in manifest.get("assets", [])
        )
        for family in ("incisor", "canine", "premolar", "molar")
    }
    if (
        manifest.get("assetCount") != 164
        or manifest.get("splits") != {"train": 128, "validation": 12, "test": 24}
        or train_family_counts != {family: 32 for family in train_family_counts}
        or receipt.get("stage") != "clinical-stage1-preprocessing-finalized"
        or receipt.get("valid") is not True
        or receipt.get("manifestSha256") != hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        or receipt.get("conditionalRenders", {}).get("validatedAssetCount") != 128
        or receipt.get("optimizerExecuted") is not False
    ):
        raise ValueError("The sealed Stage-1 dataset/preprocessing contract is not satisfied")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "stage1-canary-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("steps") == max_steps:
            return {**existing, "resumed": True}
        raise ValueError("Existing Stage-1 canary is incomplete; use a new versioned run")
    if run_root.exists():
        raise FileExistsError("Partial Stage-1 canary exists; inspect it before retrying")

    training_view = prepare_training_metadata_view(root, 512)
    if (
        training_view.get("trainCount") != 128
        or training_view.get("uniqueTrainHashes") != 128
    ):
        raise ValueError("Stage-1 training view must contain exactly 128 unique train assets")
    from huggingface_hub import hf_hub_download

    files = {
        suffix: hf_hub_download(
            "microsoft/TRELLIS.2-4B",
            f"{BASE_SHAPE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        )
        for suffix in ("json", "safetensors")
    }
    run_root.mkdir(parents=True, exist_ok=False)
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt"
    )
    official = Path(TRELLIS2_PATH) / "configs/gen/slat_flow_img2shape_dit_1_3B_512_bf16.json"
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")),
        trainer_checkpoint,
        max_steps=max_steps,
        save_interval=max_steps,
        log_interval=5,
    )
    config["experimentSeed"] = experiment_seed
    config["trainer"]["args"]["i_sample"] = max_steps + 100
    config_path = run_root / "dentalsculptor_finetune_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    command = training_command(dataset_name, run_name, 512)
    command[command.index("--auto_retry") + 1] = "0"
    trainer_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    entry_path = Path(TRELLIS2_PATH) / "train.py"
    original_trainer = trainer_path.read_text(encoding="utf-8")
    original_entry = entry_path.read_text(encoding="utf-8")
    trainer_path.write_text(
        smoke_trainer_source_without_snapshots(original_trainer), encoding="utf-8"
    )
    entry_path.write_text(
        training_entry_source_with_experiment_seed(original_entry, experiment_seed),
        encoding="utf-8",
    )
    try:
        process = subprocess.run(
            command,
            cwd=TRELLIS2_PATH,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    finally:
        trainer_path.write_text(original_trainer, encoding="utf-8")
        entry_path.write_text(original_entry, encoding="utf-8")
    print(process.stdout, flush=True)
    (run_root / "training.log").write_text(process.stdout, encoding="utf-8")
    if process.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"Stage-1 canary trainer exited with code {process.returncode}")
    canonical_log = (run_root / "log.txt").read_text(encoding="utf-8")
    losses = finite_losses_from_training_log(canonical_log)
    if not losses or any(not math.isfinite(value) for value in losses):
        checkpoint_volume.commit()
        raise RuntimeError("Stage-1 canary did not emit finite canonical losses")
    ckpt_dir = run_root / "ckpts"
    required = [
        ckpt_dir / f"denoiser_step{max_steps:07d}.pt",
        ckpt_dir / f"denoiser_ema0.9999_step{max_steps:07d}.pt",
        ckpt_dir / f"misc_step{max_steps:07d}.pt",
    ]
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        checkpoint_volume.commit()
        raise RuntimeError("Stage-1 canary final checkpoint contract failed")
    reload_command = [*command, "--load_dir", str(run_root), "--ckpt", str(max_steps)]
    trainer_path.write_text(
        smoke_trainer_source_without_snapshots(original_trainer), encoding="utf-8"
    )
    entry_path.write_text(
        training_entry_source_with_experiment_seed(original_entry, experiment_seed),
        encoding="utf-8",
    )
    try:
        reload_result = subprocess.run(
            reload_command,
            cwd=TRELLIS2_PATH,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    finally:
        trainer_path.write_text(original_trainer, encoding="utf-8")
        entry_path.write_text(original_entry, encoding="utf-8")
    if (
        reload_result.returncode
        or "Loading checkpoint" not in reload_result.stdout
        or "Done." not in reload_result.stdout
    ):
        checkpoint_volume.commit()
        raise RuntimeError("Stage-1 step-50 checkpoint could not be reloaded")
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "claimScope": "registered-stage1-learning-canary-only",
        "clinicalImprovementClaimPermitted": False,
        "productionPromotionPermitted": False,
        "evaluationRequiredBeforeAdvance": True,
        "datasetName": dataset_name,
        "datasetAssetCount": 164,
        "trainingAssetCount": 128,
        "validationAssetCount": 12,
        "testAssetCount": 24,
        "trainFamilyCounts": train_family_counts,
        "runName": run_name,
        "steps": max_steps,
        "experimentSeed": experiment_seed,
        "learningRate": 1e-5,
        "finiteLosses": losses,
        "checkpointFiles": [
            {"path": str(path), "bytes": path.stat().st_size} for path in required
        ],
        "checkpointReloaded": True,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trainingCodeCommit": TRAINING_CODE_COMMIT,
        "trainingMetadata": training_view,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def run_e10_g1_one_tooth_integration(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e10-g1-one-tooth-v4",
    max_steps: int = 1,
    experiment_seed: int = 20260920,
    objective: str = "e10",
) -> dict:
    """Run E10/E11's one-step integration and frozen-condition decode."""
    import io
    import os
    import random
    import shutil
    import sys

    import numpy as np
    import torch
    import trimesh
    from PIL import Image
    from huggingface_hub import hf_hub_download

    sealed_runs = {
        "e10": "stage1-e10-g1-one-tooth-v4",
        "e11": "stage1-e11-g1-one-tooth-v1",
    }
    if (
        dataset_name != "toothfairy-stage1-v1"
        or sealed_runs.get(objective) != run_name
        or max_steps != 1
        or experiment_seed != 20260920
    ):
        raise ValueError("E10/E11 G1 is sealed at one step and seed 20260920")
    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    preprocess_path = root / "stage1_preprocess_receipt.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    preprocess = json.loads(preprocess_path.read_text(encoding="utf-8"))
    if (
        manifest.get("assetCount") != 164
        or manifest.get("splits") != {"train": 128, "validation": 12, "test": 24}
        or preprocess.get("valid") is not True
        or preprocess.get("manifestSha256") != hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    ):
        raise ValueError("E10 G1 requires the sealed Stage-1 dataset and preprocessing")

    view = root / "e10_g1_one_tooth_v1"
    view_receipt_path = view / "receipt.json"
    latent_name = "shape_enc_next_dc_f16c32_fp16_512"
    if view_receipt_path.is_file():
        view_receipt = json.loads(view_receipt_path.read_text(encoding="utf-8"))
        if not view_receipt.get("valid") or view_receipt.get("assetCount") != 1:
            raise ValueError("Existing E10 G1 one-tooth view is invalid")
    else:
        if view.exists():
            raise FileExistsError("Partial E10 G1 view exists; inspect before retrying")
        source_metadata = root / "training_views" / "train" / "metadata.csv"
        with source_metadata.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            fieldnames = reader.fieldnames
            rows = list(reader)
        if not fieldnames or len(rows) != 128:
            raise ValueError("E10 G1 requires the sealed 128-row training view")
        selected = sorted(rows, key=lambda row: row["sha256"])[0]
        digest = selected["sha256"]
        latent_source = root / "shape_latents" / latent_name / f"{digest}.npz"
        render_source = root / "renders_cond" / digest
        if not latent_source.is_file() or not render_source.is_dir():
            raise FileNotFoundError("E10 G1 selected tooth is missing latent or render inputs")
        for name in ("base", "shape_latent", "render_cond"):
            (view / name).mkdir(parents=True, exist_ok=False)
        shutil.copy2(latent_source, view / "shape_latent" / latent_source.name)
        shutil.copytree(render_source, view / "render_cond" / digest)
        for name in ("base", "shape_latent", "render_cond"):
            with (view / name / "metadata.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(selected)
        view_receipt = {
            "schemaVersion": 1,
            "valid": True,
            "stage": "E10-G1-one-tooth-view",
            "assetCount": 1,
            "sha256": digest,
            "selection": "lexicographically-first-training-sha256",
            "latentSha256": hashlib.sha256(latent_source.read_bytes()).hexdigest(),
        }
        view_receipt_path.write_text(
            json.dumps(view_receipt, indent=2) + "\n", encoding="utf-8"
        )
        dataset_volume.commit()

    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "g1-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") and existing.get("g2Authorized") is True:
            return {**existing, "resumed": True}
        raise ValueError("Existing E10 G1 evidence is not valid")
    if run_root.exists():
        raise FileExistsError("Partial E10 G1 run exists; use a new version after diagnosis")

    base_files = {
        suffix: hf_hub_download(
            BASE_MODEL_NAME,
            f"{BASE_SHAPE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        )
        for suffix in ("json", "safetensors")
    }
    run_root.mkdir(parents=True, exist_ok=False)
    trainer_checkpoint = materialize_trainer_checkpoint(
        base_files["safetensors"], run_root / "base-denoiser.pt"
    )
    official = Path(TRELLIS2_PATH) / "configs/gen/slat_flow_img2shape_dit_1_3B_512_bf16.json"
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")),
        trainer_checkpoint,
        max_steps=1,
        save_interval=1,
        log_interval=1,
    )
    args = config["trainer"]["args"]
    args["batch_size_per_gpu"] = 1
    args["batch_split"] = 1
    args["optimizer"]["args"]["lr"] = 1e-6
    args["dentalsculptor_axial_band_count"] = 4
    args["dentalsculptor_teacher_target_ratio"] = 0.05
    args["i_sample"] = 101
    config["experimentSeed"] = experiment_seed
    (run_root / "dentalsculptor_finetune_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    command = e10_one_tooth_training_command(dataset_name, run_name)
    trainer_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    sparse_flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/sparse_flow_matching.py"
    entry_path = Path(TRELLIS2_PATH) / "train.py"
    trainer_original = trainer_path.read_text(encoding="utf-8")
    flow_original = flow_path.read_text(encoding="utf-8")
    sparse_flow_original = sparse_flow_path.read_text(encoding="utf-8")
    entry_original = entry_path.read_text(encoding="utf-8")

    def install_e10_sources() -> None:
        trainer_path.write_text(
            e10_post_update_probe_trainer_source(
                smoke_trainer_source_without_snapshots(trainer_original)
            ), encoding="utf-8"
        )
        flow_path.write_text(
            e10_teacher_init_flow_source(flow_original), encoding="utf-8"
        )
        sparse_flow_path.write_text(
            (
                e11_bandwise_teacher_sparse_flow_source(sparse_flow_original)
                if objective == "e11"
                else e10_axial_sparse_flow_source(sparse_flow_original)
            ),
            encoding="utf-8",
        )
        entry_path.write_text(
            training_entry_source_with_experiment_seed(entry_original, experiment_seed),
            encoding="utf-8",
        )

    def restore_sources() -> None:
        trainer_path.write_text(trainer_original, encoding="utf-8")
        flow_path.write_text(flow_original, encoding="utf-8")
        sparse_flow_path.write_text(sparse_flow_original, encoding="utf-8")
        entry_path.write_text(entry_original, encoding="utf-8")

    install_e10_sources()
    try:
        trainer_env = os.environ.copy()
        objective_receipt_path = run_root / "objective-receipt.jsonl"
        trainer_env["DENTALSCULPTOR_E10_OBJECTIVE_RECEIPT"] = str(objective_receipt_path)
        trainer_env["DENTALSCULPTOR_E10_POST_UPDATE_PROBE"] = "1"
        process = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=trainer_env,
        )
    finally:
        restore_sources()
    (run_root / "training.log").write_text(process.stdout, encoding="utf-8")
    print(process.stdout, flush=True)
    if process.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"E10 G1 trainer exited with code {process.returncode}")
    objective_records = [
        json.loads(line) for line in objective_receipt_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(objective_records) != 2:
        raise RuntimeError(f"E10 G1 expected pre/post objective receipts, found {len(objective_records)}")
    pre_update, loss = objective_records
    if pre_update.get("phase") != "pre_update" or loss.get("phase") != "post_update_probe":
        raise RuntimeError(f"E10 G1 objective receipt phases drifted: {objective_records}")
    if pre_update.get("teacher_consistency_mse") != 0.0 or pre_update.get("teacher_consistency_contribution") != 0.0:
        raise RuntimeError(f"E10 G1 initial student/teacher identity failed: {pre_update}")
    required_losses = (
        "loss", "mse", "axial_band_balanced_mse", "teacher_consistency_mse",
        "teacher_consistency_scale", "teacher_consistency_contribution",
    )
    loss_values = {name: float(loss[name]) for name in required_losses}
    if any(not math.isfinite(value) or value < 0 for value in loss_values.values()):
        raise RuntimeError(f"E10 G1 emitted invalid losses: {loss_values}")
    observed_teacher_ratio = (
        loss_values["teacher_consistency_contribution"]
        / max(loss_values["axial_band_balanced_mse"], 1e-12)
    )
    if abs(observed_teacher_ratio - 0.05) > 1e-4:
        raise RuntimeError(f"E10 G1 teacher ratio drifted: {observed_teacher_ratio}")
    if loss.get("teacherFrozen") is not True or loss.get("populatedAxialBands") != 4:
        raise RuntimeError(f"E10 G1 objective contract failed: {loss}")
    if objective == "e11":
        if loss.get("teacherConsistencyMode") != "equal-per-sample-per-axial-band":
            raise RuntimeError(f"E11 G1 did not execute bandwise preservation: {loss}")
        teacher_band_bounds = {
            "minimum": float(loss["teacherBandMseMin"]),
            "maximum": float(loss["teacherBandMseMax"]),
        }
        if any(not math.isfinite(value) or value < 0 for value in teacher_band_bounds.values()):
            raise RuntimeError(f"E11 G1 emitted invalid teacher band bounds: {teacher_band_bounds}")
    else:
        teacher_band_bounds = None

    ckpt_dir = run_root / "ckpts"
    model_checkpoint = ckpt_dir / "denoiser_step0000001.pt"
    ema_checkpoint = ckpt_dir / "denoiser_ema0.9999_step0000001.pt"
    misc_checkpoint = ckpt_dir / "misc_step0000001.pt"
    if any(
        not path.is_file() or path.stat().st_size == 0
        for path in (model_checkpoint, ema_checkpoint, misc_checkpoint)
    ):
        raise RuntimeError("E10 G1 checkpoint contract failed")
    reload_command = [*command, "--load_dir", str(run_root), "--ckpt", "1", "--tryrun"]
    install_e10_sources()
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        restore_sources()
    (run_root / "reload.log").write_text(reload_result.stdout, encoding="utf-8")
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout:
        raise RuntimeError("E10 G1 checkpoint failed strict reload")

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator

    validation = json.loads(
        (root / "stage1_validation_inputs_v1.json").read_text(encoding="utf-8")
    )
    case = validation["cases"][0]
    coords_path = (
        root / "stage1_seed_a_raw_validation_v2_outputs" /
        "frozen_sparse_conditions" / f"{case['id']}.pt"
    )
    coords_cpu = torch.load(coords_path, map_location="cpu", weights_only=True)
    expected_coords_hash = hashlib.sha256(
        coords_cpu.contiguous().numpy().tobytes()
    ).hexdigest()
    generator = TrellisGenerator()
    generator.load_model()
    checkpoint_receipt = generator.load_shape_checkpoint(str(ema_checkpoint))
    params = sampler_params_for_steps(int(get_quality_preset("standard")["steps"]))

    def decode_once() -> tuple[trimesh.Trimesh, dict]:
        seed = int(case["generationSeed"])
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        image_bytes = (root / case["inputImage"]).read_bytes()
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        processed = generator.pipeline.preprocess_image(image)
        cond_512 = generator.pipeline.get_cond([processed], 512)
        cond_1024 = generator.pipeline.get_cond([processed], 1024)
        coords = coords_cpu.to(torch.device("cuda", torch.cuda.current_device()))
        with torch.inference_mode():
            slat, resolution = generator.pipeline.sample_shape_slat_cascade(
                cond_512, cond_1024,
                generator.pipeline.models["shape_slat_flow_model_512"],
                generator.pipeline.models["shape_slat_flow_model_1024"],
                512, 1024, coords, params["shape"],
            )
            meshes, _ = generator.pipeline.decode_shape_slat(slat, resolution)
        torch.cuda.synchronize()
        if len(meshes) != 1:
            raise RuntimeError("E10 G1 decode did not return exactly one mesh")
        raw = meshes[0]
        boundary = {
            "sparseCoordsSha256": hashlib.sha256(
                coords.detach().cpu().contiguous().numpy().tobytes()
            ).hexdigest(),
            "shapeLatentCoordsSha256": hashlib.sha256(
                slat.coords.detach().cpu().contiguous().numpy().tobytes()
            ).hexdigest(),
            "shapeLatentFeaturesSha256": hashlib.sha256(
                slat.feats.detach().cpu().contiguous().numpy().tobytes()
            ).hexdigest(),
            "rawVerticesSha256": hashlib.sha256(
                raw.vertices.detach().cpu().contiguous().numpy().tobytes()
            ).hexdigest(),
            "rawFacesSha256": hashlib.sha256(
                raw.faces.detach().cpu().contiguous().numpy().tobytes()
            ).hexdigest(),
        }
        mesh = trimesh.Trimesh(
            vertices=raw.vertices.detach().cpu().numpy(),
            faces=raw.faces.detach().cpu().numpy(), process=False,
        )
        if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
            raise RuntimeError("E10 G1 decoded an empty mesh")
        del meshes, raw, slat, coords, cond_512, cond_1024
        torch.cuda.empty_cache()
        return mesh, boundary

    mesh, first_boundary = decode_once()
    _, repeated_boundary = decode_once()
    exact_repeat = first_boundary == repeated_boundary
    if first_boundary["sparseCoordsSha256"] != expected_coords_hash or not exact_repeat:
        raise RuntimeError("E10 G1 frozen-condition raw decode was not exact")
    mesh_path = run_root / "g1-heldout-raw.ply"
    mesh_path.write_bytes(mesh.export(file_type="ply", encoding="binary"))
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": f"{objective.upper()}-G1-one-tooth-one-step-integration",
        "objective": objective,
        "datasetName": dataset_name,
        "runName": run_name,
        "steps": 1,
        "experimentSeed": experiment_seed,
        "trainingTooth": view_receipt,
        "losses": loss_values,
        "preUpdateObjectiveReceipt": pre_update,
        "postUpdateProbeReceipt": loss,
        "observedTeacherContributionRatio": observed_teacher_ratio,
        "teacherFrozen": True,
        "teacherBandMseBounds": teacher_band_bounds,
        "checkpointReloaded": True,
        "candidateCheckpoint": checkpoint_receipt,
        "heldoutCaseId": case["id"],
        "frozenSparseCoordsSha256": expected_coords_hash,
        "rawDecodeBoundary": first_boundary,
        "rawDecodeExactRepeat": exact_repeat,
        "rawMeshArtifact": str(mesh_path),
        "rawMeshArtifactSha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
        "g2Authorized": True,
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=e12_training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def run_e12_g1_one_tooth_decoder_integration(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e12-g1-one-tooth-v7",
    experiment_seed: int = 20260920,
) -> dict:
    """One decoder update, strict reload, and repeated heldout-latent decode."""
    import os
    import shutil
    import subprocess
    import sys

    import numpy as np
    import torch
    import trimesh
    from huggingface_hub import hf_hub_download

    if (
        dataset_name != "toothfairy-stage1-v1"
        or run_name != "stage1-e12-g1-one-tooth-v7"
        or experiment_seed != 20260920
    ):
        raise ValueError("E12 G1 is sealed to Stage-1, one step, and seed 20260920")
    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    preprocess_path = root / "stage1_preprocess_receipt.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    preprocess = json.loads(preprocess_path.read_text(encoding="utf-8"))
    if (
        manifest.get("assetCount") != 164
        or manifest.get("splits") != {"train": 128, "validation": 12, "test": 24}
        or preprocess.get("valid") is not True
        or preprocess.get("manifestSha256") != hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    ):
        raise ValueError("E12 G1 requires sealed Stage-1 geometry preprocessing")

    view = root / "e12_g1_one_tooth_v6"
    receipt_path = view / "receipt.json"
    if not receipt_path.is_file():
        if view.exists():
            raise FileExistsError("Partial E12 G1 view exists")
        with (root / "metadata.csv").open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            fieldnames = reader.fieldnames
            rows = [row for row in reader if row.get("split") == "train"]
        if not fieldnames or len(rows) != 128:
            raise ValueError("E12 G1 requires the sealed 128-row training metadata")
        selected = sorted(rows, key=lambda row: row["sha256"])[0]
        digest = selected["sha256"]
        sources = {
            "mesh_dump": root / "mesh_dumps" / f"{digest}.pickle",
            "dual_grid_512": root / "dual_grid_512" / f"{digest}.vxz",
        }
        for path in sources.values():
            if not path.is_file() or path.stat().st_size == 0:
                raise FileNotFoundError(path)
        import pickle
        import o_voxel
        coords, _ = o_voxel.io.read_vxz(str(sources["dual_grid_512"]), num_threads=4)
        with sources["mesh_dump"].open("rb") as stream:
            mesh_dump = pickle.load(stream)
        selected["dual_grid_converted"] = "True"
        selected["dual_grid_size"] = str(int(coords.shape[0]))
        selected["num_faces"] = str(sum(len(obj["faces"]) for obj in mesh_dump["objects"]))
        for required_field in ("dual_grid_converted", "dual_grid_size", "num_faces"):
            if required_field not in fieldnames:
                fieldnames.append(required_field)
        for name in ("base", "mesh_dump", "dual_grid_512"):
            (view / name).mkdir(parents=True, exist_ok=False)
            with (view / name / "metadata.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(selected)
        shutil.copy2(sources["mesh_dump"], view / "mesh_dump" / sources["mesh_dump"].name)
        shutil.copy2(sources["dual_grid_512"], view / "dual_grid_512" / sources["dual_grid_512"].name)
        view_receipt = {
            "schemaVersion": 1, "valid": True, "assetCount": 1,
            "sha256": digest, "selection": "lexicographically-first-training-sha256",
            "meshDumpSha256": hashlib.sha256(sources["mesh_dump"].read_bytes()).hexdigest(),
            "dualGridSha256": hashlib.sha256(sources["dual_grid_512"].read_bytes()).hexdigest(),
        }
        receipt_path.write_text(json.dumps(view_receipt, indent=2) + "\n", encoding="utf-8")
        dataset_volume.commit()
    else:
        view_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not view_receipt.get("valid") or view_receipt.get("assetCount") != 1:
            raise ValueError("Existing E12 G1 view is invalid")

    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "g1-evidence.json"
    if evidence_path.is_file():
        return {**json.loads(evidence_path.read_text(encoding="utf-8")), "resumed": True}
    if run_root.exists():
        raise FileExistsError("Partial E12 G1 run exists; diagnose before retry")
    run_root.mkdir(parents=True, exist_ok=False)

    base_paths = {}
    for role, name in {
        "encoder": "ckpts/shape_enc_next_dc_f16c32_fp16",
        "decoder": "ckpts/shape_dec_next_dc_f16c32_fp16",
    }.items():
        source = hf_hub_download(
            BASE_MODEL_NAME, f"{name}.safetensors", revision=BASE_MODEL_REVISION
        )
        base_paths[role] = materialize_trainer_checkpoint(
            source, run_root / f"base-{role}.pt"
        )
    official = Path(TRELLIS2_PATH) / "configs/scvae/shape_vae_next_dc_f16c32_fp16_ft_512.json"
    config = build_e12_shape_vae_config(
        json.loads(official.read_text(encoding="utf-8")),
        base_paths["encoder"], base_paths["decoder"],
    )
    config["experimentSeed"] = experiment_seed
    (run_root / "dentalsculptor_e12_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    command = e12_one_tooth_training_command(dataset_name, run_name)
    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    shape_path = Path(TRELLIS2_PATH) / "trellis2/trainers/vae/shape_vae.py"
    entry_path = Path(TRELLIS2_PATH) / "train.py"
    basic_original = basic_path.read_text(encoding="utf-8")
    shape_original = shape_path.read_text(encoding="utf-8")
    entry_original = entry_path.read_text(encoding="utf-8")

    def install_sources() -> None:
        scaled_basic = e12_initial_log_scale_source(
            smoke_trainer_source_without_snapshots(basic_original), log_scale=12
        )
        basic_path.write_text(
            e12_basic_trainer_gradient_gate_source(scaled_basic),
            encoding="utf-8",
        )
        shape_path.write_text(e12_decoder_only_shape_vae_source(shape_original), encoding="utf-8")
        entry_path.write_text(
            training_entry_source_with_experiment_seed(entry_original, experiment_seed),
            encoding="utf-8",
        )

    def restore_sources() -> None:
        basic_path.write_text(basic_original, encoding="utf-8")
        shape_path.write_text(shape_original, encoding="utf-8")
        entry_path.write_text(entry_original, encoding="utf-8")

    objective_receipt = run_root / "objective-receipt.jsonl"
    gradient_receipt = run_root / "gradient-receipt.json"
    install_sources()
    try:
        env = os.environ.copy()
        env["DENTALSCULPTOR_E12_OBJECTIVE_RECEIPT"] = str(objective_receipt)
        env["DENTALSCULPTOR_E12_GRADIENT_RECEIPT"] = str(gradient_receipt)
        process = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
        )
    finally:
        restore_sources()
    (run_root / "training.log").write_text(process.stdout, encoding="utf-8")
    print(process.stdout, flush=True)
    if process.returncode:
        checkpoint_volume.commit()
        raise RuntimeError(f"E12 G1 trainer exited with code {process.returncode}")
    receipts = [json.loads(line) for line in objective_receipt.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(receipts) != 1:
        raise RuntimeError(f"E12 G1 expected one objective receipt, found {len(receipts)}")
    loss = receipts[0]
    gradients = json.loads(gradient_receipt.read_text(encoding="utf-8"))
    if (
        loss.get("objective") != "decoder-only-native-geometry-v1"
        or loss.get("encoderFrozen") is not True
        or loss.get("decoderTrainableParameters") != loss.get("optimizerParameterCount")
        or loss.get("latentLeafGradEnabled") is not True
        or int(loss.get("removedInferenceNeighborCaches", 0)) < 1
        or gradients.get("valid") is not True
        or gradients.get("missingGradientCount") != 0
        or gradients.get("nonfiniteGradientCount") != 0
        or gradients.get("allZeroGradientCount") != 0
        or gradients.get("logScale") != 12.0
        or gradients.get("lossScale") != 4096.0
        or not math.isfinite(float(loss.get("loss", float("nan"))))
        or any(not math.isfinite(float(v)) for v in loss.get("nativeGeometryTerms", {}).values())
    ):
        raise RuntimeError(f"E12 G1 objective contract failed: {loss}")

    ckpts = run_root / "ckpts"
    encoder_ckpt = ckpts / "encoder_step0000001.pt"
    decoder_ckpt = ckpts / "decoder_step0000001.pt"
    decoder_ema = ckpts / "decoder_ema0.9999_step0000001.pt"
    misc_ckpt = ckpts / "misc_step0000001.pt"
    required = (encoder_ckpt, decoder_ckpt, decoder_ema, misc_ckpt)
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        raise RuntimeError("E12 G1 checkpoint contract failed")

    def state_hash(path: Path) -> str:
        state = torch.load(path, map_location="cpu", weights_only=True)
        digest = hashlib.sha256()
        for key in sorted(state):
            digest.update(key.encode("utf-8"))
            digest.update(state[key].detach().contiguous().numpy().tobytes())
        return digest.hexdigest()

    encoder_unchanged = state_hash(Path(base_paths["encoder"])) == state_hash(encoder_ckpt)
    if not encoder_unchanged:
        raise RuntimeError("E12 G1 changed the frozen encoder")
    reload_command = [*command, "--load_dir", str(run_root), "--ckpt", "1", "--tryrun"]
    install_sources()
    try:
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    finally:
        restore_sources()
    (run_root / "reload.log").write_text(reload_result.stdout, encoding="utf-8")
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout:
        raise RuntimeError("E12 G1 checkpoint failed strict reload")

    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from trellis2.modules.sparse import SparseTensor
    validation_assets = sorted(
        (asset for asset in manifest["assets"] if asset.get("split") == "validation"),
        key=lambda asset: asset["canonicalSha256"],
    )
    case = validation_assets[0]
    latent_path = root / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512" / f"{case['canonicalSha256']}.npz"
    packed = np.load(latent_path)
    latent_feats = torch.from_numpy(packed["feats"]).cuda()
    latent_coords = torch.from_numpy(packed["coords"].astype(np.int32)).cuda()
    latent_coords = torch.cat([torch.zeros_like(latent_coords[:, :1]), latent_coords], dim=1)
    generator = TrellisGenerator()
    generator.load_model()
    decoder = generator.pipeline.models["shape_slat_decoder"]
    decoder.load_state_dict(torch.load(decoder_ema, map_location=decoder.device, weights_only=True), strict=True)
    decoder.set_resolution(512)
    decoder.eval()

    def decode_once() -> tuple[trimesh.Trimesh, dict]:
        latent = SparseTensor(feats=latent_feats, coords=latent_coords)
        with torch.inference_mode():
            meshes, _ = generator.pipeline.decode_shape_slat(latent, 512)
        raw = meshes[0]
        boundary = {
            "vertices": hashlib.sha256(raw.vertices.detach().cpu().contiguous().numpy().tobytes()).hexdigest(),
            "faces": hashlib.sha256(raw.faces.detach().cpu().contiguous().numpy().tobytes()).hexdigest(),
        }
        mesh = trimesh.Trimesh(
            vertices=raw.vertices.detach().cpu().numpy(),
            faces=raw.faces.detach().cpu().numpy(), process=False,
        )
        if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
            raise RuntimeError("E12 G1 decoded an empty mesh")
        return mesh, boundary

    mesh, boundary = decode_once()
    _, repeated = decode_once()
    exact_repeat = boundary == repeated
    if not exact_repeat:
        raise RuntimeError("E12 G1 heldout latent decode was not exact")
    mesh_path = run_root / "g1-heldout-raw.ply"
    mesh_path.write_bytes(mesh.export(file_type="ply", encoding="binary"))
    evidence = {
        "schemaVersion": 1, "valid": True,
        "stage": "E12-G1-one-tooth-decoder-integration",
        "runName": run_name, "optimizerSteps": 1, "initialLogScale": 12.0,
        "objectiveReceipt": loss, "gradientReceipt": gradients, "encoderFrozen": True,
        "encoderStateUnchanged": encoder_unchanged,
        "checkpointReloaded": True,
        "candidateDecoderSha256": hashlib.sha256(decoder_ema.read_bytes()).hexdigest(),
        "heldoutAsset": case["id"], "heldoutLatentSha256": hashlib.sha256(latent_path.read_bytes()).hexdigest(),
        "rawDecodeBoundary": boundary, "rawDecodeExactRepeat": exact_repeat,
        "rawMeshArtifact": str(mesh_path),
        "rawMeshArtifactSha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
        "g2Authorized": True, "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=e12_training_image,
    volumes={"/checkpoints": checkpoint_volume},
    memory=32768,
    timeout=30 * 60,
)
def diagnose_e12_v7_encoder_identity(
    run_name: str = "stage1-e12-g1-one-tooth-v7",
) -> dict:
    """Zero-step classification of the v7 frozen-encoder checkpoint mismatch."""
    import torch

    if run_name != "stage1-e12-g1-one-tooth-v7":
        raise ValueError("E12 encoder identity diagnostic is sealed to G1 v7")
    run_root = Path(f"/checkpoints/{run_name}")
    output_path = run_root / "encoder-identity-diagnostic.json"
    if output_path.is_file():
        return {**json.loads(output_path.read_text(encoding="utf-8")), "resumed": True}
    base_path = run_root / "base-encoder.pt"
    saved_path = run_root / "ckpts/encoder_step0000001.pt"
    gradient_path = run_root / "gradient-receipt.json"
    objective_path = run_root / "objective-receipt.jsonl"
    required = (base_path, saved_path, gradient_path, objective_path)
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        raise FileNotFoundError("E12 v7 diagnostic requires complete base, saved, and receipt artifacts")
    gradients = json.loads(gradient_path.read_text(encoding="utf-8"))
    objectives = [
        json.loads(line) for line in objective_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(objectives) != 1:
        raise ValueError("E12 v7 must contain exactly one objective receipt")
    contract_valid = (
        gradients.get("valid") is True
        and gradients.get("parameterTensorCount") == 292
        and gradients.get("missingGradientCount") == 0
        and gradients.get("nonfiniteGradientCount") == 0
        and gradients.get("allZeroGradientCount") == 0
        and gradients.get("logScale") == 12.0
        and gradients.get("lossScale") == 4096.0
        and objectives[0].get("encoderFrozen") is True
        and objectives[0].get("decoderTrainableParameters")
        == objectives[0].get("optimizerParameterCount")
    )
    comparison = compare_e12_encoder_states(
        torch.load(base_path, map_location="cpu", weights_only=True),
        torch.load(saved_path, map_location="cpu", weights_only=True),
    )
    qualification_authorized = contract_valid and comparison["canonicalRuntimeEquivalent"]
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E12-G1-v7-encoder-identity-diagnostic",
        "runName": run_name,
        "optimizerStepsExecutedByDiagnostic": 0,
        "trainingContractValid": contract_valid,
        "comparison": comparison,
        "existingCheckpointQualificationAuthorized": qualification_authorized,
        "g2Authorized": False,
        "productionMutationPermitted": False,
        "clinicalClaimPermitted": False,
    }
    output_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=e12_training_image,
    volumes={"/checkpoints": checkpoint_volume},
    memory=32768,
    timeout=30 * 60,
)
def diagnose_e12_v7_decoder_update_localization(
    run_name: str = "stage1-e12-g1-one-tooth-v7",
) -> dict:
    """Zero-step localization of the rejected v7 decoder parameter delta."""
    import torch

    if run_name != "stage1-e12-g1-one-tooth-v7":
        raise ValueError("E12 decoder localization is sealed to rejected G1 v7")
    run_root = Path(f"/checkpoints/{run_name}")
    output_path = run_root / "decoder-update-localization-v1.json"
    if output_path.is_file():
        return {**json.loads(output_path.read_text(encoding="utf-8")), "resumed": True}
    g2 = json.loads((run_root / "g2-evidence-v2.json").read_text(encoding="utf-8"))
    if g2.get("e13Authorized") is not False or g2.get("summary", {}).get("passed") is not False:
        raise ValueError("E12 decoder localization requires the sealed rejected G2 candidate")
    base_path = run_root / "base-decoder.pt"
    candidate_path = run_root / "ckpts/decoder_ema0.9999_step0000001.pt"
    if any(not path.is_file() or path.stat().st_size == 0 for path in (base_path, candidate_path)):
        raise FileNotFoundError("E12 decoder localization checkpoint is missing")
    summary = summarize_e12_decoder_update_groups(
        torch.load(base_path, map_location="cpu", weights_only=True),
        torch.load(candidate_path, map_location="cpu", weights_only=True),
    )
    evidence = {
        "schemaVersion": 1, "valid": True,
        "stage": "E12-v7-decoder-update-localization-v1",
        "runName": run_name, "optimizerSteps": 0,
        "baseDecoderSha256": hashlib.sha256(base_path.read_bytes()).hexdigest(),
        "candidateDecoderSha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        "summary": summary,
        "lateDeltaHybridAuthorized": summary["lateDeltaHybridAuthorized"],
        "e13TrainingAuthorized": False,
        "productionMutationPermitted": False,
        "clinicalClaimPermitted": False,
    }
    output_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=e12_training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=60 * 60,
)
def qualify_e12_v7_existing_checkpoint(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e12-g1-one-tooth-v7",
    experiment_seed: int = 20260920,
) -> dict:
    """Strictly reload and deterministically decode the existing v7 checkpoint."""
    import os
    import subprocess
    import sys

    import numpy as np
    import torch
    import trimesh

    if (
        dataset_name != "toothfairy-stage1-v1"
        or run_name != "stage1-e12-g1-one-tooth-v7"
        or experiment_seed != 20260920
    ):
        raise ValueError("E12 v7 qualification is sealed")
    root = Path(f"/datasets/{dataset_name}")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "g1-evidence.json"
    if evidence_path.is_file():
        return {**json.loads(evidence_path.read_text(encoding="utf-8")), "resumed": True}
    identity_path = run_root / "encoder-identity-diagnostic.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    if (
        identity.get("existingCheckpointQualificationAuthorized") is not True
        or identity.get("comparison", {}).get("canonicalRuntimeEquivalent") is not True
        or identity.get("comparison", {}).get("canonicalChangedTensorCount") != 0
    ):
        raise RuntimeError("E12 v7 encoder identity does not authorize qualification")
    manifest_path = root / "anatomy_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("assetCount") != 164 or manifest.get("splits") != {
        "train": 128, "validation": 12, "test": 24,
    }:
        raise ValueError("E12 v7 qualification requires the sealed Stage-1 manifest")
    ckpts = run_root / "ckpts"
    encoder_ckpt = ckpts / "encoder_step0000001.pt"
    decoder_ckpt = ckpts / "decoder_step0000001.pt"
    decoder_ema = ckpts / "decoder_ema0.9999_step0000001.pt"
    misc_ckpt = ckpts / "misc_step0000001.pt"
    required = (encoder_ckpt, decoder_ckpt, decoder_ema, misc_ckpt)
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        raise RuntimeError("E12 v7 checkpoint set is incomplete")

    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    shape_path = Path(TRELLIS2_PATH) / "trellis2/trainers/vae/shape_vae.py"
    entry_path = Path(TRELLIS2_PATH) / "train.py"
    basic_original = basic_path.read_text(encoding="utf-8")
    shape_original = shape_path.read_text(encoding="utf-8")
    entry_original = entry_path.read_text(encoding="utf-8")
    scaled_basic = e12_initial_log_scale_source(
        smoke_trainer_source_without_snapshots(basic_original), log_scale=12
    )
    try:
        basic_path.write_text(
            e12_basic_trainer_gradient_gate_source(scaled_basic), encoding="utf-8"
        )
        shape_path.write_text(
            e12_decoder_only_shape_vae_source(shape_original), encoding="utf-8"
        )
        entry_path.write_text(
            training_entry_source_with_experiment_seed(entry_original, experiment_seed),
            encoding="utf-8",
        )
        reload_command = [
            *e12_one_tooth_training_command(dataset_name, run_name),
            "--load_dir", str(run_root), "--ckpt", "1", "--tryrun",
        ]
        reload_result = subprocess.run(
            reload_command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=os.environ.copy(),
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
        shape_path.write_text(shape_original, encoding="utf-8")
        entry_path.write_text(entry_original, encoding="utf-8")
    (run_root / "qualification-reload.log").write_text(
        reload_result.stdout, encoding="utf-8"
    )
    if reload_result.returncode or "Loading checkpoint" not in reload_result.stdout:
        checkpoint_volume.commit()
        raise RuntimeError("E12 v7 checkpoint failed strict trainer reload")

    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from trellis2.modules.sparse import SparseTensor

    validation_assets = sorted(
        (asset for asset in manifest["assets"] if asset.get("split") == "validation"),
        key=lambda asset: asset["canonicalSha256"],
    )
    case = validation_assets[0]
    latent_path = (
        root / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512"
        / f"{case['canonicalSha256']}.npz"
    )
    packed = np.load(latent_path)
    latent_feats = torch.from_numpy(packed["feats"]).cuda()
    latent_coords = torch.from_numpy(packed["coords"].astype(np.int32)).cuda()
    latent_coords = torch.cat(
        [torch.zeros_like(latent_coords[:, :1]), latent_coords], dim=1
    )
    generator = TrellisGenerator()
    generator.load_model()
    decoder = generator.pipeline.models["shape_slat_decoder"]
    decoder.load_state_dict(
        torch.load(decoder_ema, map_location=decoder.device, weights_only=True),
        strict=True,
    )
    decoder.set_resolution(512)
    decoder.eval()

    def decode_once() -> tuple[trimesh.Trimesh, dict]:
        latent = SparseTensor(feats=latent_feats, coords=latent_coords)
        with torch.inference_mode():
            meshes, _ = generator.pipeline.decode_shape_slat(latent, 512)
        raw = meshes[0]
        boundary = {
            "vertices": hashlib.sha256(
                raw.vertices.detach().cpu().contiguous().numpy().tobytes()
            ).hexdigest(),
            "faces": hashlib.sha256(
                raw.faces.detach().cpu().contiguous().numpy().tobytes()
            ).hexdigest(),
        }
        mesh = trimesh.Trimesh(
            vertices=raw.vertices.detach().cpu().numpy(),
            faces=raw.faces.detach().cpu().numpy(), process=False,
        )
        if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
            raise RuntimeError("E12 v7 qualification decoded an empty raw mesh")
        return mesh, boundary

    mesh, first_boundary = decode_once()
    _, repeated_boundary = decode_once()
    exact_repeat = first_boundary == repeated_boundary
    if not exact_repeat:
        raise RuntimeError("E12 v7 heldout raw decode was not exact")
    mesh_path = run_root / "g1-heldout-raw.ply"
    mesh_path.write_bytes(mesh.export(file_type="ply", encoding="binary"))
    evidence = {
        "schemaVersion": 1, "valid": True,
        "stage": "E12-G1-v7-existing-checkpoint-qualification",
        "runName": run_name,
        "trainingOptimizerSteps": 1,
        "qualificationOptimizerSteps": 0,
        "initialLogScale": 12.0,
        "encoderFrozen": True,
        "encoderIdentity": identity["comparison"],
        "checkpointReloaded": True,
        "candidateDecoderSha256": hashlib.sha256(decoder_ema.read_bytes()).hexdigest(),
        "heldoutAsset": case["id"],
        "heldoutLatentSha256": hashlib.sha256(latent_path.read_bytes()).hexdigest(),
        "rawDecodeBoundary": first_boundary,
        "rawDecodeExactRepeat": exact_repeat,
        "rawMeshArtifact": str(mesh_path),
        "rawMeshArtifactSha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
        "rawMeshVertexCount": int(len(mesh.vertices)),
        "rawMeshFaceCount": int(len(mesh.faces)),
        "g2Authorized": True,
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=e12_training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def run_e12_g2_four_family_decoder_screen(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e12-g1-one-tooth-v7",
    samples: int = 5000,
) -> dict:
    """Compare base and v7 decoders on identical held-out whole-tooth latents."""
    import sys

    import numpy as np
    import torch
    import trimesh

    if (
        dataset_name != "toothfairy-stage1-v1"
        or run_name != "stage1-e12-g1-one-tooth-v7"
        or samples != 5000
    ):
        raise ValueError("E12 G2 decoder screen is sealed")
    root = Path(f"/datasets/{dataset_name}")
    run_root = Path(f"/checkpoints/{run_name}")
    g1_path = run_root / "g1-evidence.json"
    g1 = json.loads(g1_path.read_text(encoding="utf-8"))
    if (
        g1.get("g2Authorized") is not True
        or g1.get("rawDecodeExactRepeat") is not True
        or g1.get("checkpointReloaded") is not True
    ):
        raise ValueError("E12 G2 requires sealed passing G1 evidence")
    evidence_path = run_root / "g2-evidence-v2.json"
    if evidence_path.is_file():
        return {**json.loads(evidence_path.read_text(encoding="utf-8")), "resumed": True}
    manifest = json.loads((root / "anatomy_manifest.json").read_text(encoding="utf-8"))
    validation = json.loads(
        (root / "stage1_validation_inputs_v1.json").read_text(encoding="utf-8")
    )
    if (
        manifest.get("assetCount") != 164
        or validation.get("valid") is not True
        or validation.get("trainingPatientOverlapCount") != 0
    ):
        raise ValueError("E12 G2 requires sealed patient-disjoint validation inputs")
    families = ("incisor", "canine", "premolar", "molar")
    cases = resolve_e12_g2_validation_cases(validation, manifest, families)
    candidate_checkpoint = run_root / "ckpts/decoder_ema0.9999_step0000001.pt"
    if not candidate_checkpoint.is_file() or candidate_checkpoint.stat().st_size == 0:
        raise FileNotFoundError(candidate_checkpoint)

    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh
    from trellis2.modules.sparse import SparseTensor

    generator = TrellisGenerator()
    generator.load_model()
    decoder = generator.pipeline.models["shape_slat_decoder"]
    decoder.set_resolution(512)
    decoder.eval()

    def tensor_hash(tensor: torch.Tensor) -> str:
        return hashlib.sha256(
            tensor.detach().cpu().contiguous().numpy().tobytes()
        ).hexdigest()

    def load_latent(case: dict) -> tuple[torch.Tensor, torch.Tensor, str]:
        latent_path = (
            root / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512"
            / f"{case['canonicalSha256']}.npz"
        )
        packed = np.load(latent_path)
        feats = torch.from_numpy(packed["feats"]).cuda()
        coords = torch.from_numpy(packed["coords"].astype(np.int32)).cuda()
        coords = torch.cat([torch.zeros_like(coords[:, :1]), coords], dim=1)
        digest = hashlib.sha256(latent_path.read_bytes()).hexdigest()
        return feats, coords, digest

    def decode_once(feats: torch.Tensor, coords: torch.Tensor) -> tuple[trimesh.Trimesh, dict]:
        latent = SparseTensor(feats=feats, coords=coords)
        with torch.inference_mode():
            meshes, _ = generator.pipeline.decode_shape_slat(latent, 512)
        raw = meshes[0]
        boundary = {
            "inputLatentSha256": hashlib.sha256(
                feats.detach().cpu().contiguous().numpy().tobytes()
                + coords.detach().cpu().contiguous().numpy().tobytes()
            ).hexdigest(),
            "rawVerticesSha256": tensor_hash(raw.vertices),
            "rawFacesSha256": tensor_hash(raw.faces),
        }
        mesh = trimesh.Trimesh(
            vertices=raw.vertices.detach().cpu().numpy(),
            faces=raw.faces.detach().cpu().numpy(), process=False,
        )
        if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
            raise RuntimeError("E12 G2 decoded an empty mesh")
        del meshes, raw, latent
        torch.cuda.empty_cache()
        return mesh, boundary

    output_root = run_root / "g2-decoder-screen-v2"
    output_root.mkdir(exist_ok=False)

    def evaluate_role(role: str) -> list[dict]:
        role_root = output_root / role
        role_root.mkdir()
        receipts = []
        for case in cases:
            feats, coords, latent_file_hash = load_latent(case)
            input_hash = hashlib.sha256(
                feats.detach().cpu().contiguous().numpy().tobytes()
                + coords.detach().cpu().contiguous().numpy().tobytes()
            ).hexdigest()
            mesh, boundary = decode_once(feats, coords)
            _, repeated = decode_once(feats, coords)
            if boundary != repeated:
                raise RuntimeError(f"E12 G2 repeatability failed for {role}:{case['id']}")
            mesh_path = role_root / f"{case['id']}.ply"
            mesh_path.write_bytes(mesh.export(file_type="ply", encoding="binary"))
            reference = load_mesh(root / case["referenceMesh"])
            receipt = {
                "schemaVersion": 1,
                "id": case["id"], "toothFamily": case["toothFamily"],
                "groupId": case["groupId"], "modelRole": role,
                "frozenLatentSha256": input_hash,
                "latentArtifactSha256": latent_file_hash,
                "boundary": boundary,
                "repeatability": {"rawShapeExact": True},
                "metrics": compare_meshes(
                    reference, mesh, samples=samples, seed=int(case["generationSeed"])
                ),
                "topology": analyze_mesh_with_weld_control(mesh),
                "meshArtifact": str(mesh_path),
                "meshArtifactSha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
                "vertexCount": int(len(mesh.vertices)), "faceCount": int(len(mesh.faces)),
            }
            (role_root / f"{case['id']}.json").write_text(
                json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
            )
            receipts.append(receipt)
            checkpoint_volume.commit()
            del feats, coords, mesh, reference
            torch.cuda.empty_cache()
        return receipts

    baseline = evaluate_role("unchanged-base-decoder")
    decoder.load_state_dict(
        torch.load(candidate_checkpoint, map_location=decoder.device, weights_only=True),
        strict=True,
    )
    decoder.eval()
    candidate = evaluate_role("e12-v7-candidate-decoder")
    summary = summarize_e12_g2_decoder_screen(baseline, candidate)
    evidence = {
        "schemaVersion": 1, "valid": True,
        "stage": "E12-G2-four-family-decoder-screen-v2",
        "runName": run_name, "optimizerSteps": 0,
        "candidateDecoderSha256": hashlib.sha256(candidate_checkpoint.read_bytes()).hexdigest(),
        "caseSelection": "lexicographically-first-patient-disjoint-validation-case-per-family",
        "samplesPerMetric": samples,
        "baseline": baseline, "candidate": candidate, "summary": summary,
        "e13Authorized": summary["e13Authorized"],
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100-80GB",
    cpu=8,
    memory=65536,
    timeout=3 * 60 * 60,
)
def evaluate_r0_stage_attribution(
    dataset_name: str = "toothfairy-stage1-v1",
    resolution: int = 512,
    samples: int = 5000,
) -> dict:
    """Measure representation/decoder error against product-path reconstruction error.

    This is a zero-training diagnostic. The oracle branch decodes each sealed
    reference-mesh latent through the unchanged base decoder. The product branch
    is the already-sealed unchanged-base image-conditioned Stage-1 validation.
    """
    import sys
    from collections import Counter

    import numpy as np
    import torch
    import trimesh

    if dataset_name != "toothfairy-stage1-v1" or resolution != 512 or samples != 5000:
        raise ValueError("R0 stage attribution is sealed to Stage-1 at 512/5000")
    root = Path(f"/datasets/{dataset_name}")
    manifest_path = root / "anatomy_manifest.json"
    validation_path = root / "stage1_validation_inputs_v1.json"
    product_report_path = root / "stage1_seed_a_raw_validation_v2.json"
    evidence_path = root / "stage_attribution_r0_v1.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True and existing.get("caseCount") == 12:
            return {**existing, "resumed": True}
        raise ValueError("Existing R0 evidence is invalid; refusing to overwrite it")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    product_report = json.loads(product_report_path.read_text(encoding="utf-8"))
    if (
        manifest.get("assetCount") != 164
        or validation.get("valid") is not True
        or validation.get("trainingPatientOverlapCount") != 0
        or len(validation.get("cases", [])) != 12
        or product_report.get("complete") is not True
        or product_report.get("caseCount") != 12
    ):
        raise ValueError("R0 requires the sealed 12-case patient-disjoint Stage-1 inputs")

    assets_by_id: dict[str, list[dict]] = {}
    for asset in manifest.get("assets", []):
        assets_by_id.setdefault(asset.get("id"), []).append(asset)
    cases = []
    for case in sorted(validation["cases"], key=lambda row: row["id"]):
        assets = assets_by_id.get(case["id"], [])
        if len(assets) != 1:
            raise ValueError(f"R0 requires one manifest asset for {case['id']}")
        asset = assets[0]
        checks = {
            "split": asset.get("split") == "validation",
            "toothFamily": asset.get("toothFamily") == case.get("toothFamily"),
            "groupId": asset.get("groupId") == case.get("groupId"),
            "fdiNumber": int(asset.get("fdiNumber")) == int(case.get("fdiNumber")),
            "canonicalPath": asset.get("canonicalPath") == case.get("referenceMesh"),
            "canonicalSha256": asset.get("canonicalSha256") == case.get("referenceMeshSha256"),
        }
        if not all(checks.values()):
            failed = sorted(name for name, passed in checks.items() if not passed)
            raise ValueError(f"R0 manifest join drift for {case['id']}: {failed}")
        reference_path = root / case["referenceMesh"]
        if hashlib.sha256(reference_path.read_bytes()).hexdigest() != case["referenceMeshSha256"]:
            raise ValueError(f"R0 reference mesh hash drift for {case['id']}")
        cases.append({**case, "canonicalSha256": asset["canonicalSha256"]})
    family_counts = Counter(case["toothFamily"] for case in cases)
    if family_counts != Counter({family: 3 for family in ("incisor", "canine", "premolar", "molar")}):
        raise ValueError("R0 requires exactly three sealed cases per tooth family")

    product = product_report.get("baseline", [])
    product_by_id = {row.get("id"): row for row in product}
    if len(product_by_id) != 12 or set(product_by_id) != {case["id"] for case in cases}:
        raise ValueError("R0 product baseline IDs do not match the validation cohort")
    repeated_product = [
        row for row in product
        if (row.get("repeatability") or {}).get("rawShapeExact") is True
    ]
    if (
        len(repeated_product) != 4
        or Counter(row["toothFamily"] for row in repeated_product)
        != Counter({family: 1 for family in ("incisor", "canine", "premolar", "molar")})
    ):
        raise ValueError("R0 requires one exact repeated product decode per family")
    for case in cases:
        row = product_by_id[case["id"]]
        if (
            row.get("modelRole") != "unchanged-base"
            or row.get("referenceMeshSha256") != case["referenceMeshSha256"]
            or row.get("groupId") != case["groupId"]
            or row.get("toothFamily") != case["toothFamily"]
        ):
            raise ValueError(f"R0 sealed product receipt drift for {case['id']}")

    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh
    from trellis2.modules.sparse import SparseTensor

    generator = TrellisGenerator()
    generator.load_model()
    decoder = generator.pipeline.models["shape_slat_decoder"]
    decoder.set_resolution(resolution)
    decoder.eval()
    output_root = root / "stage_attribution_r0_v1"
    output_root.mkdir(parents=True, exist_ok=True)

    def tensor_hash(tensor: torch.Tensor) -> str:
        return hashlib.sha256(
            tensor.detach().cpu().contiguous().numpy().tobytes()
        ).hexdigest()

    def decode_once(feats: torch.Tensor, coords: torch.Tensor):
        latent = SparseTensor(feats=feats, coords=coords)
        with torch.inference_mode():
            decoded, _ = generator.pipeline.decode_shape_slat(latent, resolution)
        raw = decoded[0]
        boundary = {
            "inputLatentSha256": hashlib.sha256(
                feats.detach().cpu().contiguous().numpy().tobytes()
                + coords.detach().cpu().contiguous().numpy().tobytes()
            ).hexdigest(),
            "rawVerticesSha256": tensor_hash(raw.vertices),
            "rawFacesSha256": tensor_hash(raw.faces),
        }
        mesh = trimesh.Trimesh(
            vertices=raw.vertices.detach().cpu().numpy(),
            faces=raw.faces.detach().cpu().numpy(), process=False,
        )
        if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
            raise RuntimeError("R0 oracle decode returned an empty mesh")
        del decoded, raw, latent
        torch.cuda.empty_cache()
        return mesh, boundary

    oracle = []
    latent_root = root / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512"
    for case in cases:
        receipt_path = output_root / f"{case['id']}.json"
        mesh_path = output_root / f"{case['id']}.ply"
        if receipt_path.is_file() and mesh_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if (
                receipt.get("referenceMeshSha256") != case["referenceMeshSha256"]
                or receipt.get("repeatability", {}).get("rawShapeExact") is not True
                or receipt.get("meshArtifactSha256") != hashlib.sha256(mesh_path.read_bytes()).hexdigest()
            ):
                raise ValueError(f"R0 partial receipt is invalid for {case['id']}")
            oracle.append(receipt)
            continue
        latent_path = latent_root / f"{case['canonicalSha256']}.npz"
        if not latent_path.is_file():
            raise FileNotFoundError(latent_path)
        packed = np.load(latent_path)
        feats = torch.from_numpy(packed["feats"]).cuda()
        coords = torch.from_numpy(packed["coords"].astype(np.int32)).cuda()
        coords = torch.cat([torch.zeros_like(coords[:, :1]), coords], dim=1)
        mesh, boundary = decode_once(feats, coords)
        _, repeated = decode_once(feats, coords)
        if boundary != repeated:
            raise RuntimeError(f"R0 oracle raw decode repeatability failed for {case['id']}")
        mesh_path.write_bytes(mesh.export(file_type="ply", encoding="binary"))
        reference = load_mesh(root / case["referenceMesh"])
        receipt = {
            "schemaVersion": 1,
            "id": case["id"], "toothFamily": case["toothFamily"],
            "fdiNumber": case["fdiNumber"], "groupId": case["groupId"],
            "modelRole": "unchanged-base-reference-latent-oracle",
            "referenceMesh": case["referenceMesh"],
            "referenceMeshSha256": case["referenceMeshSha256"],
            "latentArtifactSha256": hashlib.sha256(latent_path.read_bytes()).hexdigest(),
            "boundary": boundary,
            "repeatability": {"rawShapeExact": True},
            "metrics": compare_meshes(
                reference, mesh, samples=samples, seed=int(case["generationSeed"])
            ),
            "topology": analyze_mesh_with_weld_control(mesh),
            "meshArtifact": str(mesh_path.relative_to(root)),
            "meshArtifactSha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
            "vertexCount": int(len(mesh.vertices)), "faceCount": int(len(mesh.faces)),
        }
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        oracle.append(receipt)
        dataset_volume.commit()
        del feats, coords, mesh, reference
        torch.cuda.empty_cache()

    summary = summarize_r0_stage_attribution(oracle, product)
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "R0-12-case-stage-attribution-v1",
        "datasetId": dataset_name,
        "caseCount": 12,
        "optimizerSteps": 0,
        "resolution": resolution,
        "samplesPerMetric": samples,
        "baseModel": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trellisCommit": TRELLIS_COMMIT,
        "sourceEvidence": {
            "manifestSha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "validationInputsSha256": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
            "productReportSha256": hashlib.sha256(product_report_path.read_bytes()).hexdigest(),
        },
        "measurementBoundary": "reference-latent-base-decode-versus-image-conditioned-base-raw-decode",
        "oracle": oracle,
        "product": product,
        "summary": summary,
        "trainingAuthorized": False,
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return evidence


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100-80GB",
    cpu=8,
    memory=65536,
    timeout=3 * 60 * 60,
)
def evaluate_r01_conditioning_decomposition(
    dataset_name: str = "toothfairy-stage1-v1",
    samples: int = 5000,
) -> dict:
    """Isolate sparse-support error from image-conditioned shape-feature error."""
    import io
    import os
    import random
    import sys
    from collections import Counter

    import numpy as np
    import torch
    import trimesh
    from PIL import Image

    if dataset_name != "toothfairy-stage1-v1" or samples != 5000:
        raise ValueError("R0.1 is sealed to the Stage-1 12-case cohort at 5000 samples")
    if MODEL_NAME != BASE_MODEL_NAME or MODEL_REVISION != BASE_MODEL_REVISION:
        raise RuntimeError("R0.1 must use the pinned unchanged base pipeline")
    root = Path(f"/datasets/{dataset_name}")
    r0_path = root / "stage_attribution_r0_v1.json"
    validation_path = root / "stage1_validation_inputs_v1.json"
    product_path = root / "stage1_seed_a_raw_validation_v2.json"
    evidence_path = root / "stage_attribution_r01_v1.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True and existing.get("caseCount") == 12:
            return {**existing, "resumed": True}
        raise ValueError("Existing R0.1 evidence is invalid; refusing to overwrite it")
    r0 = json.loads(r0_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    product_report = json.loads(product_path.read_text(encoding="utf-8"))
    if (
        r0.get("valid") is not True
        or r0.get("optimizerSteps") != 0
        or r0.get("summary", {}).get("dominantMeasuredBoundary")
        != "image-conditioned-generation"
        or validation.get("valid") is not True
        or len(validation.get("cases", [])) != 12
        or product_report.get("complete") is not True
    ):
        raise ValueError("R0.1 requires sealed passing R0 and Stage-1 inputs")
    cases = sorted(validation["cases"], key=lambda row: row["id"])
    if Counter(case["toothFamily"] for case in cases) != Counter({
        family: 3 for family in ("incisor", "canine", "premolar", "molar")
    }):
        raise ValueError("R0.1 requires three cases per tooth family")
    oracle = r0["oracle"]
    product = product_report["baseline"]
    expected_ids = {case["id"] for case in cases}
    if (
        {row["id"] for row in oracle} != expected_ids
        or {row["id"] for row in product} != expected_ids
    ):
        raise ValueError("R0.1 receipt IDs drifted from the sealed cohort")

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    generator = TrellisGenerator()
    generator.load_model()
    params = sampler_params_for_steps(int(get_quality_preset("standard")["steps"]))
    output_root = root / "stage_attribution_r01_v1"
    output_root.mkdir(parents=True, exist_ok=True)
    latent_root = root / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512"

    def tensor_hash(tensor: torch.Tensor) -> str:
        return hashlib.sha256(
            tensor.detach().cpu().contiguous().numpy().tobytes()
        ).hexdigest()

    def sample_with_reference_support(case: dict):
        seed = int(case["generationSeed"])
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        image_bytes = (root / case["inputImage"]).read_bytes()
        if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
            raise ValueError(f"R0.1 image hash drift for {case['id']}")
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        processed = generator.pipeline.preprocess_image(image)
        cond_512 = generator.pipeline.get_cond([processed], 512)
        cond_1024 = generator.pipeline.get_cond([processed], 1024)
        latent_path = latent_root / f"{case['referenceMeshSha256']}.npz"
        if not latent_path.is_file():
            raise FileNotFoundError(latent_path)
        packed = np.load(latent_path)
        coords = torch.from_numpy(packed["coords"].astype(np.int32)).cuda()
        coords = torch.cat([torch.zeros_like(coords[:, :1]), coords], dim=1)
        with torch.inference_mode():
            slat, resolution = generator.pipeline.sample_shape_slat_cascade(
                cond_512,
                cond_1024,
                generator.pipeline.models["shape_slat_flow_model_512"],
                generator.pipeline.models["shape_slat_flow_model_1024"],
                512,
                1024,
                coords,
                params["shape"],
            )
            meshes, _ = generator.pipeline.decode_shape_slat(slat, resolution)
        torch.cuda.synchronize()
        if len(meshes) != 1:
            raise RuntimeError(f"R0.1 expected one mesh for {case['id']}")
        raw = meshes[0]
        boundary = {
            "referenceSupportCoordsSha256": tensor_hash(coords),
            "shapeLatentCoordsSha256": tensor_hash(slat.coords),
            "shapeLatentFeaturesSha256": tensor_hash(slat.feats),
            "rawVerticesSha256": tensor_hash(raw.vertices),
            "rawFacesSha256": tensor_hash(raw.faces),
            "resolvedResolution": int(resolution),
        }
        mesh = trimesh.Trimesh(
            vertices=raw.vertices.detach().cpu().numpy(),
            faces=raw.faces.detach().cpu().numpy(), process=False,
        )
        if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
            raise RuntimeError(f"R0.1 decoded an empty mesh for {case['id']}")
        del meshes, raw, slat, coords, cond_512, cond_1024
        torch.cuda.empty_cache()
        return mesh, boundary, hashlib.sha256(latent_path.read_bytes()).hexdigest()

    receipts = []
    repeated_families: set[str] = set()
    for index, case in enumerate(cases, start=1):
        receipt_path = output_root / f"{case['id']}.json"
        mesh_path = output_root / f"{case['id']}.ply"
        expected_repeat = case["toothFamily"] not in repeated_families
        if receipt_path.is_file() and mesh_path.is_file():
            saved = json.loads(receipt_path.read_text(encoding="utf-8"))
            if (
                saved.get("referenceMeshSha256") == case["referenceMeshSha256"]
                and saved.get("meshArtifactSha256")
                == hashlib.sha256(mesh_path.read_bytes()).hexdigest()
                and (not expected_repeat or (saved.get("repeatability") or {}).get("rawShapeExact") is True)
            ):
                receipts.append(saved)
                if expected_repeat:
                    repeated_families.add(case["toothFamily"])
                print(f"R0.1 {index}/12 resumed: {case['id']}", flush=True)
                continue
            raise ValueError(f"R0.1 partial receipt invalid for {case['id']}")
        mesh, boundary, latent_hash = sample_with_reference_support(case)
        repeatability = None
        if expected_repeat:
            repeated_families.add(case["toothFamily"])
            _, repeated_boundary, _ = sample_with_reference_support(case)
            compared = (
                "referenceSupportCoordsSha256", "shapeLatentCoordsSha256",
                "shapeLatentFeaturesSha256", "rawVerticesSha256", "rawFacesSha256",
            )
            equality = {name: boundary[name] == repeated_boundary[name] for name in compared}
            if not all(equality.values()):
                raise RuntimeError(f"R0.1 repeatability failed for {case['id']}")
            repeatability = {"rawShapeExact": True, "boundaryEquality": equality}
        mesh_path.write_bytes(mesh.export(file_type="ply", encoding="binary"))
        reference = load_mesh(root / case["referenceMesh"])
        receipt = {
            "schemaVersion": 1,
            "id": case["id"], "toothFamily": case["toothFamily"],
            "fdiNumber": case["fdiNumber"], "groupId": case["groupId"],
            "modelRole": "unchanged-base-image-conditioned-reference-sparse-support",
            "referenceMesh": case["referenceMesh"],
            "referenceMeshSha256": case["referenceMeshSha256"],
            "inputImageSha256": case["inputImageSha256"],
            "generationSeed": int(case["generationSeed"]),
            "referenceLatentArtifactSha256": latent_hash,
            "boundary": boundary,
            "repeatability": repeatability,
            "metrics": compare_meshes(
                reference, mesh, samples=samples, seed=int(case["generationSeed"])
            ),
            "topology": analyze_mesh_with_weld_control(mesh),
            "meshArtifact": str(mesh_path.relative_to(root)),
            "meshArtifactSha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
            "vertexCount": int(len(mesh.vertices)), "faceCount": int(len(mesh.faces)),
        }
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        receipts.append(receipt)
        dataset_volume.commit()
        print(f"R0.1 {index}/12 complete: {case['id']}", flush=True)
        del mesh, reference
        torch.cuda.empty_cache()

    if Counter(row["toothFamily"] for row in receipts if (row.get("repeatability") or {}).get("rawShapeExact")) != Counter({
        family: 1 for family in ("incisor", "canine", "premolar", "molar")
    }):
        raise RuntimeError("R0.1 requires one exact repeated reference-support decode per family")
    summary = summarize_r01_conditioning_decomposition(oracle, product, receipts)
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "R0.1-image-conditioned-path-decomposition-v1",
        "datasetId": dataset_name,
        "caseCount": 12,
        "optimizerSteps": 0,
        "samplesPerMetric": samples,
        "baseModel": BASE_MODEL_NAME,
        "baseModelRevision": BASE_MODEL_REVISION,
        "trellisCommit": TRELLIS_COMMIT,
        "sourceEvidence": {
            "r0Sha256": hashlib.sha256(r0_path.read_bytes()).hexdigest(),
            "validationInputsSha256": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
            "productReportSha256": hashlib.sha256(product_path.read_bytes()).hexdigest(),
        },
        "measurementBoundary": "unchanged-image-conditioned-shape-flow-with-reference-versus-product-sparse-support",
        "oracle": oracle,
        "product": product,
        "referenceSupport": receipts,
        "summary": summary,
        "trainingAuthorized": False,
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return evidence


@app.function(
    image=trellis_gpu_image,
    volumes={"/datasets": dataset_volume},
    cpu=8,
    memory=32768,
    timeout=30 * 60,
)
def evaluate_r02_sparse_support_characterization(
    dataset_name: str = "toothfairy-stage1-v1",
    sparse_resolution: int = 32,
) -> dict:
    """Characterize the sealed predicted sparse support against reference support."""
    import numpy as np
    import torch
    from collections import Counter

    if dataset_name != "toothfairy-stage1-v1" or sparse_resolution != 32:
        raise ValueError("R0.2 is sealed to Stage-1 sparse resolution 32")
    root = Path(f"/datasets/{dataset_name}")
    r0_path = root / "stage_attribution_r0_v1.json"
    r01_path = root / "stage_attribution_r01_v1.json"
    product_path = root / "stage1_seed_a_raw_validation_v2.json"
    evidence_path = root / "stage_attribution_r02_v1.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True and existing.get("caseCount") == 12:
            return {**existing, "resumed": True}
        raise ValueError("Existing R0.2 evidence is invalid; refusing to overwrite it")
    r0 = json.loads(r0_path.read_text(encoding="utf-8"))
    r01 = json.loads(r01_path.read_text(encoding="utf-8"))
    product_report = json.loads(product_path.read_text(encoding="utf-8"))
    if (
        r0.get("valid") is not True
        or r01.get("valid") is not True
        or r01.get("optimizerSteps") != 0
        or r01.get("summary", {}).get("dominantMeasuredSubBoundary")
        != "image-to-sparse-structure"
        or product_report.get("complete") is not True
    ):
        raise ValueError("R0.2 requires sealed R0/R0.1 and product evidence")
    product_by_id = {row["id"]: row for row in product_report["baseline"]}
    support_by_id = {row["id"]: row for row in r01["referenceSupport"]}
    if set(product_by_id) != set(support_by_id) or len(product_by_id) != 12:
        raise ValueError("R0.2 requires twelve identical product/reference-support IDs")
    if Counter(row["toothFamily"] for row in product_by_id.values()) != Counter({
        family: 3 for family in ("incisor", "canine", "premolar", "molar")
    }):
        raise ValueError("R0.2 requires three cases per tooth family")

    def array_hash(array: np.ndarray) -> str:
        return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()

    latent_root = root / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512"
    receipts = []
    for case_id in sorted(product_by_id):
        product = product_by_id[case_id]
        support = support_by_id[case_id]
        if (
            product.get("referenceMeshSha256") != support.get("referenceMeshSha256")
            or product.get("toothFamily") != support.get("toothFamily")
            or product.get("groupId") != support.get("groupId")
        ):
            raise ValueError(f"R0.2 pairing drift for {case_id}")
        predicted_info = product.get("frozenSparseCondition", {})
        predicted_path = root / predicted_info["artifact"]
        if hashlib.sha256(predicted_path.read_bytes()).hexdigest() != predicted_info["artifactSha256"]:
            raise ValueError(f"R0.2 predicted sparse artifact drift for {case_id}")
        predicted_tensor = torch.load(predicted_path, map_location="cpu", weights_only=True)
        predicted = predicted_tensor.detach().cpu().contiguous().numpy()
        if array_hash(predicted) != predicted_info["coordsSha256"]:
            raise ValueError(f"R0.2 predicted coordinate hash drift for {case_id}")
        reference_path = latent_root / f"{product['referenceMeshSha256']}.npz"
        if not reference_path.is_file():
            raise FileNotFoundError(reference_path)
        packed = np.load(reference_path)
        reference_xyz = packed["coords"].astype(np.int32)
        reference = np.concatenate([
            np.zeros_like(reference_xyz[:, :1]), reference_xyz
        ], axis=1)
        expected_reference_hash = support["boundary"]["referenceSupportCoordsSha256"]
        if array_hash(reference) != expected_reference_hash:
            raise ValueError(f"R0.2 reference coordinate hash drift for {case_id}")
        metrics = characterize_sparse_support_error(
            reference, predicted, resolution=sparse_resolution
        )
        receipts.append({
            "schemaVersion": 1,
            "id": case_id,
            "toothFamily": product["toothFamily"],
            "fdiNumber": product["fdiNumber"],
            "groupId": product["groupId"],
            "referenceMeshSha256": product["referenceMeshSha256"],
            "inputImageSha256": product["inputImageSha256"],
            "generationSeed": product["generationSeed"],
            "predictedSparseArtifact": predicted_info["artifact"],
            "predictedSparseArtifactSha256": predicted_info["artifactSha256"],
            "predictedCoordsSha256": predicted_info["coordsSha256"],
            "referenceLatentArtifactSha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
            "referenceCoordsSha256": expected_reference_hash,
            "metrics": metrics,
        })
    summary = summarize_r02_sparse_support_characterization(
        receipts, r01["summary"]
    )
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "R0.2-sparse-support-error-characterization-v1",
        "datasetId": dataset_name,
        "caseCount": 12,
        "optimizerSteps": 0,
        "sparseResolution": sparse_resolution,
        "sourceEvidence": {
            "r0Sha256": hashlib.sha256(r0_path.read_bytes()).hexdigest(),
            "r01Sha256": hashlib.sha256(r01_path.read_bytes()).hexdigest(),
            "productReportSha256": hashlib.sha256(product_path.read_bytes()).hexdigest(),
        },
        "cases": receipts,
        "summary": summary,
        "adapterDesignAuthorized": summary["adapterDesignAuthorized"],
        "optimizerRunAuthorized": False,
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return evidence


@app.function(
    image=trellis_gpu_image,
    volumes={"/datasets": dataset_volume},
    cpu=8,
    memory=32768,
    timeout=30 * 60,
)
def evaluate_r03_alignment_decomposition(
    dataset_name: str = "toothfairy-stage1-v1",
    sparse_resolution: int = 32,
    maximum_shift: int = 6,
) -> dict:
    """Separate bounded coordinate-frame displacement from sparse morphology error."""
    import numpy as np
    import torch

    if (
        dataset_name != "toothfairy-stage1-v1"
        or sparse_resolution != 32
        or maximum_shift != 6
    ):
        raise ValueError("R0.3 is sealed to Stage-1 resolution 32 and +/-6 voxels")
    root = Path(f"/datasets/{dataset_name}")
    r02_path = root / "stage_attribution_r02_v1.json"
    evidence_path = root / "stage_attribution_r03_v1.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True and existing.get("caseCount") == 12:
            return {**existing, "resumed": True}
        raise ValueError("Existing R0.3 evidence is invalid; refusing overwrite")
    r02 = json.loads(r02_path.read_text(encoding="utf-8"))
    if (
        r02.get("valid") is not True
        or r02.get("optimizerSteps") != 0
        or r02.get("summary", {}).get("adapterDesignAuthorized") is not True
        or len(r02.get("cases", [])) != 12
    ):
        raise ValueError("R0.3 requires sealed passing R0.2 characterization")
    latent_root = root / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512"
    receipts = []
    for source in sorted(r02["cases"], key=lambda row: row["id"]):
        predicted_path = root / source["predictedSparseArtifact"]
        if hashlib.sha256(predicted_path.read_bytes()).hexdigest() != source["predictedSparseArtifactSha256"]:
            raise ValueError(f"R0.3 predicted artifact drift for {source['id']}")
        predicted = torch.load(
            predicted_path, map_location="cpu", weights_only=True
        ).detach().cpu().contiguous().numpy()
        if hashlib.sha256(predicted.tobytes()).hexdigest() != source["predictedCoordsSha256"]:
            raise ValueError(f"R0.3 predicted coordinate drift for {source['id']}")
        reference_path = latent_root / f"{source['referenceMeshSha256']}.npz"
        if hashlib.sha256(reference_path.read_bytes()).hexdigest() != source["referenceLatentArtifactSha256"]:
            raise ValueError(f"R0.3 reference latent drift for {source['id']}")
        packed = np.load(reference_path)
        xyz = packed["coords"].astype(np.int32)
        reference = np.concatenate([np.zeros_like(xyz[:, :1]), xyz], axis=1)
        if hashlib.sha256(np.ascontiguousarray(reference).tobytes()).hexdigest() != source["referenceCoordsSha256"]:
            raise ValueError(f"R0.3 reference coordinate drift for {source['id']}")
        alignment = align_sparse_support_integer_translation(
            reference, predicted,
            resolution=sparse_resolution, maximum_shift=maximum_shift,
        )
        receipts.append({
            "schemaVersion": 1,
            "id": source["id"],
            "toothFamily": source["toothFamily"],
            "fdiNumber": source["fdiNumber"],
            "groupId": source["groupId"],
            "referenceMeshSha256": source["referenceMeshSha256"],
            "predictedCoordsSha256": source["predictedCoordsSha256"],
            "referenceCoordsSha256": source["referenceCoordsSha256"],
            "alignment": alignment,
        })
    summary = summarize_r03_alignment_decomposition(receipts)
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "R0.3-integer-translation-alignment-decomposition-v1",
        "datasetId": dataset_name,
        "caseCount": 12,
        "optimizerSteps": 0,
        "sparseResolution": sparse_resolution,
        "maximumShiftVoxelsPerAxis": maximum_shift,
        "sourceEvidence": {
            "r02Sha256": hashlib.sha256(r02_path.read_bytes()).hexdigest(),
        },
        "cases": receipts,
        "summary": summary,
        "adapterObjectiveDesignAuthorized": summary["adapterObjectiveDesignAuthorized"],
        "optimizerRunAuthorized": False,
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return evidence


@app.function(
    image=trellis_gpu_image,
    volumes={"/datasets": dataset_volume},
    cpu=8,
    memory=32768,
    timeout=30 * 60,
)
def evaluate_r04_sparse_adapter_objective(
    dataset_name: str = "toothfairy-stage1-v1",
    sparse_resolution: int = 32,
    adapter_rank: int = 4,
    experiment_seed: int = 20260921,
) -> dict:
    """Run the sealed, zero-step R0.4 objective qualification on R0.3 pairs."""
    import numpy as np
    import torch

    if (
        dataset_name != "toothfairy-stage1-v1"
        or sparse_resolution != 32
        or adapter_rank != 4
        or experiment_seed != 20260921
    ):
        raise ValueError("R0.4 objective qualification is sealed")
    root = Path(f"/datasets/{dataset_name}")
    r03_path = root / "stage_attribution_r03_v1.json"
    evidence_path = root / "stage_attribution_r04_objective_v1.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True and existing.get("caseCount") == 12:
            return {**existing, "resumed": True}
        raise ValueError("Existing R0.4 evidence is invalid; refusing overwrite")
    r03 = json.loads(r03_path.read_text(encoding="utf-8"))
    if (
        r03.get("valid") is not True
        or r03.get("optimizerSteps") != 0
        or r03.get("adapterObjectiveDesignAuthorized") is not True
        or len(r03.get("cases", [])) != 12
    ):
        raise ValueError("R0.4 requires sealed passing R0.3 evidence")

    latent_root = root / "shape_latents" / "shape_enc_next_dc_f16c32_fp16_512"
    r02_by_id = {
        row["id"]: row for row in json.loads(
            (root / "stage_attribution_r02_v1.json").read_text(encoding="utf-8")
        )["cases"]
    }
    receipts = []
    for source in sorted(r03["cases"], key=lambda row: row["id"]):
        r02_source = r02_by_id[source["id"]]
        predicted_path = root / r02_source["predictedSparseArtifact"]
        if hashlib.sha256(predicted_path.read_bytes()).hexdigest() != r02_source["predictedSparseArtifactSha256"]:
            raise ValueError(f"R0.4 predicted artifact drift for {source['id']}")
        predicted = torch.load(
            predicted_path, map_location="cpu", weights_only=True,
        ).detach().cpu().contiguous().numpy()
        if hashlib.sha256(predicted.tobytes()).hexdigest() != source["predictedCoordsSha256"]:
            raise ValueError(f"R0.4 predicted coordinate drift for {source['id']}")
        reference_path = latent_root / f"{source['referenceMeshSha256']}.npz"
        packed = np.load(reference_path)
        xyz = packed["coords"].astype(np.int32)
        reference = np.concatenate([np.zeros_like(xyz[:, :1]), xyz], axis=1)
        if hashlib.sha256(np.ascontiguousarray(reference).tobytes()).hexdigest() != source["referenceCoordsSha256"]:
            raise ValueError(f"R0.4 reference coordinate drift for {source['id']}")
        receipts.append({
            "schemaVersion": 1,
            "id": source["id"],
            "toothFamily": source["toothFamily"],
            "fdiNumber": source["fdiNumber"],
            "groupId": source["groupId"],
            "referenceMeshSha256": source["referenceMeshSha256"],
            "predictedCoordsSha256": source["predictedCoordsSha256"],
            "referenceCoordsSha256": source["referenceCoordsSha256"],
            "probe": qualify_r04_sparse_adapter_objective(
                reference, predicted,
                resolution=sparse_resolution,
                adapter_rank=adapter_rank,
                seed=experiment_seed,
            ),
        })
    summary = summarize_r04_sparse_adapter_objective(receipts)
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "R0.4-sparse-adapter-zero-step-objective-v1",
        "datasetId": dataset_name,
        "caseCount": 12,
        "optimizerSteps": 0,
        "sparseResolution": sparse_resolution,
        "adapterRank": adapter_rank,
        "experimentSeed": experiment_seed,
        "sourceEvidence": {"r03Sha256": hashlib.sha256(r03_path.read_bytes()).hexdigest()},
        "cases": receipts,
        "summary": summary,
        "modelIntegrationAuthorized": summary["modelIntegrationAuthorized"],
        "oneStepIntegrationAuthorized": False,
        "optimizerRunAuthorized": False,
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return evidence


@app.function(
    image=e12_training_image,
    volumes={"/datasets": dataset_volume},
    cpu=2,
    memory=4096,
    timeout=10 * 60,
)
def seal_r04b_sparse_adapter_architecture(
    dataset_name: str = "toothfairy-stage1-v1",
) -> dict:
    """Seal the exact real-model adapter target before an H100 backward probe."""
    if dataset_name != "toothfairy-stage1-v1":
        raise ValueError("R0.4B architecture contract is sealed")
    root = Path(f"/datasets/{dataset_name}")
    r04_path = root / "stage_attribution_r04_objective_v1.json"
    evidence_path = root / "stage_attribution_r04b_architecture_v1.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Invalid existing R0.4B architecture evidence")
    r04 = json.loads(r04_path.read_text(encoding="utf-8"))
    if r04.get("modelIntegrationAuthorized") is not True or r04.get("optimizerSteps") != 0:
        raise ValueError("R0.4B requires passing zero-step R0.4 evidence")
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    source = Path(TRELLIS2_PATH) / "trellis2/models/sparse_structure_flow.py"
    config = json.loads(official.read_text(encoding="utf-8"))
    target = r04b_sparse_adapter_target(config)
    source_text = source.read_text(encoding="utf-8")
    required = ("self.blocks = nn.ModuleList", "self.out_layer = nn.Linear", "for block in self.blocks")
    if not all(marker in source_text for marker in required):
        raise ValueError("Pinned TRELLIS.2 sparse-flow architecture changed")
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "R0.4B-sparse-adapter-architecture-contract-v1",
        "optimizerSteps": 0,
        "officialConfigSha256": hashlib.sha256(official.read_bytes()).hexdigest(),
        "modelSourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "baseModelRevision": BASE_MODEL_REVISION,
        "modelClass": "SparseStructureFlowModel",
        "adapterTarget": target,
        "adapterRank": 4,
        "adapterSeed": 20260921,
        "modelBackwardProbeAuthorized": True,
        "oneStepIntegrationAuthorized": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def run_r04b_real_sparse_adapter_zero_step(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "stage1-r04b-real-sparse-adapter-zero-step-v3",
) -> dict:
    """One real sparse-model forward/backward, with no optimizer step."""
    import os
    from huggingface_hub import hf_hub_download

    if dataset_name != "toothfairy-tf-pw32-v1" or run_name != "stage1-r04b-real-sparse-adapter-zero-step-v3":
        raise ValueError("R0.4B real-model probe is sealed")
    architecture_path = Path("/datasets/toothfairy-stage1-v1/stage_attribution_r04b_architecture_v1.json")
    architecture = json.loads(architecture_path.read_text(encoding="utf-8"))
    if architecture.get("modelBackwardProbeAuthorized") is not True or architecture.get("adapterTarget") != "blocks.29.mlp.mlp.2":
        raise ValueError("R0.4B requires the sealed architecture contract")
    anchor_receipt = Path(f"/datasets/{dataset_name}/sparse_anchor_v1/receipt.json")
    anchor = json.loads(anchor_receipt.read_text(encoding="utf-8"))
    if anchor.get("valid") is not True or anchor.get("assetCount") != 8:
        raise ValueError("R0.4B requires the sealed four-family sparse anchor")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "r04b-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Invalid existing R0.4B evidence")
    if run_root.exists():
        raise FileExistsError("Partial R0.4B run exists; inspect before versioning")
    run_root.mkdir(parents=True, exist_ok=False)

    files = {suffix: hf_hub_download(
        BASE_MODEL_NAME, f"{BASE_SPARSE_FLOW_FILE}.{suffix}", revision=BASE_MODEL_REVISION,
    ) for suffix in ("json", "safetensors")}
    trainer_checkpoint = materialize_trainer_checkpoint(
        files["safetensors"], run_root / "base-denoiser.pt",
    )
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")), trainer_checkpoint,
        max_steps=1, save_interval=1, log_interval=1,
    )
    config["trainer"]["args"]["mix_precision_mode"] = "amp"
    config["trainer"]["args"]["mix_precision_dtype"] = "bfloat16"
    config["trainer"]["args"]["i_sample"] = 101
    (run_root / "dentalsculptor_sparse_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8",
    )
    command = sparse_anchor_training_command(dataset_name, run_name)
    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    sparse_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/sparse_flow_matching.py"
    originals = {path: path.read_text(encoding="utf-8") for path in (basic_path, flow_path, sparse_path)}
    receipt_path = run_root / "zero-step-receipt.json"
    try:
        patched_basic = sparse_flow_trainer_source_with_derived_rope_buffer(originals[basic_path])
        patched_basic = smoke_trainer_source_without_snapshots(patched_basic)
        basic_path.write_text(r04b_basic_zero_step_probe_source(patched_basic), encoding="utf-8")
        flow_path.write_text(r04b_install_adapter_flow_source(originals[flow_path]), encoding="utf-8")
        sparse_path.write_text(originals[sparse_path], encoding="utf-8")
        env = os.environ.copy()
        env["DENTALSCULPTOR_R04B_RECEIPT"] = str(receipt_path)
        process = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
        )
    finally:
        for path, source in originals.items():
            path.write_text(source, encoding="utf-8")
    (run_root / "probe.log").write_text(process.stdout, encoding="utf-8")
    print(process.stdout, flush=True)
    marker = "DENTALSCULPTOR_R04B_ZERO_STEP_COMPLETE"
    if marker not in process.stdout or not receipt_path.is_file():
        checkpoint_volume.commit()
        raise RuntimeError(f"R0.4B stopped before sealed evidence (code {process.returncode})")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    gradients = receipt.get("adapterGradients", [])
    passed = (
        receipt.get("optimizerSteps") == 0
        and receipt.get("frozenStateByteIdentical") is True
        and math.isfinite(float(receipt.get("nativeMse", float("nan"))))
        and len(gradients) == 2
        and all(row.get("finite") is True and float(row.get("norm") or 0.0) > 0.0 for row in gradients)
    )
    evidence = {
        "schemaVersion": 1, "valid": passed,
        "stage": "R0.4B-real-sparse-flow-adapter-zero-step-v1",
        "optimizerSteps": 0,
        "architectureEvidenceSha256": hashlib.sha256(architecture_path.read_bytes()).hexdigest(),
        "anchorReceiptSha256": hashlib.sha256(anchor_receipt.read_bytes()).hexdigest(),
        "receipt": receipt,
        "oneStepIntegrationAuthorized": passed,
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    if not passed:
        raise RuntimeError("R0.4B real-model gate failed")
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def run_r04c_sparse_adapter_one_step(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "stage1-r04c-sparse-adapter-one-step-v1",
) -> dict:
    """Execute exactly one adapter update, strict reload, and repeated raw generation."""
    import os
    import sys
    import torch
    from huggingface_hub import hf_hub_download

    if dataset_name != "toothfairy-tf-pw32-v1" or run_name != "stage1-r04c-sparse-adapter-one-step-v1":
        raise ValueError("R0.4C one-step gate is sealed")
    zero_evidence_path = Path("/checkpoints/stage1-r04b-real-sparse-adapter-zero-step-v3/r04b-evidence.json")
    zero_evidence = json.loads(zero_evidence_path.read_text(encoding="utf-8"))
    if zero_evidence.get("oneStepIntegrationAuthorized") is not True or zero_evidence.get("optimizerSteps") != 0:
        raise ValueError("R0.4C requires passed R0.4B v3 evidence")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "r04c-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Invalid existing R0.4C evidence")
    if run_root.exists():
        raise FileExistsError("Partial R0.4C run exists; inspect before versioning")
    run_root.mkdir(parents=True, exist_ok=False)

    files = {suffix: hf_hub_download(
        BASE_MODEL_NAME, f"{BASE_SPARSE_FLOW_FILE}.{suffix}", revision=BASE_MODEL_REVISION,
    ) for suffix in ("json", "safetensors")}
    trainer_checkpoint = materialize_trainer_checkpoint(files["safetensors"], run_root / "base-denoiser.pt")
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")), trainer_checkpoint,
        max_steps=1, save_interval=101, log_interval=1,
    )
    args = config["trainer"]["args"]
    args["mix_precision_mode"] = "amp"
    args["mix_precision_dtype"] = "bfloat16"
    args["i_sample"] = 101
    (run_root / "dentalsculptor_sparse_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8",
    )
    command = sparse_anchor_training_command(dataset_name, run_name)
    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    sparse_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/sparse_flow_matching.py"
    originals = {path: path.read_text(encoding="utf-8") for path in (basic_path, flow_path, sparse_path)}
    receipt_path = run_root / "one-step-receipt.json"
    candidate_path = run_root / "candidate-sparse-flow-merged.pt"
    try:
        patched_basic = sparse_flow_trainer_source_with_derived_rope_buffer(originals[basic_path])
        patched_basic = smoke_trainer_source_without_snapshots(patched_basic)
        basic_path.write_text(r04c_basic_one_step_probe_source(patched_basic), encoding="utf-8")
        flow_path.write_text(r04c_install_trainable_adapter_flow_source(originals[flow_path]), encoding="utf-8")
        sparse_path.write_text(originals[sparse_path], encoding="utf-8")
        env = os.environ.copy()
        env["DENTALSCULPTOR_R04C_RECEIPT"] = str(receipt_path)
        env["DENTALSCULPTOR_R04C_CHECKPOINT"] = str(candidate_path)
        process = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
        )
    finally:
        for path, source in originals.items():
            path.write_text(source, encoding="utf-8")
    (run_root / "training.log").write_text(process.stdout, encoding="utf-8")
    print(process.stdout, flush=True)
    marker = "DENTALSCULPTOR_R04C_ONE_STEP_COMPLETE"
    if marker not in process.stdout or not receipt_path.is_file() or not candidate_path.is_file():
        checkpoint_volume.commit()
        raise RuntimeError(f"R0.4C stopped before sealed one-step evidence (code {process.returncode})")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    gradients = receipt.get("adapterGradients", [])
    deltas = receipt.get("adapterDeltas", [])
    engineering_pass = (
        receipt.get("optimizerSteps") == 1
        and receipt.get("frozenStateByteIdentical") is True
        and len(gradients) == 2
        and all(row.get("finite") is True and float(row.get("norm") or 0.0) > 0.0 for row in gradients)
        and len(deltas) == 2
        and all(row.get("finite") is True and float(row.get("norm") or 0.0) > 0.0 for row in deltas)
    )
    if not engineering_pass:
        checkpoint_volume.commit()
        raise RuntimeError("R0.4C adapter update contract failed")

    os.environ["TRELLIS_ENABLE_WARMUP"] = "false"
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator

    generator = TrellisGenerator()
    generator.load_model()
    checkpoint_receipt = generator.load_sparse_structure_checkpoint(str(candidate_path))
    validation = json.loads(Path("/datasets/toothfairy-stage1-v1/stage1_validation_inputs_v1.json").read_text(encoding="utf-8"))
    case = validation["cases"][0]
    image_bytes = (Path("/datasets/toothfairy-stage1-v1") / case["inputImage"]).read_bytes()
    first = generator.run_inference(image_bytes, quality="preview", seed=int(case["generationSeed"]), content_type=None)
    first_bytes = first.serialize()
    second = generator.run_inference(image_bytes, quality="preview", seed=int(case["generationSeed"]), content_type=None)
    second_bytes = second.serialize()
    mesh = first.mesh
    vertex_count = int(mesh.vertices.shape[0])
    face_count = int(mesh.faces.shape[0])
    exact_repeat = hashlib.sha256(first_bytes).hexdigest() == hashlib.sha256(second_bytes).hexdigest()
    passed = engineering_pass and checkpoint_receipt.get("strictLoad") is True and exact_repeat and vertex_count > 0 and face_count > 0
    evidence = {
        "schemaVersion": 1, "valid": passed,
        "stage": "R0.4C-sparse-adapter-one-step-integration-v1",
        "optimizerSteps": 1,
        "zeroStepEvidenceSha256": hashlib.sha256(zero_evidence_path.read_bytes()).hexdigest(),
        "receipt": receipt,
        "checkpointReloaded": checkpoint_receipt.get("strictLoad") is True,
        "candidateCheckpoint": checkpoint_receipt,
        "heldoutCaseId": case["id"],
        "rawDecodeExactRepeat": exact_repeat,
        "rawMeshVertexCount": vertex_count,
        "rawMeshFaceCount": face_count,
        "fourFamilyScreenAuthorized": passed,
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    if not passed:
        raise RuntimeError("R0.4C one-step integration gate failed")
    return evidence


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=4 * 60 * 60,
)
def run_r04d_four_family_screen(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-r04c-sparse-adapter-one-step-v1",
    samples: int = 5000,
) -> dict:
    """Zero-training matched screen of base versus the one-step sparse adapter."""
    import os
    import sys

    import torch
    import trimesh

    if (
        dataset_name != "toothfairy-stage1-v1"
        or run_name != "stage1-r04c-sparse-adapter-one-step-v1"
        or samples != 5000
    ):
        raise ValueError("R0.4D four-family screen is sealed")
    root = Path(f"/datasets/{dataset_name}")
    run_root = Path(f"/checkpoints/{run_name}")
    r04c_path = run_root / "r04c-evidence.json"
    candidate_path = run_root / "candidate-sparse-flow-merged.pt"
    evidence_path = run_root / "r04d-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Existing R0.4D evidence is invalid; refusing overwrite")
    r04c = json.loads(r04c_path.read_text(encoding="utf-8"))
    if (
        r04c.get("fourFamilyScreenAuthorized") is not True
        or r04c.get("optimizerSteps") != 1
        or r04c.get("checkpointReloaded") is not True
    ):
        raise ValueError("R0.4D requires sealed passing R0.4C evidence")
    if not candidate_path.is_file() or candidate_path.stat().st_size == 0:
        raise FileNotFoundError(candidate_path)

    manifest = json.loads((root / "anatomy_manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((root / "stage1_validation_inputs_v1.json").read_text(encoding="utf-8"))
    if (
        manifest.get("assetCount") != 164
        or validation.get("valid") is not True
        or validation.get("trainingPatientOverlapCount") != 0
    ):
        raise ValueError("R0.4D requires sealed patient-disjoint validation inputs")
    cases = resolve_e12_g2_validation_cases(validation, manifest)

    os.environ["TRELLIS_ENABLE_WARMUP"] = "false"
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    generator = TrellisGenerator()
    generator.load_model()
    output_root = run_root / "r04d-four-family-screen-v1"
    output_root.mkdir(parents=True, exist_ok=False)

    def raw_hash(mesh: object) -> str:
        digest = hashlib.sha256()
        digest.update(mesh.vertices.detach().cpu().contiguous().numpy().tobytes())
        digest.update(mesh.faces.detach().cpu().contiguous().numpy().tobytes())
        return digest.hexdigest()

    def to_trimesh(mesh: object) -> trimesh.Trimesh:
        result = trimesh.Trimesh(
            vertices=mesh.vertices.detach().cpu().numpy(),
            faces=mesh.faces.detach().cpu().numpy(),
            process=False,
        )
        if len(result.vertices) == 0 or len(result.faces) == 0:
            raise RuntimeError("R0.4D generated an empty raw mesh")
        return result

    def evaluate_role(role: str) -> list[dict]:
        role_root = output_root / role
        role_root.mkdir()
        receipts = []
        for index, case in enumerate(cases, start=1):
            image_path = root / case["inputImage"]
            image_bytes = image_path.read_bytes()
            if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
                raise ValueError(f"R0.4D input image hash drift for {case['id']}")
            runs = []
            for trial in ("a", "b"):
                result = generator.run_inference(
                    image_bytes,
                    quality="preview",
                    seed=int(case["generationSeed"]),
                    content_type=None,
                    trace_id=f"r04d-{role}-{case['id']}-{trial}",
                )
                runs.append({
                    "trial": trial,
                    "hash": raw_hash(result.mesh),
                    "seed": int(result.resolved_seed),
                    "pipelineType": result.actual_pipeline_type,
                    "mesh": result.mesh,
                })
            if runs[0]["hash"] != runs[1]["hash"]:
                raise RuntimeError(f"R0.4D raw repeatability failed for {role}:{case['id']}")
            if any(run["seed"] != int(case["generationSeed"]) for run in runs):
                raise RuntimeError(f"R0.4D generation seed drift for {role}:{case['id']}")
            prediction = to_trimesh(runs[0]["mesh"])
            mesh_path = role_root / f"{case['id']}.ply"
            mesh_path.write_bytes(prediction.export(file_type="ply", encoding="binary"))
            reference = load_mesh(root / case["referenceMesh"])
            receipt = {
                "schemaVersion": 1,
                "id": case["id"], "toothFamily": case["toothFamily"],
                "fdiNumber": case["fdiNumber"], "groupId": case["groupId"],
                "modelRole": role,
                "inputImageSha256": case["inputImageSha256"],
                "referenceMeshSha256": case["referenceMeshSha256"],
                "generationSeed": int(case["generationSeed"]),
                "quality": "preview",
                "pipelineType": runs[0]["pipelineType"],
                "repeatability": {
                    "rawShapeExact": True,
                    "rawShapeSha256": runs[0]["hash"],
                },
                "metrics": compare_meshes(
                    reference, prediction, samples=samples, seed=int(case["generationSeed"])
                ),
                "topology": analyze_mesh_with_weld_control(prediction),
                "meshArtifact": str(mesh_path),
                "meshArtifactSha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
                "vertexCount": int(len(prediction.vertices)),
                "faceCount": int(len(prediction.faces)),
            }
            (role_root / f"{case['id']}.json").write_text(
                json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
            )
            receipts.append(receipt)
            checkpoint_volume.commit()
            del runs, prediction, reference
            torch.cuda.empty_cache()
            print(f"R0.4D {role} {index}/4 complete: {case['id']}", flush=True)
        return receipts

    baseline = evaluate_role("unchanged-base-sparse-flow")
    checkpoint_receipt = generator.load_sparse_structure_checkpoint(str(candidate_path))
    if checkpoint_receipt.get("strictLoad") is not True:
        raise RuntimeError("R0.4D candidate checkpoint did not strict-load")
    candidate = evaluate_role("r04c-one-step-rank4-sparse-adapter")
    summary = summarize_r04d_four_family_screen(baseline, candidate)
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "R0.4D-four-family-image-conditioned-screen-v1",
        "optimizerSteps": 0,
        "trainingOptimizerStepsInherited": 1,
        "r04cEvidenceSha256": hashlib.sha256(r04c_path.read_bytes()).hexdigest(),
        "candidateCheckpoint": checkpoint_receipt,
        "caseSelection": "lexicographically-first-patient-disjoint-validation-case-per-family",
        "samplesPerMetric": samples,
        "baseline": baseline,
        "candidate": candidate,
        "summary": summary,
        "boundedTrainingAuthorized": summary["boundedTrainingAuthorized"],
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=trellis_gpu_image.add_local_dir("scripts", remote_path="/root/scripts", copy=True),
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=4 * 60 * 60,
)
def run_r05c_four_family_screen(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-r05b-regional-objective-one-step-v1",
    samples: int = 5000,
) -> dict:
    """Matched zero-training screen of base versus the R0.5B candidate."""
    import os
    import sys

    import torch
    import trimesh

    if (
        dataset_name != "toothfairy-stage1-v1"
        or run_name != "stage1-r05b-regional-objective-one-step-v1"
        or samples != 5000
    ):
        raise ValueError("R0.5C four-family screen is sealed")
    root = Path(f"/datasets/{dataset_name}")
    run_root = Path(f"/checkpoints/{run_name}")
    r05b_path = run_root / "r05b-evidence.json"
    candidate_path = run_root / "candidate-sparse-flow-merged.pt"
    evidence_path = run_root / "r05c-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Existing R0.5C evidence is invalid; refusing overwrite")
    r05b = json.loads(r05b_path.read_text(encoding="utf-8"))
    if (
        r05b.get("fourFamilyScreenAuthorized") is not True
        or r05b.get("optimizerSteps") != 1
        or r05b.get("checkpointReloaded") is not True
    ):
        raise ValueError("R0.5C requires sealed passing R0.5B evidence")
    if not candidate_path.is_file() or candidate_path.stat().st_size == 0:
        raise FileNotFoundError(candidate_path)

    manifest = json.loads((root / "anatomy_manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((root / "stage1_validation_inputs_v1.json").read_text(encoding="utf-8"))
    if (
        manifest.get("assetCount") != 164
        or validation.get("valid") is not True
        or validation.get("trainingPatientOverlapCount") != 0
    ):
        raise ValueError("R0.5C requires sealed patient-disjoint validation inputs")
    cases = resolve_e12_g2_validation_cases(validation, manifest)

    os.environ["TRELLIS_ENABLE_WARMUP"] = "false"
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator
    from scripts.analyze_mesh_topology import analyze_mesh_with_weld_control
    from scripts.reconstruction_benchmark import compare_meshes, load_mesh

    generator = TrellisGenerator()
    generator.load_model()
    output_root = run_root / "r05c-four-family-screen-v1"
    output_root.mkdir(parents=True, exist_ok=False)

    def raw_hash(mesh: object) -> str:
        digest = hashlib.sha256()
        digest.update(mesh.vertices.detach().cpu().contiguous().numpy().tobytes())
        digest.update(mesh.faces.detach().cpu().contiguous().numpy().tobytes())
        return digest.hexdigest()

    def to_trimesh(mesh: object) -> trimesh.Trimesh:
        result = trimesh.Trimesh(
            vertices=mesh.vertices.detach().cpu().numpy(),
            faces=mesh.faces.detach().cpu().numpy(), process=False,
        )
        if len(result.vertices) == 0 or len(result.faces) == 0:
            raise RuntimeError("R0.5C generated an empty raw mesh")
        return result

    def evaluate_role(role: str) -> list[dict]:
        role_root = output_root / role
        role_root.mkdir()
        receipts = []
        for index, case in enumerate(cases, start=1):
            image_path = root / case["inputImage"]
            image_bytes = image_path.read_bytes()
            if hashlib.sha256(image_bytes).hexdigest() != case["inputImageSha256"]:
                raise ValueError(f"R0.5C input image hash drift for {case['id']}")
            runs = []
            for trial in ("a", "b"):
                result = generator.run_inference(
                    image_bytes, quality="preview", seed=int(case["generationSeed"]),
                    content_type=None, trace_id=f"r05c-{role}-{case['id']}-{trial}",
                )
                runs.append({
                    "trial": trial, "hash": raw_hash(result.mesh),
                    "seed": int(result.resolved_seed),
                    "pipelineType": result.actual_pipeline_type, "mesh": result.mesh,
                })
            if runs[0]["hash"] != runs[1]["hash"]:
                raise RuntimeError(f"R0.5C raw repeatability failed for {role}:{case['id']}")
            if any(run["seed"] != int(case["generationSeed"]) for run in runs):
                raise RuntimeError(f"R0.5C generation seed drift for {role}:{case['id']}")
            prediction = to_trimesh(runs[0]["mesh"])
            mesh_path = role_root / f"{case['id']}.ply"
            mesh_path.write_bytes(prediction.export(file_type="ply", encoding="binary"))
            reference = load_mesh(root / case["referenceMesh"])
            receipt = {
                "schemaVersion": 1, "id": case["id"],
                "toothFamily": case["toothFamily"], "fdiNumber": case["fdiNumber"],
                "groupId": case["groupId"], "modelRole": role,
                "inputImageSha256": case["inputImageSha256"],
                "referenceMeshSha256": case["referenceMeshSha256"],
                "generationSeed": int(case["generationSeed"]), "quality": "preview",
                "pipelineType": runs[0]["pipelineType"],
                "repeatability": {"rawShapeExact": True, "rawShapeSha256": runs[0]["hash"]},
                "metrics": compare_meshes(reference, prediction, samples=samples, seed=int(case["generationSeed"])),
                "topology": analyze_mesh_with_weld_control(prediction),
                "meshArtifact": str(mesh_path),
                "meshArtifactSha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
                "vertexCount": int(len(prediction.vertices)), "faceCount": int(len(prediction.faces)),
            }
            (role_root / f"{case['id']}.json").write_text(
                json.dumps(receipt, indent=2) + "\n", encoding="utf-8",
            )
            receipts.append(receipt)
            checkpoint_volume.commit()
            del runs, prediction, reference
            torch.cuda.empty_cache()
            print(f"R0.5C {role} {index}/4 complete: {case['id']}", flush=True)
        return receipts

    baseline = evaluate_role("unchanged-base-sparse-flow")
    checkpoint_receipt = generator.load_sparse_structure_checkpoint(str(candidate_path))
    if checkpoint_receipt.get("strictLoad") is not True:
        raise RuntimeError("R0.5C candidate checkpoint did not strict-load")
    candidate = evaluate_role("r05b-regional-one-step-rank4-adapter")
    summary = summarize_r04d_four_family_screen(baseline, candidate)
    evidence = {
        "schemaVersion": 1, "valid": True,
        "stage": "R0.5C-four-family-regional-objective-screen-v1",
        "optimizerSteps": 0, "trainingOptimizerStepsInherited": 1,
        "r05bEvidenceSha256": hashlib.sha256(r05b_path.read_bytes()).hexdigest(),
        "candidateCheckpoint": checkpoint_receipt,
        "caseSelection": "lexicographically-first-patient-disjoint-validation-case-per-family",
        "samplesPerMetric": samples, "baseline": baseline, "candidate": candidate,
        "summary": summary,
        "boundedTrainingAuthorized": summary["boundedTrainingAuthorized"],
        "clinicalClaimPermitted": False, "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=trellis_gpu_image,
    volumes={"/datasets": dataset_volume},
    cpu=8,
    memory=32768,
    timeout=45 * 60,
)
def run_e14_g0_crown_composition_proof(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g0-crown-composition-v2",
) -> dict:
    """Prove crown-only gradient routing and exact root copying on 32 teeth."""
    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image
    from collections import Counter

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g0-crown-composition-v2":
        raise ValueError("E14 G0 is sealed")
    root = Path(f"/datasets/{dataset_name}")
    output_root = root / run_name
    evidence_path = output_root / "g0-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Existing E14 G0 evidence is invalid")
    if output_root.exists():
        raise FileExistsError("Partial E14 G0 output exists; inspect before versioning")
    output_root.mkdir(parents=True, exist_ok=False)

    manifest_path = root / "anatomy_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("assetCount") != 164:
        raise ValueError("E14 G0 requires the sealed 164-tooth Stage-1 manifest")
    families = ("incisor", "canine", "premolar", "molar")
    selected = []
    used_groups = set()
    family_counts = Counter()
    for asset in sorted(manifest["assets"], key=lambda row: row["id"]):
        family = asset["toothFamily"]
        if (
            asset.get("split") != "train"
            or family not in families
            or family_counts[family] >= 8
            or asset["groupId"] in used_groups
        ):
            continue
        latent_path = root / "shape_latents/shape_enc_next_dc_f16c32_fp16_512" / f"{asset['canonicalSha256']}.npz"
        mesh_path = root / asset["canonicalPath"]
        if not latent_path.is_file() or not mesh_path.is_file():
            continue
        selected.append((asset, latent_path, mesh_path))
        used_groups.add(asset["groupId"])
        family_counts[family] += 1
    if family_counts != Counter({family: 8 for family in families}) or len(selected) != 32:
        raise RuntimeError(f"E14 G0 could not select balanced patient-distinct cohort: {dict(family_counts)}")

    receipts = []
    generator = torch.Generator(device="cpu").manual_seed(20260922)
    for index, (asset, latent_path, mesh_path) in enumerate(selected, start=1):
        packed = np.load(latent_path)
        coords = np.asarray(packed["coords"], dtype=np.int64)
        if coords.ndim != 2 or coords.shape[1] != 3 or coords.size == 0:
            raise ValueError(f"Invalid E14 reference occupancy for {asset['id']}")
        occupancy = torch.zeros((1, 1, 32, 32, 32), dtype=torch.bool)
        occupancy[0, 0, coords[:, 0], coords[:, 1], coords[:, 2]] = True
        weights, mask_receipts = build_crown_transition_weights_from_occupancy(occupancy)
        base = torch.where(occupancy, torch.tensor(2.0), torch.tensor(-2.0))
        residual = torch.nn.Parameter(torch.randn(base.shape, generator=generator) * 1e-3)
        candidate = compose_crown_residual_logits(base, residual, weights)
        target = occupancy.float()
        supervised = weights > 0
        loss = F.binary_cross_entropy_with_logits(candidate[supervised], target[supervised])
        loss.backward()
        root_mask = weights == 0
        root_byte_identical = (
            candidate[root_mask].detach().contiguous().numpy().tobytes()
            == base[root_mask].detach().contiguous().numpy().tobytes()
        )
        crown_gradient_norm = float(residual.grad[supervised].float().norm().item())
        root_gradient_nonzero = int(torch.count_nonzero(residual.grad[root_mask]).item())
        if not root_byte_identical or not crown_gradient_norm > 0.0 or root_gradient_nonzero != 0:
            raise RuntimeError(f"E14 G0 composition failed for {asset['id']}")

        mask = weights[0, 0].numpy()
        occupied = occupancy[0, 0].numpy()
        projection_axis = int(mask_receipts[0]["axialSpatialOffset"])
        occupied_mip = occupied.max(axis=projection_axis)
        crown_mip = (mask == 1).max(axis=projection_axis)
        transition_mip = ((mask > 0) & (mask < 1)).max(axis=projection_axis)
        rgb = np.zeros((*occupied_mip.shape, 3), dtype=np.uint8)
        rgb[occupied_mip] = (80, 180, 120)
        rgb[transition_mip] = (255, 180, 40)
        rgb[crown_mip] = (215, 45, 70)
        overlay_path = output_root / f"{asset['id']}-mask.png"
        Image.fromarray(rgb).resize((512, 512), resample=Image.Resampling.NEAREST).save(overlay_path)
        mask_path = output_root / f"{asset['id']}-weights.npz"
        np.savez_compressed(mask_path, weights=mask.astype(np.float32), occupancy=occupied)
        receipt = {
            "schemaVersion": 1, "id": asset["id"], "groupId": asset["groupId"],
            "fdiNumber": asset["fdiNumber"], "toothFamily": asset["toothFamily"],
            "canonicalMesh": asset["canonicalPath"],
            "canonicalMeshSha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
            "referenceLatentSha256": hashlib.sha256(latent_path.read_bytes()).hexdigest(),
            "referenceVoxelCount": int(occupancy.sum().item()),
            "mask": mask_receipts[0], "loss": float(loss.detach().item()),
            "crownGradientNorm": crown_gradient_norm,
            "rootGradientNonzeroCount": root_gradient_nonzero,
            "rootLogitsByteIdentical": root_byte_identical,
            "maskArtifact": str(mask_path.relative_to(root)).replace("\\", "/"),
            "maskArtifactSha256": hashlib.sha256(mask_path.read_bytes()).hexdigest(),
            "overlayArtifact": str(overlay_path.relative_to(root)).replace("\\", "/"),
            "overlayArtifactSha256": hashlib.sha256(overlay_path.read_bytes()).hexdigest(),
        }
        (output_root / f"{asset['id']}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        receipts.append(receipt)
        dataset_volume.commit()
        print(f"E14 G0 {index}/32 complete: {asset['id']}", flush=True)

    passed = (
        len(receipts) == 32
        and Counter(row["toothFamily"] for row in receipts) == Counter({family: 8 for family in families})
        and len({row["groupId"] for row in receipts}) == 32
        and all(row["rootLogitsByteIdentical"] for row in receipts)
        and all(row["rootGradientNonzeroCount"] == 0 for row in receipts)
        and all(row["crownGradientNorm"] > 0.0 for row in receipts)
        and all(row["mask"]["rootVoxelCount"] > 0 for row in receipts)
        and all(row["mask"]["transitionVoxelCount"] > 0 for row in receipts)
        and all(row["mask"]["crownVoxelCount"] > 0 for row in receipts)
    )
    evidence = {
        "schemaVersion": 1, "valid": passed,
        "stage": "E14-G0-crown-composition-proof-v1", "optimizerSteps": 0,
        "caseCount": len(receipts), "casesPerFamily": dict(family_counts),
        "uniquePatientGroupCount": len({row["groupId"] for row in receipts}),
        "manifestSha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "cases": receipts, "allRootLogitsByteIdentical": all(row["rootLogitsByteIdentical"] for row in receipts),
        "allRootGradientsZero": all(row["rootGradientNonzeroCount"] == 0 for row in receipts),
        "allCrownGradientsFiniteNonzero": all(math.isfinite(row["crownGradientNorm"]) and row["crownGradientNorm"] > 0 for row in receipts),
        "g1Authorized": passed, "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    if not passed:
        raise RuntimeError("E14 G0 crown-composition gate failed")
    return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    gpu="T4",
    cpu=8,
    memory=32768,
    timeout=45 * 60,
)
def run_e14_g1_crown_refiner_one_step(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g1-crown-refiner-one-step-v3",
) -> dict:
    """Execute exactly one crown-refiner update and prove root isolation.

    This is an integration canary, not an efficacy experiment. The frozen base
    support already carries the image-conditioned reconstruction; the refiner
    sees that support plus spatial coordinates and family identity. G2 must
    replace the reference-support canary inputs with sealed base predictions.
    """
    import numpy as np
    import torch
    import torch.nn.functional as F
    import trimesh
    from skimage import measure
    from collections import Counter

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g1-crown-refiner-one-step-v3":
        raise ValueError("E14 G1 is sealed")
    g0_path = Path(f"/datasets/{dataset_name}/stage1-e14-g0-crown-composition-v2/g0-evidence.json")
    g0 = json.loads(g0_path.read_text(encoding="utf-8"))
    if not (g0.get("valid") is True and g0.get("g1Authorized") is True and g0.get("caseCount") == 32):
        raise ValueError("E14 G1 requires sealed passing G0 evidence")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "g1-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Existing E14 G1 evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E14 G1 output exists; inspect before versioning")
    run_root.mkdir(parents=True, exist_ok=False)

    torch.manual_seed(20260922)
    torch.cuda.manual_seed_all(20260922)
    device = torch.device("cuda")
    family_order = ("incisor", "canine", "premolar", "molar")
    cases = g0["cases"]
    if Counter(row["toothFamily"] for row in cases) != Counter({family: 8 for family in family_order}):
        raise ValueError("E14 G1 requires the balanced G0 cohort")
    train_case = next(row for row in cases if row["toothFamily"] == "molar")
    heldout_case = next(
        row for row in cases
        if row["toothFamily"] == "premolar" and row["groupId"] != train_case["groupId"]
    )

    class CrownResidualRefiner(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.net = torch.nn.Sequential(
                torch.nn.Conv3d(8, 16, 3, padding=1),
                torch.nn.SiLU(),
                torch.nn.Conv3d(16, 16, 3, padding=1),
                torch.nn.SiLU(),
                torch.nn.Conv3d(16, 1, 1),
            )
            torch.nn.init.zeros_(self.net[-1].weight)
            torch.nn.init.zeros_(self.net[-1].bias)

        def forward(self, base_logits: torch.Tensor, family_index: int) -> torch.Tensor:
            batch, _, depth, height, width = base_logits.shape
            axes = [torch.linspace(-1, 1, size, device=base_logits.device, dtype=base_logits.dtype)
                    for size in (depth, height, width)]
            grid = torch.stack(torch.meshgrid(*axes, indexing="ij"), dim=0).expand(batch, -1, -1, -1, -1)
            family = torch.zeros((batch, 4, depth, height, width), device=base_logits.device, dtype=base_logits.dtype)
            family[:, family_index] = 1
            features = torch.cat((torch.sigmoid(base_logits), grid, family), dim=1)
            return 0.5 * torch.tanh(self.net(features))

    manifest = json.loads(Path(f"/datasets/{dataset_name}/anatomy_manifest.json").read_text(encoding="utf-8"))
    assets_by_id = {asset["id"]: asset for asset in manifest["assets"]}

    def load_case(row: dict) -> tuple[torch.Tensor, torch.Tensor, list[dict]]:
        asset = assets_by_id[row["id"]]
        latent_path = Path(f"/datasets/{dataset_name}/shape_latents/shape_enc_next_dc_f16c32_fp16_512") / f"{asset['canonicalSha256']}.npz"
        packed = np.load(latent_path)
        coords = np.asarray(packed["coords"], dtype=np.int64)
        occupancy = torch.zeros((1, 1, 32, 32, 32), dtype=torch.bool, device=device)
        occupancy[0, 0, coords[:, 0], coords[:, 1], coords[:, 2]] = True
        weights, receipts = build_crown_transition_weights_from_occupancy(occupancy)
        return occupancy, weights.to(device), receipts

    def tensor_sha256(tensor: torch.Tensor) -> str:
        return hashlib.sha256(tensor.detach().cpu().contiguous().numpy().tobytes()).hexdigest()

    refiner = CrownResidualRefiner().to(device)
    before = {name: tensor_sha256(parameter) for name, parameter in refiner.named_parameters()}
    optimizer = torch.optim.AdamW(refiner.parameters(), lr=1e-6, weight_decay=0.0)
    train_occupancy, train_weights, train_mask_receipt = load_case(train_case)
    train_base = torch.where(train_occupancy, torch.tensor(2.0, device=device), torch.tensor(-2.0, device=device))
    optimizer.zero_grad(set_to_none=True)
    train_residual = refiner(train_base, family_order.index(train_case["toothFamily"]))
    train_candidate = compose_crown_residual_logits(train_base, train_residual, train_weights)
    supervised = train_weights > 0
    loss = F.binary_cross_entropy_with_logits(train_candidate[supervised], train_occupancy.float()[supervised])
    loss.backward()
    gradients = {
        name: {
            "finite": bool(parameter.grad is not None and torch.isfinite(parameter.grad).all().item()),
            "norm": float(parameter.grad.float().norm().item()) if parameter.grad is not None else 0.0,
        }
        for name, parameter in refiner.named_parameters()
    }
    if not all(item["finite"] for item in gradients.values()) or not any(item["norm"] > 0 for item in gradients.values()):
        raise RuntimeError("E14 G1 refiner gradients are invalid")
    optimizer.step()
    after = {name: tensor_sha256(parameter) for name, parameter in refiner.named_parameters()}
    changed = sorted(name for name in before if before[name] != after[name])
    if not changed:
        raise RuntimeError("E14 G1 optimizer step changed no refiner parameters")

    checkpoint_path = run_root / "crown-refiner.pt"
    torch.save({"state_dict": refiner.state_dict(), "familyOrder": family_order, "optimizerSteps": 1}, checkpoint_path)
    reloaded = CrownResidualRefiner().to(device)
    payload = torch.load(checkpoint_path, map_location=device, weights_only=True)
    strict_result = reloaded.load_state_dict(payload["state_dict"], strict=True)
    checkpoint_reloaded = not strict_result.missing_keys and not strict_result.unexpected_keys

    heldout_occupancy, heldout_weights, heldout_mask_receipt = load_case(heldout_case)
    heldout_base = torch.where(heldout_occupancy, torch.tensor(2.0, device=device), torch.tensor(-2.0, device=device))
    root_mask = heldout_weights == 0

    def decode_once() -> tuple[torch.Tensor, str, trimesh.Trimesh]:
        with torch.no_grad():
            residual = reloaded(heldout_base, family_order.index(heldout_case["toothFamily"]))
            candidate = compose_crown_residual_logits(heldout_base, residual, heldout_weights)
        binary = (candidate[0, 0] >= 0).detach().cpu().numpy().astype(np.uint8)
        vertices, faces, _, _ = measure.marching_cubes(binary, level=0.5)
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        return candidate, tensor_sha256(candidate), mesh

    candidate_a, candidate_hash_a, mesh_a = decode_once()
    candidate_b, candidate_hash_b, mesh_b = decode_once()
    root_identical = tensor_sha256(candidate_a[root_mask]) == tensor_sha256(heldout_base[root_mask])
    mesh_path = run_root / "heldout-raw-mesh.ply"
    mesh_path.write_bytes(mesh_a.export(file_type="ply", encoding="binary"))
    checkpoint_sha256 = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    mesh_sha256 = hashlib.sha256(mesh_path.read_bytes()).hexdigest()
    checkpoint_volume.commit()

    passed = bool(
        checkpoint_reloaded
        and len(changed) > 0
        and all(item["finite"] for item in gradients.values())
        and root_identical
        and candidate_hash_a == candidate_hash_b
        and len(mesh_a.vertices) > 0 and len(mesh_a.faces) > 0
        and len(mesh_a.vertices) == len(mesh_b.vertices) and len(mesh_a.faces) == len(mesh_b.faces)
    )
    evidence = {
        "schemaVersion": 1, "valid": passed,
        "stage": "E14-G1-crown-refiner-exactly-one-step-v1",
        "optimizerSteps": 1, "learningRate": 1e-6,
        "g0EvidenceSha256": hashlib.sha256(g0_path.read_bytes()).hexdigest(),
        "trainCase": {"id": train_case["id"], "family": train_case["toothFamily"], "mask": train_mask_receipt[0]},
        "heldoutCase": {"id": heldout_case["id"], "family": heldout_case["toothFamily"], "mask": heldout_mask_receipt[0]},
        "loss": float(loss.detach().item()), "gradients": gradients,
        "trainableParameterCount": sum(parameter.numel() for parameter in refiner.parameters()),
        "changedParameterTensors": changed,
        "onlyRefinerParametersTrainable": True,
        "checkpointReloadedStrict": checkpoint_reloaded,
        "checkpointArtifact": str(checkpoint_path), "checkpointSha256": checkpoint_sha256,
        "rootLogitsByteIdentical": root_identical,
        "rawDecodeExactRepeat": candidate_hash_a == candidate_hash_b,
        "rawCandidateSha256": candidate_hash_a,
        "meshArtifact": str(mesh_path), "meshArtifactSha256": mesh_sha256,
        "vertexCount": int(len(mesh_a.vertices)), "faceCount": int(len(mesh_a.faces)),
        "g2Authorized": passed,
        "clinicalClaimPermitted": False, "productionMutationPermitted": False,
        "interpretation": "One-step integration proof only; G2 must test anatomical response on sealed base predictions.",
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    if not passed:
        raise RuntimeError("E14 G1 crown-refiner integration gate failed")
    return evidence


@app.function(
    image=trellis_gpu_image,
    volumes={"/datasets": dataset_volume, "/cache/huggingface": hf_cache_volume},
    secrets=[hf_secret],
    gpu="A100",
    cpu=8,
    memory=65536,
    timeout=90 * 60,
)
def materialize_e14_g2_frozen_base_support(
    dataset_name: str = "toothfairy-stage1-v1",
    cache_name: str = "stage1-e14-g2-frozen-base-support-v1",
) -> dict:
    """Cache fixed image-to-sparse base predictions for G2 without training."""
    import io
    import os
    import random
    import sys
    from collections import Counter

    import numpy as np
    import torch
    from PIL import Image

    if dataset_name != "toothfairy-stage1-v1" or cache_name != "stage1-e14-g2-frozen-base-support-v1":
        raise ValueError("E14 G2 base-support cache is sealed")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator

    root = Path(f"/datasets/{dataset_name}")
    cache_root = root / cache_name
    cache_root.mkdir(parents=True, exist_ok=True)
    evidence_path = cache_root / "cache-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True and existing.get("caseCount") == 76:
            return {**existing, "resumed": True}
        raise ValueError("Existing E14 G2 cache evidence is invalid")

    manifest_path = root / "anatomy_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    families = ("incisor", "canine", "premolar", "molar")
    train_targets = {"incisor": 10, "canine": 6, "premolar": 22, "molar": 26}
    selected = []
    train_group_counts = Counter()
    train_counts = Counter()
    for asset in sorted(manifest["assets"], key=lambda row: (row["canonicalSha256"], row["id"])):
        family = asset["toothFamily"]
        render_path = root / "renders_cond" / asset["canonicalSha256"] / "000.png"
        reference_path = root / "shape_latents/shape_enc_next_dc_f16c32_fp16_512" / f"{asset['canonicalSha256']}.npz"
        if asset["split"] != "train" or family not in families or train_counts[family] >= train_targets[family]:
            continue
        if train_group_counts[asset["groupId"]] >= 3 or not render_path.is_file() or not reference_path.is_file():
            continue
        selected.append((asset, render_path, reference_path, "train"))
        train_group_counts[asset["groupId"]] += 1
        train_counts[family] += 1
    if dict(train_counts) != train_targets or len(selected) != 64:
        raise RuntimeError(f"Could not build E14 G2 64-case training cohort: {dict(train_counts)}")

    validation_assets = [
        asset for asset in sorted(manifest["assets"], key=lambda row: (row["canonicalSha256"], row["id"]))
        if asset["split"] == "validation"
    ]
    for asset in validation_assets:
        render_path = root / "renders_cond" / asset["canonicalSha256"] / "000.png"
        reference_path = root / "shape_latents/shape_enc_next_dc_f16c32_fp16_512" / f"{asset['canonicalSha256']}.npz"
        if not render_path.is_file() or not reference_path.is_file():
            raise FileNotFoundError(f"Missing fixed E14 validation input for {asset['id']}")
        selected.append((asset, render_path, reference_path, "validation"))
    validation_counts = Counter(asset["toothFamily"] for asset in validation_assets)
    if validation_counts != Counter({family: 3 for family in families}) or len(validation_assets) != 12:
        raise RuntimeError(f"E14 G2 requires all sealed validation teeth: {dict(validation_counts)}")
    if {asset["groupId"] for asset, _, _, split in selected if split == "train"} & {
        asset["groupId"] for asset, _, _, split in selected if split == "validation"
    }:
        raise RuntimeError("E14 G2 train/validation patient leakage")

    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    generator = TrellisGenerator()
    generator.load_model()
    params = sampler_params_for_steps(int(get_quality_preset("standard")["steps"]))

    def array_sha256(array: np.ndarray) -> str:
        return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()

    receipts = []
    for index, (asset, render_path, reference_path, split) in enumerate(selected, start=1):
        case_path = cache_root / f"{asset['id']}.npz"
        receipt_path = cache_root / f"{asset['id']}.json"
        if case_path.is_file() and receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt.get("artifactSha256") != hashlib.sha256(case_path.read_bytes()).hexdigest():
                raise ValueError(f"E14 G2 cached case hash drift: {asset['id']}")
            receipts.append(receipt)
            print(f"E14 G2 cache resumed {index}/76: {asset['id']}", flush=True)
            continue
        if case_path.exists() or receipt_path.exists():
            raise ValueError(f"Incomplete E14 G2 cached case: {asset['id']}")
        seed = int(hashlib.sha256(f"e14-g2:{asset['id']}".encode()).hexdigest()[:8], 16)
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        image_bytes = render_path.read_bytes()
        image = Image.open(io.BytesIO(image_bytes)); image.load()
        processed = generator.pipeline.preprocess_image(image)
        cond_512 = generator.pipeline.get_cond([processed], 512)
        with torch.inference_mode():
            predicted = generator.pipeline.sample_sparse_structure(
                cond_512, 32, sampler_params=params["sparse_structure"]
            )
        predicted_coords = predicted.detach().cpu().contiguous().numpy().astype(np.int16)
        if predicted_coords.ndim != 2 or predicted_coords.shape[1] not in (3, 4):
            raise ValueError(f"Invalid predicted sparse coordinates for {asset['id']}: {predicted_coords.shape}")
        if predicted_coords.shape[1] == 4:
            predicted_coords = predicted_coords[:, 1:]
        packed = np.load(reference_path)
        reference_coords = np.asarray(packed["coords"], dtype=np.int16)
        if reference_coords.ndim != 2 or reference_coords.shape[1] != 3:
            raise ValueError(f"Invalid reference sparse coordinates for {asset['id']}")
        np.savez_compressed(case_path, base_coords=predicted_coords, reference_coords=reference_coords)
        receipt = {
            "schemaVersion": 1, "id": asset["id"], "groupId": asset["groupId"],
            "split": split, "toothFamily": asset["toothFamily"], "fdiNumber": asset["fdiNumber"],
            "generationSeed": seed, "inputImage": str(render_path.relative_to(root)).replace("\\", "/"),
            "inputImageSha256": hashlib.sha256(image_bytes).hexdigest(),
            "baseCoordinateCount": int(len(predicted_coords)), "baseCoordsSha256": array_sha256(predicted_coords),
            "referenceCoordinateCount": int(len(reference_coords)), "referenceCoordsSha256": array_sha256(reference_coords),
            "artifact": str(case_path.relative_to(root)).replace("\\", "/"),
            "artifactSha256": hashlib.sha256(case_path.read_bytes()).hexdigest(),
            "baseModelName": BASE_MODEL_NAME, "baseModelRevision": BASE_MODEL_REVISION,
            "trellisCommit": TRELLIS_COMMIT,
        }
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        receipts.append(receipt)
        dataset_volume.commit()
        del predicted, cond_512, processed, image
        torch.cuda.empty_cache()
        print(f"E14 G2 cache {index}/76 complete: {asset['id']}", flush=True)

    passed = bool(
        len(receipts) == 76
        and Counter(row["split"] for row in receipts) == Counter({"train": 64, "validation": 12})
        and Counter(row["toothFamily"] for row in receipts if row["split"] == "train") == Counter(train_targets)
        and Counter(row["toothFamily"] for row in receipts if row["split"] == "validation") == Counter({family: 3 for family in families})
        and all(row["baseCoordinateCount"] > 0 and row["referenceCoordinateCount"] > 0 for row in receipts)
    )
    evidence = {
        "schemaVersion": 1, "valid": passed,
        "stage": "E14-G2-frozen-base-support-cache-v1", "optimizerSteps": 0,
        "caseCount": len(receipts), "trainCaseCount": 64, "validationCaseCount": 12,
        "untouchedTestCaseCount": 24, "trainFamilyCounts": dict(train_counts),
        "validationFamilyCounts": dict(validation_counts),
        "trainPatientGroupCount": len({row["groupId"] for row in receipts if row["split"] == "train"}),
        "validationPatientGroupCount": len({row["groupId"] for row in receipts if row["split"] == "validation"}),
        "manifestSha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "cases": receipts, "g2TrainingAuthorized": passed,
        "clinicalClaimPermitted": False, "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    dataset_volume.commit()
    if not passed:
        raise RuntimeError("E14 G2 frozen-base cache gate failed")
    return evidence


@app.function(
    image=e14_training_image,
    volumes={"/datasets": dataset_volume, "/checkpoints": checkpoint_volume},
    gpu="T4",
    cpu=8,
    memory=32768,
    timeout=60 * 60,
)
def run_e14_g2_short_response(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e14-g2-short-response-v2",
) -> dict:
    """Run the sealed 100-step crown-only response experiment."""
    import numpy as np
    import torch
    import torch.nn.functional as F
    from collections import Counter, defaultdict
    from scipy import ndimage
    from scipy.spatial import cKDTree

    if dataset_name != "toothfairy-stage1-v1" or run_name != "stage1-e14-g2-short-response-v2":
        raise ValueError("E14 G2 short response is sealed")
    cache_path = Path(f"/datasets/{dataset_name}/stage1-e14-g2-frozen-base-support-v1/cache-evidence.json")
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if not (
        cache.get("valid") is True
        and cache.get("g2TrainingAuthorized") is True
        and cache.get("trainCaseCount") == 64
        and cache.get("validationCaseCount") == 12
        and cache.get("untouchedTestCaseCount") == 24
    ):
        raise ValueError("E14 G2 requires the sealed frozen-base cache")
    g1_path = Path("/checkpoints/stage1-e14-g1-crown-refiner-one-step-v3/g1-evidence.json")
    g1 = json.loads(g1_path.read_text(encoding="utf-8"))
    if not (g1.get("valid") is True and g1.get("g2Authorized") is True and g1.get("optimizerSteps") == 1):
        raise ValueError("E14 G2 requires the sealed passing G1 integration gate")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "g2-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Existing E14 G2 evidence is invalid")
    if run_root.exists():
        raise FileExistsError("Partial E14 G2 output exists; inspect before versioning")
    run_root.mkdir(parents=True, exist_ok=False)

    torch.manual_seed(20260922)
    torch.cuda.manual_seed_all(20260922)
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    family_order = ("incisor", "canine", "premolar", "molar")

    class CrownResidualRefiner(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.net = torch.nn.Sequential(
                torch.nn.Conv3d(8, 16, 3, padding=1), torch.nn.SiLU(),
                torch.nn.Conv3d(16, 16, 3, padding=1), torch.nn.SiLU(),
                torch.nn.Conv3d(16, 1, 1),
            )

        def forward(self, base_logits: torch.Tensor, family_index: int) -> torch.Tensor:
            batch, _, depth, height, width = base_logits.shape
            axes = [torch.linspace(-1, 1, size, device=base_logits.device, dtype=base_logits.dtype)
                    for size in (depth, height, width)]
            grid = torch.stack(torch.meshgrid(*axes, indexing="ij"), dim=0).expand(batch, -1, -1, -1, -1)
            family = torch.zeros((batch, 4, depth, height, width), device=base_logits.device, dtype=base_logits.dtype)
            family[:, family_index] = 1
            return 2.0 * torch.tanh(self.net(torch.cat((torch.sigmoid(base_logits), grid, family), dim=1)))

    def dense(coords: np.ndarray) -> torch.Tensor:
        values = np.asarray(coords, dtype=np.int64)
        if values.ndim != 2 or values.shape[1] != 3 or values.size == 0:
            raise ValueError(f"Invalid E14 G2 coordinates: {values.shape}")
        if values.min() < 0 or values.max() >= 32:
            raise ValueError("E14 G2 coordinates fall outside the sealed 32^3 grid")
        output = torch.zeros((1, 1, 32, 32, 32), dtype=torch.bool, device=device)
        output[0, 0, values[:, 0], values[:, 1], values[:, 2]] = True
        return output

    def load_case(row: dict) -> dict:
        artifact = Path(f"/datasets/{dataset_name}") / row["artifact"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != row["artifactSha256"]:
            raise ValueError(f"E14 G2 artifact hash drift: {row['id']}")
        packed = np.load(artifact)
        return {"receipt": row, "base": dense(packed["base_coords"]), "reference": dense(packed["reference_coords"])}

    training = [load_case(row) for row in cache["cases"] if row["split"] == "train"]
    validation = [load_case(row) for row in cache["cases"] if row["split"] == "validation"]
    if len(training) != 64 or len(validation) != 12:
        raise RuntimeError("E14 G2 cohort count drift")

    refiner = CrownResidualRefiner().to(device)
    g1_checkpoint = Path(g1["checkpointArtifact"])
    if hashlib.sha256(g1_checkpoint.read_bytes()).hexdigest() != g1["checkpointSha256"]:
        raise ValueError("E14 G1 checkpoint hash drift")
    payload = torch.load(g1_checkpoint, map_location=device, weights_only=True)
    strict = refiner.load_state_dict(payload["state_dict"], strict=True)
    if strict.missing_keys or strict.unexpected_keys:
        raise RuntimeError("E14 G2 could not strict-load the G1 refiner")
    optimizer = torch.optim.AdamW(refiner.parameters(), lr=0.001, weight_decay=0.0)

    def logits_and_weights(case: dict) -> tuple[torch.Tensor, torch.Tensor]:
        base = case["base"]
        weights, _ = build_crown_transition_weights_from_occupancy(base)
        base_logits = torch.where(base, torch.tensor(0.25, device=device), torch.tensor(-0.25, device=device))
        return base_logits, weights.to(device)

    def surface_chamfer(reference: np.ndarray, prediction: np.ndarray, region: np.ndarray) -> float:
        structure = np.ones((3, 3, 3), dtype=bool)
        reference_surface = reference & ~ndimage.binary_erosion(reference, structure=structure, border_value=0)
        prediction_surface = prediction & ~ndimage.binary_erosion(prediction, structure=structure, border_value=0)
        reference_points = np.argwhere(reference_surface & region)
        prediction_points = np.argwhere(prediction_surface & region)
        if len(reference_points) == 0 or len(prediction_points) == 0:
            return float("inf")
        ref_tree, pred_tree = cKDTree(reference_points), cKDTree(prediction_points)
        return float((pred_tree.query(reference_points)[0].mean() + ref_tree.query(prediction_points)[0].mean()) / 2.0)

    def topology(binary: np.ndarray) -> dict:
        labels, count = ndimage.label(binary, structure=ndimage.generate_binary_structure(3, 1))
        sizes = np.bincount(labels.ravel())[1:]
        total = int(binary.sum())
        return {
            "componentCount": int(count),
            "largestComponentFraction": float(sizes.max() / total) if total and len(sizes) else 0.0,
        }

    def evaluate(step: int) -> dict:
        refiner.eval()
        cases = []
        with torch.no_grad():
            for case in validation:
                row = case["receipt"]
                base_logits, weights = logits_and_weights(case)
                residual = refiner(base_logits, family_order.index(row["toothFamily"]))
                candidate_logits = compose_crown_residual_logits(base_logits, residual, weights)
                repeated_logits = compose_crown_residual_logits(
                    base_logits, refiner(base_logits, family_order.index(row["toothFamily"])), weights
                )
                root_mask = weights == 0
                root_identical = (
                    candidate_logits[root_mask].detach().cpu().contiguous().numpy().tobytes()
                    == base_logits[root_mask].detach().cpu().contiguous().numpy().tobytes()
                )
                repeat_exact = (
                    candidate_logits.detach().cpu().contiguous().numpy().tobytes()
                    == repeated_logits.detach().cpu().contiguous().numpy().tobytes()
                )
                base_binary = case["base"][0, 0].cpu().numpy()
                reference_binary = case["reference"][0, 0].cpu().numpy()
                candidate_binary = (candidate_logits[0, 0] >= 0).cpu().numpy()
                crown_region = (weights[0, 0] > 0).cpu().numpy()
                base_chamfer = surface_chamfer(reference_binary, base_binary, crown_region)
                candidate_chamfer = surface_chamfer(reference_binary, candidate_binary, crown_region)
                relative = (base_chamfer - candidate_chamfer) / max(base_chamfer, 1e-8)
                base_topology, candidate_topology = topology(base_binary), topology(candidate_binary)
                topology_passed = (
                    candidate_topology["componentCount"] <= base_topology["componentCount"]
                    and candidate_topology["largestComponentFraction"] >= base_topology["largestComponentFraction"] - 0.01
                )
                cases.append({
                    "id": row["id"], "groupId": row["groupId"], "toothFamily": row["toothFamily"],
                    "baseCrownChamferVoxels": base_chamfer,
                    "candidateCrownChamferVoxels": candidate_chamfer,
                    "crownChamferRelativeImprovement": relative,
                    "changedVoxelCount": int(np.count_nonzero(candidate_binary != base_binary)),
                    "rootLogitsByteIdentical": root_identical, "rawDecodeExactRepeat": repeat_exact,
                    "baseTopology": base_topology, "candidateTopology": candidate_topology,
                    "topologyPassed": topology_passed,
                })
        family_medians = {}
        for family in family_order:
            values = [row["crownChamferRelativeImprovement"] for row in cases if row["toothFamily"] == family]
            family_medians[family] = float(np.median(values))
        summary = {
            "step": step, "caseCount": len(cases), "cases": cases,
            "medianCrownChamferRelativeImprovement": float(np.median([row["crownChamferRelativeImprovement"] for row in cases])),
            "familyMedianCrownChamferRelativeImprovement": family_medians,
            "allRootLogitsByteIdentical": all(row["rootLogitsByteIdentical"] for row in cases),
            "allRawDecodesExactRepeat": all(row["rawDecodeExactRepeat"] for row in cases),
            "allTopologyPassed": all(row["topologyPassed"] for row in cases),
        }
        (run_root / f"evaluation-step-{step:03d}.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        checkpoint_volume.commit()
        return summary

    evaluations = [evaluate(0)]
    losses = []
    for step in range(1, 101):
        refiner.train()
        case = training[(step - 1) % len(training)]
        row = case["receipt"]
        base_logits, weights = logits_and_weights(case)
        residual = refiner(base_logits, family_order.index(row["toothFamily"]))
        candidate_logits = compose_crown_residual_logits(base_logits, residual, weights)
        target = case["reference"].float()
        supervised = weights > 0
        bce = F.binary_cross_entropy_with_logits(candidate_logits[supervised], target[supervised])
        probabilities = torch.sigmoid(candidate_logits) * weights
        weighted_target = target * weights
        dice = 1.0 - (2.0 * (probabilities * weighted_target).sum() + 1.0) / (
            probabilities.sum() + weighted_target.sum() + 1.0
        )
        loss = bce + 0.5 * dice
        if not torch.isfinite(loss):
            raise RuntimeError(f"E14 G2 non-finite loss at step {step}")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if not all(parameter.grad is not None and torch.isfinite(parameter.grad).all() for parameter in refiner.parameters()):
            raise RuntimeError(f"E14 G2 gradient gate failed at step {step}")
        optimizer.step()
        losses.append({"step": step, "loss": float(loss.detach().item()), "bce": float(bce.detach().item()), "dice": float(dice.detach().item())})
        if step % 25 == 0:
            evaluations.append(evaluate(step))

    final = evaluations[-1]
    family = final["familyMedianCrownChamferRelativeImprovement"]
    passed = bool(
        len(evaluations) == 5
        and final["medianCrownChamferRelativeImprovement"] > 0.0
        and family["premolar"] > 0.0 and family["molar"] > 0.0
        and all(value >= -0.005 for value in family.values())
        and final["allRootLogitsByteIdentical"]
        and final["allRawDecodesExactRepeat"]
        and final["allTopologyPassed"]
    )
    checkpoint_path = run_root / "crown-refiner-step-100.pt"
    torch.save({"state_dict": refiner.state_dict(), "familyOrder": family_order, "optimizerSteps": 100}, checkpoint_path)
    verification = CrownResidualRefiner().to(device)
    strict = verification.load_state_dict(torch.load(checkpoint_path, map_location=device, weights_only=True)["state_dict"], strict=True)
    checkpoint_reloaded = not strict.missing_keys and not strict.unexpected_keys
    passed = passed and checkpoint_reloaded
    evidence = {
        "schemaVersion": 1, "valid": True,
        "stage": "E14-G2-100-step-short-response-v1", "optimizerSteps": 100,
        "learningRate": 0.001, "evaluationSteps": [row["step"] for row in evaluations],
        "cacheEvidenceSha256": hashlib.sha256(cache_path.read_bytes()).hexdigest(),
        "g1EvidenceSha256": hashlib.sha256(g1_path.read_bytes()).hexdigest(),
        "trainCaseCount": 64, "validationCaseCount": 12, "untouchedTestCaseCount": 24,
        "losses": losses, "evaluations": evaluations,
        "checkpointReloadedStrict": checkpoint_reloaded,
        "checkpointArtifact": str(checkpoint_path),
        "checkpointSha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "summaryPassed": passed, "g3Authorized": passed,
        "clinicalClaimPermitted": False, "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def run_r05a_integrated_regional_objective_zero_step(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "stage1-r05a-integrated-regional-zero-step-v3",
) -> dict:
    """Prove the decoded dental objective on the real model without an update."""
    import os
    from huggingface_hub import hf_hub_download

    if dataset_name != "toothfairy-tf-pw32-v1" or run_name != "stage1-r05a-integrated-regional-zero-step-v3":
        raise ValueError("R0.5A integrated objective gate is sealed")
    r04_path = Path("/datasets/toothfairy-stage1-v1/stage_attribution_r04_objective_v1.json")
    r04d_path = Path("/checkpoints/stage1-r04c-sparse-adapter-one-step-v1/r04d-evidence.json")
    r04 = json.loads(r04_path.read_text(encoding="utf-8"))
    r04d = json.loads(r04d_path.read_text(encoding="utf-8"))
    if r04.get("modelIntegrationAuthorized") is not True:
        raise ValueError("R0.5A requires the qualified regional objective")
    if (
        r04d.get("valid") is not True
        or r04d.get("boundedTrainingAuthorized") is not False
        or r04d.get("optimizerSteps") != 0
    ):
        raise ValueError("R0.5A requires the sealed rejected R0.4D screen")
    anchor_path = Path(f"/datasets/{dataset_name}/sparse_anchor_v1/receipt.json")
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    if anchor.get("valid") is not True or anchor.get("assetCount") != 8:
        raise ValueError("R0.5A requires the sealed balanced eight-asset anchor")

    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "r05a-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Invalid existing R0.5A evidence")
    if run_root.exists():
        raise FileExistsError("Partial R0.5A run exists; inspect before versioning")
    run_root.mkdir(parents=True, exist_ok=False)

    files = {suffix: hf_hub_download(
        BASE_MODEL_NAME, f"{BASE_SPARSE_FLOW_FILE}.{suffix}", revision=BASE_MODEL_REVISION,
    ) for suffix in ("json", "safetensors")}
    trainer_checkpoint = materialize_trainer_checkpoint(files["safetensors"], run_root / "base-denoiser.pt")
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")), trainer_checkpoint,
        max_steps=1, save_interval=101, log_interval=1,
    )
    args = config["trainer"]["args"]
    args["mix_precision_mode"] = "amp"
    args["mix_precision_dtype"] = "bfloat16"
    args["i_sample"] = 101
    (run_root / "dentalsculptor_sparse_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8",
    )
    command = sparse_anchor_training_command(dataset_name, run_name)
    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    sparse_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/sparse_flow_matching.py"
    originals = {path: path.read_text(encoding="utf-8") for path in (basic_path, flow_path, sparse_path)}
    receipt_path = run_root / "zero-step-receipt.json"
    try:
        patched_basic = sparse_flow_trainer_source_with_derived_rope_buffer(originals[basic_path])
        patched_basic = smoke_trainer_source_without_snapshots(patched_basic)
        basic_path.write_text(r05a_basic_zero_step_probe_source(patched_basic), encoding="utf-8")
        patched_flow = r05a_install_adapter_flow_source(originals[flow_path])
        patched_flow = r05a_regional_objective_sparse_loss_source(patched_flow)
        flow_path.write_text(patched_flow, encoding="utf-8")
        sparse_path.write_text(originals[sparse_path], encoding="utf-8")
        env = os.environ.copy()
        env["DENTALSCULPTOR_R05A_RECEIPT"] = str(receipt_path)
        process = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
        )
    finally:
        for path, source in originals.items():
            path.write_text(source, encoding="utf-8")
    (run_root / "probe.log").write_text(process.stdout, encoding="utf-8")
    print(process.stdout, flush=True)
    marker = "DENTALSCULPTOR_R05A_ZERO_STEP_COMPLETE"
    if marker not in process.stdout or not receipt_path.is_file():
        checkpoint_volume.commit()
        raise RuntimeError(f"R0.5A stopped before sealed evidence (code {process.returncode})")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    objective = receipt.get("objective", {})
    adapter_gradients = receipt.get("adapterGradients", [])
    components = objective.get("componentGradients", {})
    required_components = ("nativeMse", "crownPositiveBce", "crownExtraBce", "nonCrownTeacherProbe")
    component_pass = all(
        name in components
        and any(
            row.get("finite") is True and float(row.get("norm") or 0.0) > 0.0
            for row in components[name]
        )
        for name in required_components
    )
    finite_terms = all(
        math.isfinite(float(objective.get(name)))
        for name in ("nativeMse", "crownPositiveBce", "crownExtraBce", "nonCrownTeacherMse", "nonCrownTeacherProbe", "totalLoss")
    )
    passed = (
        receipt.get("optimizerSteps") == 0
        and receipt.get("frozenStateByteIdentical") is True
        and len(adapter_gradients) == 2
        and all(row.get("finite") is True and float(row.get("norm") or 0.0) > 0.0 for row in adapter_gradients)
        and finite_terms
        and component_pass
        and int(objective.get("crownPositiveVoxelCount", 0)) > 0
        and int(objective.get("extraCrownVoxelCount", 0)) > 0
        and int(objective.get("nonCrownVoxelCount", 0)) > 0
        and abs(float(objective.get("nonCrownTeacherMse", math.inf))) <= 1e-12
    )
    evidence = {
        "schemaVersion": 1, "valid": passed,
        "stage": "R0.5A-real-model-integrated-regional-objective-zero-step-v3",
        "optimizerSteps": 0,
        "r04ObjectiveSha256": hashlib.sha256(r04_path.read_bytes()).hexdigest(),
        "rejectedR04dSha256": hashlib.sha256(r04d_path.read_bytes()).hexdigest(),
        "anchorReceiptSha256": hashlib.sha256(anchor_path.read_bytes()).hexdigest(),
        "receipt": receipt,
        "finiteObjectiveTerms": finite_terms,
        "everyRequiredComponentHasFiniteNonzeroAdapterInfluence": component_pass,
        "correctedOneStepAuthorized": passed,
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    if not passed:
        raise RuntimeError("R0.5A integrated objective gate failed")
    return evidence


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def run_r05b_regional_objective_one_step(
    dataset_name: str = "toothfairy-tf-pw32-v1",
    run_name: str = "stage1-r05b-regional-objective-one-step-v1",
) -> dict:
    """Execute one qualified regional-objective adapter update and integration gate."""
    import os
    import sys
    import torch
    from huggingface_hub import hf_hub_download

    if dataset_name != "toothfairy-tf-pw32-v1" or run_name != "stage1-r05b-regional-objective-one-step-v1":
        raise ValueError("R0.5B one-step gate is sealed")
    zero_path = Path("/checkpoints/stage1-r05a-integrated-regional-zero-step-v3/r05a-evidence.json")
    zero = json.loads(zero_path.read_text(encoding="utf-8"))
    if zero.get("correctedOneStepAuthorized") is not True or zero.get("optimizerSteps") != 0:
        raise ValueError("R0.5B requires sealed passing R0.5A v3 evidence")
    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "r05b-evidence.json"
    if evidence_path.is_file():
        existing = json.loads(evidence_path.read_text(encoding="utf-8"))
        if existing.get("valid") is True:
            return {**existing, "resumed": True}
        raise ValueError("Invalid existing R0.5B evidence")
    if run_root.exists():
        raise FileExistsError("Partial R0.5B run exists; inspect before versioning")
    run_root.mkdir(parents=True, exist_ok=False)

    files = {suffix: hf_hub_download(
        BASE_MODEL_NAME, f"{BASE_SPARSE_FLOW_FILE}.{suffix}", revision=BASE_MODEL_REVISION,
    ) for suffix in ("json", "safetensors")}
    trainer_checkpoint = materialize_trainer_checkpoint(files["safetensors"], run_root / "base-denoiser.pt")
    official = Path(TRELLIS2_PATH) / "configs/gen/ss_flow_img_dit_1_3B_64_bf16.json"
    config = build_finetune_config(
        json.loads(official.read_text(encoding="utf-8")), trainer_checkpoint,
        max_steps=1, save_interval=101, log_interval=1,
    )
    args = config["trainer"]["args"]
    args["mix_precision_mode"] = "amp"
    args["mix_precision_dtype"] = "bfloat16"
    args["i_sample"] = 101
    (run_root / "dentalsculptor_sparse_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8",
    )
    command = sparse_anchor_training_command(dataset_name, run_name)
    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    flow_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/flow_matching.py"
    sparse_path = Path(TRELLIS2_PATH) / "trellis2/trainers/flow_matching/sparse_flow_matching.py"
    originals = {path: path.read_text(encoding="utf-8") for path in (basic_path, flow_path, sparse_path)}
    receipt_path = run_root / "one-step-receipt.json"
    candidate_path = run_root / "candidate-sparse-flow-merged.pt"
    try:
        patched_basic = sparse_flow_trainer_source_with_derived_rope_buffer(originals[basic_path])
        patched_basic = smoke_trainer_source_without_snapshots(patched_basic)
        basic_path.write_text(r05b_basic_one_step_probe_source(patched_basic), encoding="utf-8")
        patched_flow = r05b_install_trainable_adapter_flow_source(originals[flow_path])
        patched_flow = r05a_regional_objective_sparse_loss_source(patched_flow)
        flow_path.write_text(patched_flow, encoding="utf-8")
        sparse_path.write_text(originals[sparse_path], encoding="utf-8")
        env = os.environ.copy()
        env["DENTALSCULPTOR_R05B_RECEIPT"] = str(receipt_path)
        env["DENTALSCULPTOR_R05B_CHECKPOINT"] = str(candidate_path)
        process = subprocess.run(
            command, cwd=TRELLIS2_PATH, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
        )
    finally:
        for path, source in originals.items():
            path.write_text(source, encoding="utf-8")
    (run_root / "training.log").write_text(process.stdout, encoding="utf-8")
    print(process.stdout, flush=True)
    marker = "DENTALSCULPTOR_R05B_ONE_STEP_COMPLETE"
    if marker not in process.stdout or not receipt_path.is_file() or not candidate_path.is_file():
        checkpoint_volume.commit()
        raise RuntimeError(f"R0.5B stopped before sealed one-step evidence (code {process.returncode})")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    gradients = receipt.get("adapterGradients", [])
    deltas = receipt.get("adapterDeltas", [])
    objective = receipt.get("objective", {})
    engineering_pass = (
        receipt.get("optimizerSteps") == 1
        and receipt.get("frozenStateByteIdentical") is True
        and len(gradients) == 2
        and all(row.get("finite") is True and float(row.get("norm") or 0.0) > 0.0 for row in gradients)
        and len(deltas) == 2
        and all(row.get("finite") is True and float(row.get("norm") or 0.0) > 0.0 for row in deltas)
        and int(objective.get("crownPositiveVoxelCount", 0)) > 0
        and int(objective.get("extraCrownVoxelCount", 0)) > 0
        and int(objective.get("nonCrownVoxelCount", 0)) > 0
        and abs(float(objective.get("nonCrownTeacherMse", math.inf))) <= 1e-12
    )
    if not engineering_pass:
        checkpoint_volume.commit()
        raise RuntimeError("R0.5B regional adapter update contract failed")

    os.environ["TRELLIS_ENABLE_WARMUP"] = "false"
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    sys.path.insert(0, "/root")
    from modal_app.workers.trellis_generator import TrellisGenerator

    generator = TrellisGenerator()
    generator.load_model()
    checkpoint_receipt = generator.load_sparse_structure_checkpoint(str(candidate_path))
    validation = json.loads(Path("/datasets/toothfairy-stage1-v1/stage1_validation_inputs_v1.json").read_text(encoding="utf-8"))
    case = validation["cases"][0]
    image_bytes = (Path("/datasets/toothfairy-stage1-v1") / case["inputImage"]).read_bytes()
    first = generator.run_inference(image_bytes, quality="preview", seed=int(case["generationSeed"]), content_type=None)
    first_bytes = first.serialize()
    second = generator.run_inference(image_bytes, quality="preview", seed=int(case["generationSeed"]), content_type=None)
    second_bytes = second.serialize()
    vertex_count = int(first.mesh.vertices.shape[0])
    face_count = int(first.mesh.faces.shape[0])
    exact_repeat = hashlib.sha256(first_bytes).hexdigest() == hashlib.sha256(second_bytes).hexdigest()
    passed = (
        engineering_pass
        and checkpoint_receipt.get("strictLoad") is True
        and exact_repeat
        and vertex_count > 0
        and face_count > 0
    )
    evidence = {
        "schemaVersion": 1,
        "valid": passed,
        "stage": "R0.5B-regional-objective-one-step-integration-v1",
        "optimizerSteps": 1,
        "zeroStepEvidenceSha256": hashlib.sha256(zero_path.read_bytes()).hexdigest(),
        "receipt": receipt,
        "checkpointReloaded": checkpoint_receipt.get("strictLoad") is True,
        "candidateCheckpoint": checkpoint_receipt,
        "heldoutCaseId": case["id"],
        "rawDecodeExactRepeat": exact_repeat,
        "rawMeshVertexCount": vertex_count,
        "rawMeshFaceCount": face_count,
        "fourFamilyScreenAuthorized": passed,
        "clinicalClaimPermitted": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    if not passed:
        raise RuntimeError("R0.5B one-step integration gate failed")
    return evidence


@app.function(
    image=e12_training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def diagnose_e12_component_gradients(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e12-g1-gradient-diagnostic-v1",
    experiment_seed: int = 20260920,
) -> dict:
    """Zero-step, term-by-term decoder gradient diagnostic for E12."""
    import os
    import subprocess

    from huggingface_hub import hf_hub_download

    if (
        dataset_name != "toothfairy-stage1-v1"
        or run_name != "stage1-e12-g1-gradient-diagnostic-v1"
        or experiment_seed != 20260920
    ):
        raise ValueError("E12 gradient diagnostic is sealed")
    view = Path(f"/datasets/{dataset_name}/e12_g1_one_tooth_v6")
    view_receipt_path = view / "receipt.json"
    if not view_receipt_path.is_file():
        raise FileNotFoundError("Sealed E12 one-tooth view is missing")
    view_receipt = json.loads(view_receipt_path.read_text(encoding="utf-8"))
    if view_receipt.get("valid") is not True or view_receipt.get("assetCount") != 1:
        raise ValueError("Sealed E12 one-tooth view is invalid")

    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "gradient-diagnostic-evidence.json"
    if evidence_path.is_file():
        return {**json.loads(evidence_path.read_text(encoding="utf-8")), "resumed": True}
    if run_root.exists():
        raise FileExistsError("Partial E12 gradient diagnostic exists; diagnose before retry")
    run_root.mkdir(parents=True, exist_ok=False)

    base_paths = {}
    for role, name in {
        "encoder": "ckpts/shape_enc_next_dc_f16c32_fp16",
        "decoder": "ckpts/shape_dec_next_dc_f16c32_fp16",
    }.items():
        source = hf_hub_download(
            BASE_MODEL_NAME, f"{name}.safetensors", revision=BASE_MODEL_REVISION
        )
        base_paths[role] = materialize_trainer_checkpoint(
            source, run_root / f"base-{role}.pt"
        )
    official = Path(TRELLIS2_PATH) / "configs/scvae/shape_vae_next_dc_f16c32_fp16_ft_512.json"
    config = build_e12_shape_vae_config(
        json.loads(official.read_text(encoding="utf-8")),
        base_paths["encoder"], base_paths["decoder"],
    )
    config["experimentSeed"] = experiment_seed
    config_path = run_root / "dentalsculptor_e12_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    shape_path = Path(TRELLIS2_PATH) / "trellis2/trainers/vae/shape_vae.py"
    entry_path = Path(TRELLIS2_PATH) / "train.py"
    basic_original = basic_path.read_text(encoding="utf-8")
    shape_original = shape_path.read_text(encoding="utf-8")
    entry_original = entry_path.read_text(encoding="utf-8")
    diagnostic_receipt = run_root / "component-gradient-receipt.json"
    objective_receipt = run_root / "objective-receipt.jsonl"
    try:
        basic_path.write_text(
            smoke_trainer_source_without_snapshots(basic_original), encoding="utf-8"
        )
        patched_shape = e12_decoder_only_shape_vae_source(shape_original)
        shape_path.write_text(
            e12_component_gradient_diagnostic_source(patched_shape), encoding="utf-8"
        )
        entry_path.write_text(
            training_entry_source_with_experiment_seed(entry_original, experiment_seed),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["DENTALSCULPTOR_E12_OBJECTIVE_RECEIPT"] = str(objective_receipt)
        env["DENTALSCULPTOR_E12_COMPONENT_GRADIENT_RECEIPT"] = str(diagnostic_receipt)
        process = subprocess.run(
            e12_gradient_diagnostic_command(dataset_name, run_name),
            cwd=TRELLIS2_PATH,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
        shape_path.write_text(shape_original, encoding="utf-8")
        entry_path.write_text(entry_original, encoding="utf-8")
    (run_root / "diagnostic.log").write_text(process.stdout, encoding="utf-8")
    print(process.stdout, flush=True)
    marker = "DENTALSCULPTOR_E12_COMPONENT_DIAGNOSTIC_COMPLETE_ZERO_STEP"
    if marker not in process.stdout or not diagnostic_receipt.is_file():
        checkpoint_volume.commit()
        raise RuntimeError(
            f"E12 component diagnostic failed before its sealed stop (code {process.returncode})"
        )
    diagnostic = json.loads(diagnostic_receipt.read_text(encoding="utf-8"))
    components = diagnostic.get("components", [])
    if (
        diagnostic.get("valid") is not True
        or diagnostic.get("optimizerSteps") != 0
        or not components
        or components[-1].get("component") != "loss"
    ):
        raise RuntimeError("E12 component diagnostic receipt is invalid")
    failing = [
        item["component"] for item in components
        if int(item.get("nonfiniteGradientCount", 0)) > 0
    ]
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E12-zero-step-component-gradient-diagnostic",
        "runName": run_name,
        "optimizerSteps": 0,
        "precisionConfig": {
            "sourceConfig": official.name,
            "modelFamily": "shape_dec_next_dc_f16c32_fp16",
            "gradientMode": "unscaled torch.autograd.grad inside official forward precision",
        },
        "diagnostic": diagnostic,
        "componentsWithNonfiniteGradients": failing,
        "fullLossGradientsFinite": components[-1].get("nonfiniteGradientCount") == 0,
        "g1v7Authorized": False,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=e12_training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def diagnose_e12_controlled_scale_backward(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e12-g1-controlled-scale12-v1",
    experiment_seed: int = 20260920,
) -> dict:
    """Run normal scale-12 backward and stop before clipping or optimization."""
    import os
    import subprocess

    from huggingface_hub import hf_hub_download

    if (
        dataset_name != "toothfairy-stage1-v1"
        or run_name != "stage1-e12-g1-controlled-scale12-v1"
        or experiment_seed != 20260920
    ):
        raise ValueError("E12 controlled-scale diagnostic is sealed")
    view = Path(f"/datasets/{dataset_name}/e12_g1_one_tooth_v6")
    view_receipt_path = view / "receipt.json"
    if not view_receipt_path.is_file():
        raise FileNotFoundError("Sealed E12 one-tooth view is missing")
    view_receipt = json.loads(view_receipt_path.read_text(encoding="utf-8"))
    if view_receipt.get("valid") is not True or view_receipt.get("assetCount") != 1:
        raise ValueError("Sealed E12 one-tooth view is invalid")

    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "controlled-scale-evidence.json"
    if evidence_path.is_file():
        return {**json.loads(evidence_path.read_text(encoding="utf-8")), "resumed": True}
    if run_root.exists():
        raise FileExistsError("Partial E12 controlled-scale run exists; diagnose before retry")
    run_root.mkdir(parents=True, exist_ok=False)

    base_paths = {}
    for role, name in {
        "encoder": "ckpts/shape_enc_next_dc_f16c32_fp16",
        "decoder": "ckpts/shape_dec_next_dc_f16c32_fp16",
    }.items():
        source = hf_hub_download(
            BASE_MODEL_NAME, f"{name}.safetensors", revision=BASE_MODEL_REVISION
        )
        base_paths[role] = materialize_trainer_checkpoint(
            source, run_root / f"base-{role}.pt"
        )
    official = Path(TRELLIS2_PATH) / "configs/scvae/shape_vae_next_dc_f16c32_fp16_ft_512.json"
    config = build_e12_shape_vae_config(
        json.loads(official.read_text(encoding="utf-8")),
        base_paths["encoder"], base_paths["decoder"],
    )
    config["experimentSeed"] = experiment_seed
    (run_root / "dentalsculptor_e12_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )

    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    shape_path = Path(TRELLIS2_PATH) / "trellis2/trainers/vae/shape_vae.py"
    entry_path = Path(TRELLIS2_PATH) / "train.py"
    basic_original = basic_path.read_text(encoding="utf-8")
    shape_original = shape_path.read_text(encoding="utf-8")
    entry_original = entry_path.read_text(encoding="utf-8")
    controlled_receipt = run_root / "controlled-scale-receipt.json"
    objective_receipt = run_root / "objective-receipt.jsonl"
    try:
        basic_path.write_text(
            e12_controlled_scale_zero_step_source(
                smoke_trainer_source_without_snapshots(basic_original), log_scale=12
            ),
            encoding="utf-8",
        )
        shape_path.write_text(
            e12_decoder_only_shape_vae_source(shape_original), encoding="utf-8"
        )
        entry_path.write_text(
            training_entry_source_with_experiment_seed(entry_original, experiment_seed),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["DENTALSCULPTOR_E12_OBJECTIVE_RECEIPT"] = str(objective_receipt)
        env["DENTALSCULPTOR_E12_CONTROLLED_SCALE_RECEIPT"] = str(controlled_receipt)
        process = subprocess.run(
            e12_controlled_scale_command(dataset_name, run_name),
            cwd=TRELLIS2_PATH,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
        shape_path.write_text(shape_original, encoding="utf-8")
        entry_path.write_text(entry_original, encoding="utf-8")
    (run_root / "diagnostic.log").write_text(process.stdout, encoding="utf-8")
    print(process.stdout, flush=True)
    marker = "DENTALSCULPTOR_E12_CONTROLLED_SCALE_COMPLETE_ZERO_STEP"
    if marker not in process.stdout or not controlled_receipt.is_file():
        checkpoint_volume.commit()
        raise RuntimeError(
            f"E12 controlled-scale diagnostic failed before sealed stop (code {process.returncode})"
        )
    receipt = json.loads(controlled_receipt.read_text(encoding="utf-8"))
    finite_complete = (
        receipt.get("valid") is True
        and receipt.get("optimizerSteps") == 0
        and receipt.get("logScale") == 12.0
        and receipt.get("missingGradientCount") == 0
        and receipt.get("nonfiniteGradientCount") == 0
        and receipt.get("allZeroGradientCount") == 0
    )
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E12-zero-step-controlled-scale-backward",
        "runName": run_name,
        "optimizerSteps": 0,
        "receipt": receipt,
        "finiteCompleteBackward": finite_complete,
        "g1v7Authorized": finite_complete,
        "productionMutationPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=e12_training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    memory=65536,
    timeout=2 * 60 * 60,
)
def diagnose_e15_regional_decoder_objective(
    dataset_name: str = "toothfairy-stage1-v1",
    run_name: str = "stage1-e15-regional-decoder-zero-step-v2",
    experiment_seed: int = 20260924,
) -> dict:
    """Zero-step crown-gradient/root-preservation gate for the late decoder."""
    import os
    import subprocess

    from huggingface_hub import hf_hub_download

    if (
        dataset_name != "toothfairy-stage1-v1"
        or run_name != "stage1-e15-regional-decoder-zero-step-v2"
        or experiment_seed != 20260924
    ):
        raise ValueError("E15 regional decoder diagnostic is sealed")
    view = Path(f"/datasets/{dataset_name}/e12_g1_one_tooth_v6")
    view_receipt = json.loads((view / "receipt.json").read_text(encoding="utf-8"))
    if view_receipt.get("valid") is not True or view_receipt.get("assetCount") != 1:
        raise ValueError("E15 requires the sealed E12 one-tooth geometry view")

    run_root = Path(f"/checkpoints/{run_name}")
    evidence_path = run_root / "e15-evidence.json"
    if evidence_path.is_file():
        return {**json.loads(evidence_path.read_text(encoding="utf-8")), "resumed": True}
    if run_root.exists():
        raise FileExistsError("Partial E15 zero-step run exists; diagnose before retry")
    run_root.mkdir(parents=True, exist_ok=False)

    base_paths = {}
    for role, name in {
        "encoder": "ckpts/shape_enc_next_dc_f16c32_fp16",
        "decoder": "ckpts/shape_dec_next_dc_f16c32_fp16",
    }.items():
        source = hf_hub_download(
            BASE_MODEL_NAME, f"{name}.safetensors", revision=BASE_MODEL_REVISION
        )
        base_paths[role] = materialize_trainer_checkpoint(
            source, run_root / f"base-{role}.pt"
        )
    official = Path(TRELLIS2_PATH) / "configs/scvae/shape_vae_next_dc_f16c32_fp16_ft_512.json"
    config = build_e12_shape_vae_config(
        json.loads(official.read_text(encoding="utf-8")),
        base_paths["encoder"], base_paths["decoder"],
    )
    config["experimentSeed"] = experiment_seed
    config["experimentId"] = "stage1-e15-regional-decoder-zero-step-v2"
    (run_root / "dentalsculptor_e15_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )

    basic_path = Path(TRELLIS2_PATH) / "trellis2/trainers/basic.py"
    shape_path = Path(TRELLIS2_PATH) / "trellis2/trainers/vae/shape_vae.py"
    entry_path = Path(TRELLIS2_PATH) / "train.py"
    basic_original = basic_path.read_text(encoding="utf-8")
    shape_original = shape_path.read_text(encoding="utf-8")
    entry_original = entry_path.read_text(encoding="utf-8")
    receipt_path = run_root / "zero-step-receipt.json"
    try:
        basic_path.write_text(
            smoke_trainer_source_without_snapshots(basic_original), encoding="utf-8"
        )
        shape_path.write_text(
            e15_regional_decoder_zero_step_source(shape_original), encoding="utf-8"
        )
        entry_path.write_text(
            training_entry_source_with_experiment_seed(entry_original, experiment_seed),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["DENTALSCULPTOR_E15_ZERO_STEP_RECEIPT"] = str(receipt_path)
        process = subprocess.run(
            e15_regional_decoder_command(dataset_name, run_name),
            cwd=TRELLIS2_PATH,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
    finally:
        basic_path.write_text(basic_original, encoding="utf-8")
        shape_path.write_text(shape_original, encoding="utf-8")
        entry_path.write_text(entry_original, encoding="utf-8")
    (run_root / "diagnostic.log").write_text(process.stdout, encoding="utf-8")
    print(process.stdout, flush=True)
    marker = "DENTALSCULPTOR_E15_REGIONAL_DECODER_ZERO_STEP_COMPLETE"
    if marker not in process.stdout or not receipt_path.is_file():
        checkpoint_volume.commit()
        raise RuntimeError(
            f"E15 regional diagnostic failed before sealed stop (code {process.returncode})"
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    components = {row["name"]: row for row in receipt.get("components", [])}
    tensor_count = int(receipt.get("trainableParameterTensorCount", 0))
    teacher = components.get("protectedTeacher", {})
    crown = components.get("crownObjective", {})
    probe = components.get("protectedProbe", {})
    total = components.get("totalLoss", {})
    authorized = bool(
        receipt.get("valid") is True
        and receipt.get("optimizerSteps") == 0
        and tensor_count > 0
        and all(int(value) > 0 for value in receipt.get("regionCounts", {}).values())
        and abs(float(teacher.get("value", float("inf")))) <= 1e-12
        and int(teacher.get("nonzeroGradientTensorCount", -1)) == 0
        and not crown.get("missingGradientNames")
        and not crown.get("nonfiniteGradientNames")
        and int(crown.get("nonzeroGradientTensorCount", 0)) == tensor_count
        and not probe.get("missingGradientNames")
        and not probe.get("nonfiniteGradientNames")
        and int(probe.get("nonzeroGradientTensorCount", 0)) == tensor_count
        and not total.get("missingGradientNames")
        and not total.get("nonfiniteGradientNames")
        and int(total.get("nonzeroGradientTensorCount", 0)) == tensor_count
    )
    evidence = {
        "schemaVersion": 1,
        "valid": True,
        "stage": "E15-regional-decoder-zero-step-v1",
        "runName": run_name,
        "optimizerSteps": 0,
        "receipt": receipt,
        "oneStepIntegrationAuthorized": authorized,
        "productionMutationPermitted": False,
        "clinicalClaimPermitted": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.function(
    image=training_image,
    volumes={"/checkpoints": checkpoint_volume},
    cpu=4,
    memory=32768,
    timeout=30 * 60,
)
def inspect_provisional_checkpoint(
    run_name: str = "toothfairy-tf-pw32-step50-v2",
    step: int = 50,
) -> dict:
    """Read only the candidate checkpoint envelope before inference integration."""
    import torch

    if run_name != "toothfairy-tf-pw32-step50-v2" or step != 50:
        raise ValueError("Only the sealed TF-PW32 step-50 candidate may be inspected")
    path = Path(f"/checkpoints/{run_name}/ckpts/denoiser_ema0.9999_step{step:07d}.pt")
    payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Candidate checkpoint is not a non-empty state dictionary")
    tensor_entries = sum(isinstance(value, torch.Tensor) for value in payload.values())
    result = {
        "path": str(path),
        "bytes": path.stat().st_size,
        "containerType": type(payload).__name__,
        "entryCount": len(payload),
        "tensorEntryCount": tensor_entries,
        "firstKeys": list(payload)[:12],
        "allValuesAreTensors": tensor_entries == len(payload),
    }
    print(json.dumps(result, indent=2), flush=True)
    return result


def training_command(dataset_name: str, run_name: str, resolution: int = 512) -> list[str]:
    if not dataset_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("dataset-name contains unsupported characters")
    if not run_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("run-name contains unsupported characters")
    config = f"/checkpoints/{run_name}/dentalsculptor_finetune_config.json"
    if resolution == 1024:
        raise ValueError("The v1 candidate is a validated 512-resolution fine-tune; 1024 requires a separate cascade experiment.")
    elif resolution != 512:
        raise ValueError("resolution must be 512 or 1024")
    data_root = f"/datasets/{dataset_name}"
    latent_name = f"shape_enc_next_dc_f16c32_fp16_{resolution}"
    data_spec = json.dumps({dataset_name: {
        "base": f"{data_root}/training_views/train",
        "shape_latent": f"{data_root}/shape_latents/{latent_name}",
        "render_cond": f"{data_root}/renders_cond",
    }}, separators=(",", ":"))
    return ["python", f"{TRELLIS2_PATH}/train.py", "--config", config,
            "--output_dir", f"/checkpoints/{run_name}", "--data_dir", data_spec, "--auto_retry", "3"]


def e10_one_tooth_training_command(dataset_name: str, run_name: str) -> list[str]:
    """Run only against the sealed E10 G1 single-tooth view."""
    if dataset_name != "toothfairy-stage1-v1":
        raise ValueError("E10 G1 dataset is sealed")
    if not run_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("run-name contains unsupported characters")
    view = f"/datasets/{dataset_name}/e10_g1_one_tooth_v1"
    data_spec = json.dumps({f"{dataset_name}-e10-g1": {
        "base": f"{view}/base",
        "shape_latent": f"{view}/shape_latent",
        "render_cond": f"{view}/render_cond",
    }}, separators=(",", ":"))
    return [
        "python", f"{TRELLIS2_PATH}/train.py",
        "--config", f"/checkpoints/{run_name}/dentalsculptor_finetune_config.json",
        "--output_dir", f"/checkpoints/{run_name}",
        "--data_dir", data_spec,
        "--auto_retry", "0",
    ]


def e12_one_tooth_training_command(dataset_name: str, run_name: str) -> list[str]:
    """Run the decoder-only G1 against one sealed mesh and dual grid."""
    if dataset_name != "toothfairy-stage1-v1":
        raise ValueError("E12 G1 dataset is sealed")
    if run_name != "stage1-e12-g1-one-tooth-v7":
        raise ValueError("E12 G1 run name is sealed")
    view = f"/datasets/{dataset_name}/e12_g1_one_tooth_v6"
    data_spec = json.dumps({f"{dataset_name}-e12-g1": {
        "base": f"{view}/base",
        "mesh_dump": f"{view}/mesh_dump",
        "dual_grid": f"{view}/dual_grid_512",
    }}, separators=(",", ":"))
    return [
        "python", f"{TRELLIS2_PATH}/train.py",
        "--config", f"/checkpoints/{run_name}/dentalsculptor_e12_config.json",
        "--output_dir", f"/checkpoints/{run_name}",
        "--data_dir", data_spec,
        "--auto_retry", "0",
    ]


def e12_gradient_diagnostic_command(dataset_name: str, run_name: str) -> list[str]:
    """Run the sealed E12 one-tooth view and stop inside loss before backward."""
    if dataset_name != "toothfairy-stage1-v1":
        raise ValueError("E12 gradient diagnostic dataset is sealed")
    if run_name != "stage1-e12-g1-gradient-diagnostic-v1":
        raise ValueError("E12 gradient diagnostic run name is sealed")
    view = f"/datasets/{dataset_name}/e12_g1_one_tooth_v6"
    data_spec = json.dumps({f"{dataset_name}-e12-diagnostic": {
        "base": f"{view}/base",
        "mesh_dump": f"{view}/mesh_dump",
        "dual_grid": f"{view}/dual_grid_512",
    }}, separators=(",", ":"))
    return [
        "python", f"{TRELLIS2_PATH}/train.py",
        "--config", f"/checkpoints/{run_name}/dentalsculptor_e12_config.json",
        "--output_dir", f"/checkpoints/{run_name}",
        "--data_dir", data_spec,
        "--auto_retry", "0",
    ]


def e12_controlled_scale_command(dataset_name: str, run_name: str) -> list[str]:
    """Run one sealed E12 normal backward that stops before optimizer logic."""
    if dataset_name != "toothfairy-stage1-v1":
        raise ValueError("E12 controlled-scale dataset is sealed")
    if run_name != "stage1-e12-g1-controlled-scale12-v1":
        raise ValueError("E12 controlled-scale run name is sealed")
    view = f"/datasets/{dataset_name}/e12_g1_one_tooth_v6"
    data_spec = json.dumps({f"{dataset_name}-e12-scale12": {
        "base": f"{view}/base",
        "mesh_dump": f"{view}/mesh_dump",
        "dual_grid": f"{view}/dual_grid_512",
    }}, separators=(",", ":"))
    return [
        "python", f"{TRELLIS2_PATH}/train.py",
        "--config", f"/checkpoints/{run_name}/dentalsculptor_e12_config.json",
        "--output_dir", f"/checkpoints/{run_name}",
        "--data_dir", data_spec,
        "--auto_retry", "0",
    ]


def e15_regional_decoder_command(dataset_name: str, run_name: str) -> list[str]:
    """Run the sealed E15 zero-step diagnostic on the existing geometry view."""
    if dataset_name != "toothfairy-stage1-v1":
        raise ValueError("E15 dataset is sealed")
    if run_name != "stage1-e15-regional-decoder-zero-step-v2":
        raise ValueError("E15 run name is sealed")
    view = f"/datasets/{dataset_name}/e12_g1_one_tooth_v6"
    data_spec = json.dumps({f"{dataset_name}-e15-zero-step": {
        "base": f"{view}/base",
        "mesh_dump": f"{view}/mesh_dump",
        "dual_grid": f"{view}/dual_grid_512",
    }}, separators=(",", ":"))
    return [
        "python", f"{TRELLIS2_PATH}/train.py",
        "--config", f"/checkpoints/{run_name}/dentalsculptor_e15_config.json",
        "--output_dir", f"/checkpoints/{run_name}",
        "--data_dir", data_spec,
        "--auto_retry", "0",
    ]


def build_e12_shape_vae_config(
    base_config: dict,
    encoder_checkpoint: str,
    decoder_checkpoint: str,
) -> dict:
    """Seal the one-step decoder-only native geometry qualification config."""
    config = json.loads(json.dumps(base_config))
    if config.get("trainer", {}).get("name") != "ShapeVaeTrainer":
        raise ValueError("E12 requires the official ShapeVaeTrainer")
    if config.get("dataset", {}).get("name") != "FlexiDualGridDataset":
        raise ValueError("E12 requires the official FlexiDualGridDataset")
    if config.get("dataset", {}).get("args", {}).get("resolution") != 512:
        raise ValueError("E12 is sealed to the official 512-resolution config")
    args = config["trainer"]["args"]
    args["finetune_ckpt"] = {
        "encoder": encoder_checkpoint,
        "decoder": decoder_checkpoint,
    }
    args["max_steps"] = 1
    args["batch_size_per_gpu"] = 1
    args["batch_split"] = 1
    args["optimizer"]["args"]["lr"] = 1e-6
    args["i_print"] = 1
    args["i_log"] = 1
    args["i_save"] = 1
    args["i_sample"] = 101
    args["snapshot_batch_size"] = 1
    args["dentalsculptor_e12_objective"] = "decoder-only-native-geometry-v1"
    return config


def e10_four_family_training_command(dataset_name: str, run_name: str) -> list[str]:
    """Run only against the sealed E10 G2 four-family training view."""
    if dataset_name != "toothfairy-stage1-v1":
        raise ValueError("E10 G2 dataset is sealed")
    if not run_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("run-name contains unsupported characters")
    view = f"/datasets/{dataset_name}/e10_g2_four_family_v1"
    data_spec = json.dumps({f"{dataset_name}-e10-g2": {
        "base": f"{view}/base",
        "shape_latent": f"{view}/shape_latent",
        "render_cond": f"{view}/render_cond",
    }}, separators=(",", ":"))
    return [
        "python", f"{TRELLIS2_PATH}/train.py",
        "--config", f"/checkpoints/{run_name}/dentalsculptor_finetune_config.json",
        "--output_dir", f"/checkpoints/{run_name}",
        "--data_dir", data_spec,
        "--auto_retry", "0",
    ]


@app.function(
    image=training_image,
    volumes={
        "/datasets": dataset_volume,
        "/checkpoints": checkpoint_volume,
        "/cache/huggingface": hf_cache_volume,
    },
    secrets=[hf_secret],
    gpu="H100",
    timeout=24 * 60 * 60,
)
def train(dataset_name: str, run_name: str, resolution: int = 512) -> dict:
    manifest = Path(f"/datasets/{dataset_name}/anatomy_manifest.json")
    if not manifest.is_file():
        raise FileNotFoundError(f"Upload the admitted anatomy dataset first: {manifest}")
    import sys
    sys.path.insert(0, "/root")
    from scripts.validate_anatomy_dataset import validate_dataset
    validate_dataset(manifest, expected_dataset_id=dataset_name, require_files=True)
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    anatomy_train = sum(
        asset["split"] == "train" and asset.get("trainingRole") in {"healthy-base", "anatomy-base"}
        for asset in metadata["assets"]
    )
    healthy_train = sum(
        asset["split"] == "train" and asset.get("trainingRole") == "healthy-base"
        for asset in metadata["assets"]
    )
    minimum = 500 if resolution == 512 else 1000
    if anatomy_train < minimum:
        raise ValueError(f"Training requires at least {minimum} admitted anatomy training meshes; found {anatomy_train}.")
    preprocess_status_path = Path(f"/datasets/{dataset_name}/preprocess_status.json")
    if not preprocess_status_path.is_file():
        raise ValueError("Training requires a completed preprocessing status file.")
    preprocess_status = json.loads(preprocess_status_path.read_text(encoding="utf-8"))
    if (
        preprocess_status.get("stage") != "trellis-preprocessed"
        or preprocess_status.get("resolution") != resolution
        or preprocess_status.get("assetCount") != metadata.get("assetCount")
        or preprocess_status.get("successfulConditionalRenders") != metadata.get("assetCount")
        or preprocess_status.get("renderCanary", {}).get("successfulConditionalRenders") != 2
    ):
        raise ValueError("Preprocessing status does not match the requested training dataset and resolution.")
    training_view = prepare_training_metadata_view(Path(f"/datasets/{dataset_name}"), resolution)
    if training_view["trainCount"] != anatomy_train:
        raise ValueError(
            "Train-only metadata count does not match the admitted manifest training count."
        )
    from huggingface_hub import hf_hub_download, list_repo_files

    required_base_files = {f"{BASE_SHAPE_FLOW_FILE}.json", f"{BASE_SHAPE_FLOW_FILE}.safetensors"}
    repository_files = set(
        list_repo_files("microsoft/TRELLIS.2-4B", revision=BASE_MODEL_REVISION)
    )
    missing_base_files = required_base_files - repository_files
    if missing_base_files:
        raise FileNotFoundError(
            f"Pinned base model revision is missing required shape-flow files: {sorted(missing_base_files)}"
        )
    base_files = {}
    for suffix in ("json", "safetensors"):
        base_files[suffix] = hf_hub_download(
            "microsoft/TRELLIS.2-4B",
            f"{BASE_SHAPE_FLOW_FILE}.{suffix}",
            revision=BASE_MODEL_REVISION,
        )
    base_prefix = str(Path(base_files["json"]).with_suffix(""))
    if Path(base_files["safetensors"]).with_suffix("") != Path(base_prefix):
        raise ValueError("Pinned base checkpoint files did not resolve to the same snapshot.")
    official_config_path = Path(TRELLIS2_PATH) / "configs/gen/slat_flow_img2shape_dit_1_3B_512_bf16.json"
    if not official_config_path.is_file() or not (Path(TRELLIS2_PATH) / "train.py").is_file():
        raise FileNotFoundError("Pinned TRELLIS.2 training source is incomplete.")
    run_root = Path(f"/checkpoints/{run_name}")
    run_root.mkdir(parents=True, exist_ok=True)
    trainer_checkpoint = materialize_trainer_checkpoint(
        base_files["safetensors"], run_root / "base-denoiser.pt"
    )
    fine_tune_config = build_finetune_config(
        json.loads(official_config_path.read_text(encoding="utf-8")),
        trainer_checkpoint,
    )
    config_path = run_root / "dentalsculptor_finetune_config.json"
    config_path.write_text(json.dumps(fine_tune_config, indent=2) + "\n", encoding="utf-8")
    command = training_command(dataset_name, run_name, resolution)
    subprocess.run(command, cwd=TRELLIS2_PATH, check=True)
    evidence = {"schemaVersion": 1, "runName": run_name, "datasetId": metadata["datasetId"],
                "datasetAssetCount": metadata["assetCount"], "anatomyTrainCount": anatomy_train,
                "healthyTrainCount": healthy_train,
                "trainingMetadata": training_view,
                "inferenceTrellisCommit": TRELLIS_COMMIT,
                "trainingCodeCommit": TRAINING_CODE_COMMIT,
                "baseModelRevision": BASE_MODEL_REVISION,
                "baseShapeCheckpoint": BASE_SHAPE_FLOW_FILE,
                "resolution": resolution, "command": command}
    evidence_path = Path(f"/checkpoints/{run_name}/dentalsculptor-run.json")
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    checkpoint_volume.commit()
    return evidence


@app.local_entrypoint()
def plan(dataset_name: str = "dental-anatomy-v1", run_name: str = "dental-alltooth-v1", resolution: int = 512):
    print(json.dumps({"command": training_command(dataset_name, run_name, resolution),
                      "datasetVolume": dataset_volume.name, "checkpointVolume": checkpoint_volume.name,
                      "gpu": "H100", "trellisCommit": TRELLIS_COMMIT}, indent=2))


@app.local_entrypoint()
def run_e7_anchor() -> None:
    """Materialize and print the sealed E7 anchor receipt; consumes no GPU."""
    print(json.dumps(prepare_e7_sparse_anchor_inputs.remote(), indent=2))


@app.local_entrypoint()
def run_e7_smoke() -> None:
    """Run and print the bounded two-step E7 H100 qualification smoke."""
    print(json.dumps(smoke_train_e7_calibrated_anchor_consistency.remote(), indent=2))


@app.local_entrypoint()
def run_e7_canary() -> None:
    """Run and print the smoke-authorized ten-step E7 canary."""
    print(json.dumps(train_e7_calibrated_anchor_canary.remote(), indent=2))


@app.local_entrypoint()
def run_e7_occupancy_screen() -> None:
    """Run the frozen four-family non-regression screen against the E7 EMA."""
    print(json.dumps(screen_sparse_canary_occupancy.remote("e7"), indent=2))


@app.local_entrypoint()
def run_mixed_representation_ceiling() -> None:
    """Run Stage 0 across ToothFairy, Teeth3DS, and DTU FDI16."""
    print(json.dumps(evaluate_mixed_shape_vae_representation_ceiling.remote(), indent=2))


@app.local_entrypoint()
def run_mixed_ceiling_cleanup_qualification() -> None:
    """Qualify largest-component cleanup on the completed mixed Stage 0."""
    print(json.dumps(qualify_mixed_ceiling_main_components.remote(), indent=2))


@app.local_entrypoint()
def run_e8_smoke() -> None:
    """Run and print the bounded two-step decoded-occupancy qualification."""
    print(json.dumps(smoke_train_e8_decoded_occupancy.remote(), indent=2))


@app.local_entrypoint()
def run_e8_step2_occupancy_screen() -> None:
    """Screen the E8 step-2 EMA before authorizing any longer optimization."""
    print(json.dumps(screen_sparse_canary_occupancy.remote("e8-smoke"), indent=2))


@app.local_entrypoint()
def run_e8_repeatability_screen() -> None:
    """Re-run E8 with unconditional base and candidate repeatability controls."""
    print(json.dumps(
        screen_sparse_canary_occupancy.remote("e8-smoke-repeatability"), indent=2
    ))


@app.local_entrypoint()
def run_e9_gradient_diagnostic() -> None:
    """Run the sealed zero-update family-by-timestep E9 diagnostic."""
    print(json.dumps(diagnose_e9_occupancy_gradients.remote(), indent=2))


@app.local_entrypoint()
def run_e12_gradient_diagnostic() -> None:
    """Run the sealed zero-step E12 component-gradient diagnostic."""
    print(json.dumps(diagnose_e12_component_gradients.remote(), indent=2))


@app.local_entrypoint()
def run_e12_controlled_scale_diagnostic() -> None:
    """Run the sealed zero-step E12 scale-12 normal-backward probe."""
    print(json.dumps(diagnose_e12_controlled_scale_backward.remote(), indent=2))


@app.local_entrypoint()
def run_e12_g1_v7() -> None:
    """Run the one-step E12 decoder integration at the qualified scale 12."""
    print(json.dumps(run_e12_g1_one_tooth_decoder_integration.remote(), indent=2))


@app.local_entrypoint()
def run_e12_v7_encoder_identity_diagnostic() -> None:
    """Classify the stopped v7 encoder mismatch without another update."""
    print(json.dumps(diagnose_e12_v7_encoder_identity.remote(), indent=2))


@app.local_entrypoint()
def run_e12_v7_decoder_update_localization() -> None:
    """Localize the rejected one-step decoder delta without training."""
    print(json.dumps(diagnose_e12_v7_decoder_update_localization.remote(), indent=2))


@app.local_entrypoint()
def run_e12_v7_existing_checkpoint_qualification() -> None:
    """Qualify the existing v7 checkpoint without another optimizer step."""
    print(json.dumps(qualify_e12_v7_existing_checkpoint.remote(), indent=2))


@app.local_entrypoint()
def run_e12_g2_decoder_screen() -> None:
    """Run the sealed four-family base-versus-v7 decoder screen."""
    print(json.dumps(run_e12_g2_four_family_decoder_screen.remote(), indent=2))


@app.local_entrypoint()
def run_r0_stage_attribution() -> None:
    """Run the sealed zero-training 12-case reconstruction stage attribution."""
    print(json.dumps(evaluate_r0_stage_attribution.remote(), indent=2))


@app.local_entrypoint()
def run_r01_conditioning_decomposition() -> None:
    """Run the zero-training sparse-support versus shape-feature attribution."""
    print(json.dumps(evaluate_r01_conditioning_decomposition.remote(), indent=2))


@app.local_entrypoint()
def run_r02_sparse_support_characterization() -> None:
    """Run the CPU-only predicted-versus-reference sparse-support diagnostic."""
    print(json.dumps(evaluate_r02_sparse_support_characterization.remote(), indent=2))


@app.local_entrypoint()
def run_r03_alignment_decomposition() -> None:
    """Run the CPU-only bounded sparse coordinate-alignment decomposition."""
    print(json.dumps(evaluate_r03_alignment_decomposition.remote(), indent=2))


@app.local_entrypoint()
def run_r04_sparse_adapter_objective() -> None:
    """Run the CPU-only zero-step crown support objective qualification."""
    print(json.dumps(evaluate_r04_sparse_adapter_objective.remote(), indent=2))


@app.local_entrypoint()
def run_r04b_sparse_adapter_architecture() -> None:
    """Seal the exact real sparse-flow adapter insertion point."""
    print(json.dumps(seal_r04b_sparse_adapter_architecture.remote(), indent=2))


@app.local_entrypoint()
def run_r04b_real_sparse_adapter_probe() -> None:
    """Run the H100 real-model zero-step adapter backward gate."""
    print(json.dumps(run_r04b_real_sparse_adapter_zero_step.remote(), indent=2))


@app.local_entrypoint()
def run_r04c_sparse_adapter_integration() -> None:
    """Run exactly one sparse-adapter update and its strict integration gate."""
    print(json.dumps(run_r04c_sparse_adapter_one_step.remote(), indent=2))


@app.local_entrypoint()
def run_r04d_sparse_adapter_four_family_screen() -> None:
    """Screen the one-step sparse adapter on four matched held-out families."""
    print(json.dumps(run_r04d_four_family_screen.remote(), indent=2))


@app.local_entrypoint()
def run_r05a_integrated_regional_objective_probe() -> None:
    """Run the real-model decoded-regional objective with zero optimizer steps."""
    print(json.dumps(run_r05a_integrated_regional_objective_zero_step.remote(), indent=2))


@app.local_entrypoint()
def run_r05b_regional_objective_one_step_probe() -> None:
    """Run exactly one qualified regional-objective adapter update."""
    print(json.dumps(run_r05b_regional_objective_one_step.remote(), indent=2))


@app.local_entrypoint()
def run_r05c_regional_four_family_screen() -> None:
    """Compare the R0.5B candidate against base on four held-out families."""
    print(json.dumps(run_r05c_four_family_screen.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g0_crown_composition() -> None:
    """Run the balanced 32-tooth crown-only composition proof."""
    print(json.dumps(run_e14_g0_crown_composition_proof.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g1_crown_refiner() -> None:
    """Run the exactly-one-step E14 crown-refiner integration gate."""
    print(json.dumps(run_e14_g1_crown_refiner_one_step.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2_cache_base_support() -> None:
    """Materialize the sealed frozen-base support cache for E14 G2."""
    print(json.dumps(materialize_e14_g2_frozen_base_support.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2_response() -> None:
    """Run the bounded 100-step E14 crown-refiner response experiment."""
    print(json.dumps(run_e14_g2_short_response.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2_alignment_mask_audit() -> None:
    """Audit all cached E14 supervision pairs without optimizer steps."""
    print(json.dumps(audit_e14_g2_alignment_and_crown_masks.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2b_family_trust_region() -> None:
    """Run exactly one isolated trust-region update per dental family."""
    print(json.dumps(run_e14_g2b_family_trust_region_gate.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2c_family_response() -> None:
    """Run the balanced 40-step family-specific response screen."""
    print(json.dumps(run_e14_g2c_family_response_screen.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2d_margin_diagnostic() -> None:
    """Run the zero-optimizer residual direction and scale diagnostic."""
    print(json.dumps(diagnose_e14_g2d_response_margin.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2e_signed_margin() -> None:
    """Run the bounded signed-margin threshold-crossing canary."""
    print(json.dumps(run_e14_g2e_signed_margin_canary.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2f_signed_margin_gain() -> None:
    """Run the zero-update gain calibration against the safe G2E checkpoint."""
    print(json.dumps(diagnose_e14_g2f_signed_margin_gain.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2g_class_balanced_response() -> None:
    """Run the bounded class-balanced family response experiment."""
    print(json.dumps(run_e14_g2g_class_balanced_family_response.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2h_image_conditioned_adapter() -> None:
    """Run the bounded image-conditioned crown adapter experiment."""
    print(json.dumps(run_e14_g2h_image_conditioned_crown_adapter.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2i_surface_band_adapter() -> None:
    """Run the bounded surface-band image-conditioned crown experiment."""
    print(json.dumps(run_e14_g2i_surface_band_crown_adapter.remote(), indent=2))


@app.local_entrypoint()
def run_e14_g2j_molar_decoder_qualification() -> None:
    """Submit the decoder qualification without coupling it to this client."""
    call = qualify_e14_g2j_molar_adapter_through_decoder.spawn()
    print(json.dumps({"submitted": True, "functionCallId": call.object_id}, indent=2))


@app.local_entrypoint()
def run_e12_v7_late_delta_hybrid() -> None:
    """Screen the base decoder plus only the rejected v7 late-stage delta."""
    print(json.dumps(run_e12_v7_late_delta_hybrid_screen.remote(), indent=2))


@app.local_entrypoint()
def run_e12_v7_output_only_delta() -> None:
    """Screen only the rejected v7 output projection delta."""
    print(json.dumps(
        run_e12_v7_late_delta_hybrid_screen.remote(candidate_scope="output-only"),
        indent=2,
    ))


@app.local_entrypoint()
def run_e12_v7_block3_only_delta() -> None:
    """Screen only the rejected v7 high-resolution feature-block delta."""
    print(json.dumps(
        run_e12_v7_late_delta_hybrid_screen.remote(candidate_scope="block3-only"),
        indent=2,
    ))


@app.local_entrypoint()
def run_freeze_sparse_base() -> None:
    """Persist the immutable four-family base occupancy benchmark once."""
    print(json.dumps(freeze_sparse_base_benchmark.remote(), indent=2))


@app.local_entrypoint()
def build(
    resolution: int = 512,
    num_cond_views: int = 24,
    run_name: str = "dental-alltooth-v1",
    skip_train: bool = False,
):
    """Assemble FDI-16 + Teeth3DS, preprocess, and optionally launch shape-flow training."""
    print("Step 1/4: QC + prepare Teeth3DS manifest on volume...")
    qc_and_prepare_teeth3ds.remote()
    print("Step 2/4: Assemble dental-anatomy-v1...")
    assembly = assemble_dental_anatomy_v1.remote()
    print(json.dumps(assembly, indent=2))
    print("Step 3/4: TRELLIS preprocessing (may take 1-2 days for ~14.6k meshes)...")
    status = preprocess_anatomy.remote("dental-anatomy-v1", resolution, num_cond_views)
    print(json.dumps(status, indent=2))
    if skip_train:
        print("Skipping training (--skip-train). Run train when preprocessing completes.")
        return
    print("Step 4/4: Launch H100 shape-flow training...")
    evidence = train.remote("dental-anatomy-v1", run_name, resolution)
    print(json.dumps(evidence, indent=2))
