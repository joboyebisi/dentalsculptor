import pytest

from scripts.representation_ceiling import summarize_representation_ceiling


def _case(case_id: str, family: str, chamfer: float) -> dict:
    return {
        "id": case_id,
        "toothFamily": family,
        "metrics": {
            "symmetricChamferPercentDiagonal": chamfer,
            "hausdorff95PercentDiagonal": 2.0,
            "surfaceFscoreAt1Percent": 0.5,
            "surfaceFscoreAt2Percent": 0.75,
            "sortedExtentRelativeError": 0.1,
        },
    }


def test_representation_ceiling_summary_is_family_stratified_and_non_promoting():
    report = summarize_representation_ceiling([
        _case("i1", "incisor", 1.0),
        _case("i2", "incisor", 3.0),
        _case("m1", "molar", 4.0),
    ])
    assert report["aggregate"]["symmetricChamferPercentDiagonal"] == 2.666667
    assert report["byToothFamily"]["incisor"]["metrics"]["symmetricChamferPercentDiagonal"] == 2.0
    assert report["representationCeilingEstablished"] is False
    assert report["productionPromotionPermitted"] is False


def test_representation_ceiling_rejects_incomplete_metrics():
    with pytest.raises(ValueError, match="missing metrics"):
        summarize_representation_ceiling([{"id": "x", "toothFamily": "molar", "metrics": {}}])
