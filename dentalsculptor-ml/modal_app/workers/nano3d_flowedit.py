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
        operation: str,
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

        def stage(name: str, progress: int) -> None:
            if stage_callback:
                stage_callback(name, progress)

        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="dentalsculptor-nano3d-") as tmp:
            root = Path(tmp)
            source_path = root / "source.png"
            target_path = root / "edited.png"
            source_path.write_bytes(source_image)
            target_path.write_bytes(edited_image)
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
        }
