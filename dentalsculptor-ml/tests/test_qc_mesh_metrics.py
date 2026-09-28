import trimesh

from scripts.qc_fdi16_meshes import assess_mesh


def test_boundary_ratio_uses_face_incidence_not_edge_length():
    watertight = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
    watertight_metrics = assess_mesh(watertight)
    assert watertight_metrics["boundaryEdgeRatio"] == 0.0

    open_mesh = watertight.copy()
    open_mesh.update_faces([False] + [True] * (len(open_mesh.faces) - 1))
    open_mesh.remove_unreferenced_vertices()
    open_metrics = assess_mesh(open_mesh)
    assert open_metrics["boundaryEdgeRatio"] > 0.0
    assert "open-mesh-expected-for-ios-segment" in open_metrics["observations"]
    assert "open-mesh-expected-for-ios-segment" not in open_metrics["reviewFlags"]
