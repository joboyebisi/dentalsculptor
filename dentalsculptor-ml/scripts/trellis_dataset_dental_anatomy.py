"""Minimal TRELLIS data_toolkit dataset adapter for canonical dental anatomy meshes."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import partial

import pandas as pd
from tqdm import tqdm


def add_args(parser) -> None:
    parser.add_argument("--subset", type=str, default="DentalAnatomy", help="Dataset subset label")


def foreach_instance(metadata, download_root, func, max_workers=0, desc="Processing", no_file=False, **_kwargs):
    del download_root, _kwargs
    if hasattr(metadata, "reset_index") and (
        metadata.index.name == "sha256" or "sha256" not in getattr(metadata, "columns", [])
    ):
        metadata = metadata.reset_index()
    rows = metadata.to_dict("records")
    records = []

    def _run(row):
        try:
            if no_file:
                result = func(None, row)
            else:
                result = func(row["local_path"], row)
            return result or {"sha256": row["sha256"]}
        except Exception as error:
            return {"sha256": row["sha256"], "error": str(error)}

    if max_workers and max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for result in tqdm(pool.map(_run, rows), total=len(rows), desc=desc):
                if result:
                    records.append(result)
    else:
        for row in tqdm(rows, desc=desc):
            result = _run(row)
            if result:
                records.append(result)
    return pd.DataFrame.from_records(records)
