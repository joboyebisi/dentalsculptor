"""Create Modal huggingface secret from HF_TOKEN in .env (avoids PowerShell arg issues)."""
import re
import subprocess
import sys
from pathlib import Path

env_path = Path(__file__).resolve().parents[2] / "dentalsculptor-app" / ".env"
token = None
for line in env_path.read_text(encoding="utf-8-sig").splitlines():
    m = re.match(r"^\s*HF_TOKEN=(.+)$", line)
    if m:
        token = m.group(1).strip().strip('"').strip("'")

if not token:
    print("ERROR: HF_TOKEN missing in .env", file=sys.stderr)
    sys.exit(1)

# Check if secret already exists
listed = subprocess.run(["modal", "secret", "list"], capture_output=True, text=True)
if listed.returncode == 0 and "huggingface" in listed.stdout:
    print("Modal secret huggingface already exists - skipping create.")
    sys.exit(0)

result = subprocess.run(
    ["modal", "secret", "create", "huggingface", f"HF_TOKEN={token}"],
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    # Already exists is OK on some Modal versions
    combined = (result.stdout + result.stderr).lower()
    if "already exists" in combined or "huggingface" in listed.stdout:
        print("Modal secret huggingface already exists.")
        sys.exit(0)
    print(result.stdout, file=sys.stderr)
    print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)

print("Modal secret huggingface created.")
