"""Pure reporting helpers for the frozen SC-VAE representation-ceiling gate."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean


LOWER_IS_BETTER = (
    "symmetricChamferPercentDiagonal",
    "hausdorff95PercentDiagonal",
    "sortedExtentRelativeError",
)
HIGHER_IS_BETTER = ("surfaceFscoreAt1Percent", "surfaceFscoreAt2Percent")


def summarize_representation_ceiling(cases: list[dict]) -> dict:
    """Aggregate E0 cases without turning an engineering run into a pass claim."""
    if not cases:
        raise ValueError("At least one representation-ceiling case is required")
    required = set(LOWER_IS_BETTER + HIGHER_IS_BETTER)
    families: dict[str, list[dict]] = defaultdict(list)
    for case in cases:
        missing = required - set(case.get("metrics", {}))
        if missing:
            raise ValueError(f"Case {case.get('id')} is missing metrics: {sorted(missing)}")
        families[case["toothFamily"]].append(case)

    def aggregate(rows: list[dict]) -> dict:
        return {
            metric: round(mean(float(row["metrics"][metric]) for row in rows), 6)
            for metric in (*LOWER_IS_BETTER, *HIGHER_IS_BETTER)
        }

    return {
        "caseCount": len(cases),
        "aggregate": aggregate(cases),
        "byToothFamily": {
            family: {"caseCount": len(rows), "metrics": aggregate(rows)}
            for family, rows in sorted(families.items())
        },
        "representationCeilingEstablished": False,
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
        "interpretation": (
            "measurement-complete-thresholds-require-preregistered-validation-cohort"
        ),
    }
