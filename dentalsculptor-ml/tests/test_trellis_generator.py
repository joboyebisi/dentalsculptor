from __future__ import annotations

import unittest

from modal_app.trellis_config import MAX_INPUT_PIXELS
from modal_app.workers.trellis_generator import (
    build_success_response,
    validate_pixel_count,
    validate_upload_metadata,
)


class InputValidationTests(unittest.TestCase):
    def test_supported_image_metadata_is_accepted(self) -> None:
        validate_upload_metadata(b"image", "image/png")

    def test_unsupported_mime_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported image type"):
            validate_upload_metadata(b"image", "application/pdf")

    def test_empty_upload_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Image must be"):
            validate_upload_metadata(b"", "image/png")

    def test_excessive_pixel_count_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "too many pixels"):
            validate_pixel_count(MAX_INPUT_PIXELS + 1, 1)


class CompatibilityResponseTests(unittest.TestCase):
    def test_base64_contract_remains_available(self) -> None:
        response = build_success_response(
            b"glb",
            pipeline_type="512",
            load_time=1.25,
            seed=7,
            timings={"total": 2.5},
            quality="preview",
            metrics={"peakAllocatedBytes": 10},
        )
        self.assertEqual(response["status"], "completed")
        self.assertEqual(response["format"], "glb")
        self.assertEqual(response["modelBase64"], "Z2xi")
        self.assertEqual(response["quality"], "preview")


if __name__ == "__main__":
    unittest.main()
