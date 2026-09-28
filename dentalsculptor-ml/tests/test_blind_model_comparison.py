from scripts.blind_model_comparison import blinded_order
from scripts.unblind_model_comparison import unblind


def test_blinding_is_stable_and_unblinds_scores():
    first = blinded_order("case-001", 42)
    assert first == blinded_order("case-001", 42)
    key = [{"id": "case-001", "A": first[0], "B": first[1], "metrics": {
        "base": {"anatomyQuality": {"score": 0.81}}, "candidate": {"anatomyQuality": {"score": 0.92}}}}]
    review = {"preferred": "B", "anatomyScoreA": 0.7, "anatomyScoreB": 0.9,
              "landmarkMedianErrorMmA": 0.7, "landmarkMedianErrorMmB": 0.4,
              "ridgeGrooveContinuityA": 0.7, "ridgeGrooveContinuityB": 0.95}
    result = unblind([{"id": "case-001", "toothClass": "molar", "review": review}], key)[0]
    assert result["educatorPreference"] == key[0]["B"]
    assert result["candidate"]["anatomyGateScore"] == 0.92
