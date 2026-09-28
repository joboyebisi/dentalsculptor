"""Fail-closed repeatability comparison for immutable E1 topology trials."""

from __future__ import annotations

import json
import argparse
from pathlib import Path

from scripts.reconstruction_benchmark import compare_meshes, load_mesh


def calibrated_pairwise_geometry(
    left,
    right,
    *,
    samples: int = 10000,
    seed: int = 1724708096,
) -> dict:
    """Measure two surfaces and calibrate the decision to sampling noise."""
    calibration = {
        "distanceMultiplier": 1.5,
        "distanceAbsoluteSlackPercentDiagonal": 0.02,
        "fscoreAbsoluteSlack": 0.02,
        "extentAbsoluteTolerance": 0.005,
    }
    metrics = compare_meshes(left, right, samples=samples, seed=seed)
    sampling_floor = compare_meshes(left, left, samples=samples, seed=seed + 100000)
    thresholds = {
        "symmetricChamferPercentDiagonal": (
            sampling_floor["symmetricChamferPercentDiagonal"]
            * calibration["distanceMultiplier"]
            + calibration["distanceAbsoluteSlackPercentDiagonal"]
        ),
        "hausdorff95PercentDiagonal": (
            sampling_floor["hausdorff95PercentDiagonal"]
            * calibration["distanceMultiplier"]
            + calibration["distanceAbsoluteSlackPercentDiagonal"]
        ),
        "surfaceFscoreAt2Percent": max(
            0.0,
            sampling_floor["surfaceFscoreAt2Percent"]
            - calibration["fscoreAbsoluteSlack"],
        ),
        "sortedExtentRelativeError": calibration["extentAbsoluteTolerance"],
    }
    passed = (
        metrics["symmetricChamferPercentDiagonal"] <= thresholds["symmetricChamferPercentDiagonal"]
        and metrics["hausdorff95PercentDiagonal"] <= thresholds["hausdorff95PercentDiagonal"]
        and metrics["surfaceFscoreAt2Percent"] >= thresholds["surfaceFscoreAt2Percent"]
        and metrics["sortedExtentRelativeError"] <= thresholds["sortedExtentRelativeError"]
    )
    return {
        "metrics": metrics,
        "samplingNoiseFloor": sampling_floor,
        "calibratedThresholds": thresholds,
        "calibration": calibration,
        "passed": passed,
    }


def compare_trials(first: dict, second: dict) -> dict:
    required_equal = (
        "datasetId", "datasetManifestSha256", "baseModelRevision",
        "trellisCommit", "pipelineType",
    )
    mismatches = {
        field: [first.get(field), second.get(field)]
        for field in required_equal
        if first.get(field) != second.get(field)
    }
    if mismatches:
        raise ValueError(f"Trials do not share a frozen experiment contract: {mismatches}")
    if len(first.get("cases", [])) != len(second.get("cases", [])):
        raise ValueError("Trial case counts differ")
    first_cases = {case["id"]: case for case in first["cases"]}
    second_cases = {case["id"]: case for case in second["cases"]}
    if set(first_cases) != set(second_cases):
        raise ValueError("Trial case IDs differ")

    cases = []
    for case_id in sorted(first_cases):
        left = first_cases[case_id]
        right = second_cases[case_id]
        if left.get("seed") != right.get("seed") or left.get("inputImageSha256") != right.get("inputImageSha256"):
            raise ValueError(f"Seed/input mismatch for {case_id}")
        left_stages = {stage["stage"]: stage for stage in left["stages"]}
        right_stages = {stage["stage"]: stage for stage in right["stages"]}
        stage_rows = []
        for stage_name in ("pipeline-decoded", "post-remesh", "final-glb"):
            a = left_stages[stage_name]
            b = right_stages[stage_name]
            a_weld = a["topologyWeldControl"]["coincidentVertexWeldedTopology"]
            b_weld = b["topologyWeldControl"]["coincidentVertexWeldedTopology"]
            metric_deltas = {
                metric: round(float(b["referenceMetrics"][metric]) - float(a["referenceMetrics"][metric]), 6)
                for metric in (
                    "symmetricChamferPercentDiagonal",
                    "hausdorff95PercentDiagonal",
                    "surfaceFscoreAt2Percent",
                    "sortedExtentRelativeError",
                )
            }
            stage_rows.append({
                "stage": stage_name,
                "artifactBytesIdentical": a["artifactSha256"] == b["artifactSha256"],
                "firstArtifactSha256": a["artifactSha256"],
                "secondArtifactSha256": b["artifactSha256"],
                "weldedComponentDelta": int(b_weld["componentCount"] - a_weld["componentCount"]),
                "largestComponentAreaFractionDelta": round(
                    float(b_weld["largestComponentAreaFraction"])
                    - float(a_weld["largestComponentAreaFraction"]), 6
                ),
                "metricDeltas": metric_deltas,
            })
        cases.append({"id": case_id, "stages": stage_rows})

    byte_repeatable = all(
        stage["artifactBytesIdentical"]
        for case in cases for stage in case["stages"]
    )
    return {
        "schemaVersion": 1,
        "experiment": "E1-fixed-seed-repeatability",
        "firstTrialId": first.get("trialId"),
        "secondTrialId": second.get("trialId"),
        "firstRuntime": first.get("runtime"),
        "secondRuntime": second.get("runtime"),
        "caseCount": len(cases),
        "cases": cases,
        "byteRepeatable": byte_repeatable,
        "repeatabilityGatePassed": byte_repeatable,
        "productionPromotionPermitted": False,
        "clinicalClaimPermitted": False,
    }


def compare_files(first_path: Path, second_path: Path, output_path: Path) -> dict:
    report = compare_trials(
        json.loads(first_path.read_text(encoding="utf-8")),
        json.loads(second_path.read_text(encoding="utf-8")),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def add_direct_geometry_comparison(
    report: dict,
    first: dict,
    second: dict,
    first_root: Path,
    second_root: Path,
    *,
    samples: int = 10000,
    seed: int = 1724708096,
) -> dict:
    """Compare trial artifacts directly, calibrated against sampling noise.

    ``compare_meshes`` independently samples each surface, so even a mesh compared
    with itself has a non-zero distance.  Each stage therefore gets its own
    self-comparison floor.  The repeatability decision asks whether the trial pair
    stays close to that floor instead of pretending the estimator is exact.
    """
    first_cases = {case["id"]: case for case in first["cases"]}
    second_cases = {case["id"]: case for case in second["cases"]}
    report_cases = {case["id"]: case for case in report["cases"]}
    direct_pass = True
    calibration = None
    for case_index, case_id in enumerate(sorted(first_cases)):
        left_stages = {stage["stage"]: stage for stage in first_cases[case_id]["stages"]}
        right_stages = {stage["stage"]: stage for stage in second_cases[case_id]["stages"]}
        report_stages = {stage["stage"]: stage for stage in report_cases[case_id]["stages"]}
        for stage_index, stage_name in enumerate(("pipeline-decoded", "post-remesh", "final-glb")):
            left_case_dir = first_cases[case_id].get(
                "artifactDirectory", first_cases[case_id].get("referenceMeshSha256", case_id)
            )
            right_case_dir = second_cases[case_id].get(
                "artifactDirectory", second_cases[case_id].get("referenceMeshSha256", case_id)
            )
            left = load_mesh(first_root / left_case_dir / left_stages[stage_name]["artifact"])
            right = load_mesh(second_root / right_case_dir / right_stages[stage_name]["artifact"])
            stage_seed = seed + case_index * 10 + stage_index
            comparison = calibrated_pairwise_geometry(
                left, right, samples=samples, seed=stage_seed
            )
            calibration = comparison["calibration"]
            report_stages[stage_name]["directPairwiseGeometry"] = comparison["metrics"]
            report_stages[stage_name]["samplingNoiseFloor"] = comparison["samplingNoiseFloor"]
            report_stages[stage_name]["calibratedThresholds"] = comparison["calibratedThresholds"]
            report_stages[stage_name]["directPairwiseGeometryPassed"] = comparison["passed"]
            direct_pass = direct_pass and comparison["passed"]
    report["directPairwiseCalibration"] = calibration
    report["directPairwiseSamples"] = samples
    report["directPairwiseGeometryPassed"] = direct_pass
    report["repeatabilityGatePassed"] = bool(
        report["byteRepeatable"] or direct_pass
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", required=True, type=Path)
    parser.add_argument("--second", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(compare_files(args.first, args.second, args.output), indent=2))


if __name__ == "__main__":
    main()
