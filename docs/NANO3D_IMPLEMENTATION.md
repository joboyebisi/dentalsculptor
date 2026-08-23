# Nano3D implementation — DentalSculptor

**Updated:** 23 August 2026  
**Status:** Case 3 path wired (CPU v1); full GPU FlowEdit is next

---

## What Nano3D does (research model)

Nano3D extends **Microsoft TRELLIS** for editing an existing GLB without retraining:

1. **Encode** source mesh → sparse structure + structured latent (SLat)
2. **Render** reference views of the source
3. **Edit** the front/reference image (Qwen-Image or user-supplied edited PNG)
4. **FlowEdit** in latent space — merge edited region with preserved source latents
5. **Decode** → new GLB

**Case 3** (what we use): supply **source GLB + edited 2D reference**. The 2D edit can come from masked inpaint using the educator's instruction.

Nano3D has **no native paint API** — DentalSculptor adds mask + region marks in the **2D step** before Case 3.

---

## Our educator workflow (product)

```text
Case preset → Mark region / paint mask → Add|Remove|Replace → Semantic text
    → Preview 2D (approve) → Generate 3D (async) → Accept revision → Export
```

See [EDITOR_INTERACTION_FRAMEWORK.md](./EDITOR_INTERACTION_FRAMEWORK.md).

---

## Architecture today

| Layer | File | Role |
|-------|------|------|
| Editor UI | `editor-workspace.tsx` | Collects mask, camera, regions, instruction |
| 2D preview | `edit-2d-preview.ts` | Client masked preview before 3D |
| Edit API | `edit-jobs/route.ts` | Auth, prompt expansion, proxy to Modal, persist GLB |
| Poll API | `edit-jobs/[jobId]/route.ts` | Poll Modal job-status, upload result |
| Modal endpoint | `modal_app/app.py` → `edit` | Queue async edit job |
| Worker | `nano3d_utils.py` | **v1:** masked 2D stub + vertex deform; **v2:** full Case 3 GPU |

---

## Payload contract

| Field | Type | Purpose |
|-------|------|---------|
| `sourceModelUrl` | URL | Current GLB revision |
| `referenceImage` | PNG | Captured viewport at edit time |
| `maskImage` | PNG | White = editable, black = protected |
| `camera` | JSON | View/projection matrices + width/height |
| `instruction` | string | Semantic edit (+ region refs appended) |
| `operation` | add \| remove \| replace | Nano3D operation mode |
| `regionMarks` | JSON | Normalized rects + optional 3D corners |

---

## Implementation phases

### Phase 1 — Done (this sprint)

- Editor mask + region attachments + 2D preview
- Edit job API proxy to Modal
- Modal CPU worker: masked 2D stub + camera-projected vertex deform
- Job status polling + GLB upload + DB persist

### Phase 2 — Next (GPU Case 3)

- Modal image: CUDA + Nano3D repo + TRELLIS weights volume
- Replace vertex deform with Case 3 inference path
- Optional Qwen-Image worker on A100-80GB for true inpaint

---

## Deploy edit worker

```bash
cd dentalsculptor-ml
python -m modal deploy -m modal_app.app
```

Set in Vercel: `MODAL_EDIT_URL`, `MODAL_JOB_STATUS_URL`, `MODAL_WEBHOOK_SECRET`.
