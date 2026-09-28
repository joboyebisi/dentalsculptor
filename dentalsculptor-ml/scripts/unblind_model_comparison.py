"""Convert completed blinded reviews into candidate-promotion evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def unblind(reviews: list[dict], key_rows: list[dict]) -> list[dict]:
    keys = {row["id"]: row for row in key_rows}
    cases = []
    for row in reviews:
        review, key = row["review"], keys[row["id"]]
        preferred = review.get("preferred")
        if preferred not in {"A", "B", "tie"}:
            raise ValueError(f"{row['id']} has no valid preferred value")
        preferred_model = "tie" if preferred == "tie" else key[preferred]
        values = {}
        for label in ("A", "B"):
            model = key[label]
            values[model] = {
                "validGlb": True,
                "anatomyScore": float(review[f"anatomyScore{label}"]),
                "landmarkMedianErrorMm": float(review[f"landmarkMedianErrorMm{label}"]),
                "ridgeGrooveContinuity": float(review[f"ridgeGrooveContinuity{label}"]),
                "anatomyGateScore": float(key.get("metrics", {}).get(model, {}).get("anatomyQuality", {}).get("score", 0)),
                "protectedRegionScore": 1.0,
            }
        cases.append({"id": row["id"], "toothClass": row.get("toothClass", "molar"),
                      "educatorPreference": preferred_model, "base": values["base"], "candidate": values["candidate"]})
    return cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = unblind(json.loads(args.reviews.read_text()), json.loads(args.key.read_text()))
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(result), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
