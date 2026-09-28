"""Topology diagnostics that do not mutate generated reconstruction artifacts."""

from __future__ import annotations

import numpy as np
import trimesh


def _boundary_edge_metrics(mesh: trimesh.Trimesh) -> tuple[int, int, float]:
    """Return boundary edge/loop counts and total boundary length.

    ``trimesh`` has changed its boundary helpers across releases, so this uses
    the invariant definition directly: an undirected edge referenced by one
    face is a boundary edge.  Loop count is the number of connected boundary
    edge graphs; malformed open chains are intentionally counted as components
    rather than silently discarded.
    """
    edges = np.sort(np.asarray(mesh.edges, dtype=np.int64), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = unique[counts == 1]
    if not len(boundary):
        return 0, 0, 0.0
    vertices = np.unique(boundary)
    vertex_map = {int(vertex): index for index, vertex in enumerate(vertices)}
    adjacency = np.asarray(
        [[vertex_map[int(a)], vertex_map[int(b)]] for a, b in boundary],
        dtype=np.int64,
    )
    loops = trimesh.graph.connected_components(
        adjacency, nodes=np.arange(len(vertices)), min_len=1
    )
    lengths = np.linalg.norm(
        np.asarray(mesh.vertices)[boundary[:, 0]] - np.asarray(mesh.vertices)[boundary[:, 1]],
        axis=1,
    )
    return int(len(boundary)), int(len(loops)), float(lengths.sum())


def analyze_mesh(mesh: trimesh.Trimesh) -> dict:
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
        raise ValueError("A non-empty Trimesh is required")
    components = trimesh.graph.connected_components(
        mesh.face_adjacency,
        nodes=np.arange(len(mesh.faces)),
        min_len=1,
    )
    face_areas = np.asarray(mesh.area_faces, dtype=float)
    component_rows = []
    for faces in components:
        faces = np.asarray(faces, dtype=np.int64)
        component_rows.append({
            "faceCount": int(len(faces)),
            "surfaceArea": float(face_areas[faces].sum()),
        })
    component_rows.sort(key=lambda row: (row["surfaceArea"], row["faceCount"]), reverse=True)
    total_area = float(face_areas.sum())
    largest = component_rows[0]
    area_threshold = total_area * 0.001
    boundary_edge_count, boundary_loop_count, boundary_length = _boundary_edge_metrics(mesh)
    unique_edges = np.sort(np.asarray(mesh.edges_unique, dtype=np.int64), axis=1)
    incidence = np.bincount(mesh.edges_unique_inverse, minlength=len(unique_edges))
    return {
        "vertexCount": int(len(mesh.vertices)),
        "faceCount": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "componentCount": len(component_rows),
        "largestComponentFaceFraction": largest["faceCount"] / len(mesh.faces),
        "largestComponentAreaFraction": largest["surfaceArea"] / total_area if total_area else 0.0,
        "singleFaceComponentCount": sum(row["faceCount"] == 1 for row in component_rows),
        "materialComponentCount": sum(row["surfaceArea"] >= area_threshold for row in component_rows),
        "topTenAreaFraction": (
            sum(row["surfaceArea"] for row in component_rows[:10]) / total_area if total_area else 0.0
        ),
        "surfaceArea": total_area,
        "extents": [float(value) for value in mesh.extents],
        "boundaryEdgeCount": boundary_edge_count,
        "boundaryLoopCount": boundary_loop_count,
        "boundaryLength": boundary_length,
        "nonManifoldEdgeCount": int(np.count_nonzero(incidence > 2)),
        "eulerNumber": int(mesh.euler_number),
    }


def analyze_mesh_with_weld_control(mesh: trimesh.Trimesh) -> dict:
    """Report indexed topology and a geometry-only coincident-vertex control.

    GLB UV charts legitimately duplicate vertices. Counting components on the
    indexed render mesh alone can therefore mistake UV seams for disconnected
    geometry. The welded control ignores texture/normal splits while retaining
    spatially distinct fragments and must always be reported alongside—not in
    place of—the exact exported topology.
    """
    indexed = analyze_mesh(mesh)
    welded = mesh.copy()
    welded.merge_vertices(merge_tex=True, merge_norm=True)
    welded.remove_unreferenced_vertices()
    geometry = analyze_mesh(welded)
    return {
        "indexedTopology": indexed,
        "coincidentVertexWeldedTopology": geometry,
        "uvSeamComponentInflation": indexed["componentCount"] - geometry["componentCount"],
        "weldedVertexReduction": indexed["vertexCount"] - geometry["vertexCount"],
    }
