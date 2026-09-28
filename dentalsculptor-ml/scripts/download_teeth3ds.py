"""CLI wrapper for Teeth3DS OSF download and merge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.teeth3ds_ingest import OSF_PARTS, ingest_parts, load_existing_evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--parts", default="1,2,3,4,5,6", help="Comma-separated OSF part numbers")
    parser.add_argument("--skip-download", action="store_true", help="Only merge/extract already downloaded archives")
    args = parser.parse_args()
    selected = [f"data_part_{item.strip()}" for item in args.parts.split(",") if item.strip()]
    unknown = [part for part in selected if part not in OSF_PARTS]
    if unknown:
        raise SystemExit(f"Unsupported parts: {unknown}")
    existing = load_existing_evidence(args.output)
    if existing and set(existing.get("osfParts", [])) >= set(selected) and not args.skip_download:
        print(json.dumps({"status": "already-ingested", **existing}, indent=2))
        return
    evidence = ingest_parts(args.output, selected, skip_download=args.skip_download)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
