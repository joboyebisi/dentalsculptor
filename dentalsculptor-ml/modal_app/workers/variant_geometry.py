"""Validated, mask-local teaching variants derived from an immutable master mesh."""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from modal_app.workers.nano3d_utils import (
    _apply_masked_mesh_deform,
    _load_mesh_from_url,
    _mask_array,
    _project_vertex_weights,
)

SEVERITY_SCALE = {"small": 0.72, "moderate": 1.0, "large": 1.35}
PRESET_CONTRACT: dict[str, tuple[str, str, str]] = {
    "fracture-small-chip": ("fracture", "boolean", "remove"),
    "fracture-oblique": ("fracture", "boolean", "remove"),
    "fracture-large": ("fracture", "boolean", "remove"),
    "class1-small": ("class-i", "boolean", "remove"),
    "class1-standard": ("class-i", "boolean", "remove"),
    "class1-deep": ("class-i", "boolean", "remove"),
    "class2-standard": ("class-ii", "boolean", "remove"),
    "endo-conservative": ("endo", "boolean", "remove"),
    "endo-traditional": ("endo", "boolean", "remove"),
    "caries-visual": ("caries", "material", "add"),
    "caries-excavate": ("caries", "boolean", "remove"),
    "crown-occlusal": ("crown", "boolean", "remove"),
    "crown-full": ("crown", "boolean", "remove"),
    "cusp-restore": ("cusp-restoration", "generative", "add"),
    "cusp-reconstruct": ("cusp-restoration", "generative", "replace"),
    "incisal-reconstruct": ("cusp-restoration", "generative", "replace"),
    "cusp-build-up": ("morphology", "deform", "add"),
    "cusp-reduction": ("morphology", "deform", "remove"),
    "surface-smooth": ("surface", "deform", "replace"),
    "surface-stain": ("surface", "material", "add"),
    "surface-whiten": ("surface", "material", "replace"),
}


def validate_variant_recipe(recipe_json: str) -> dict[str, Any]:
    try:
        recipe = json.loads(recipe_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid teaching variant recipe JSON.") from exc
    if not isinstance(recipe, dict) or recipe.get("schemaVersion") != 1:
        raise ValueError("Unsupported teaching variant recipe version.")
    preset_id = recipe.get("presetId")
    expected = PRESET_CONTRACT.get(str(preset_id))
    if not expected:
        raise ValueError("Unknown teaching variant preset.")
    actual = (recipe.get("caseId"), recipe.get("technique"), recipe.get("operation"))
    if actual != expected:
        raise ValueError("Teaching variant recipe contradicts its preset contract.")
    if recipe.get("severity") not in SEVERITY_SCALE:
        raise ValueError("Invalid teaching variant severity.")
    depth = float(recipe.get("depthMm") or 0)
    if not 0.2 <= depth <= 6.0:
        raise ValueError("Edit depth must be between 0.2 mm and 6 mm.")
    angle = float(recipe.get("angleDeg") or 0)
    if expected[0] == "fracture" and not 5 <= angle <= 85:
        raise ValueError("Fracture angle must be between 5 and 85 degrees.")
    if recipe.get("targetSurface") not in {
        "occlusal", "buccal", "lingual", "mesial", "distal", "incisal"
    }:
        raise ValueError("Invalid target surface.")
    return recipe


def _validate_source_mesh(mesh) -> None:
    vertices = np.asarray(mesh.vertices)
    if len(vertices) < 20 or len(mesh.faces) < 20:
        raise ValueError("The source model has insufficient mesh geometry for editing.")
    if not np.isfinite(vertices).all():
        raise ValueError("The source model contains invalid vertex coordinates.")
    diagonal = float(np.linalg.norm(mesh.extents))
    if not np.isfinite(diagonal) or diagonal <= 1e-8:
        raise ValueError("The source model has invalid physical bounds.")


def _validate_target(weights: np.ndarray) -> np.ndarray:
    selected = np.flatnonzero(weights > 0)
    ratio = len(selected) / max(len(weights), 1)
    if len(selected) < 4:
        raise ValueError(
            "The marked region does not intersect enough tooth geometry. "
            "Fit the tooth to view and repaint a slightly larger target."
        )
    if ratio > 0.55:
        raise ValueError(
            "The marked region covers too much of the model. "
            "Use a smaller mask around only the structure to change."
        )
    return selected


def _soften_weights(mesh, weights: np.ndarray, iterations: int = 3) -> np.ndarray:
    """Feather mask edges over mesh adjacency without escaping the local neighbourhood."""
    soft = weights.astype(np.float64, copy=True)
    neighbours = mesh.vertex_neighbors
    for _ in range(iterations):
        prior = soft.copy()
        for index, adjacent in enumerate(neighbours):
            if not adjacent:
                continue
            neighbour_mean = float(prior[np.asarray(adjacent, dtype=int)].mean())
            soft[index] = max(prior[index], neighbour_mean * 0.62)
    soft[soft < 0.08] = 0
    return np.clip(soft, 0, 1).astype(np.float32)


def _target_frame(mesh, selected: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    points = np.asarray(mesh.vertices)[selected]
    centre = points.mean(axis=0)
    normals = np.asarray(mesh.vertex_normals)[selected]
    normal = normals.mean(axis=0)
    normal_norm = float(np.linalg.norm(normal))
    if normal_norm <= 1e-8:
        normal = centre - np.asarray(mesh.centroid)
        normal_norm = float(np.linalg.norm(normal))
    normal = normal / max(normal_norm, 1e-8)

    centred = points - centre
    _, _, vh = np.linalg.svd(centred, full_matrices=False)
    tangent = vh[0] - normal * float(np.dot(vh[0], normal))
    tangent_norm = float(np.linalg.norm(tangent))
    if tangent_norm <= 1e-8:
        axis = np.array([1.0, 0.0, 0.0])
        if abs(float(np.dot(axis, normal))) > 0.9:
            axis = np.array([0.0, 1.0, 0.0])
        tangent = np.cross(normal, axis)
        tangent_norm = float(np.linalg.norm(tangent))
    tangent = tangent / max(tangent_norm, 1e-8)
    bitangent = np.cross(normal, tangent)
    bitangent /= max(float(np.linalg.norm(bitangent)), 1e-8)
    return centre, tangent, bitangent, normal


def _oriented_ellipsoid(trimesh, centre, tangent, bitangent, normal, radii):
    primitive = trimesh.creation.icosphere(subdivisions=3, radius=1.0)
    transform = np.eye(4)
    transform[:3, :3] = np.column_stack((tangent, bitangent, normal)) @ np.diag(radii)
    transform[:3, 3] = centre
    primitive.apply_transform(transform)
    return primitive


def _oriented_box(trimesh, centre, tangent, bitangent, normal, extents):
    primitive = trimesh.creation.box(extents=extents)
    transform = np.eye(4)
    transform[:3, :3] = np.column_stack((tangent, bitangent, normal))
    transform[:3, 3] = centre
    primitive.apply_transform(transform)
    return primitive


def _depth_in_model_units(recipe: dict[str, Any], diagonal: float) -> float:
    # Generated single teeth are normalized around a 12 mm long axis.
    return min(diagonal * 0.28, max(diagonal * 0.025, float(recipe["depthMm"]) * diagonal / 12.0))


def _build_cutters(mesh, recipe: dict[str, Any], selected: np.ndarray):
    import trimesh

    case_id = recipe["caseId"]
    severity = SEVERITY_SCALE[recipe["severity"]]
    diagonal = float(np.linalg.norm(mesh.extents))
    depth = _depth_in_model_units(recipe, diagonal)
    centre, tangent, bitangent, normal = _target_frame(mesh, selected)
    points = np.asarray(mesh.vertices)[selected]
    tangent_span = max(float(np.ptp((points - centre) @ tangent)), diagonal * 0.035)
    bitangent_span = max(float(np.ptp((points - centre) @ bitangent)), diagonal * 0.035)
    radius = diagonal * 0.085 * severity
    inward = centre - normal * depth * 0.34

    if case_id == "fracture":
        cutter = _oriented_ellipsoid(
            trimesh,
            centre - normal * depth * 0.12,
            tangent,
            bitangent,
            normal,
            (max(radius * 1.5, tangent_span * 0.62), max(radius * 0.8, bitangent_span * 0.5), max(depth, radius)),
        )
        angle = np.deg2rad(float(recipe["angleDeg"]))
        cutter.apply_transform(trimesh.transformations.rotation_matrix(angle, bitangent, point=centre))
        return [cutter], "fracture-ellipsoid"

    if case_id == "class-i":
        cutter = _oriented_ellipsoid(
            trimesh, inward, tangent, bitangent, normal,
            (max(radius, tangent_span * 0.52), max(radius * 0.42, bitangent_span * 0.35), depth),
        )
        return [cutter], "class-i-rounded-fissure"

    if case_id == "class-ii":
        cutter = _oriented_box(
            trimesh, inward, tangent, bitangent, normal,
            (max(radius * 1.2, tangent_span * 0.7), max(radius * 0.75, bitangent_span * 0.55), depth * 1.3),
        )
        return [cutter], "class-ii-proximal-box"

    if case_id == "endo":
        cutter = trimesh.creation.cone(radius=max(radius * 0.58, bitangent_span * 0.35), height=depth * 1.35, sections=48)
        transform = np.eye(4)
        transform[:3, :3] = np.column_stack((tangent, bitangent, normal))
        transform[:3, 3] = centre - normal * depth * 0.72
        cutter.apply_transform(transform)
        return [cutter], "endo-tapered-access"

    if case_id == "caries":
        offsets = (-0.34, 0.0, 0.31)
        cutters = [
            _oriented_ellipsoid(
                trimesh,
                inward + tangent * radius * offset,
                tangent,
                bitangent,
                normal,
                (radius * (0.55 + 0.08 * index), radius * (0.38 + 0.05 * index), depth * (0.72 + 0.1 * index)),
            )
            for index, offset in enumerate(offsets)
        ]
        return cutters, "caries-irregular-excavation"

    if case_id == "crown":
        cutter = _oriented_box(
            trimesh,
            centre + normal * depth * 0.36,
            tangent,
            bitangent,
            normal,
            (max(tangent_span * 1.2, radius * 2.4), max(bitangent_span * 1.2, radius * 2.4), depth),
        )
        return [cutter], "crown-planar-reduction"

    raise ValueError(f"No deterministic geometry strategy exists for case '{case_id}'.")


def _boolean_remove(mesh, cutters):
    result = mesh.copy()
    for cutter in cutters:
        result = __import__("trimesh").boolean.difference(
            [result, cutter], engine="manifold", check_volume=False
        )
        if result is None or not len(result.faces):
            raise ValueError("The geometry operation produced an empty model.")
    return result


def _points_inside_convex_cutter(points: np.ndarray, cutter) -> np.ndarray:
    """Classify points against a convex cutter without requiring an rtree index."""
    from scipy.spatial import ConvexHull

    hull = ConvexHull(np.asarray(cutter.vertices))
    planes = np.asarray(hull.equations)
    scale = max(float(np.linalg.norm(cutter.extents)), 1.0)
    return np.all(points @ planes[:, :3].T + planes[:, 3] <= scale * 1e-7, axis=1)


def _surface_clip_remove(mesh, cutters):
    """Remove cutter-intersecting faces and cap the new boundary.

    Generated reconstructions are frequently useful but not watertight, which makes
    solid booleans unreliable. This fallback operates on the visible surface and
    preserves the source topology everywhere outside the marked target.
    """
    import trimesh

    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    centres = vertices[faces].mean(axis=1)
    remove = np.zeros(len(faces), dtype=bool)
    for cutter in cutters:
        centre_inside = _points_inside_convex_cutter(centres, cutter)
        vertex_inside = _points_inside_convex_cutter(vertices, cutter)
        remove |= centre_inside | (vertex_inside[faces].sum(axis=1) >= 2)

    removed_count = int(remove.sum())
    if removed_count == 0:
        raise ValueError("The marked target did not intersect the source surface.")
    if removed_count >= int(len(faces) * 0.58):
        raise ValueError("The requested cut would remove too much of the source model.")

    edge_faces: dict[tuple[int, int], list[bool]] = {}
    for face, is_removed in zip(faces, remove):
        for start, end in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge = (int(min(start, end)), int(max(start, end)))
            edge_faces.setdefault(edge, []).append(bool(is_removed))
    cut_edges = [edge for edge, states in edge_faces.items() if any(states) and not all(states)]

    kept_faces = faces[~remove]
    used = np.unique(kept_faces.reshape(-1))
    remap = np.full(len(vertices), -1, dtype=np.int64)
    remap[used] = np.arange(len(used))
    result_vertices = vertices[used].copy()
    result_faces = remap[kept_faces]

    adjacency: dict[int, set[int]] = {}
    for start, end in cut_edges:
        if remap[start] < 0 or remap[end] < 0:
            continue
        adjacency.setdefault(start, set()).add(end)
        adjacency.setdefault(end, set()).add(start)
    components: list[set[int]] = []
    unseen = set(adjacency)
    while unseen:
        seed = unseen.pop()
        component = {seed}
        stack = [seed]
        while stack:
            current = stack.pop()
            for neighbour in adjacency.get(current, ()):
                if neighbour not in component:
                    component.add(neighbour)
                    unseen.discard(neighbour)
                    stack.append(neighbour)
        components.append(component)

    cap_faces: list[list[int]] = []
    cap_centres: list[np.ndarray] = []
    for component in components:
        component_edges = [edge for edge in cut_edges if edge[0] in component and edge[1] in component]
        if len(component_edges) < 3:
            continue
        centre_index = len(result_vertices) + len(cap_centres)
        cap_centres.append(vertices[np.asarray(sorted(component), dtype=int)].mean(axis=0))
        for start, end in component_edges:
            cap_faces.append([int(remap[start]), int(remap[end]), centre_index])

    if cap_centres:
        result_vertices = np.vstack((result_vertices, np.asarray(cap_centres)))
        result_faces = np.vstack((result_faces, np.asarray(cap_faces, dtype=np.int64)))

    result = trimesh.Trimesh(
        vertices=result_vertices,
        faces=result_faces,
        metadata=dict(mesh.metadata),
        process=False,
    )
    result.remove_unreferenced_vertices()
    # Avoid global winding repair here: reconstructed surfaces may have existing
    # holes/non-manifold edges, and renderers calculate per-face normals safely.
    result.metadata["surfaceClipRemovedFaces"] = removed_count
    result.metadata["surfaceClipCapFaces"] = len(cap_faces)
    return result


def _apply_material(mesh, weights: np.ndarray, preset_id: str, severity: str):
    import trimesh

    result = mesh.copy()
    soft = _soften_weights(mesh, weights, iterations=2)
    vertex_colours = getattr(result.visual, "vertex_colors", None)
    if vertex_colours is None:
        vertex_colours = result.visual.to_color().vertex_colors
    colours = np.asarray(vertex_colours).astype(np.float64)
    targets = {
        "caries-visual": np.array([88, 48, 24, 255], dtype=np.float64),
        "surface-stain": np.array([145, 102, 45, 255], dtype=np.float64),
        "surface-whiten": np.array([246, 242, 224, 255], dtype=np.float64),
    }
    target = targets[preset_id]
    strength = {"small": 0.48, "moderate": 0.7, "large": 0.88}[severity]
    # Stable enamel mottling avoids a flat painted patch while remaining deterministic.
    vertices = np.asarray(mesh.vertices)
    noise = 0.9 + 0.1 * np.sin(vertices[:, 0] * 37 + vertices[:, 1] * 53 + vertices[:, 2] * 29)
    alpha = np.clip(soft * strength * noise, 0, 1)[:, None]
    colours = colours * (1 - alpha) + target * alpha
    result.visual = trimesh.visual.ColorVisuals(result, vertex_colors=np.clip(colours, 0, 255).astype(np.uint8))
    return result, soft


def _apply_deform(mesh, weights: np.ndarray, recipe: dict[str, Any]):
    import trimesh

    soft = _soften_weights(mesh, weights, iterations=4)
    operation = recipe["operation"]
    if recipe["presetId"] == "surface-smooth":
        vertices = np.asarray(mesh.vertices).copy()
        neighbours = mesh.vertex_neighbors
        smoothed = vertices.copy()
        for index, adjacent in enumerate(neighbours):
            if adjacent:
                smoothed[index] = vertices[np.asarray(adjacent, dtype=int)].mean(axis=0)
        blend = (soft * 0.42)[:, None]
        vertices = vertices * (1 - blend) + smoothed * blend
        result = trimesh.Trimesh(
            vertices=vertices,
            faces=mesh.faces,
            visual=mesh.visual.copy(),
            metadata=dict(mesh.metadata),
            process=False,
        )
        result.fix_normals()
        return result, soft, "localized-laplacian-smoothing"

    result = _apply_masked_mesh_deform(mesh, soft, operation)
    return result, soft, f"localized-{operation}-deformation"


def _copy_vertex_colours(source, target):
    import trimesh
    from scipy.spatial import cKDTree

    try:
        colours = np.asarray(source.visual.to_color().vertex_colors)
        nearest = cKDTree(np.asarray(source.vertices)).query(np.asarray(target.vertices), k=1)[1]
        target.visual = trimesh.visual.ColorVisuals(target, vertex_colors=colours[nearest])
    except Exception:
        target.visual = trimesh.visual.ColorVisuals(
            target,
            vertex_colors=np.tile(np.array([238, 229, 205, 255], dtype=np.uint8), (len(target.vertices), 1)),
        )


def _quality_metrics(source, result, weights: np.ndarray, method: str) -> dict[str, Any]:
    source_diag = max(float(np.linalg.norm(source.extents)), 1e-9)
    bounds_drift = float(np.linalg.norm(result.extents - source.extents) / source_diag)
    centroid_drift = float(np.linalg.norm(np.asarray(result.centroid) - np.asarray(source.centroid)) / source_diag)
    metrics: dict[str, Any] = {
        "techniqueUsed": method,
        "sourceVertices": int(len(source.vertices)),
        "resultVertices": int(len(result.vertices)),
        "sourceFaces": int(len(source.faces)),
        "resultFaces": int(len(result.faces)),
        "watertight": bool(result.is_watertight),
        "sourceWatertight": bool(source.is_watertight),
        "boundsDriftRatio": bounds_drift,
        "centroidDriftRatio": centroid_drift,
        "maskedVertexRatio": float(np.count_nonzero(weights > 0) / max(len(weights), 1)),
    }
    if "surfaceClipRemovedFaces" in result.metadata:
        metrics["removedFaces"] = int(result.metadata["surfaceClipRemovedFaces"])
        metrics["capFaces"] = int(result.metadata.get("surfaceClipCapFaces", 0))
    if source.is_volume and result.is_volume and abs(float(source.volume)) > 1e-9:
        metrics["volumeChangeRatio"] = float((result.volume - source.volume) / abs(source.volume))
    return metrics


def _validate_result(source, result, recipe: dict[str, Any], metrics: dict[str, Any]) -> None:
    vertices = np.asarray(result.vertices)
    if len(vertices) < 20 or len(result.faces) < 20 or not np.isfinite(vertices).all():
        raise ValueError("The edit produced invalid or insufficient mesh geometry.")
    if metrics["boundsDriftRatio"] > 0.38 or metrics["centroidDriftRatio"] > 0.16:
        raise ValueError("The edit changed global model bounds and was rejected for safety.")
    if recipe["technique"] == "boolean":
        unchanged_topology = (
            metrics["sourceVertices"] == metrics["resultVertices"]
            and metrics["sourceFaces"] == metrics["resultFaces"]
        )
        if unchanged_topology and abs(float(metrics.get("volumeChangeRatio", 0))) < 1e-5:
            raise ValueError("The requested removal did not change the model.")
        if float(metrics.get("volumeChangeRatio", -1e-3)) > 0.015:
            raise ValueError("A removal operation unexpectedly increased model volume.")


def build_case_variant(
    mesh,
    recipe: dict[str, Any],
    mask_bytes: bytes | None,
    camera: dict[str, Any] | None,
) -> dict[str, Any]:
    _validate_source_mesh(mesh)
    width = int((camera or {}).get("width") or 512)
    height = int((camera or {}).get("height") or 512)
    weights = _project_vertex_weights(
        np.asarray(mesh.vertices),
        _camera_or_none(camera),
        _mask_array(mask_bytes, width, height),
        np.asarray(mesh.vertex_normals),
    )
    selected = _validate_target(weights)
    technique = recipe["technique"]

    if technique == "material":
        result, proof_weights = _apply_material(mesh, weights, recipe["presetId"], recipe["severity"])
        method = f"localized-material-{recipe['presetId']}"
    elif technique == "deform":
        result, proof_weights, method = _apply_deform(mesh, weights, recipe)
        _copy_vertex_colours(mesh, result)
    elif technique == "boolean":
        cutters, method = _build_cutters(mesh, recipe, selected)
        try:
            result = _boolean_remove(mesh, cutters)
        except Exception:
            result = _surface_clip_remove(mesh, cutters)
            method = f"{method}-surface-clip"
        proof_weights = weights
        _copy_vertex_colours(mesh, result)
    else:
        raise ValueError("Generative variants must use the validated FlowEdit pathway.")

    metrics = _quality_metrics(mesh, result, proof_weights, method)
    _validate_result(mesh, result, recipe, metrics)
    glb = result.export(file_type="glb")
    if len(glb) < 256:
        raise ValueError("The edited GLB is empty or corrupt.")
    return {
        "format": "glb",
        "source": method,
        "glbBytes": glb,
        "maskedVertexRatio": metrics["maskedVertexRatio"],
        "metrics": metrics,
    }


def run_case_variant(
    source_model_url: str,
    recipe_json: str,
    mask_bytes: bytes | None,
    camera_json: str | None,
) -> dict[str, Any]:
    recipe = validate_variant_recipe(recipe_json)
    try:
        camera = json.loads(camera_json) if camera_json else None
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid camera metadata.") from exc
    mesh = _load_mesh_from_url(source_model_url)
    return build_case_variant(mesh, recipe, mask_bytes, camera)


def _camera_or_none(camera):
    return camera if isinstance(camera, dict) else None
