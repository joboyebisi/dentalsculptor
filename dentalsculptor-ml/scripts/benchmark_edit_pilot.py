"""Pilot edit benchmark skeleton — Nano3D image-input FlowEdit gate.

Records per-case observations for the six pilot templates defined in
docs/REALTIME_EVALUATION_HANDOFF.md. Full automation (mask capture, 2D
inpaint, edit submit) requires authenticated app session — this script
starts with direct Modal edit probes and expands to app API calls.

Usage (Modal edit probe only):

  $env:MODAL_WEBHOOK_SECRET = "<secret>"
  python scripts/benchmark_edit_pilot.py `
    --source-image ..\research\validation\trellis-teeth\images\12-upper-molar-three-roots-a.png `
    --edited-image .\fixtures\cusp-fracture-edited.png `
    --endpoint https://dentalsculptor--edit.modal.run `
    --operation remove `
    --seed 1 `
    --output ..\docs\benchmarks\edit-pilot-runs
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PILOT_CASES = (
    {"order": 1, "id": "anatomy-molar-id", "requiresEdit": False},
    {"order": 2, "id": "pathology-fracture-cusp", "operation": "remove", "preset": "cusp-fracture"},
    {"order": 3, "id": "prep-class-1-amalgam", "operation": "remove", "preset": "class1-prep"},
    {"order": 4, "id": "endo-access-intro", "operation": "remove", "preset": "endo-access"},
    {"order": 5, "id": "caries-occlusal-excavation", "operation": "remove", "preset": "remove-caries"},
    {"order": 6, "id": "crown-prep-molar", "operation": "remove", "preset": "crown-prep"},
)


@dataclass
class EditObservation:
    case_id: str
    operation: str
    seed: int
    ok: bool
    status_code: int
    job_id: str | None
    provider: str | None
    error: str | None
    submit_seconds: float
    poll_seconds: float | None
    final_status: str | None


def multipart_edit_body(
    fields: dict[str, str],
    files: dict[str, Path],
) -> tuple[bytes, str]:
    boundary = f"----dentalsculptor-edit-{uuid.uuid4().hex}"
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
    for name, path in files.items():
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{path.name}"\r\n'
                ).encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                path.read_bytes(),
                b"\r\n",
            ]
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def submit_edit_job(
    endpoint: str,
    secret: str,
    source_image: Path,
    edited_image: Path,
    operation: str,
    seed: int,
    job_status_url: str | None,
) -> EditObservation:
    started = time.perf_counter()
    body, boundary = multipart_edit_body(
        {
            "operation": operation,
            "instruction": "benchmark edit probe",
            "sourceModelUrl": "https://example.invalid/benchmark.glb",
            "seed": str(seed),
        },
        {
            "sourceImage": source_image,
            "editedImage": edited_image,
        },
    )
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode())
            submit_seconds = time.perf_counter() - started
            job_id = payload.get("jobId")
            provider = payload.get("provider")
            poll_seconds = None
            final_status = payload.get("status")
            if job_id and job_status_url:
                poll_started = time.perf_counter()
                final_status = poll_job(job_status_url, secret, job_id)
                poll_seconds = time.perf_counter() - poll_started
            return EditObservation(
                case_id="direct-modal-probe",
                operation=operation,
                seed=seed,
                ok=resp.status == 200 and final_status in (None, "completed", "queued", "running"),
                status_code=resp.status,
                job_id=job_id,
                provider=provider,
                error=None,
                submit_seconds=submit_seconds,
                poll_seconds=poll_seconds,
                final_status=final_status,
            )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        return EditObservation(
            case_id="direct-modal-probe",
            operation=operation,
            seed=seed,
            ok=False,
            status_code=exc.code,
            job_id=None,
            provider=None,
            error=detail[:500],
            submit_seconds=time.perf_counter() - started,
            poll_seconds=None,
            final_status=None,
        )
    except Exception as exc:  # noqa: BLE001 — benchmark CLI
        return EditObservation(
            case_id="direct-modal-probe",
            operation=operation,
            seed=seed,
            ok=False,
            status_code=0,
            job_id=None,
            provider=None,
            error=str(exc),
            submit_seconds=time.perf_counter() - started,
            poll_seconds=None,
            final_status=None,
        )


def poll_job(status_url: str, secret: str, job_id: str, timeout_s: int = 900) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        req = urllib.request.Request(
            f"{status_url.rstrip('/')}?jobId={job_id}",
            headers={"Authorization": f"Bearer {secret}"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        status = data.get("status", "unknown")
        if status in {"completed", "failed"}:
            return status
        time.sleep(5)
    return "timeout"


def write_summary(output_dir: Path, observations: list[EditObservation]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "observations.json"
    json_path.write_text(json.dumps([asdict(o) for o in observations], indent=2))
    md_path = output_dir / "summary.md"
    lines = [
        "# Edit pilot benchmark run",
        "",
        f"- Observations: {len(observations)}",
        f"- Passed: {sum(1 for o in observations if o.ok)}",
        "",
        "| case | ok | provider | final_status | submit_s | poll_s |",
        "|------|----|-----------|--------------|---------:|-------:|",
    ]
    for o in observations:
        lines.append(
            f"| {o.case_id} | {o.ok} | {o.provider or '-'} | {o.final_status or '-'} | "
            f"{o.submit_seconds:.1f} | {o.poll_seconds if o.poll_seconds is not None else '-'} |"
        )
    md_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pilot edit benchmark (Modal probe skeleton)")
    parser.add_argument("--source-image", type=Path, required=True)
    parser.add_argument("--edited-image", type=Path, required=True)
    parser.add_argument("--endpoint", required=True, help="MODAL_EDIT_URL")
    parser.add_argument("--job-status-url", default="", help="MODAL_JOB_STATUS_URL")
    parser.add_argument("--operation", default="remove", choices=["add", "remove", "replace"])
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("../docs/benchmarks/edit-pilot-runs"))
    args = parser.parse_args()

    secret = __import__("os").environ.get("MODAL_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise SystemExit("Set MODAL_WEBHOOK_SECRET")

    obs = submit_edit_job(
        args.endpoint,
        secret,
        args.source_image,
        args.edited_image,
        args.operation,
        args.seed,
        args.job_status_url or None,
    )
    write_summary(args.output, [obs])


if __name__ == "__main__":
    main()
