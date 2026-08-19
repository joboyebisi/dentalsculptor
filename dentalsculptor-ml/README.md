# dentalsculptor-ml — Modal GPU workers

**Status:** Scaffold (E0)  
**Purpose:** TRELLIS image→3D generation, Nano3D mesh editing, export mesh repair.

Parent milestone: [docs/MILESTONE_E0_E2.md](../docs/MILESTONE_E0_E2.md)

---

## Layout (planned)

```
dentalsculptor-ml/
├── README.md                 # this file
├── pyproject.toml
├── modal_app/
│   ├── __init__.py
│   ├── app.py                # modal.App("dentalsculptor")
│   ├── images/
│   │   ├── trellis.py        # CUDA image with TRELLIS deps
│   │   └── nano3d.py         # Nano3D + extensions
│   ├── volumes/
│   │   └── weights.py        # trellis-weights-v1, nano3d-weights-v1
│   └── workers/
│       ├── generate.py       # TRELLIS image → GLB
│       ├── edit.py           # Nano3D Case 3
│       └── export_mesh.py    # watertight STL/PLY/GLB
└── scripts/
    ├── benchmark_trellis.py
    └── benchmark_nano3d.py
```

---

## Modal resources

| Resource | Name | Use |
|----------|------|-----|
| Volume | `trellis-weights-v1` | Microsoft TRELLIS checkpoints |
| Volume | `nano3d-weights-v1` | Nano3D + TRELLIS shared weights |
| Secret | `dentalsculptor-r2` | R2 credentials for job I/O |
| GPU (generate) | `A100-40GB` | TRELLIS inference |
| GPU (edit) | `L40S` | Nano3D Case 3 |
| CPU | default | Export / mesh fix |

---

## HTTP contract (called from Next.js)

### POST `/v1/generate`

```json
{
  "jobId": "cuid",
  "imageUrl": "https://...",
  "seed": 42,
  "outputKey": "jobs/{jobId}/model.glb"
}
```

Response: `{ "status": "queued", "modalCallId": "..." }`

### POST `/v1/edit`

```json
{
  "jobId": "cuid",
  "sourceGlbUrl": "https://...",
  "editedImageUrl": "https://...",
  "operation": "remove",
  "outputKey": "jobs/{jobId}/edited.glb"
}
```

### POST `/v1/export`

```json
{
  "jobId": "cuid",
  "sourceGlbUrl": "https://...",
  "preset": "simodont",
  "outputKey": "jobs/{jobId}/export.stl"
}
```

---

## Environment (Next.js → Modal)

| Variable | Where |
|----------|-------|
| `MODAL_TOKEN_ID` | Vercel server |
| `MODAL_TOKEN_SECRET` | Vercel server |
| `MODAL_WEBHOOK_URL` | Optional async callback |
| `R2_*` or `STORAGE_BACKEND` | Shared with app |

---

## Build spike (E0 week 1)

1. Reproduce upstream TRELLIS single-image example on Modal A100.
2. Run Nano3D `inference2.py` path with sample GLB + edited PNG.
3. Measure cold start, VRAM, seconds per job, credits per job.
4. Pin Docker base: `nvidia/cuda:12.4.0-devel-ubuntu22.04`, Torch 2.4+, commit SHAs.

---

## Not in this folder yet

Implementation starts in E0 sprint 1. Until workers deploy, Next.js keeps **fal.ai** fallback via `FAL_KEY`.
