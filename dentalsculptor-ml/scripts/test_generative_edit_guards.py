#!/usr/bin/env python3
"""Offline tests for generative preview locality guards."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modal_app.workers.nano3d_flowedit import validate_localized_image_edit  # noqa: E402


def expect_failure(source: Path, target: Path, mask: Path, phrase: str) -> None:
    try:
        validate_localized_image_edit(source, target, mask)
    except ValueError as exc:
        assert phrase in str(exc), f"expected '{phrase}', got '{exc}'"
        return
    raise AssertionError(f"expected validation failure containing '{phrase}'")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ds-generative-guards-") as tmp:
        root = Path(tmp)
        source = root / "source.png"
        valid = root / "valid.png"
        outside = root / "outside.png"
        unchanged = root / "unchanged.png"
        mask = root / "mask.png"
        broad_mask = root / "broad-mask.png"

        Image.new("RGB", (128, 128), (210, 210, 205)).save(source)
        Image.open(source).save(unchanged)

        mask_image = Image.new("L", (128, 128), 0)
        ImageDraw.Draw(mask_image).rectangle((48, 32, 82, 68), fill=255)
        mask_image.save(mask)

        valid_image = Image.open(source)
        ImageDraw.Draw(valid_image).ellipse((52, 36, 78, 64), fill=(95, 55, 30))
        valid_image.save(valid)

        outside_image = valid_image.copy()
        ImageDraw.Draw(outside_image).rectangle((0, 0, 40, 40), fill=(20, 20, 20))
        outside_image.save(outside)

        Image.new("L", (128, 128), 255).save(broad_mask)

        metrics = validate_localized_image_edit(source, valid, mask)
        assert metrics["insidePreviewChangeRatio"] > 0
        assert metrics["outsidePreviewChangeRatio"] == 0
        expect_failure(source, outside, mask, "outside")
        expect_failure(source, unchanged, mask, "visible edit")
        expect_failure(source, valid, broad_mask, "covers too much")

    print("Validated generative preview locality guards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
