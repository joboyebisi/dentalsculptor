"""Bootstrap TRELLIS metadata.csv and raw asset tree from anatomy_manifest.json."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

from scripts.anatomy_common import sha256_file


def bootstrap(manifest_path: Path, source_root: Path, output_root: Path, subset: str = "DentalAnatomy") -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_dir = output_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in manifest["assets"]:
        digest = asset.get("canonicalSha256") or asset.get("rawSha256")
        if not digest:
            raise ValueError(f"Asset {asset['id']} missing sha256")
        canonical_rel = asset.get("canonicalPath") or asset.get("rawPath")
        source_path = source_root / canonical_rel
        if not source_path.is_file():
            source_path = source_root / asset["rawPath"]
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        linked = raw_dir / f"{digest}{source_path.suffix.lower()}"
        if not linked.exists() and not linked.is_file():
            shutil.copy2(source_path, linked)
        rows.append(
            {
                "sha256": digest,
                "file_identifier": asset["id"],
                "local_path": str(linked.resolve()),
                "aesthetic_score": 10.0,
                "caption": f"FDI {asset['fdiNumber']} {asset.get('toothFamily', '')}".strip(),
                "subset": subset,
                "split": asset["split"],
                "mesh_dumped": False,
            }
        )
    metadata = pd.DataFrame(rows)
    metadata.to_csv(output_root / "metadata.csv", index=False)
    (output_root / "dataset_subset.txt").write_text(subset + "\n", encoding="utf-8")
    return {"assetCount": len(rows), "metadata": str(output_root / "metadata.csv"), "subset": subset}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--subset", default="DentalAnatomy")
    args = parser.parse_args()
    print(json.dumps(bootstrap(args.manifest, args.source, args.output, args.subset), indent=2))


if __name__ == "__main__":
    main()
