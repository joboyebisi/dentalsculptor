"""Apply DentalSculptor's promotion gates to blinded base/candidate results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.regional_anatomy_gate import evaluate_regional_non_regression


def mean(values):
    return sum(values) / len(values) if values else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True, help="JSON array; see finetune/README.md")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if len(cases) < 20:
        raise SystemExit("At least 20 held-out cases are required for a promotion decision.")
    preferences = [c for c in cases if c.get("educatorPreference") in {"base", "candidate", "tie"}]
    candidate_preference = sum(c["educatorPreference"] == "candidate" for c in preferences) / max(len(preferences), 1)
    base_success = mean([float(c["base"]["validGlb"]) for c in cases])
    candidate_success = mean([float(c["candidate"]["validGlb"]) for c in cases])
    protected = [float(c["candidate"].get("protectedRegionScore", 1)) for c in cases]
    landmark_errors = [float(c["candidate"]["landmarkMedianErrorMm"]) for c in cases if "landmarkMedianErrorMm" in c["candidate"]]
    ridge_scores = [float(c["candidate"]["ridgeGrooveContinuity"]) for c in cases if "ridgeGrooveContinuity" in c["candidate"]]
    anatomy_gate_scores = [float(c["candidate"]["anatomyGateScore"]) for c in cases if "anatomyGateScore" in c["candidate"]]
    non_molar = [c for c in cases if c.get("toothClass") != "molar"]
    non_molar_regressions = sum(
        float(c["candidate"].get("anatomyScore", 0)) + 0.25 < float(c["base"].get("anatomyScore", 0))
        for c in non_molar
    )
    regional_results = [
        evaluate_regional_non_regression(
            c["base"].get("reconstructionMetrics", c["base"]),
            c["candidate"].get("reconstructionMetrics", c["candidate"]),
        )
        for c in cases
    ]
    regional_failures = [
        {"id": case.get("id"), "reasons": result.get("reasons", [])}
        for case, result in zip(cases, regional_results)
        if not result.get("passed")
    ]
    gates = {
        "minimumCases": len(cases) >= 20,
        "educatorPreferenceAtLeast60Percent": candidate_preference >= 0.60,
        "validGlbNotWorse": candidate_success >= base_success,
        "protectedRegionMeanAtLeast095": mean(protected) >= 0.95,
        "noMaterialNonMolarRegression": non_molar_regressions == 0,
        "landmarksMeasuredForEveryCase": len(landmark_errors) == len(cases),
        "landmarkMedianErrorAtMost05mm": mean(landmark_errors) <= 0.5 if landmark_errors else False,
        "ridgeGrooveContinuityAtLeast090": mean(ridge_scores) >= 0.9 if len(ridge_scores) == len(cases) else False,
        "anatomyGateMeanAtLeast080": mean(anatomy_gate_scores) >= 0.8 if len(anatomy_gate_scores) == len(cases) else False,
        "regionalCrownRootMetricsPresentForEveryCase": all(
            "missing-canonical-axial-anatomy-proxy" not in result.get("reasons", [])
            for result in regional_results
        ),
        "noCrownOrRootRegionalRegression": not regional_failures,
    }
    report = {
        "schemaVersion": 1,
        "gatesPassed": all(gates.values()),
        "gates": gates,
        "metrics": {
            "caseCount": len(cases), "candidatePreference": candidate_preference,
            "baseValidGlbRate": base_success, "candidateValidGlbRate": candidate_success,
            "protectedRegionMean": mean(protected), "nonMolarRegressions": non_molar_regressions,
            "landmarkMedianErrorMm": mean(landmark_errors),
            "ridgeGrooveContinuity": mean(ridge_scores),
            "anatomyGateMean": mean(anatomy_gate_scores),
            "regionalFailureCount": len(regional_failures),
            "regionalFailures": regional_failures,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["gatesPassed"] else 2)


if __name__ == "__main__": main()
