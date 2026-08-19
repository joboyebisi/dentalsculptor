"""Benchmark deployed TRELLIS Modal endpoints with fixed dental inputs and seeds.

The script never fabricates cold/warm labels: it records the worker's
``metrics.coldContainer`` value. To obtain a real cold sample, scale the
development app to zero or redeploy before starting a matrix cell.
"""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
import os
import statistics
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PRESETS = ("preview", "standard", "final")
FIXED_SEEDS = (
    1724708096,
    401927113,
    918273645,
    125680934,
    2093847561,
    772345018,
    319876542,
    1452098736,
    608431927,
    198765432,
)


@dataclass
class Observation:
    gpu: str
    quality: str
    image: str
    seed: int
    run: int
    requested_cold_candidate: bool
    server_cold_container: bool | None
    ok: bool
    status_code: int
    end_to_end_seconds: float
    server_total_seconds: float | None
    peak_reserved_bytes: int | None
    error: str | None


def parse_mapping(values: list[str], label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{label} must use NAME=VALUE syntax: {value!r}")
        name, mapped = value.split("=", 1)
        result[name.strip()] = mapped.strip()
    return result


def multipart_body(fields: dict[str, str], image_path: Path) -> tuple[bytes, str]:
    boundary = f"----dentalsculptor-{uuid.uuid4().hex}"
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
    content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="image"; '
                f'filename="{image_path.name}"\r\n'
            ).encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            image_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(parts), boundary


def request_generation(
    endpoint: str,
    secret: str,
    image_path: Path,
    quality: str,
    seed: int,
    timeout: int,
) -> tuple[int, dict[str, Any], float]:
    fields = {
        "quality": quality,
        "seed": str(seed),
        "traceId": f"benchmark-{uuid.uuid4()}",
        "submittedAtMs": str(int(time.time() * 1000)),
    }
    body, boundary = multipart_body(fields, image_path)
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload, time.perf_counter() - started
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"detail": raw[:500]}
        return exc.code, payload, time.perf_counter() - started


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentile_value * len(ordered)) - 1)
    return round(ordered[index], 3)


def summarize(
    observations: list[Observation],
    hourly_rates: dict[str, float],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    cells = sorted({(item.gpu, item.quality) for item in observations})
    for gpu, quality in cells:
        cell = [
            item for item in observations if item.gpu == gpu and item.quality == quality
        ]
        successes = [item for item in cell if item.ok]
        warm = [
            item.end_to_end_seconds
            for item in successes
            if item.server_cold_container is False
        ]
        server_seconds = [
            item.server_total_seconds
            for item in successes
            if item.server_total_seconds is not None
        ]
        rate = hourly_rates.get(gpu)
        estimated_cost = (
            round(statistics.mean(server_seconds) * (rate / 3600), 6)
            if rate is not None and server_seconds
            else None
        )
        summaries.append(
            {
                "gpu": gpu,
                "quality": quality,
                "attempts": len(cell),
                "successes": len(successes),
                "failureRate": round(1 - (len(successes) / len(cell)), 4)
                if cell
                else None,
                "warmP50Seconds": percentile(warm, 0.50),
                "warmP95Seconds": percentile(warm, 0.95),
                "peakReservedBytes": max(
                    (
                        item.peak_reserved_bytes
                        for item in successes
                        if item.peak_reserved_bytes is not None
                    ),
                    default=None,
                ),
                "estimatedGpuCostPerSuccess": estimated_cost,
                "hourlyGpuRateProvided": rate,
            }
        )
    return summaries


def markdown_report(summary: list[dict[str, Any]]) -> str:
    lines = [
        "# TRELLIS Modal benchmark",
        "",
        "Latency and cost values below are measured or calculated from this run. "
        "`—` means the endpoint did not report enough evidence.",
        "",
        "| GPU | Preset | Attempts | Failures | Warm p50 | Warm p95 | Peak reserved | Est. GPU cost/success |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        failures = row["attempts"] - row["successes"]
        peak = row["peakReservedBytes"]
        lines.append(
            "| {gpu} | {quality} | {attempts} | {failures} | {p50} | {p95} | {peak} | {cost} |".format(
                gpu=row["gpu"],
                quality=row["quality"],
                attempts=row["attempts"],
                failures=failures,
                p50=f'{row["warmP50Seconds"]:.3f}s'
                if row["warmP50Seconds"] is not None
                else "—",
                p95=f'{row["warmP95Seconds"]:.3f}s'
                if row["warmP95Seconds"] is not None
                else "—",
                peak=f"{peak / (1024**3):.2f} GiB" if peak is not None else "—",
                cost=f'${row["estimatedGpuCostPerSuccess"]:.6f}'
                if row["estimatedGpuCostPerSuccess"] is not None
                else "—",
            )
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument(
        "--endpoint",
        action="append",
        required=True,
        help="Repeat as GPU=URL for L40S, A100-40GB and H100 development apps.",
    )
    parser.add_argument(
        "--gpu-hourly-rate",
        action="append",
        default=[],
        help="Optional measured/current price as GPU=USD_PER_HOUR.",
    )
    parser.add_argument("--warm-runs", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    secret = os.getenv("MODAL_WEBHOOK_SECRET", "")
    if not secret:
        raise SystemExit("MODAL_WEBHOOK_SECRET is required.")
    endpoints = parse_mapping(args.endpoint, "--endpoint")
    raw_rates = parse_mapping(args.gpu_hourly_rate, "--gpu-hourly-rate")
    hourly_rates = {gpu: float(rate) for gpu, rate in raw_rates.items()}
    images = sorted(
        path
        for path in args.images.iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if len(images) != 10:
        raise SystemExit(f"Expected exactly 10 validation images, found {len(images)}.")

    observations: list[Observation] = []
    for gpu, endpoint in endpoints.items():
        for quality in PRESETS:
            for image_index, image_path in enumerate(images):
                seed = FIXED_SEEDS[image_index]
                for run in range(args.warm_runs + 1):
                    status = 0
                    payload: dict[str, Any] = {}
                    elapsed = 0.0
                    error: str | None = None
                    try:
                        status, payload, elapsed = request_generation(
                            endpoint,
                            secret,
                            image_path,
                            quality,
                            seed,
                            args.timeout,
                        )
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                    metrics = payload.get("metrics") or {}
                    timings = payload.get("timings") or {}
                    ok = status == 200 and payload.get("status") == "completed"
                    if not ok and error is None:
                        error = str(
                            payload.get("detail")
                            or payload.get("error")
                            or f"HTTP {status}"
                        )
                    observation = Observation(
                        gpu=gpu,
                        quality=quality,
                        image=image_path.name,
                        seed=seed,
                        run=run,
                        requested_cold_candidate=run == 0,
                        server_cold_container=metrics.get("coldContainer"),
                        ok=ok,
                        status_code=status,
                        end_to_end_seconds=round(elapsed, 3),
                        server_total_seconds=timings.get("total"),
                        peak_reserved_bytes=metrics.get("peakReservedBytes"),
                        error=error,
                    )
                    observations.append(observation)
                    print(json.dumps(asdict(observation), sort_keys=True), flush=True)

    summary = summarize(observations, hourly_rates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(
        json.dumps(
            {
                "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "observations": [asdict(item) for item in observations],
                "summary": summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    args.output.with_suffix(".md").write_text(
        markdown_report(summary),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
