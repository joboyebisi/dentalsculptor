"""Quality-control filtering for FDI-16 IOS molar pilot meshes.

This is a research triage gate, not a clinical diagnosis tool. Meshes flagged as
uncertain should be reviewed by an educator before training admission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from scripts.fdi16_ingest import DATASET_ID, FDI16_LICENSE


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(path, force="scene")
    meshes = [item for item in loaded.geometry.values() if len(item.faces)]
    if not meshes:
        raise ValueError("empty geometry")
    return trimesh.util.concatenate(tuple(meshes))


def assess_mesh(mesh: trimesh.Trimesh) -> dict:
    reasons: list[str] = []
    review_flags: list[str] = []
    observations: list[str] = []
    vertices = np.asarray(mesh.vertices, dtype=float)
    if not np.isfinite(vertices).all():
        reasons.append("non-finite-geometry")

    components = mesh.split(only_watertight=False)
    face_counts = sorted((len(part.faces) for part in components), reverse=True)
    largest_ratio = face_counts[0] / max(len(mesh.faces), 1)
    if len(face_counts) > 1 and face_counts[1] / max(len(mesh.faces), 1) > 0.08:
        reasons.append("multiple-large-components")
    elif len(face_counts) > 3:
        review_flags.append("many-connected-components")

    extents = np.asarray(mesh.extents, dtype=float)
    positive = extents[extents > 1e-8]
    if len(positive) == 0:
        reasons.append("zero-extent-geometry")
    else:
        if float(positive.min()) < 2.0:
            reasons.append("extreme-thin-dimension")
        if float(positive.max()) > 35.0:
            reasons.append("extreme-large-dimension")
        aspect = float(positive.max() / positive.min()) if len(positive) == 3 else float("inf")
        if aspect > 12.0:
            review_flags.append("elongated-aspect-ratio")

    if float(mesh.area) < 80.0:
        reasons.append("very-small-surface-area")

    edges_unique = mesh.edges_unique
    # A boundary edge belongs to exactly one face. ``edges_unique_length`` is
    # geometric length and must not be used as an incidence count.
    edge_face_counts = np.bincount(mesh.edges_unique_inverse, minlength=len(edges_unique))
    boundary_edges = edges_unique[edge_face_counts == 1]
    boundary_ratio = len(boundary_edges) / max(len(edges_unique), 1)
    if boundary_ratio > 0.22:
        review_flags.append("open-boundary-heavy")
    if boundary_ratio > 0.38:
        reasons.append("severe-truncation-or-open-surface")

    bbox = mesh.bounds
    span = bbox[1] - bbox[0]
    if float(span.max()) > 0 and float(span.min()) / float(span.max()) < 0.18:
        review_flags.append("likely-truncated-contact-surface")

    if len(components) >= 2:
        centroids = np.array([part.centroid for part in components[:4]])
        if len(centroids) >= 2:
            distances = np.linalg.norm(centroids[:, None, :] - centroids[None, :, :], axis=-1)
            distances = distances[np.triu_indices(len(centroids), k=1)]
            if len(distances) and float(distances.min()) < float(positive.max()) * 0.12:
                review_flags.append("possible-aligner-attachment")

    if not mesh.is_watertight:
        # Isolated IOS crown segments normally have an open cervical boundary.
        # Preserve this fact without sending every usable crown to manual review.
        observations.append("open-mesh-expected-for-ios-segment")

    return {
        "vertexCount": int(len(mesh.vertices)),
        "faceCount": int(len(mesh.faces)),
        "componentCount": int(len(components)),
        "largestComponentRatio": round(largest_ratio, 4),
        "extentsMm": [round(float(value), 4) for value in extents],
        "surfaceAreaMm2": round(float(mesh.area), 4),
        "boundaryEdgeRatio": round(boundary_ratio, 4),
        "watertight": bool(mesh.is_watertight),
        "rejectReasons": reasons,
        "reviewFlags": review_flags,
        "observations": observations,
        "admitted": not reasons,
        "reviewRequired": bool(review_flags) or bool(reasons),
    }


def run_qc(source_root: Path, output: Path, *, manifest_name: str = "selection_manifest.json") -> dict:
    source = json.loads((source_root / "source.json").read_text(encoding="utf-8"))
    manifest = json.loads((source_root / manifest_name).read_text(encoding="utf-8"))
    admitted, rejected, uncertain = [], [], []
    seen_hashes: dict[str, str] = {}

    total = len(manifest)
    for index, entry in enumerate(manifest, start=1):
        mesh_path = source_root / entry["relativePath"]
        digest = sha256(mesh_path)
        record = {
            **entry,
            "sha256": digest,
            "officialSplit": entry.get("officialSplit"),
            "sourceMemberPath": entry.get("sourceMemberPath"),
        }
        if digest in seen_hashes:
            rejected.append({**record, "rejectReasons": ["duplicate-mesh"], "reviewFlags": [], "admitted": False})
            continue
        seen_hashes[digest] = entry["relativePath"]
        mesh = load_mesh(mesh_path)
        metrics = assess_mesh(mesh)
        record.update(metrics)
        if metrics["rejectReasons"]:
            rejected.append(record)
        elif metrics["reviewFlags"]:
            uncertain.append(record)
            admitted.append(record)
        else:
            admitted.append(record)
        if index == 1 or index % 250 == 0 or index == total:
            print(
                f"QC progress {index}/{total}: admitted={len(admitted)} "
                f"rejected={len(rejected)} uncertain={len(uncertain)}",
                flush=True,
            )

    summary = {
        "schemaVersion": 1,
        "datasetId": source.get("datasetId", DATASET_ID),
        "license": source.get("license", FDI16_LICENSE),
        "sourceMeshCount": len(manifest),
        "admittedCount": len(admitted),
        "rejectedCount": len(rejected),
        "uncertainCount": len(uncertain),
        "admittedBySplit": {
            split: sum(1 for item in admitted if item.get("officialSplit") == split)
            for split in ("train", "validation", "test")
        },
        "rejectedByReason": {},
        "note": "Automated QC does not prove a tooth is healthy; review uncertain meshes before training.",
    }
    for item in rejected:
        for reason in item["rejectReasons"]:
            summary["rejectedByReason"][reason] = summary["rejectedByReason"].get(reason, 0) + 1

    output.mkdir(parents=True, exist_ok=True)
    (output / "qc_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output / "admitted_manifest.json").write_text(json.dumps(admitted, indent=2) + "\n", encoding="utf-8")
    (output / "rejected_manifest.json").write_text(json.dumps(rejected, indent=2) + "\n", encoding="utf-8")
    if uncertain:
        (output / "uncertain_manifest.json").write_text(json.dumps(uncertain, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="Extracted pilot root containing source.json")
    parser.add_argument("--output", type=Path, required=True, help="QC output directory")
    parser.add_argument("--manifest-name", default="selection_manifest.json", help="Manifest filename under source root")
    args = parser.parse_args()
    print(json.dumps(run_qc(args.source, args.output, manifest_name=args.manifest_name), indent=2))


if __name__ == "__main__":
    main()
