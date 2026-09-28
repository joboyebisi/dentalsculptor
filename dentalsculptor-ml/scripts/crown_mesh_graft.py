"""Cut and stitch a candidate crown onto a protected baseline root."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import trimesh


def _plane_boundary_loop(mesh: trimesh.Trimesh, plane_z: float, tolerance: float) -> np.ndarray:
    edges = np.asarray(mesh.edges_sorted)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = unique[counts == 1]
    on_plane = np.all(np.abs(np.asarray(mesh.vertices)[boundary, 2] - plane_z) <= tolerance, axis=1)
    plane_edges = boundary[on_plane]
    if len(plane_edges) < 3:
        raise ValueError("cut produced no usable plane boundary")
    adjacency: dict[int, list[int]] = defaultdict(list)
    for left, right in plane_edges:
        adjacency[int(left)].append(int(right)); adjacency[int(right)].append(int(left))
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise ValueError("cut boundary is not a simple manifold loop")
    loops=[]; unvisited=set(adjacency)
    while unvisited:
        start=next(iter(unvisited)); loop=[start]; previous=None; current=start
        while True:
            choices=[value for value in adjacency[current] if value != previous]
            next_vertex=choices[0]
            if next_vertex==start: break
            if next_vertex in loop: raise ValueError("cut boundary self-intersects topologically")
            loop.append(next_vertex); previous,current=current,next_vertex
        unvisited.difference_update(loop); loops.append(np.asarray(loop,dtype=np.int64))
    if len(loops)!=1:
        raise ValueError(f"expected one cut loop, found {len(loops)}")
    return loops[0]


def _signed_area_xy(vertices: np.ndarray) -> float:
    x=vertices[:,0]; y=vertices[:,1]
    return 0.5*float(np.sum(x*np.roll(y,-1)-np.roll(x,-1)*y))


def _normalized_arclength(vertices: np.ndarray) -> np.ndarray:
    lengths=np.linalg.norm(np.roll(vertices,-1,axis=0)-vertices,axis=1)
    total=float(lengths.sum())
    if total<=1e-12: raise ValueError("boundary loop has zero perimeter")
    return np.concatenate(([0.0],np.cumsum(lengths[:-1])/total))


def _zipper_faces(root_loop: np.ndarray, crown_loop: np.ndarray, vertices: np.ndarray) -> np.ndarray:
    root_points=vertices[root_loop]; crown_points=vertices[crown_loop]
    if _signed_area_xy(root_points)*_signed_area_xy(crown_points)>0:
        crown_loop=crown_loop[::-1]; crown_points=crown_points[::-1]
    root_phase=_normalized_arclength(root_points); crown_phase=_normalized_arclength(crown_points)
    i=j=0; n=len(root_loop); m=len(crown_loop); faces=[]
    while i<n or j<m:
        next_root=(root_phase[(i+1)%n]+(1.0 if i+1>=n else 0.0)) if i<n else float("inf")
        next_crown=(crown_phase[(j+1)%m]+(1.0 if j+1>=m else 0.0)) if j<m else float("inf")
        root_i=int(root_loop[i%n]); crown_j=int(crown_loop[j%m])
        if next_root<=next_crown:
            faces.append((root_i,int(root_loop[(i+1)%n]),crown_j)); i+=1
        else:
            faces.append((root_i,int(crown_loop[(j+1)%m]),crown_j)); j+=1
    return np.asarray(faces,dtype=np.int64)


def graft_candidate_crown(
    baseline: trimesh.Trimesh,
    aligned_candidate: trimesh.Trimesh,
    *,
    cut_height: float=0.72,
) -> tuple[trimesh.Trimesh,dict]:
    """Keep baseline below the plane, candidate above it, and stitch their loops."""
    if not 0.0<cut_height<1.0: raise ValueError("cut height must be in (0, 1)")
    base_vertices=np.asarray(baseline.vertices,dtype=np.float64)
    z_min=float(base_vertices[:,2].min()); z_span=float(np.ptp(base_vertices[:,2])); plane_z=z_min+cut_height*z_span
    tolerance=max(z_span*1e-6,1e-9); origin=np.array([0.0,0.0,plane_z])
    root=trimesh.intersections.slice_mesh_plane(baseline,plane_normal=[0,0,-1],plane_origin=origin,cap=False)
    crown=trimesh.intersections.slice_mesh_plane(aligned_candidate,plane_normal=[0,0,1],plane_origin=origin,cap=False)
    if len(root.faces)==0 or len(crown.faces)==0: raise ValueError("cut removed root or crown")
    for part in (root,crown):
        part.merge_vertices(digits_vertex=6)
        part.update_faces(part.nondegenerate_faces())
        part.update_faces(part.unique_faces())
        part.remove_unreferenced_vertices()
        part.merge_vertices(digits_vertex=6)
    root_loop=_plane_boundary_loop(root,plane_z,tolerance); crown_loop_local=_plane_boundary_loop(crown,plane_z,tolerance)
    vertices=np.vstack((np.asarray(root.vertices),np.asarray(crown.vertices)))
    crown_faces=np.asarray(crown.faces)+len(root.vertices); crown_loop=crown_loop_local+len(root.vertices)
    bridge=_zipper_faces(root_loop,crown_loop,vertices)
    faces=np.vstack((np.asarray(root.faces),crown_faces,bridge))
    graft=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    unique_edges,edge_counts=np.unique(np.sort(np.asarray(graft.edges),axis=1),axis=0,return_counts=True)
    boundary_edges=int(np.count_nonzero(edge_counts==1)); nonmanifold_edges=int(np.count_nonzero(edge_counts>2))
    receipt={
        "method":"single-plane-cut-zipper-stitch-v1","cutHeight":cut_height,"planeZ":plane_z,
        "rootLoopVertexCount":int(len(root_loop)),"crownLoopVertexCount":int(len(crown_loop)),
        "bridgeFaceCount":int(len(bridge)),"rootVertexCount":int(len(root.vertices)),"crownVertexCount":int(len(crown.vertices)),
        "boundaryEdgeCount":boundary_edges,"nonManifoldEdgeCount":nonmanifold_edges,
        "watertight":bool(graft.is_watertight),"clinicalCejClaimPermitted":False,
    }
    return graft,receipt
