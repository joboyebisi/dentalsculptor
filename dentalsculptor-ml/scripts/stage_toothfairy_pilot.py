"""Deterministically stage a bounded ToothFairy2 label-volume pilot from its archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath


LABEL_RE = re.compile(r"(?:^|/)labelsTr/(ToothFairy2([FP])_\d+)\.mha$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_entries(
    names: list[str], *, per_prefix: int, seed: int,
    exclude_subjects: set[str] | None = None,
) -> list[tuple[str, str, str]]:
    exclude_subjects = exclude_subjects or set()
    candidates: dict[str, list[tuple[str, str]]] = {"F": [], "P": []}
    for name in names:
        match = LABEL_RE.search(name)
        if match:
            subject_id, prefix = match.groups()
            if subject_id in exclude_subjects:
                continue
            candidates[prefix].append((subject_id, name))
    selected: list[tuple[str, str, str]] = []
    for prefix in ("F", "P"):
        ranked = sorted(
            candidates[prefix],
            key=lambda item: hashlib.sha256(f"{seed}:{item[0]}".encode()).hexdigest(),
        )
        if len(ranked) < per_prefix:
            raise ValueError(f"Archive only contains {len(ranked)} {prefix} label volumes")
        selected.extend((prefix, subject_id, name) for subject_id, name in ranked[:per_prefix])
    return selected


def stage_pilot(
    archive: Path, output: Path, *, per_prefix: int, seed: int,
    exclude_subjects: set[str] | None = None,
) -> dict:
    archive = archive.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as handle:
        infos = {entry.filename: entry for entry in handle.infolist()}
        selected = select_entries(
            list(infos), per_prefix=per_prefix, seed=seed,
            exclude_subjects=exclude_subjects,
        )
        assets = []
        for prefix, subject_id, entry_name in selected:
            target = (output / PurePosixPath(entry_name).name).resolve()
            if output not in target.parents:
                raise ValueError(f"Unsafe extraction target: {target}")
            with handle.open(entry_name) as source, target.open("wb") as destination:
                for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
                    destination.write(chunk)
            assets.append({
                "subjectId": subject_id,
                "acquisitionSet": prefix,
                "archiveEntry": entry_name,
                "archiveEntryBytes": infos[entry_name].file_size,
                "stagedFilename": target.name,
                "stagedBytes": target.stat().st_size,
                "sha256": sha256_file(target),
            })
    receipt = {
        "schemaVersion": 1,
        "dataset": "ToothFairy2",
        "selectionSeed": seed,
        "subjectsPerAcquisitionSet": per_prefix,
        "subjectCount": len(assets),
        "archiveFilename": archive.name,
        "excludedSubjectIds": sorted(exclude_subjects or set()),
        "assets": assets,
    }
    (output / "pilot_staging_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-prefix", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260918)
    parser.add_argument("--exclude-subject", action="append", default=[])
    args = parser.parse_args()
    if args.per_prefix < 1:
        raise SystemExit("--per-prefix must be positive")
    receipt = stage_pilot(
        args.archive, args.output, per_prefix=args.per_prefix, seed=args.seed,
        exclude_subjects=set(args.exclude_subject),
    )
    print(json.dumps({
        "subjectCount": receipt["subjectCount"],
        "subjects": [asset["subjectId"] for asset in receipt["assets"]],
    }, indent=2))


if __name__ == "__main__":
    main()
