from scripts.regional_anatomy_gate import evaluate_regional_non_regression


def _metrics(value=1.0, fscore=0.8):
    region = {
        "available": True,
        "symmetricChamferPercentDiagonal": value,
        "hausdorff95PercentDiagonal": value * 2,
        "surfaceFscoreAt2Percent": fscore,
        "sampleShareAbsoluteError": 0.01,
    }
    return {"canonicalAxialAnatomyProxy": {
        "regions": {name: dict(region) for name in (
            "apicalRootProxy", "middleRootProxy", "cervicalProxy", "crownProxy"
        )},
        "robustPoleProxyErrorsPercentDiagonal": {"apical": 1.0, "coronal": 1.0},
    }}


def test_regional_gate_passes_equal_candidate():
    assert evaluate_regional_non_regression(_metrics(), _metrics())["passed"] is True


def test_regional_gate_rejects_hidden_crown_regression():
    baseline = _metrics()
    candidate = _metrics()
    candidate["canonicalAxialAnatomyProxy"]["regions"]["crownProxy"][
        "symmetricChamferPercentDiagonal"
    ] = 1.5
    result = evaluate_regional_non_regression(baseline, candidate)
    assert result["passed"] is False
    assert "crownProxy:symmetricChamferPercentDiagonal-regressed" in result["reasons"]


def test_regional_gate_fails_closed_when_metrics_missing():
    result = evaluate_regional_non_regression({}, _metrics())
    assert result["passed"] is False
