"""Fail-closed crown/root non-regression gate for reconstruction candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_TOLERANCES = {
    "symmetricChamferPercentDiagonal": 0.02,
    "hausdorff95PercentDiagonal": 0.05,
    "surfaceFscoreAt2Percent": 0.005,
    "sampleShareAbsoluteError": 0.005,
    "poleErrorPercentDiagonal": 0.05,
}


def evaluate_regional_non_regression(
    baseline_metrics: dict,
    candidate_metrics: dict,
    tolerances: dict | None = None,
) -> dict:
    limits = {**DEFAULT_TOLERANCES, **(tolerances or {})}
    baseline = baseline_metrics.get("canonicalAxialAnatomyProxy")
    candidate = candidate_metrics.get("canonicalAxialAnatomyProxy")
    if not baseline or not candidate:
        return {
            "passed": False,
            "reasons": ["missing-canonical-axial-anatomy-proxy"],
            "clinicalLandmarkClaimPermitted": False,
        }
    reasons = []
    rows = []
    for region in ("apicalRootProxy", "middleRootProxy", "cervicalProxy", "crownProxy"):
        before = baseline.get("regions", {}).get(region, {})
        after = candidate.get("regions", {}).get(region, {})
        if not before.get("available") or not after.get("available"):
            reasons.append(f"{region}:missing")
            continue
        checks = {
            "symmetricChamferPercentDiagonal": after["symmetricChamferPercentDiagonal"]
            <= before["symmetricChamferPercentDiagonal"] + limits["symmetricChamferPercentDiagonal"],
            "hausdorff95PercentDiagonal": after["hausdorff95PercentDiagonal"]
            <= before["hausdorff95PercentDiagonal"] + limits["hausdorff95PercentDiagonal"],
            "surfaceFscoreAt2Percent": after["surfaceFscoreAt2Percent"]
            >= before["surfaceFscoreAt2Percent"] - limits["surfaceFscoreAt2Percent"],
            "sampleShareAbsoluteError": after["sampleShareAbsoluteError"]
            <= before["sampleShareAbsoluteError"] + limits["sampleShareAbsoluteError"],
        }
        for metric, passed in checks.items():
            if not passed:
                reasons.append(f"{region}:{metric}-regressed")
        rows.append({"region": region, "checks": checks, "passed": all(checks.values())})
    pole_checks = {}
    for pole in ("apical", "coronal"):
        before = baseline.get("robustPoleProxyErrorsPercentDiagonal", {}).get(pole)
        after = candidate.get("robustPoleProxyErrorsPercentDiagonal", {}).get(pole)
        passed = before is not None and after is not None and after <= before + limits["poleErrorPercentDiagonal"]
        pole_checks[pole] = passed
        if not passed:
            reasons.append(f"{pole}:robust-pole-error-regressed-or-missing")
    return {
        "schemaVersion": 1,
        "gate": "canonical-axial-anatomy-proxy-non-regression-v1",
        "passed": not reasons,
        "tolerances": limits,
        "regions": rows,
        "poleChecks": pole_checks,
        "reasons": reasons,
        "clinicalLandmarkClaimPermitted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = evaluate_regional_non_regression(
        json.loads(args.baseline.read_text(encoding="utf-8")),
        json.loads(args.candidate.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 2)


if __name__ == "__main__":
    main()
