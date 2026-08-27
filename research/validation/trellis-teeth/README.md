# TRELLIS generation validation set (20 images)

Used by `dentalsculptor-ml/scripts/benchmark_trellis_modal.py` and the real-time evaluation gates in `docs/REALTIME_EVALUATION_HANDOFF.md`.

## Requirements

- **20** single-tooth PNG/JPG/WebP images
- Balanced across: incisors, canines, premolars, molars
- Mix of: clean background, reflective enamel, slight rotation, teaching-lab photos
- De-identified or synthetic — no patient metadata in filenames

## Current status

| Count | Source |
|-------|--------|
| 15 | Copied from `dentalsculptor-app/public/generation-library/` (teaching specimens) |
| 5 | **TODO** — add caries/pathology/clinical photos when licensed |

Run from repo root to refresh symlinks/copies:

```powershell
python research/validation/trellis-teeth/sync_from_generation_library.py
```

## Layout

```text
research/validation/trellis-teeth/
  manifest.json          # case metadata for benchmarks
  images/                # 01-incisor-labial.png … 20-*.png
  sync_from_generation_library.py
```

## manifest.json fields

Each entry:

- `id` — stable slug
- `filename` — file under `images/`
- `toothType` — incisor | canine | premolar | molar
- `fdiHint` — representative FDI (educator confirms in app)
- `notes` — optional (e.g. "lingual view", "two roots")

## Running the generation benchmark

See `docs/benchmarks/README.md`.
