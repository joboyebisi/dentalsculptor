"""Smoke-test the deployed TRELLIS endpoint without writing the GLB to disk."""

from __future__ import annotations

import json
import argparse
import mimetypes
import re
import time
import urllib.request
import uuid
from pathlib import Path


def multipart_image(path: Path) -> tuple[bytes, str]:
    boundary = f"----DentalSculptor{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode()
        + path.read_bytes()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return body, boundary


parser = argparse.ArgumentParser()
parser.add_argument("image", type=Path)
parser.add_argument(
    "--endpoint",
    default="https://dentalsculptor--generate.modal.run",
)
parser.add_argument(
    "--quality",
    choices=("preview", "standard", "final"),
    default="standard",
)
args = parser.parse_args()
image_path = args.image
env_path = Path(__file__).resolve().parents[2] / "dentalsculptor-app" / ".env"
webhook_secret = ""
for line in env_path.read_text(encoding="utf-8-sig").splitlines():
    match = re.match(r"^\s*MODAL_WEBHOOK_SECRET=(.+)$", line)
    if match:
        webhook_secret = match.group(1).strip().strip('"').strip("'")
        break
if not webhook_secret:
    raise RuntimeError("MODAL_WEBHOOK_SECRET is missing from dentalsculptor-app/.env")

body, boundary = multipart_image(image_path)
# Insert validated quality before the closing boundary.
closing = f"--{boundary}--\r\n".encode()
body = body[: -len(closing)] + (
    f'--{boundary}\r\nContent-Disposition: form-data; name="quality"\r\n\r\n'
    f"{args.quality}\r\n"
).encode() + closing
request = urllib.request.Request(
    args.endpoint,
    data=body,
    headers={
        "Authorization": f"Bearer {webhook_secret}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    },
    method="POST",
)

started = time.time()
with urllib.request.urlopen(request, timeout=900) as response:
    result = json.loads(response.read())

print(
    json.dumps(
        {
            "seconds": round(time.time() - started, 1),
            "source": result.get("source"),
            "pipeline": result.get("pipelineType"),
            "seed": result.get("seed"),
            "timings": result.get("timings"),
            "metrics": result.get("metrics"),
            "glbBase64Chars": len(result.get("modelBase64", "")),
            "error": result.get("error"),
            "message": result.get("message"),
        },
        indent=2,
    )
)
