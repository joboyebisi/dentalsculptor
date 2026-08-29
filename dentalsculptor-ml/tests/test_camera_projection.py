import unittest

import numpy as np

from modal_app.workers.nano3d_utils import _project_vertex_weights


class CameraProjectionTests(unittest.TestCase):
    def test_threejs_column_major_camera_matrices_project_to_mask(self):
        # Three.js Matrix4.toArray() is column-major. This view translates x by
        # -0.5, placing the vertex at x=.5 in the centre of the viewport.
        camera = {
            "width": 100,
            "height": 100,
            "viewMatrix": [
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                -0.5, 0, 0, 1,
            ],
            "projectionMatrix": [
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                0, 0, 0, 1,
            ],
        }
        mask = np.zeros((100, 100), dtype=bool)
        mask[48:53, 48:53] = True

        weights = _project_vertex_weights(np.array([[0.5, 0.0, 0.0]]), camera, mask)

        self.assertEqual(weights.tolist(), [1.0])


    def test_projection_rejects_a_mask_away_from_the_tooth(self):
        camera = {
            "width": 100,
            "height": 100,
            "viewMatrix": np.eye(4).T.reshape(-1).tolist(),
            "projectionMatrix": np.eye(4).T.reshape(-1).tolist(),
        }
        mask = np.zeros((100, 100), dtype=bool)
        mask[5:10, 5:10] = True

        weights = _project_vertex_weights(np.array([[0.0, 0.0, 0.0]]), camera, mask)

        self.assertEqual(weights.tolist(), [0.0])


if __name__ == "__main__":
    unittest.main()
