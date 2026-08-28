#!/usr/bin/env python3
"""Modal-level cusp fracture smoke test (no browser).

Steps:
1. Generate 3D from upper molar validation image (CPU stub or GPU if configured)
2. SDXL inpaint 2D preview with synthetic cusp mask
3. Submit Nano3D image-input edit (remove)
4. Poll job status and validate GLB header

Requires MODAL_WEBHOOK_SECRET in environment.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import struct
import sys
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = (
    ROOT / "research" / "validation" / "trellis-teeth" / "images" / "12-upper-molar-three-roots-a.png"
)
OUTPUT_DIR = ROOT / "docs" / "benchmarks" / "smoke-runs"


def multipart_body(fields: dict[str, str], files: dict[str, tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = f"----ds-smoke-{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )
    for name, (filename, path) in files.items():
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode(),
                f"Content-Type: {ctype}\r\n\r\n".encode(),
                path.read_bytes(),
                b"\r\n",
            ]
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def post_multipart(url: str, secret: str, fields: dict[str, str], files: dict[str, tuple[str, Path]]) -> tuple[int, dict]:
    body, boundary = multipart_body(fields, files)
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        try:
            payload = json.loads(detail)
        except json.JSONDecodeError:
            payload = {"error": detail[:500]}
        return exc.code, payload


def get_json(url: str, secret: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {secret}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, {"error": exc.read().decode(errors="replace")[:500]}


def make_cusp_mask_png(out_path: Path, size: int = 512) -> None:
    """Simple upper-right cusp mask for smoke test."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        raise SystemExit("Install pillow: pip install pillow") from None
    img = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(img)
    draw.ellipse((size * 0.55, size * 0.08, size * 0.92, size * 0.42), fill=255)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def is_valid_glb(data: bytes) -> bool:
    if len(data) < 12:
        return False
    magic, _version, length = struct.unpack("<4sII", data[:12])
    return magic == b"glTF" and length <= len(data)


def poll_job(status_url: str, secret: str, job_id: str, timeout_s: int = 1800) -> dict:
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        code, data = get_json(f"{status_url.rstrip('/')}?jobId={job_id}", secret)
        last = data
        status = data.get("status")
        stage = data.get("stage")
        progress = data.get("progress")
        print(f"  job {job_id}: {status} / {stage} ({progress}%)")
        if status in {"completed", "failed"}:
            return data
        time.sleep(8)
    last["status"] = "timeout"
    return last


def download_result(url: str) -> bytes:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def load_webhook_secret() -> str:
    secret = os.environ.get("MODAL_WEBHOOK_SECRET", "").strip()
    if secret:
        return secret
    env_path = ROOT / "dentalsculptor-app" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("MODAL_WEBHOOK_SECRET="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Cusp fracture Modal smoke test")
    parser.add_argument("--source-image", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--generate-url", default=os.environ.get("MODAL_GENERATE_URL", "https://dentalsculptor--generate.modal.run"))
    parser.add_argument("--inpaint-url", default=os.environ.get("MODAL_INPAINT_URL", "https://dentalsculptor--inpaint.modal.run"))
    parser.add_argument("--edit-url", default=os.environ.get("MODAL_EDIT_URL", "https://dentalsculptor--edit.modal.run"))
    parser.add_argument("--job-status-url", default=os.environ.get("MODAL_JOB_STATUS_URL", "https://dentalsculptor--job-status.modal.run"))
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    secret = load_webhook_secret()
    if not secret:
        print("ERROR: Set MODAL_WEBHOOK_SECRET in env or dentalsculptor-app/.env", file=sys.stderr)
        return 1
    if not args.source_image.exists():
        print(f"ERROR: Missing source image {args.source_image}", file=sys.stderr)
        return 1

    run_dir = OUTPUT_DIR / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    mask_path = run_dir / "cusp-mask.png"
    make_cusp_mask_png(mask_path)

    result: dict = {
        "date": time.strftime("%Y-%m-%d"),
        "sourceImage": args.source_image.name,
        "seed": args.seed,
        "steps": {},
        "passed": False,
    }

    print("== 1) Generate 3D ==")
    code, gen = post_multipart(
        args.generate_url,
        secret,
        {"quality": "preview", "seed": str(args.seed)},
        {"image": (args.source_image.name, args.source_image)},
    )
    result["steps"]["generate"] = {"code": code, "response": gen}
    print(f"  generate HTTP {code}")
    if code != 200:
        print(json.dumps(gen, indent=2))
        _write_result(run_dir, result)
        return 1

    glb_b64 = gen.get("glbBase64") or gen.get("meshBase64") or gen.get("modelBase64")
    model_url = gen.get("modelUrl") or gen.get("glbUrl")
    glb_bytes: bytes | None = None
    if glb_b64:
        glb_bytes = base64.b64decode(glb_b64)
        (run_dir / "generated.glb").write_bytes(glb_bytes)
    elif model_url:
        glb_bytes = download_result(model_url)
        (run_dir / "generated.glb").write_bytes(glb_bytes)
    else:
        print("  WARN: no inline GLB — continuing with source photo only for edit path")

    if not model_url and glb_b64:
        model_url = None  # pass GLB as file upload instead of oversized form field

    print("== 2) 2D inpaint preview ==")
    code, inp = post_multipart(
        args.inpaint_url,
        secret,
        {
            "instruction": "Remove the masked cusp fragment and create an irregular oblique enamel fracture edge",
            "operation": "remove",
        },
        {
            "referenceImage": ("reference.png", args.source_image),
            "maskImage": ("mask.png", mask_path),
        },
    )
    result["steps"]["inpaint"] = {"code": code, "response": {k: v for k, v in inp.items() if k != "previewBase64"}}
    preview_provider = inp.get("provider", "unknown")
    result["previewProvider"] = preview_provider
    print(f"  inpaint HTTP {code} provider={preview_provider}")
    if code != 200 or not inp.get("previewBase64"):
        print(json.dumps(inp, indent=2)[:800])
        _write_result(run_dir, result)
        return 1
    edited_path = run_dir / "edited-preview.png"
    edited_path.write_bytes(base64.b64decode(inp["previewBase64"]))

    print("== 3) Nano3D image-input edit ==")
    edit_files: dict[str, tuple[str, Path]] = {
        "sourceImage": ("source.png", args.source_image),
        "editedImage": ("edited.png", edited_path),
    }
    if glb_bytes:
        edit_files["sourceModel"] = ("generated.glb", run_dir / "generated.glb")
    if not model_url and not glb_bytes:
        print("ERROR: no source model for edit (missing GLB from generate step)")
        _write_result(run_dir, result)
        return 1
    code, edit = post_multipart(
        args.edit_url,
        secret,
        {
            "operation": "remove",
            "instruction": "Remove the masked cusp fragment and create an irregular oblique enamel fracture edge",
            "sourceModelUrl": model_url or "",
            "seed": str(args.seed),
        },
        edit_files,
    )
    result["steps"]["edit_submit"] = {"code": code, "response": edit}
    print(f"  edit HTTP {code} provider={edit.get('provider')}")
    if code != 200:
        print(json.dumps(edit, indent=2))
        _write_result(run_dir, result)
        return 1

    job_id = edit.get("jobId")
    if not job_id:
        print("ERROR: no jobId")
        _write_result(run_dir, result)
        return 1

    print("== 4) Poll job ==")
    final = poll_job(args.job_status_url, secret, job_id)
    result["steps"]["edit_final"] = final
    result["editProvider"] = final.get("provider") or edit.get("provider")

    if final.get("status") != "completed":
        _write_result(run_dir, result)
        return 1

    out_url = final.get("modelUrl") or final.get("resultModelUrl") or final.get("glbUrl")
    glb_ok = False
    if out_url:
        edited_glb = download_result(out_url)
        (run_dir / "edited.glb").write_bytes(edited_glb)
        glb_ok = is_valid_glb(edited_glb)
        result["editedGlbBytes"] = len(edited_glb)
        result["editedGlbValid"] = glb_ok
        print(f"  edited GLB: {len(edited_glb)} bytes valid={glb_ok}")
    elif final.get("glbBase64") or final.get("modelBase64"):
        edited_glb = base64.b64decode(final.get("glbBase64") or final.get("modelBase64"))
        (run_dir / "edited.glb").write_bytes(edited_glb)
        glb_ok = is_valid_glb(edited_glb)
        result["editedGlbValid"] = glb_ok

    passed = (
        preview_provider in {"modal-sdxl-inpaint", "modal-sdxl", "fal", "sdxl"}
        and result.get("editProvider") == "nano3d-flowedit"
        and final.get("status") == "completed"
        and glb_ok
    )
    result["passed"] = passed
    _write_result(run_dir, result)
    print(f"\n{'PASS' if passed else 'FAIL'} — artifacts in {run_dir}")
    return 0 if passed else 1


def _write_result(run_dir: Path, result: dict) -> None:
    path = run_dir / "result.json"
    path.write_text(json.dumps(result, indent=2))
    print(f"Wrote {path}")


if __name__ == "__main__":
    raise SystemExit(main())
