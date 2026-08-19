"""Diagnose HF_TOKEN in .env without printing the token."""
import re
import sys
from pathlib import Path

env_path = Path(__file__).resolve().parents[2] / "dentalsculptor-app" / ".env"
if not env_path.exists():
    print("ERROR: .env not found", file=sys.stderr)
    sys.exit(1)

token = None
for line in env_path.read_text(encoding="utf-8-sig").splitlines():
    m = re.match(r"^\s*HF_TOKEN=(.+)$", line)
    if m:
        token = m.group(1).strip().strip('"').strip("'")

if not token:
    print("ERROR: HF_TOKEN line missing or empty", file=sys.stderr)
    sys.exit(1)

print(f"format ok: starts with hf_ = {token.startswith('hf_')}, length = {len(token)}")

try:
    from huggingface_hub import HfApi

    info = HfApi(token=token).whoami()
    print("HF user:", info.get("name") or info.get("email") or "ok")
except Exception as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(1)
