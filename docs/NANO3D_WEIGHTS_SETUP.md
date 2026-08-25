# Nano3D weights — Modal volume setup

**Updated:** 25 August 2026  
**Status:** Prep for Case 3 GPU (shares TRELLIS weights)

---

## Overview

Nano3D Case 3 reuses **Microsoft TRELLIS** encoders/decoders. You do **not** download a separate “Nano3D-only” HF repo for v1 — weights come from the same cache as generation:

| Volume | Modal name | Contents |
|--------|------------|----------|
| HF cache | `trellis2-hf-cache` | `microsoft/TRELLIS.2-4B`, DINOv3, RMBG |
| Nano3D code | Modal image build | GitHub `JAMESYJL/Nano3D` (cloned at deploy) |

When `NANO3D_GPU=1`, `nano3d_gpu.py` will load from this shared cache.

---

## Prerequisites

Same as [TRELLIS_GPU_SETUP.md](./TRELLIS_GPU_SETUP.md):

1. Hugging Face token with access to TRELLIS.2-4B, RMBG-2.0, DINOv3  
2. Modal secret: `modal secret create huggingface HF_TOKEN=hf_xxxx`

---

## Step 1 — Pre-cache TRELLIS weights (if not done)

```bash
cd dentalsculptor-ml
python -m modal run -m modal_app.app::download_trellis_weights
```

This populates `trellis2-hf-cache` on Modal. Nano3D Case 3 reads the same sparse/latent checkpoints.

Verify in Modal dashboard → **Volumes** → `trellis2-hf-cache`.

---

## Step 2 — Deploy with GPU + inpaint + edit endpoints

```powershell
cd dentalsculptor-ml
$env:HF_TOKEN = "hf_your_token"   # or use Modal huggingface secret
python -m modal deploy -m modal_app.app
```

Copy **all** endpoint URLs from deploy output into Vercel:

| Env var | Endpoint label |
|---------|----------------|
| `MODAL_GENERATE_ASYNC_URL` | `generate-job` |
| `MODAL_EDIT_URL` | `edit` |
| `MODAL_INPAINT_URL` | `inpaint` |
| `MODAL_JOB_STATUS_URL` | `job-status` |

---

## Step 3 — Enable Nano3D GPU path (when Case 3 code lands)

On Modal, set environment or secret:

```env
NANO3D_GPU=1
```

Redeploy. Until `nano3d_gpu.py` implements full FlowEdit, this flag will fail fast with a clear error — CPU v1 (`nano3d_utils.py`) remains the default.

Recommended GPU: **L40S** (48 GB) minimum for Case 3 + inpaint on separate endpoints.

---

## Step 4 — SDXL inpaint weights (2D preview)

The `inpaint` endpoint downloads automatically on first run:

```
diffusers/stable-diffusion-xl-1.0-inpainting-0.1
```

No manual volume step — uses HF cache volume + `huggingface` secret. First cold start ~1–2 min.

---

## Checklist before enabling Nano3D GPU in production

- [ ] `download_trellis_weights` completed successfully  
- [ ] `MODAL_INPAINT_URL` set and 2D preview works  
- [ ] `MODAL_EDIT_URL` + `MODAL_JOB_STATUS_URL` working  
- [ ] Nano3D repo pinned in Modal image (see `nano3d_gpu.py` implementation PR)  
- [ ] 20-case benchmark pass (see `docs/research/GENERATION_AND_EDITING_RESEARCH.md`)

---

## Related

- [NANO3D_IMPLEMENTATION.md](./NANO3D_IMPLEMENTATION.md)  
- [MODAL_SETUP_GUIDE.md](./MODAL_SETUP_GUIDE.md) — inpaint URL section  
- [TRELLIS_GPU_SETUP.md](./TRELLIS_GPU_SETUP.md)
