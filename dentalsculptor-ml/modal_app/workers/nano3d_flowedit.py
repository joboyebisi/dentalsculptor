"""Programmatic adapter for upstream Nano3D image-input FlowEdit.

Pinned upstream: JAMESYJL/Nano3D@7d20eb6887cb73e3bb4ec349ee27e0b670004512
This follows inference2.py without its interactive prompt or Qwen dependency.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import Callable


def validate_localized_image_edit(source_path: Path, target_path: Path, mask_path: Path) -> dict[str, float]:
    """Reject unchanged previews and edits that repaint pixels outside the mask."""
    import numpy as np
    from PIL import Image

    source_pixels = np.asarray(Image.open(source_path).convert("RGB"), dtype=np.int16)
    target_pixels = np.asarray(Image.open(target_path).convert("RGB"), dtype=np.int16)
    mask_pixels = np.asarray(Image.open(mask_path).convert("L")) >= 128
    mask_ratio = float(mask_pixels.mean())
    if mask_ratio < 0.0005 or mask_ratio > 0.55:
        raise ValueError("The generative edit mask is empty or covers too much of the view.")
    delta = np.abs(target_pixels - source_pixels).mean(axis=2)
    outside_change_ratio = float((delta[~mask_pixels] > 18).mean())
    inside_change_ratio = float((delta[mask_pixels] > 12).mean())
    if outside_change_ratio > 0.025:
        raise ValueError("The proposed preview changes anatomy outside the marked region.")
    if inside_change_ratio < 0.005:
        raise ValueError("The proposed preview does not contain a visible edit.")
    return {
        "maskCoverageRatio": mask_ratio,
        "outsidePreviewChangeRatio": outside_change_ratio,
        "insidePreviewChangeRatio": inside_change_ratio,
    }


class Nano3DFlowEdit:
    def __init__(self) -> None:
        self.pipeline = None
        self.load_seconds = 0.0

    @staticmethod
    def _ensure_inference_package() -> None:
        """Skip Nano3D inference/__init__.py (pulls optional Qwen diffusers deps)."""
        import sys
        import types

        if "inference" in sys.modules:
            return
        root = Path(os.environ.get("NANO3D_PATH", "/opt/nano3d"))
        pkg = types.ModuleType("inference")
        pkg.__path__ = [str(root / "inference")]
        pkg.__package__ = "inference"
        sys.modules["inference"] = pkg

    def load(self) -> None:
        if self.pipeline is not None:
            return
        started = time.perf_counter()
        import torch

        self._ensure_inference_package()
        from trellis.pipelines import TrellisImageTo3DPipeline
        from inference.model_utils import inject_methods, load_sparse_structure_encoder

        torch.set_grad_enabled(False)
        pipeline = TrellisImageTo3DPipeline.from_pretrained(
            "microsoft/TRELLIS-image-large"
        )
        pipeline.cuda()
        pipeline = load_sparse_structure_encoder(pipeline)
        self.pipeline = inject_methods(pipeline)
        self.load_seconds = round(time.perf_counter() - started, 2)

    def edit_from_images(
        self,
        source_image: bytes,
        edited_image: bytes,
        source_model: bytes | None,
        operation: str,
        mask_bytes: bytes | None,
        seed: int = 1,
        stage_callback: Callable[[str, int], None] | None = None,
    ) -> dict[str, object]:
        if operation not in {"add", "remove", "replace"}:
            raise ValueError("Nano3D operation must be add, remove, or replace.")
        self.load()
        assert self.pipeline is not None

        from PIL import Image, ImageOps
        from trellis.utils import postprocessing_utils
        import torch
        import numpy as np

        def stage(name: str, progress: int) -> None:
            if stage_callback:
                stage_callback(name, progress)

        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="dentalsculptor-nano3d-") as tmp:
            root = Path(tmp)
            source_path = root / "source.png"
            target_path = root / "edited.png"
            mask_path = root / "mask.png"
            source_path.write_bytes(source_image)
            target_path.write_bytes(edited_image)
            if not mask_bytes:
                raise ValueError("A mask is required for generative edits.")
            mask_path.write_bytes(mask_bytes)
            # Normalize both sides identically; mismatched dimensions cause the
            # framing drift visible in earlier DentalSculptor previews.
            for path in (source_path, target_path):
                image = Image.open(path).convert("RGBA")
                image.thumbnail((512, 512), Image.Resampling.LANCZOS)
                # Preserve camera geometry. Stretching a wide editor capture into
                # a square was interpreted by FlowEdit as an anatomical change.
                image = ImageOps.pad(
                    image,
                    (512, 512),
                    method=Image.Resampling.LANCZOS,
                    color=(255, 255, 255, 255),
                    centering=(0.5, 0.5),
                )
                image.save(path)

            mask = Image.open(mask_path).convert("L")
            mask.thumbnail((512, 512), Image.Resampling.NEAREST)
            mask = ImageOps.pad(
                mask,
                (512, 512),
                method=Image.Resampling.NEAREST,
                color=0,
                centering=(0.5, 0.5),
            )
            mask.save(mask_path)

            edit_metrics = validate_localized_image_edit(source_path, target_path, mask_path)

            stage("reconstructing_source", 15)
            result = self.pipeline.run_custom(
                str(source_path), seed=seed, output_path=str(root)
            )

            stage("flowedit_structure", 45)
            outputs = self.pipeline.run(
                str(source_path),
                str(target_path),
                source_ply_path=str(root / "voxels.ply"),
                source_voxel_latent_path=str(root / "latent.pt"),
                source_slat=result["src_slat"],
                editing_mode=operation,
                seed=seed,
                output_path=str(root),
            )

            stage("decoding_glb", 82)
            with torch.enable_grad():
                glb = postprocessing_utils.to_glb(
                    outputs["gaussian"][0],
                    outputs["mesh"][0],
                    simplify=0.95,
                    texture_size=1024,
                )

            # FlowEdit reconstructs the source and can return a globally thinner
            # object even when only a cusp was targeted. Normalize the edited
            # scene back to the trusted generated model's bounds. This preserves
            # the original width, height, depth and export scale while leaving
            # the localized edit encoded within that coordinate frame.
            bounds_normalized = False
            bounds_drift_ratio = None
            if source_model:
                import io
                import trimesh

                source_scene = trimesh.load(io.BytesIO(source_model), file_type="glb", force="scene")
                source_bounds = np.asarray(source_scene.bounds, dtype=np.float64)
                edited_bounds = np.asarray(glb.bounds, dtype=np.float64)
                source_extent = source_bounds[1] - source_bounds[0]
                edited_extent = edited_bounds[1] - edited_bounds[0]
                if np.all(source_extent > 1e-8) and np.all(edited_extent > 1e-8):
                    axis_ratios = edited_extent / source_extent
                    if np.any(axis_ratios < 0.5) or np.any(axis_ratios > 1.85):
                        raise ValueError("Generative edit changed the global tooth proportions.")
                    # Use one uniform scale. Per-axis normalization hides and
                    # compounds elongated reconstructions.
                    scale = float(np.median(source_extent / edited_extent))
                    edited_center = edited_bounds.mean(axis=0)
                    source_center = source_bounds.mean(axis=0)
                    transform = np.eye(4)
                    transform[:3, :3] = np.eye(3) * scale
                    transform[:3, 3] = source_center - scale * edited_center
                    glb.apply_transform(transform)
                    bounds_normalized = True
                    normalized_extent = np.asarray(glb.bounds, dtype=np.float64)[1] - np.asarray(glb.bounds, dtype=np.float64)[0]
                    bounds_drift_ratio = float(
                        np.linalg.norm(normalized_extent - source_extent)
                        / max(np.linalg.norm(source_extent), 1e-9)
                    )
                    if bounds_drift_ratio > 0.32:
                        raise ValueError("Generative edit failed global bounds validation.")
            output_path = root / "edit_mesh.glb"
            glb.export(str(output_path))
            payload = output_path.read_bytes()

        return {
            "glbBytes": payload,
            "format": "glb",
            "source": "nano3d-flowedit-image-v1",
            "seed": seed,
            "loadSeconds": self.load_seconds,
            "inferenceSeconds": round(time.perf_counter() - started, 2),
            "upstreamCommit": os.environ.get(
                "NANO3D_COMMIT", "7d20eb6887cb73e3bb4ec349ee27e0b670004512"
            ),
            "boundsNormalizedToSource": bounds_normalized,
            "boundsDriftRatio": bounds_drift_ratio,
            **edit_metrics,
        }
