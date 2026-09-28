"""Create standardized multi-view review images and a fail-closed audit queue."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

RENDERER_VERSION = "toothfairy-review-v2-six-view-full-surface"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def review_eligibility(asset: dict) -> tuple[bool, list[str]]:
    reasons = []
    if asset.get("touchesVolumeBoundary"):
        reasons.append("volume-boundary-contact-possible-apex-truncation")
    reasons.extend(
        flag for flag in asset.get("reviewFlags", [])
        if flag == "non-watertight-extracted-surface"
    )
    return not reasons, sorted(set(reasons))


def canonical_review_vertices(vertices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """PCA-align a tooth and put the broader (usually crown) end at the top."""
    vertices = np.asarray(vertices, dtype=float)
    centered = vertices - vertices.mean(axis=0)
    values, vectors = np.linalg.eigh(np.cov(centered.T))
    order = np.argsort(values)
    x_axis = vectors[:, order[0]]
    z_axis = vectors[:, order[-1]]
    y_axis = np.cross(z_axis, x_axis)
    y_axis /= np.linalg.norm(y_axis)
    rotation = np.column_stack((x_axis, y_axis, z_axis))
    aligned = centered @ rotation
    z = aligned[:, 2]
    low, high = np.quantile(z, [0.2, 0.8])
    transverse = np.linalg.norm(aligned[:, :2], axis=1)
    bottom_width = float(np.median(transverse[z <= low]))
    top_width = float(np.median(transverse[z >= high]))
    if top_width < bottom_width:
        aligned[:, 1:] *= -1
        rotation[:, 1:] *= -1
    return aligned, rotation


def _render_view(
    draw: ImageDraw.ImageDraw,
    mesh: trimesh.Trimesh,
    aligned: np.ndarray,
    rotation: np.ndarray,
    *,
    azimuth: float,
    box: tuple[int, int, int, int],
    max_faces: int,
) -> None:
    angle = np.deg2rad(azimuth)
    horizontal = aligned[:, 0] * np.cos(angle) - aligned[:, 1] * np.sin(angle)
    depth = aligned[:, 0] * np.sin(angle) + aligned[:, 1] * np.cos(angle)
    vertical = aligned[:, 2]
    left, top, right, bottom = box
    margin = 28
    scale = min(
        (right - left - margin * 2) / max(float(np.ptp(horizontal)), 1e-6),
        (bottom - top - margin * 2) / max(float(np.ptp(vertical)), 1e-6),
    )
    sx = (left + right) / 2 + horizontal * scale
    sy = (top + bottom) / 2 - vertical * scale
    faces = np.asarray(mesh.faces)
    face_indices = np.arange(len(faces))
    if len(face_indices) > max_faces:
        face_indices = face_indices[:: int(np.ceil(len(face_indices) / max_faces))]
    face_indices = face_indices[np.argsort(depth[faces[face_indices]].mean(axis=1))]
    normals = np.asarray(mesh.face_normals) @ rotation
    light = np.array([-0.35, -0.25, 0.9])
    light /= np.linalg.norm(light)
    intensity = np.clip(normals @ light * 0.38 + 0.62, 0.25, 1.0)
    for face_index in face_indices:
        points = [(float(sx[index]), float(sy[index])) for index in faces[face_index]]
        shade = int(185 + 65 * intensity[face_index])
        draw.polygon(points, fill=(shade, int(shade * 0.96), int(shade * 0.84)))


def _render_axial_view(
    draw: ImageDraw.ImageDraw,
    mesh: trimesh.Trimesh,
    aligned: np.ndarray,
    rotation: np.ndarray,
    *,
    apical: bool,
    box: tuple[int, int, int, int],
    max_faces: int,
) -> None:
    horizontal = aligned[:, 0]
    vertical = aligned[:, 1] * (-1 if apical else 1)
    depth = aligned[:, 2] * (-1 if apical else 1)
    left, top, right, bottom = box
    margin = 28
    scale = min(
        (right - left - margin * 2) / max(float(np.ptp(horizontal)), 1e-6),
        (bottom - top - margin * 2) / max(float(np.ptp(vertical)), 1e-6),
    )
    sx = (left + right) / 2 + horizontal * scale
    sy = (top + bottom) / 2 - vertical * scale
    faces = np.asarray(mesh.faces)
    face_indices = np.arange(len(faces))
    if len(face_indices) > max_faces:
        face_indices = face_indices[:: int(np.ceil(len(face_indices) / max_faces))]
    face_indices = face_indices[np.argsort(depth[faces[face_indices]].mean(axis=1))]
    normals = np.asarray(mesh.face_normals) @ rotation
    light = np.array([-0.35, -0.25, -0.9 if apical else 0.9])
    light /= np.linalg.norm(light)
    intensity = np.clip(normals @ light * 0.38 + 0.62, 0.25, 1.0)
    for face_index in face_indices:
        points = [(float(sx[index]), float(sy[index])) for index in faces[face_index]]
        shade = int(185 + 65 * intensity[face_index])
        draw.polygon(points, fill=(shade, int(shade * 0.96), int(shade * 0.84)))


def render_review_image(mesh: trimesh.Trimesh, asset: dict, destination: Path) -> None:
    width, height = 1800, 920
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(18)
    aligned, rotation = canonical_review_vertices(np.asarray(mesh.vertices))
    panel_width = width // 3
    panel_height = 410
    for index, azimuth in enumerate((0, 90, 180, 270)):
        column, row = index % 3, index // 3
        left, top = column * panel_width, row * panel_height
        draw.rectangle((left, top, left + panel_width - 1, top + panel_height - 1), outline="#d7deea")
        _render_view(
            draw, mesh, aligned, rotation,
            azimuth=azimuth,
            box=(left, top + 42, left + panel_width, top + panel_height - 8),
            max_faces=100000,
        )
        draw.text((left + 12, top + 12), f"circumferential {azimuth} deg", fill="#173568", font=font)
    for offset, (label, apical) in enumerate((("occlusal", False), ("apical", True)), start=4):
        column, row = offset % 3, offset // 3
        left, top = column * panel_width, row * panel_height
        draw.rectangle((left, top, left + panel_width - 1, top + panel_height - 1), outline="#d7deea")
        _render_axial_view(
            draw, mesh, aligned, rotation,
            apical=apical,
            box=(left, top + 42, left + panel_width, top + panel_height - 8),
            max_faces=100000,
        )
        draw.text((left + 12, top + 12), label, fill="#173568", font=font)
    title = (
        f"{asset['groupId']} | FDI {asset['fdiNumber']} | {asset['toothFamily']} | "
        f"{asset['vertexCount']} vertices | extents {asset['extentsMm']} mm"
    )
    draw.text((16, 844), title, fill="#172033", font=font)
    draw.text(
        (16, 872),
        "Clinical review: identity | complete crown | complete root/apex | segmentation leakage | artifact",
        fill="#52637a",
        font=font,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, optimize=True)


def write_review_form(records: list[dict], destination: Path) -> None:
    with destination.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = [
            "id", "groupId", "split", "fdiNumber", "toothFamily", "automaticGate",
            "reviewRenderPath", "reviewer", "status", "toothIdentityCorrect",
            "crownComplete", "rootAndApexComplete", "segmentationLeakage",
            "artifactSeverity", "notes",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            audit = record["clinicalAudit"]
            writer.writerow({
                "id": record["id"], "groupId": record["groupId"], "split": record["split"],
                "fdiNumber": record["fdiNumber"], "toothFamily": record["toothFamily"],
                "automaticGate": record["automaticGate"],
                "reviewRenderPath": record.get("reviewRenderPath", ""), "reviewer": "",
                "status": audit["status"], "toothIdentityCorrect": "", "crownComplete": "",
                "rootAndApexComplete": "", "segmentationLeakage": "",
                "artifactSeverity": "", "notes": "",
            })


def build_review_queue(manifest_path: Path, dataset_root: Path, output: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    render_dir = output / "renders"
    records = []
    for index, asset in enumerate(manifest["assets"], start=1):
        eligible, reasons = review_eligibility(asset)
        record = {
            "id": asset["id"],
            "groupId": asset["groupId"],
            "split": asset["split"],
            "fdiNumber": asset["fdiNumber"],
            "toothFamily": asset["toothFamily"],
            "rawMeshPath": asset["rawMeshPath"],
            "rawMeshSha256": asset["rawMeshSha256"],
            "automaticGate": "eligible-for-clinical-review" if eligible else "quarantined",
            "automaticExclusionReasons": reasons,
            "clinicalAudit": {
                "status": "pending" if eligible else "automatically-excluded",
                "reviewer": None,
                "toothIdentityCorrect": None,
                "crownComplete": None,
                "rootAndApexComplete": None,
                "segmentationLeakage": None,
                "artifactSeverity": None,
                "notes": None,
            },
        }
        if eligible:
            mesh_path = dataset_root / asset["rawMeshPath"]
            mesh = trimesh.load(mesh_path, force="mesh", process=False)
            destination = render_dir / f"{asset['id']}.png"
            render_review_image(mesh, asset, destination)
            record["reviewRenderPath"] = destination.relative_to(output).as_posix()
            record["reviewRenderSha256"] = sha256_file(destination)
        records.append(record)
        if index == 1 or index % 25 == 0 or index == len(manifest["assets"]):
            print(f"Review rendering {index}/{len(manifest['assets'])}", flush=True)
    queue = {
        "schemaVersion": 1,
        "rendererVersion": RENDERER_VERSION,
        "datasetId": manifest["datasetId"],
        "sourceManifestSha256": sha256_file(manifest_path),
        "assetCount": len(records),
        "pendingClinicalReviewCount": sum(
            record["clinicalAudit"]["status"] == "pending" for record in records
        ),
        "automaticExclusionCount": sum(
            record["clinicalAudit"]["status"] == "automatically-excluded" for record in records
        ),
        "records": records,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "clinical_review_queue.json").write_text(
        json.dumps(queue, indent=2) + "\n", encoding="utf-8"
    )
    write_review_form(records, output / "clinical_review_form.csv")
    return queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    queue = build_review_queue(args.manifest, args.dataset_root, args.output)
    print(json.dumps({
        "assetCount": queue["assetCount"],
        "pendingClinicalReviewCount": queue["pendingClinicalReviewCount"],
        "automaticExclusionCount": queue["automaticExclusionCount"],
    }, indent=2))


if __name__ == "__main__":
    main()
