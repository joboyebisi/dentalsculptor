from __future__ import annotations

import unittest

from modal_app.trellis_config import (
    MAX_CONTAINERS,
    MIN_CONTAINERS,
    QUALITY_PRESETS,
    get_quality_preset,
    sampler_params_for_steps,
)


class QualityPresetTests(unittest.TestCase):
    def test_expected_presets_are_available(self) -> None:
        self.assertEqual(set(QUALITY_PRESETS), {"preview", "standard", "final"})
        self.assertEqual(get_quality_preset("preview")["pipeline_type"], "512")
        self.assertEqual(
            get_quality_preset("standard")["pipeline_type"], "1024_cascade"
        )
        self.assertEqual(get_quality_preset("final")["texture_size"], 4096)

    def test_preset_is_a_defensive_copy(self) -> None:
        preset = get_quality_preset("standard")
        preset["steps"] = 1
        self.assertEqual(get_quality_preset("standard")["steps"], 12)

    def test_invalid_quality_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported quality"):
            get_quality_preset("arbitrary-browser-settings")

    def test_steps_are_applied_to_all_sampler_stages(self) -> None:
        params = sampler_params_for_steps(8)
        self.assertEqual(
            {stage["steps"] for stage in params.values()},
            {8},
        )

    def test_capacity_bounds_are_valid(self) -> None:
        self.assertLessEqual(MIN_CONTAINERS, MAX_CONTAINERS)


if __name__ == "__main__":
    unittest.main()
