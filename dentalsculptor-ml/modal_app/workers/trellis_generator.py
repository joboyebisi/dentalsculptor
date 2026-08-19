"""TRELLIS.2 inference — image to GLB in one GPU call."""

from __future__ import annotations

import base64
import io
import json
import secrets
import time
import uuid
from typing import Any, Callable

from modal_app.trellis_config import (
    ALLOWED_IMAGE_MIME_TYPES,
    DEFAULT_RANDOMIZE_SEED,
    DEFAULT_SEED,
    DEFAULT_QUALITY,
    ENABLE_TF32,
    ENABLE_WARMUP,
    HF_CACHE_PATH,
    HF_REPOSITORIES,
    MAX_INPUT_BYTES,
    MAX_INPUT_PIXELS,
    MODEL_NAME,
    TRELLIS_COMMIT,
    get_quality_preset,
    sampler_params_for_steps,
)

from modal_app.workers.mesh_state import deserialize_mesh, serialize_mesh

NVDIFFRAST_MAX_FACES = 16_777_216


class InferenceResult:
    """Intermediate TRELLIS output kept between preview and final GLB extraction."""

    __slots__ = ("mesh", "resolved_seed", "timings", "actual_pipeline_type", "resolved_quality")

    def __init__(
        self,
        mesh: object,
        resolved_seed: int,
        timings: dict[str, float],
        actual_pipeline_type: str,
        resolved_quality: str,
    ) -> None:
        self.mesh = mesh
        self.resolved_seed = resolved_seed
        self.timings = timings
        self.actual_pipeline_type = actual_pipeline_type
        self.resolved_quality = resolved_quality

    def serialize(self) -> bytes:
        return serialize_mesh(self.mesh)

    @classmethod
    def deserialize(cls, payload: bytes) -> InferenceResult:
        mesh = deserialize_mesh(payload)
        return cls(mesh, 0, {}, "512", "preview")


def validate_upload_metadata(image_bytes: bytes, content_type: str | None) -> None:
    if content_type and content_type.lower() not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValueError(
            f"Unsupported image type {content_type!r}; use JPEG, PNG or WebP."
        )
    if not image_bytes or len(image_bytes) > MAX_INPUT_BYTES:
        raise ValueError(
            f"Image must be between 1 byte and {MAX_INPUT_BYTES} bytes."
        )


def validate_pixel_count(width: int, height: int) -> None:
    if width < 1 or height < 1 or width * height > MAX_INPUT_PIXELS:
        raise ValueError(
            f"Image contains too many pixels; maximum is {MAX_INPUT_PIXELS}."
        )


class TrellisGenerator:
    """Loads TRELLIS.2 once per container; runs generate + GLB extract."""

    def __init__(self) -> None:
        self.pipeline = None
        self.load_time = 0.0
        self.load_timings: dict[str, float] = {}
        self.last_metrics: dict[str, Any] = {}
        self.request_count = 0

    @property
    def is_ready(self) -> bool:
        return self.pipeline is not None

    def load_model(self) -> None:
        import_started = time.perf_counter()
        import torch
        from huggingface_hub import snapshot_download

        torch.set_grad_enabled(False)
        torch.backends.cuda.matmul.allow_tf32 = ENABLE_TF32
        torch.backends.cudnn.allow_tf32 = ENABLE_TF32
        torch.set_float32_matmul_precision("high")

        from trellis2.pipelines import Trellis2ImageTo3DPipeline

        self.load_timings["imports"] = time.perf_counter() - import_started
        load_started = time.perf_counter()
        try:
            model_path = snapshot_download(
                repo_id=MODEL_NAME,
                revision=HF_REPOSITORIES[MODEL_NAME],
                cache_dir=HF_CACHE_PATH,
                local_files_only=True,
            )
        except Exception as exc:
            raise RuntimeError(
                "Pinned TRELLIS weights are missing from trellis2-hf-cache. "
                "Run `python -m modal run -m modal_app.app::download_trellis_weights` "
                "before deploying the serving app."
            ) from exc
        self.pipeline = Trellis2ImageTo3DPipeline.from_pretrained(model_path)
        self.load_timings["weights"] = time.perf_counter() - load_started
        transfer_started = time.perf_counter()
        self.pipeline.cuda()
        torch.cuda.synchronize()
        self.load_timings["cudaTransfer"] = time.perf_counter() - transfer_started

        if ENABLE_WARMUP:
            warmup_started = time.perf_counter()
            try:
                self._warmup()
                self.load_timings["warmup"] = time.perf_counter() - warmup_started
            except Exception as exc:
                self.load_timings["warmupFailed"] = time.perf_counter() - warmup_started
                print(f"[trellis] optional warmup failed: {type(exc).__name__}: {exc}")

        self.load_timings = {
            name: round(seconds, 2) for name, seconds in self.load_timings.items()
        }
        self.load_time = round(sum(self.load_timings.values()), 2)
        print(
            "[trellis] model_load="
            + json.dumps(
                {
                    "timings": self.load_timings,
                    "gpu": torch.cuda.get_device_name(0),
                    "tf32": ENABLE_TF32,
                    "commit": TRELLIS_COMMIT,
                },
                sort_keys=True,
            )
        )

    def _warmup(self) -> None:
        """Optionally initialize CUDA kernels with a deterministic lightweight run."""
        import torch
        from PIL import Image, ImageDraw

        image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((76, 28, 180, 224), fill=(236, 228, 205, 255))
        processed = self.pipeline.preprocess_image(image)
        params = sampler_params_for_steps(1)
        with torch.inference_mode():
            self.pipeline.run(
                processed,
                seed=0,
                pipeline_type="512",
                preprocess_image=False,
                sparse_structure_sampler_params=params["sparse_structure"],
                shape_slat_sampler_params=params["shape"],
                tex_slat_sampler_params=params["texture"],
            )
        torch.cuda.synchronize()

    def run_inference(
        self,
        image_bytes: bytes,
        *,
        quality: str | None = None,
        seed: int | None = None,
        content_type: str | None = None,
        trace_id: str | None = None,
        stage_callback: Callable[[str], None] | None = None,
    ) -> InferenceResult:
        import numpy as np
        import torch
        from PIL import Image

        if self.pipeline is None:
            raise RuntimeError("TRELLIS pipeline not loaded.")
        validate_upload_metadata(image_bytes, content_type)

        preset = get_quality_preset(quality)
        resolved_quality = (quality or DEFAULT_QUALITY).strip().lower()
        pipeline_type = str(preset["pipeline_type"])
        sampler_params = sampler_params_for_steps(int(preset["steps"]))
        resolved_seed = (
            secrets.randbelow(2**31)
            if seed is None and DEFAULT_RANDOMIZE_SEED
            else DEFAULT_SEED if seed is None else seed
        )
        timings: dict[str, float] = {}
        fallback_reason: str | None = None
        self.request_count += 1
        is_first_request = self.request_count == 1
        torch.cuda.reset_peak_memory_stats()

        stage_started = time.perf_counter()
        if stage_callback:
            stage_callback("preprocessing")
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
        except Exception as exc:
            raise ValueError("The uploaded file is not a readable image.") from exc
        validate_pixel_count(image.width, image.height)
        processed = self.pipeline.preprocess_image(image)
        processed_array = np.asarray(processed)
        foreground = np.max(processed_array[:, :, :3], axis=2) > 8
        foreground_fraction = float(np.count_nonzero(foreground) / foreground.size)
        if min(processed.size) < 64 or foreground_fraction < 0.01:
            raise ValueError(
                "The tooth could not be isolated from the background. "
                "Use a larger, well-lit image with one clearly visible tooth."
            )
        timings["preprocess"] = time.perf_counter() - stage_started

        stage_started = time.perf_counter()
        actual_pipeline_type = pipeline_type
        if stage_callback:
            stage_callback("generating_shape")
        try:
            with torch.inference_mode():
                meshes = self.pipeline.run(
                    processed,
                    seed=resolved_seed,
                    pipeline_type=pipeline_type,
                    preprocess_image=False,
                    sparse_structure_sampler_params=sampler_params["sparse_structure"],
                    shape_slat_sampler_params=sampler_params["shape"],
                    tex_slat_sampler_params=sampler_params["texture"],
                )
        except IndexError as exc:
            if "non-zero size" not in str(exc) or pipeline_type == "512":
                raise
            torch.cuda.empty_cache()
            actual_pipeline_type = "512"
            fallback_reason = "empty_1024_sparse_decode"
            resolved_seed = (resolved_seed + 1) % (2**31)
            print(
                "[trellis] 1024 sparse decode was empty; "
                f"retrying pipeline=512 seed={resolved_seed}"
            )
            with torch.inference_mode():
                meshes = self.pipeline.run(
                    processed,
                    seed=resolved_seed,
                    pipeline_type=actual_pipeline_type,
                    preprocess_image=False,
                    sparse_structure_sampler_params=sampler_params["sparse_structure"],
                    shape_slat_sampler_params=sampler_params["shape"],
                    tex_slat_sampler_params=sampler_params["texture"],
                )
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            raise
        mesh = meshes[0]
        if stage_callback:
            stage_callback("generating_material")
        mesh.simplify(NVDIFFRAST_MAX_FACES)
        timings["generation"] = time.perf_counter() - stage_started
        timings = {name: round(seconds, 2) for name, seconds in timings.items()}
        self.last_metrics = {
            "traceId": trace_id,
            "quality": resolved_quality,
            "pipelineType": actual_pipeline_type,
            "gpu": torch.cuda.get_device_name(0),
            "coldContainer": is_first_request,
            "seed": resolved_seed,
            "trellisCommit": TRELLIS_COMMIT,
            "inputBytes": len(image_bytes),
            "fallbackReason": fallback_reason,
            "timings": timings,
        }
        return InferenceResult(
            mesh,
            resolved_seed,
            timings,
            actual_pipeline_type,
            resolved_quality,
        )

    def extract_glb_from_mesh(
        self,
        mesh: object,
        *,
        quality: str,
        trace_id: str | None = None,
        stage_callback: Callable[[str], None] | None = None,
        seed: int | None = None,
        pipeline_type: str | None = None,
        prior_timings: dict[str, float] | None = None,
    ) -> tuple[bytes, dict[str, float]]:
        import torch
        from o_voxel.postprocess import to_glb

        preset = get_quality_preset(quality)
        resolved_quality = quality.strip().lower()
        decimation_target = int(preset["decimation_target"])
        texture_size = int(preset["texture_size"])
        timings = dict(prior_timings or {})
        stage_started = time.perf_counter()
        if stage_callback:
            stage_callback("extracting_mesh")
        with torch.inference_mode():
            glb_mesh = to_glb(
                vertices=mesh.vertices,
                faces=mesh.faces,
                attr_volume=mesh.attrs,
                coords=mesh.coords,
                attr_layout=mesh.layout,
                aabb=torch.tensor(
                    [[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
                    device="cuda",
                ),
                voxel_size=mesh.voxel_size,
                decimation_target=decimation_target,
                texture_size=texture_size,
                remesh=True,
                remesh_band=1.0,
                remesh_project=0.0,
                verbose=False,
            )
        timings["glbExtraction"] = time.perf_counter() - stage_started

        stage_started = time.perf_counter()
        buffer = io.BytesIO()
        glb_mesh.export(buffer, file_type="glb")
        buffer.seek(0)
        timings["serialization"] = time.perf_counter() - stage_started
        timings = {name: round(seconds, 2) for name, seconds in timings.items()}
        timings["total"] = round(sum(timings.values()), 2)
        output = buffer.read()
        self.last_metrics = {
            **self.last_metrics,
            "traceId": trace_id,
            "quality": resolved_quality,
            "pipelineType": pipeline_type or self.last_metrics.get("pipelineType"),
            "seed": seed if seed is not None else self.last_metrics.get("seed"),
            "outputBytes": len(output),
            "peakAllocatedBytes": torch.cuda.max_memory_allocated(),
            "peakReservedBytes": torch.cuda.max_memory_reserved(),
            "timings": timings,
            "phase": "extract",
        }
        print("[trellis] extract=" + json.dumps(self.last_metrics, sort_keys=True))
        return output, timings

    def extract_glb_from_state(
        self,
        mesh_state: bytes,
        *,
        quality: str,
        trace_id: str | None = None,
        stage_callback: Callable[[str], None] | None = None,
        seed: int | None = None,
        pipeline_type: str | None = None,
        prior_timings: dict[str, float] | None = None,
    ) -> tuple[bytes, dict[str, float]]:
        import torch

        mesh = deserialize_mesh(mesh_state)
        mesh.vertices = mesh.vertices.cuda()
        mesh.faces = mesh.faces.cuda()
        mesh.attrs = mesh.attrs.cuda()
        mesh.coords = mesh.coords.cuda()
        if isinstance(mesh.voxel_size, torch.Tensor):
            mesh.voxel_size = mesh.voxel_size.cuda()
        return self.extract_glb_from_mesh(
            mesh,
            quality=quality,
            trace_id=trace_id,
            stage_callback=stage_callback,
            seed=seed,
            pipeline_type=pipeline_type,
            prior_timings=prior_timings,
        )

    def generate_glb_from_bytes(
        self,
        image_bytes: bytes,
        *,
        quality: str | None = None,
        seed: int | None = None,
        content_type: str | None = None,
        trace_id: str | None = None,
        stage_callback: Callable[[str], None] | None = None,
    ) -> tuple[bytes, int, dict[str, float], str]:
        inference = self.run_inference(
            image_bytes,
            quality=quality,
            seed=seed,
            content_type=content_type,
            trace_id=trace_id,
            stage_callback=stage_callback,
        )
        glb, timings = self.extract_glb_from_mesh(
            inference.mesh,
            quality=inference.resolved_quality,
            trace_id=trace_id,
            stage_callback=stage_callback,
            seed=inference.resolved_seed,
            pipeline_type=inference.actual_pipeline_type,
            prior_timings=inference.timings,
        )
        self.last_metrics["inputBytes"] = len(image_bytes)
        print("[trellis] request=" + json.dumps(self.last_metrics, sort_keys=True))
        return glb, inference.resolved_seed, timings, inference.actual_pipeline_type

    def generate_preview_with_state(
        self,
        image_bytes: bytes,
        *,
        seed: int | None = None,
        content_type: str | None = None,
        trace_id: str | None = None,
        stage_callback: Callable[[str], None] | None = None,
    ) -> tuple[bytes, bytes, int, dict[str, float], str]:
        """Run inference once, return preview GLB plus serialized mesh for finalize."""
        inference = self.run_inference(
            image_bytes,
            quality="preview",
            seed=seed,
            content_type=content_type,
            trace_id=trace_id,
            stage_callback=stage_callback,
        )
        preview_glb, timings = self.extract_glb_from_mesh(
            inference.mesh,
            quality="preview",
            trace_id=trace_id,
            stage_callback=stage_callback,
            seed=inference.resolved_seed,
            pipeline_type=inference.actual_pipeline_type,
            prior_timings=inference.timings,
        )
        self.last_metrics["phase"] = "preview"
        self.last_metrics["inputBytes"] = len(image_bytes)
        print("[trellis] preview=" + json.dumps(self.last_metrics, sort_keys=True))
        return (
            preview_glb,
            inference.serialize(),
            inference.resolved_seed,
            timings,
            inference.actual_pipeline_type,
        )


def build_success_response(
    glb_bytes: bytes,
    *,
    pipeline_type: str,
    load_time: float,
    seed: int,
    timings: dict[str, float],
    quality: str = DEFAULT_QUALITY,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "jobId": str(uuid.uuid4()),
        "status": "completed",
        "format": "glb",
        "source": "modal-trellis2-gpu",
        "pipelineType": pipeline_type,
        "seed": seed,
        "quality": quality,
        "timings": timings,
        "metrics": metrics or {},
        "modelBase64": base64.b64encode(glb_bytes).decode("ascii"),
        "loadTimeSeconds": round(load_time, 2),
        "message": "TRELLIS.2 generation complete.",
    }
