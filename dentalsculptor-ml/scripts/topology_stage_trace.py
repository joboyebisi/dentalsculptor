"""Stage-labelled topology evidence for TRELLIS decode/export diagnostics."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import trimesh

from scripts.analyze_mesh_topology import analyze_mesh, analyze_mesh_with_weld_control


STAGE_ORDER = ("pipeline-decoded", "post-remesh", "final-glb")


def mesh_from_arrays(vertices, faces) -> trimesh.Trimesh:
    """Copy torch/numpy geometry to a non-mutating CPU trimesh."""
    if hasattr(vertices, "detach"):
        vertices = vertices.detach().cpu().numpy()
    if hasattr(faces, "detach"):
        faces = faces.detach().cpu().numpy()
    return trimesh.Trimesh(
        vertices=np.asarray(vertices, dtype=np.float64),
        faces=np.asarray(faces, dtype=np.int64),
        process=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_topology_stage_report(stages: list[dict]) -> dict:
    names = [stage["stage"] for stage in stages]
    if names != list(STAGE_ORDER):
        raise ValueError(f"Expected topology stages {STAGE_ORDER}, got {names}")
    for stage in stages:
        if "topology" not in stage or "artifactSha256" not in stage:
            raise ValueError(f"Incomplete topology stage: {stage.get('stage')}")
    def geometry_components(stage: dict) -> int:
        control = stage.get("topologyWeldControl")
        if control:
            return int(control["coincidentVertexWeldedTopology"]["componentCount"])
        return int(stage["topology"]["componentCount"])

    first_components = geometry_components(stages[0])
    return {
        "stageOrder": list(STAGE_ORDER),
        "stages": stages,
        "decodedGeometryFragmented": first_components > 1,
        "decodedGeometryComponentCount": first_components,
        "firstGeometryFragmentationAmplificationStage": next(
            (
                stage["stage"]
                for stage in stages
                if geometry_components(stage) > first_components
            ),
            None,
        ),
        "clinicalClaimPermitted": False,
        "productionPromotionPermitted": False,
    }


def write_mesh_stage(mesh: trimesh.Trimesh, path: Path, stage: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(mesh.export(file_type=path.suffix.lstrip(".")))
    return {
        "stage": stage,
        "artifact": path.name,
        "artifactSha256": sha256_file(path),
        "topology": analyze_mesh(mesh),
        "topologyWeldControl": analyze_mesh_with_weld_control(mesh),
    }


def remesh_geometry_for_diagnostics(
    vertices,
    faces,
    *,
    resolution: int,
    decimation_target: int,
    remesh_band: float = 1.0,
    remesh_project: float = 0.0,
) -> trimesh.Trimesh:
    """Run only the geometry branch used by official ``to_glb(remesh=True)``.

    This deliberately stops before UV unwrapping and texture baking so a stage
    artifact can be measured. It requires the pinned CUDA CuMesh runtime and is
    called only by the isolated Modal research job.
    """
    import torch
    import cumesh

    vertices = vertices.cuda()
    faces = faces.cuda()
    mesh = cumesh.CuMesh()
    mesh.init(vertices, faces)
    mesh.fill_holes(max_hole_perimeter=3e-2)
    cleaned_vertices, cleaned_faces = mesh.read()
    bvh = cumesh.cuBVH(cleaned_vertices, cleaned_faces)
    remeshed = cumesh.remeshing.remesh_narrow_band_dc(
        cleaned_vertices,
        cleaned_faces,
        center=torch.zeros(3, device="cuda"),
        scale=(resolution + 3 * remesh_band) / resolution,
        resolution=resolution,
        band=remesh_band,
        project_back=remesh_project,
        verbose=False,
        bvh=bvh,
    )
    mesh.init(*remeshed)
    mesh.simplify(decimation_target, verbose=False)
    out_vertices, out_faces = mesh.read()
    return mesh_from_arrays(out_vertices, out_faces)
