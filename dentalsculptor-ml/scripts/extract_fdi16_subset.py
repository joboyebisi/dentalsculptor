"""Extract a verified, bounded mesh subset from the official FDI-16 archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.fdi16_ingest import ingest_from_archive, load_existing_evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum", type=int, default=750)
    parser.add_argument("--force", action="store_true", help="Re-extract even if source.json exists")
    args = parser.parse_args()
    if not args.force:
        existing = load_existing_evidence(args.output)
        if existing:
            print(json.dumps(existing, indent=2))
            return
    print(json.dumps(ingest_from_archive(args.archive, args.output, args.maximum), indent=2))


if __name__ == "__main__":
    main()
