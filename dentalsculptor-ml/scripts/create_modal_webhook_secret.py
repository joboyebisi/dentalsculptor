"""Create the Modal webhook secret from the app's local environment."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parents[2] / "dentalsculptor-app" / ".env"
SECRET_NAME = "dentalsculptor-webhook"


def read_secret() -> str:
    for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"^\s*MODAL_WEBHOOK_SECRET=(.+)$", line)
        if match:
            return match.group(1).strip().strip('"').strip("'")
    return ""


secret = read_secret()
if not secret:
    print("ERROR: MODAL_WEBHOOK_SECRET missing in dentalsculptor-app/.env", file=sys.stderr)
    sys.exit(1)

listed = subprocess.run(
    ["modal", "secret", "list"],
    capture_output=True,
    text=True,
    check=False,
)
if listed.returncode == 0 and SECRET_NAME in listed.stdout:
    print(f"Modal secret {SECRET_NAME} already exists.")
    sys.exit(0)

created = subprocess.run(
    ["modal", "secret", "create", SECRET_NAME, f"MODAL_WEBHOOK_SECRET={secret}"],
    capture_output=True,
    text=True,
    check=False,
)
if created.returncode != 0:
    print(created.stdout, file=sys.stderr)
    print(created.stderr, file=sys.stderr)
    sys.exit(created.returncode)

print(f"Modal secret {SECRET_NAME} created.")
