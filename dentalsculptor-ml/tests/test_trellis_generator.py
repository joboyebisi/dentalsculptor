from __future__ import annotations

import unittest
from pathlib import Path

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


class CandidateCheckpointTests(unittest.TestCase):
    def test_shape_checkpoint_loader_is_explicit_and_strict(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "modal_app"
            / "workers"
            / "trellis_generator.py"
        ).read_text(encoding="utf-8")
        self.assertIn('model_key = "shape_slat_flow_model_512"', source)
        self.assertIn("load_state_dict(state, strict=True)", source)
        self.assertIn('"checkpointSha256": digest.hexdigest()', source)

    def test_sparse_checkpoint_loader_targets_only_official_sparse_slot(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "modal_app"
            / "workers"
            / "trellis_generator.py"
        ).read_text(encoding="utf-8")
        self.assertIn("def load_sparse_structure_checkpoint", source)
        self.assertIn('model_key = "sparse_structure_flow_model"', source)
        self.assertIn('self.last_metrics["sparseStructureCheckpoint"]', source)
        self.assertIn("with torch.inference_mode():", source)


if __name__ == "__main__":
    unittest.main()
