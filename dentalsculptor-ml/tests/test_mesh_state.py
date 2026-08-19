"""Tests for two-phase mesh state helpers."""

from __future__ import annotations

import unittest


class MeshStateKeyTests(unittest.TestCase):
    def test_preview_and_mesh_state_keys(self) -> None:
        from modal_app.workers.s3_results import mesh_state_key, preview_result_key

        job_id = "abc-123"
        self.assertEqual(mesh_state_key(job_id), "jobs/abc-123/mesh-state.pt")
        self.assertEqual(preview_result_key(job_id), "jobs/abc-123/preview.glb")


if __name__ == "__main__":
    unittest.main()
