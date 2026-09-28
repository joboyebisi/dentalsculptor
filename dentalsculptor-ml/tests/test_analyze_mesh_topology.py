import trimesh

from scripts.analyze_mesh_topology import analyze_mesh, analyze_mesh_with_weld_control


def test_analyze_mesh_topology_reports_material_components():
    large = trimesh.creation.box(extents=[2, 2, 2])
    small = trimesh.creation.box(extents=[0.01, 0.01, 0.01])
    small.apply_translation([10, 0, 0])
    report = analyze_mesh(trimesh.util.concatenate((large, small)))
    assert report["componentCount"] == 2
    assert report["largestComponentAreaFraction"] > 0.99
    assert report["materialComponentCount"] == 1
    assert report["topTenAreaFraction"] == 1.0
    assert report["boundaryEdgeCount"] == 0
    assert report["boundaryLoopCount"] == 0
    assert report["nonManifoldEdgeCount"] == 0


def test_analyze_mesh_topology_reports_open_boundary_loop():
    mesh = trimesh.creation.box()
    mesh.update_faces([False] + [True] * (len(mesh.faces) - 1))
    mesh.remove_unreferenced_vertices()
    report = analyze_mesh(mesh)
    assert report["watertight"] is False
    assert report["boundaryEdgeCount"] == 3
    assert report["boundaryLoopCount"] == 1
    assert report["boundaryLength"] > 0


def test_weld_control_separates_index_splits_from_geometry_components():
    # Two triangles share geometric positions but use distinct vertex indices,
    # like adjacent UV charts in an exported GLB.
    mesh = trimesh.Trimesh(
        vertices=[
            [0, 0, 0], [1, 0, 0], [0, 1, 0],
            [1, 0, 0], [1, 1, 0], [0, 1, 0],
        ],
        faces=[[0, 1, 2], [3, 4, 5]],
        process=False,
    )
    report = analyze_mesh_with_weld_control(mesh)
    assert report["indexedTopology"]["componentCount"] == 2
    assert report["coincidentVertexWeldedTopology"]["componentCount"] == 1
    assert report["uvSeamComponentInflation"] == 1
