"""Private S3 result storage for asynchronous Modal jobs."""

from __future__ import annotations

import os
from typing import Any


def _s3_client():
    import boto3

    region = os.environ.get("AWS_REGION", "eu-west-1").strip()
    return boto3.client("s3", region_name=region)


def _require_bucket() -> str:
    bucket = os.environ.get("AWS_S3_BUCKET", "").strip()
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET is required for asynchronous results.")
    return bucket


def mesh_state_key(job_id: str) -> str:
    return f"jobs/{job_id}/mesh-state.pt"


def preview_result_key(job_id: str) -> str:
    return f"jobs/{job_id}/preview.glb"


def upload_mesh_state(job_id: str, payload: bytes) -> dict[str, str]:
    bucket = _require_bucket()
    key = mesh_state_key(job_id)
    _s3_client().put_object(
        Bucket=bucket,
        Key=key,
        Body=payload,
        ContentType="application/octet-stream",
        ServerSideEncryption="AES256",
    )
    return {"meshStateKey": key}


def download_mesh_state(job_id: str) -> bytes:
    bucket = _require_bucket()
    key = mesh_state_key(job_id)
    response = _s3_client().get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def upload_preview_result(
    job_id: str,
    glb_bytes: bytes,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    bucket = _require_bucket()
    key = preview_result_key(job_id)
    string_metadata = {
        str(name): str(value)[:1024]
        for name, value in (metadata or {}).items()
        if value is not None
    }
    response = _s3_client().put_object(
        Bucket=bucket,
        Key=key,
        Body=glb_bytes,
        ContentType="model/gltf-binary",
        ServerSideEncryption="AES256",
        Metadata=string_metadata,
    )
    return {
        "resultKey": key,
        "etag": str(response.get("ETag", "")).strip('"'),
    }


def upload_generation_result(
    job_id: str,
    glb_bytes: bytes,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    bucket = _require_bucket()
    key = f"jobs/{job_id}/output.glb"
    string_metadata = {
        str(name): str(value)[:1024]
        for name, value in (metadata or {}).items()
        if value is not None
    }
    response = _s3_client().put_object(
        Bucket=bucket,
        Key=key,
        Body=glb_bytes,
        ContentType="model/gltf-binary",
        ServerSideEncryption="AES256",
        Metadata=string_metadata,
    )
    return {
        "resultKey": key,
        "etag": str(response.get("ETag", "")).strip('"'),
    }


def store_generation_result(
    job_id: str,
    glb_bytes: bytes,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Upload to S3 when configured; otherwise inline base64 for job-status polling."""
    import base64

    bucket = os.environ.get("AWS_S3_BUCKET", "").strip()
    if bucket:
        return upload_generation_result(job_id, glb_bytes, metadata=metadata)
    return {
        "modelBase64": base64.b64encode(glb_bytes).decode("ascii"),
    }
