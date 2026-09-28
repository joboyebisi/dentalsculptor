import numpy as np

from scripts.render_toothfairy_clinical_review import (
    canonical_review_vertices,
    review_eligibility,
)


def test_quarantines_boundary_and_nonwatertight_assets():
    assert review_eligibility({"touchesVolumeBoundary": False, "reviewFlags": []}) == (True, [])
    eligible, reasons = review_eligibility({
        "touchesVolumeBoundary": True,
        "reviewFlags": ["non-watertight-extracted-surface"],
    })
    assert not eligible
    assert reasons == [
        "non-watertight-extracted-surface",
        "volume-boundary-contact-possible-apex-truncation",
    ]


def test_canonical_review_orientation_places_broader_end_at_top():
    rng = np.random.default_rng(7)
    narrow = np.column_stack((
        rng.normal(0, 0.3, 300), rng.normal(0, 0.3, 300), rng.uniform(-6, -3, 300)
    ))
    broad = np.column_stack((
        rng.normal(0, 1.4, 600), rng.normal(0, 1.1, 600), rng.uniform(2, 4, 600)
    ))
    aligned, rotation = canonical_review_vertices(np.vstack((narrow, broad)))
    assert rotation.shape == (3, 3)
    z = aligned[:, 2]
    radius = np.linalg.norm(aligned[:, :2], axis=1)
    assert np.median(radius[z >= np.quantile(z, 0.8)]) > np.median(
        radius[z <= np.quantile(z, 0.2)]
    )
