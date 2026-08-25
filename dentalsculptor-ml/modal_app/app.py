"""
DentalSculptor Modal app — TRELLIS generate (GPU), Nano3D edit (CPU), job-status.

Deploy (CPU stub — no HuggingFace needed):
  python -m modal deploy -m modal_app.app

Deploy TRELLIS GPU (after HF setup — see docs/TRELLIS_GPU_SETUP.md):
  modal secret create huggingface HF_TOKEN=hf_xxxx
  $env:TRELLIS_GPU = "1"
  python -m modal deploy -m modal_app.app
"""

from __future__ import annotations

import base64
import hmac
import json
import os
import time
import traceback
import uuid

import modal
from fastapi import File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from modal_app.images.trellis_gpu import (
    GPU_TYPE,
    HF_CACHE_PATH,
    hf_cache_volume,
    hf_secret,
    trellis_gpu_image,
)
from modal_app.trellis_config import (
    ASYNC_S3_ENABLED,
    BUFFER_CONTAINERS,
    DEFAULT_QUALITY,
    HF_REPOSITORIES,
    MAX_CONTAINERS,
    MIN_CONTAINERS,
    SCALEDOWN_WINDOW,
    get_quality_preset,
    modal_runtime_env,
)
from modal_app.workers.mesh_utils import generate_response_from_image
from modal_app.workers.nano3d_utils import run_nano3d_edit
from modal_app.workers.s3_results import (
    download_mesh_state,
    upload_generation_result,
    upload_mesh_state,
    upload_preview_result,
)
from modal_app.workers.trellis_generator import (
    TrellisGenerator,
    build_success_response,
    validate_upload_metadata,
)

APP_NAME = os.getenv("MODAL_APP_NAME", "dentalsculptor")
WEB_LABEL_SUFFIX = os.getenv("MODAL_WEB_LABEL_SUFFIX", "").strip()


def web_label(name: str) -> str:
    return f"{name}-{WEB_LABEL_SUFFIX}" if WEB_LABEL_SUFFIX else name

cpu_image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastapi[standard]>=0.115.0",
    "boto3>=1.35.0",
    "pillow>=10.0.0",
    "numpy>=1.26.0",
    "trimesh>=4.0.0",
).env(modal_runtime_env())
weights_image = cpu_image.pip_install("huggingface-hub>=0.34.0")

app = modal.App(APP_NAME, image=cpu_image)
jobs_dict = modal.Dict.from_name("dentalsculptor-jobs-v1", create_if_missing=True)
webhook_secret = modal.Secret.from_name("dentalsculptor-webhook")
aws_secret = (
    modal.Secret.from_name("dentalsculptor-aws") if ASYNC_S3_ENABLED else None
)
trellis_secrets = [hf_secret, webhook_secret]
if aws_secret is not None:
    trellis_secrets.append(aws_secret)


def authorize(request: Request) -> None:
    expected = os.environ.get("MODAL_WEBHOOK_SECRET", "")
    supplied = request.headers.get("authorization", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Webhook authentication is not configured.")
    if not hmac.compare_digest(supplied, f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Unauthorized.")


@app.function(
    image=weights_image,
    timeout=60 * 60 * 6,
    secrets=[hf_secret],
    volumes={HF_CACHE_PATH: hf_cache_volume},
)
def download_trellis_weights() -> dict[str, str]:
    """Pre-cache every pinned serving artifact in the persistent HF volume."""
    from huggingface_hub import snapshot_download
    from pathlib import Path

    downloaded: dict[str, str] = {}
    for repo_id, revision in HF_REPOSITORIES.items():
        downloaded[repo_id] = snapshot_download(
            repo_id=repo_id,
            revision=revision,
            cache_dir=HF_CACHE_PATH,
        )
        ref_path = (
            Path(HF_CACHE_PATH)
            / f"models--{repo_id.replace('/', '--')}"
            / "refs"
            / "main"
        )
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(revision, encoding="utf-8")
    hf_cache_volume.commit()
    return downloaded


@app.function(image=cpu_image, timeout=600, secrets=[webhook_secret])
@modal.fastapi_endpoint(method="POST", label=web_label("generate-cpu"))
async def generate_cpu_stub(request: Request, image: UploadFile = File(...)):
    """CPU silhouette placeholder."""
    authorize(request)
    data = await image.read()
    return generate_response_from_image(data)


@app.cls(
    image=trellis_gpu_image,
    gpu=GPU_TYPE,
    secrets=trellis_secrets,
    volumes={HF_CACHE_PATH: hf_cache_volume},
    timeout=900,
    min_containers=MIN_CONTAINERS,
    buffer_containers=BUFFER_CONTAINERS,
    scaledown_window=SCALEDOWN_WINDOW,
    max_containers=MAX_CONTAINERS,
)
class TrellisGenerateService:
    @modal.enter()
    def load_model(self) -> None:
        self.generator = TrellisGenerator()
        self.generator.load_model()

    @modal.method()
    def warm(self) -> dict[str, object]:
        """Ensure GPU container is loaded; returns load timings for observability."""
        return {
            "ready": True,
            "loadTimeSeconds": self.generator.load_time,
            "loadTimings": self.generator.load_timings,
        }

    @modal.method()
    def generate_job(
        self,
        job_id: str,
        image_bytes: bytes,
        content_type: str | None,
        quality: str,
        seed: int | None,
        trace_id: str | None,
        submitted_at_ms: int,
    ) -> None:
        queue_or_cold_start_seconds = round(
            max(0.0, time.time() - (submitted_at_ms / 1000)),
            2,
        )

        def update_stage(stage: str) -> None:
            current = jobs_dict.get(job_id) or {"jobId": job_id}
            jobs_dict[job_id] = {
                **current,
                "status": "running",
                "stage": stage,
                "progress": {
                    "preprocessing": 15,
                    "generating_shape": 30,
                    "generating_material": 60,
                    "extracting_mesh": 75,
                }.get(stage, current.get("progress", 5)),
            }

        jobs_dict[job_id] = {
            "jobId": job_id,
            "status": "running",
            "stage": "starting",
            "progress": 5,
            "quality": quality,
            "traceId": trace_id,
        }
        try:
            if quality == "preview":
                preview_glb, mesh_state, resolved_seed, timings, actual_pipeline_type = (
                    self.generator.generate_preview_with_state(
                        image_bytes,
                        seed=seed,
                        content_type=content_type,
                        trace_id=trace_id,
                        stage_callback=update_stage,
                    )
                )
                jobs_dict[job_id] = {
                    **(jobs_dict.get(job_id) or {}),
                    "status": "running",
                    "stage": "uploading",
                    "progress": 90,
                }
                upload_started = time.perf_counter()
                stored = upload_preview_result(
                    job_id,
                    preview_glb,
                    metadata={
                        "quality": "preview",
                        "pipeline": actual_pipeline_type,
                        "seed": resolved_seed,
                        "trace-id": trace_id,
                    },
                )
                mesh_stored = upload_mesh_state(job_id, mesh_state)
                timings["upload"] = round(time.perf_counter() - upload_started, 2)
                timings["queueOrColdStart"] = queue_or_cold_start_seconds
                jobs_dict[job_id] = {
                    "jobId": job_id,
                    "status": "completed",
                    "stage": "completed",
                    "progress": 100,
                    "format": "glb",
                    "quality": "preview",
                    "pipelineType": actual_pipeline_type,
                    "seed": resolved_seed,
                    "timings": timings,
                    "metrics": self.generator.last_metrics,
                    "canFinalize": True,
                    "phase": "preview",
                    **stored,
                    **mesh_stored,
                }
                return

            glb, resolved_seed, timings, actual_pipeline_type = (
                self.generator.generate_glb_from_bytes(
                    image_bytes,
                    quality=quality,
                    seed=seed,
                    content_type=content_type,
                    trace_id=trace_id,
                    stage_callback=update_stage,
                )
            )
            jobs_dict[job_id] = {
                **(jobs_dict.get(job_id) or {}),
                "status": "running",
                "stage": "uploading",
                "progress": 90,
            }
            upload_started = time.perf_counter()
            stored = upload_generation_result(
                job_id,
                glb,
                metadata={
                    "quality": quality,
                    "pipeline": actual_pipeline_type,
                    "seed": resolved_seed,
                    "trace-id": trace_id,
                },
            )
            timings["upload"] = round(time.perf_counter() - upload_started, 2)
            timings["queueOrColdStart"] = queue_or_cold_start_seconds
            jobs_dict[job_id] = {
                "jobId": job_id,
                "status": "completed",
                "stage": "completed",
                "progress": 100,
                "format": "glb",
                "quality": quality,
                "pipelineType": actual_pipeline_type,
                "seed": resolved_seed,
                "timings": timings,
                "metrics": self.generator.last_metrics,
                **stored,
            }
        except Exception as exc:
            traceback.print_exc()
            jobs_dict[job_id] = {
                "jobId": job_id,
                "status": "failed",
                "stage": "failed",
                "progress": 100,
                "quality": quality,
                "error": str(exc),
            }

    @modal.method()
    def finalize_job(
        self,
        job_id: str,
        quality: str,
        trace_id: str | None,
    ) -> None:
        jobs_dict[job_id] = {
            **(jobs_dict.get(job_id) or {}),
            "status": "running",
            "stage": "extracting_mesh",
            "progress": 70,
            "quality": quality,
        }
        try:
            get_quality_preset(quality)
            prior = jobs_dict.get(job_id) or {}
            mesh_state = download_mesh_state(job_id)
            glb, timings = self.generator.extract_glb_from_state(
                mesh_state,
                quality=quality,
                trace_id=trace_id,
                seed=prior.get("seed"),
                pipeline_type=prior.get("pipelineType"),
                prior_timings=prior.get("timings"),
            )
            jobs_dict[job_id] = {
                **prior,
                "status": "running",
                "stage": "uploading",
                "progress": 90,
            }
            upload_started = time.perf_counter()
            stored = upload_generation_result(
                job_id,
                glb,
                metadata={
                    "quality": quality,
                    "pipeline": prior.get("pipelineType"),
                    "seed": prior.get("seed"),
                    "trace-id": trace_id,
                },
            )
            timings["upload"] = round(time.perf_counter() - upload_started, 2)
            jobs_dict[job_id] = {
                "jobId": job_id,
                "status": "completed",
                "stage": "completed",
                "progress": 100,
                "format": "glb",
                "quality": quality,
                "pipelineType": prior.get("pipelineType"),
                "seed": prior.get("seed"),
                "timings": timings,
                "metrics": self.generator.last_metrics,
                "canFinalize": False,
                "phase": "finalized",
                **stored,
            }
        except Exception as exc:
            traceback.print_exc()
            jobs_dict[job_id] = {
                **(jobs_dict.get(job_id) or {}),
                "jobId": job_id,
                "status": "failed",
                "stage": "failed",
                "progress": 100,
                "error": str(exc),
            }

    @modal.fastapi_endpoint(method="POST", label=web_label("generate"))
    def generate(
        self,
        request: Request,
        image: UploadFile = File(...),
        quality: str = Form("standard"),
        seed: int | None = Form(None),
        traceId: str = Form(""),
        submittedAtMs: int | None = Form(None),
    ):
        authorize(request)
        data = image.file.read()
        queue_seconds = (
            max(0.0, time.time() - (submittedAtMs / 1000))
            if submittedAtMs is not None
            else None
        )
        try:
            glb, seed, timings, actual_pipeline_type = (
                self.generator.generate_glb_from_bytes(
                    data,
                    quality=quality,
                    seed=seed,
                    content_type=image.content_type,
                    trace_id=traceId or None,
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail="The 3D reconstruction failed during model decoding.",
            ) from exc
        if queue_seconds is not None:
            timings["queueOrColdStart"] = round(queue_seconds, 2)
            self.generator.last_metrics["queueOrColdStartSeconds"] = round(
                queue_seconds, 2
            )
        print(
            "[trellis] response="
            + json.dumps(
                {
                    "traceId": traceId or None,
                    "quality": quality,
                    "pipelineType": actual_pipeline_type,
                    "queueOrColdStartSeconds": (
                        round(queue_seconds, 2)
                        if queue_seconds is not None
                        else None
                    ),
                },
                sort_keys=True,
            )
        )
        return build_success_response(
            glb,
            pipeline_type=actual_pipeline_type,
            load_time=self.generator.load_time,
            seed=seed,
            timings=timings,
            quality=quality,
            metrics=self.generator.last_metrics,
        )


@app.function(image=cpu_image, timeout=60, secrets=[webhook_secret])
@modal.fastapi_endpoint(method="POST", label=web_label("warm-gpu"))
async def warm_gpu(request: Request):
    """Spin up a GPU container and load TRELLIS (fire-and-forget)."""
    authorize(request)
    TrellisGenerateService().warm.spawn()
    return JSONResponse({"status": "warming"}, status_code=202)


@app.function(image=cpu_image, timeout=60, secrets=[webhook_secret])
@modal.fastapi_endpoint(method="POST", label=web_label("generate-job"))
async def create_generation_job(
    request: Request,
    image: UploadFile = File(...),
    quality: str = Form(DEFAULT_QUALITY),
    seed: int | None = Form(None),
    traceId: str = Form(""),
    jobId: str = Form(""),
    submittedAtMs: int | None = Form(None),
):
    authorize(request)
    if not ASYNC_S3_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Asynchronous S3 generation is disabled for this deployment.",
        )
    try:
        get_quality_preset(quality)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    data = await image.read()
    validate_upload_metadata(data, image.content_type)
    job_id = jobId.strip() or str(uuid.uuid4())
    submitted_at_ms = submittedAtMs or int(time.time() * 1000)
    jobs_dict[job_id] = {
        "jobId": job_id,
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "quality": quality,
        "traceId": traceId or None,
    }
    TrellisGenerateService().generate_job.spawn(
        job_id,
        data,
        image.content_type,
        quality,
        seed,
        traceId or None,
        submitted_at_ms,
    )
    return JSONResponse(
        {
            "jobId": job_id,
            "status": "queued",
            "stage": "queued",
            "quality": quality,
        },
        status_code=202,
    )


@app.function(image=cpu_image, timeout=60, secrets=[webhook_secret])
@modal.fastapi_endpoint(method="POST", label=web_label("finalize-job"))
async def finalize_generation_job(
    request: Request,
    jobId: str = Form(...),
    quality: str = Form("standard"),
    traceId: str = Form(""),
):
    authorize(request)
    if not ASYNC_S3_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Asynchronous S3 generation is disabled for this deployment.",
        )
    try:
        get_quality_preset(quality)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if quality == "preview":
        raise HTTPException(
            status_code=422,
            detail="Finalize requires standard or final quality.",
        )
    job_id = jobId.strip()
    if not job_id:
        raise HTTPException(status_code=422, detail="jobId is required.")
    prior = jobs_dict.get(job_id)
    if not prior or prior.get("status") != "completed" or not prior.get("canFinalize"):
        raise HTTPException(
            status_code=409,
            detail="Preview job is not ready for finalization.",
        )
    jobs_dict[job_id] = {
        **prior,
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "quality": quality,
    }
    TrellisGenerateService().finalize_job.spawn(job_id, quality, traceId or None)
    return JSONResponse(
        {
            "jobId": job_id,
            "status": "queued",
            "stage": "queued",
            "quality": quality,
        },
        status_code=202,
    )


@app.function(image=cpu_image, timeout=600)
def run_edit_job(
    job_id: str,
    source_model_url: str,
    operation: str,
    instruction: str,
    mask_bytes: bytes | None,
    reference_bytes: bytes | None = None,
    camera_json: str | None = None,
    region_marks_json: str | None = None,
    reference_edited: bool = False,
):
    jobs_dict[job_id] = {"jobId": job_id, "status": "running", "progress": 20, "stage": "preprocessing"}
    try:
        jobs_dict[job_id] = {**jobs_dict[job_id], "progress": 40, "stage": "2d_inpaint"}
        result = run_nano3d_edit(
            source_model_url,
            operation,
            instruction,
            mask_bytes,
            reference_bytes,
            camera_json,
            region_marks_json,
            reference_edited=reference_edited,
        )
        jobs_dict[job_id] = {**jobs_dict[job_id], "progress": 80, "stage": "extracting_mesh"}
        payload = {
            "jobId": job_id,
            "status": "completed",
            "progress": 100,
            "stage": result.get("source", "nano3d"),
            "format": result["format"],
            "modelBase64": base64.b64encode(result["glbBytes"]).decode("ascii"),
            "maskedVertexRatio": result.get("maskedVertexRatio", 0),
            "regionMarkCount": result.get("regionMarkCount", 0),
            "message": "Nano3D Case 3 path (CPU v1) — masked edit applied.",
        }
        edited_2d = result.get("edited2dPng")
        if edited_2d:
            payload["preview2dBase64"] = base64.b64encode(edited_2d).decode("ascii")
        jobs_dict[job_id] = payload
    except Exception as exc:
        jobs_dict[job_id] = {
            "jobId": job_id,
            "status": "failed",
            "progress": 100,
            "stage": "error",
            "error": str(exc),
        }


@app.function(image=cpu_image, timeout=600, secrets=[webhook_secret])
@modal.fastapi_endpoint(method="POST", label=web_label("edit"))
async def edit(
    request: Request,
    sourceModelUrl: str = Form(""),
    instruction: str = Form(""),
    operation: str = Form("replace"),
    camera: str = Form(""),
    regionMarks: str = Form(""),
    maskImage: UploadFile | None = File(None),
    referenceImage: UploadFile | None = File(None),
    referenceEdited: str = Form(""),
):
    authorize(request)
    job_id = str(uuid.uuid4())
    mask_bytes = await maskImage.read() if maskImage else None
    reference_bytes = await referenceImage.read() if referenceImage else None
    ref_edited = referenceEdited.strip().lower() in ("1", "true", "yes")
    jobs_dict[job_id] = {"jobId": job_id, "status": "queued", "progress": 0, "stage": "queued"}
    run_edit_job.spawn(
        job_id,
        sourceModelUrl,
        operation,
        instruction,
        mask_bytes,
        reference_bytes,
        camera or None,
        regionMarks or None,
        ref_edited,
    )
    return {"jobId": job_id, "status": "queued"}


@app.function(image=cpu_image, secrets=[webhook_secret])
@modal.fastapi_endpoint(method="GET", label=web_label("job-status"))
def job_status(request: Request, jobId: str = ""):
    authorize(request)
    if not jobId:
        return {"error": "jobId required", "status": "failed"}
    stored = jobs_dict.get(jobId)
    if stored:
        return stored
    raise HTTPException(status_code=404, detail="Job not found or expired.")
