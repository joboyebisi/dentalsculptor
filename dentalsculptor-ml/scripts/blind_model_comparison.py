"""Generate a blinded base-vs-candidate dental model review set."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path

try:
    from .benchmark_trellis_modal import request_generation
except ImportError:  # direct script execution
    from benchmark_trellis_modal import request_generation

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def blinded_order(case_id: str, seed: int) -> tuple[str, str]:
    value = hashlib.sha256(f"{case_id}:{seed}:dentalsculptor-blind-v1".encode()).digest()[0]
    return ("base", "candidate") if value % 2 == 0 else ("candidate", "base")


def extract_glb(payload: dict) -> bytes:
    encoded = payload.get("modelBase64")
    if not isinstance(encoded, str):
        raise ValueError("Generation response did not contain modelBase64; use the synchronous Modal generation endpoint.")
    result = base64.b64decode(encoded, validate=True)
    if result[:4] != b"glTF":
        raise ValueError("Generation response was not a valid GLB.")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--candidate-url", required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quality", choices=("preview", "standard", "final"), default="standard")
    parser.add_argument("--seed", type=int, default=1724708096)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    secret = os.environ.get("MODAL_WEBHOOK_SECRET")
    if not secret:
        raise SystemExit("Set MODAL_WEBHOOK_SECRET; it is never written to the review bundle.")
    images = sorted(path for path in args.images.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        raise SystemExit("No supported test images found.")
    args.output.mkdir(parents=True, exist_ok=True)
    public_cases, private_key = [], []
    for index, image in enumerate(images, 1):
        case_id = f"case-{index:03d}"
        outputs = {}
        for model, endpoint in (("base", args.base_url), ("candidate", args.candidate_url)):
            status, payload, elapsed = request_generation(endpoint, secret, image, args.quality, args.seed, args.timeout)
            if status != 200:
                raise RuntimeError(f"{model} failed for {image.name}: HTTP {status} {payload.get('detail', '')}")
            outputs[model] = {"bytes": extract_glb(payload), "metrics": payload.get("metrics", {}), "elapsed": elapsed}
        order = blinded_order(case_id, args.seed)
        labels = {"A": order[0], "B": order[1]}
        case_dir = args.output / case_id
        case_dir.mkdir(exist_ok=True)
        for label, model in labels.items():
            (case_dir / f"{label}.glb").write_bytes(outputs[model]["bytes"])
        public_cases.append({"id": case_id, "sourceImage": image.name, "seed": args.seed, "quality": args.quality,
                             "A": {"path": f"{case_id}/A.glb"}, "B": {"path": f"{case_id}/B.glb"},
                             "review": {"preferred": None, "anatomyScoreA": None, "anatomyScoreB": None,
                                        "landmarkMedianErrorMmA": None, "landmarkMedianErrorMmB": None,
                                        "ridgeGrooveContinuityA": None, "ridgeGrooveContinuityB": None}})
        private_key.append({"id": case_id, "A": labels["A"], "B": labels["B"],
                            "metrics": {model: outputs[model]["metrics"] for model in outputs},
                            "elapsedSeconds": {model: round(outputs[model]["elapsed"], 3) for model in outputs}})
    (args.output / "review-cases.json").write_text(json.dumps(public_cases, indent=2) + "\n", encoding="utf-8")
    (args.output / "DO_NOT_SHARE_blinding-key.json").write_text(json.dumps(private_key, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(public_cases), "review": str(args.output / "review-cases.json"),
                      "privateKey": str(args.output / "DO_NOT_SHARE_blinding-key.json")}, indent=2))


if __name__ == "__main__":
    main()
