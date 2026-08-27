#!/usr/bin/env python3
"""Copy generation-library teaching images into the validation set folder."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIBRARY = ROOT / "dentalsculptor-app" / "public" / "generation-library"
HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
MANIFEST = HERE / "manifest.json"

COPY_MAP = [
    ("upper-lateral-incisor-labial.png", "01-upper-lateral-incisor-labial.png"),
    ("upper-lateral-incisor-lingual.png", "02-upper-lateral-incisor-lingual.png"),
    ("upper-lateral-incisor-proximal-a.png", "03-upper-lateral-incisor-proximal-a.png"),
    ("upper-lateral-incisor-proximal-b.png", "04-upper-lateral-incisor-proximal-b.png"),
    ("upper-canine-labial-a.png", "05-upper-canine-labial-a.png"),
    ("upper-canine-labial-b.png", "06-upper-canine-labial-b.png"),
    ("upper-canine-lingual.png", "07-upper-canine-lingual.png"),
    ("upper-canine-proximal.png", "08-upper-canine-proximal.png"),
    ("upper-first-premolar-two-roots-a.png", "09-upper-first-premolar-two-roots-a.png"),
    ("upper-first-premolar-two-roots-b.png", "10-upper-first-premolar-two-roots-b.png"),
    ("premolar-single-root-proximal.png", "11-premolar-single-root-proximal.png"),
    ("upper-molar-three-roots-a.png", "12-upper-molar-three-roots-a.png"),
    ("upper-molar-three-roots-b.png", "13-upper-molar-three-roots-b.png"),
    ("upper-molar-proximal.png", "14-upper-molar-proximal.png"),
    ("lower-molar-two-roots.png", "15-lower-molar-two-roots.png"),
]


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src_name, dest_name in COPY_MAP:
        src = LIBRARY / src_name
        dest = IMAGES / dest_name
        if not src.exists():
            print(f"skip missing: {src}")
            continue
        shutil.copy2(src, dest)
        copied += 1
        print(f"copied {dest_name}")

    ready = sum(1 for item in json.loads(MANIFEST.read_text())["items"] if (IMAGES / item["filename"]).exists())
    print(f"\n{copied} files copied; {ready}/20 manifest slots have images on disk.")
    if ready < 20:
        print("Add slots 16–20 under images/ and update manifest.json when clinical photos are ready.")


if __name__ == "__main__":
    main()
