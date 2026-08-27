# Pilot evaluation release — 27 August 2026

This document inventories every meaningful change in the working tree that ships with this push: the **real-time evaluation pilot** (generation → 2D review → Nano3D edit → export/publish), the **Modal GPU fix** for `Nano3DEditService`, and supporting research/benchmark assets.

**Previous pushed commit:** `96a6594` — generation image library + case-wizard hints  
**This release:** pilot UX, Nano3D FlowEdit on Modal, publish/share, validation set skeleton

---

## What you can test after deploy

| Flow | Status |
|------|--------|
| Pick library image → generate (TRELLIS.2 on Modal) | Implemented |
| Persist source photo on project reopen | Implemented |
| Mask + preset → 2D preview (Modal SDXL / fal / local fallback) | Implemented with provider labelling |
| Approve 2D → Nano3D image-input edit on Modal GPU | **Fixed & deployed** (was crash-looping) |
| Poll edit job → reload GLB in editor | Implemented |
| Export wizard (Simodont, Quest, teaching bundle, PPT GLB) | Implemented |
| Share → publish to community gallery | Implemented |

**Not yet product claims:** clinically accurate Nano3D anatomy, 20-case benchmark pass, export validation inside Simodont/Quest/PPT, educator study sessions. See [REALTIME_EVALUATION_HANDOFF.md](./REALTIME_EVALUATION_HANDOFF.md).

---

## 1. DentalSculptor app (`dentalsculptor-app/`)

### API routes

| File | Change |
|------|--------|
| `src/app/api/generate/mesh/route.ts` | Persists the exact submitted generation image to `DentalModel.sourceImageUrl` so library picks and uploads survive editor reopen and feed Nano3D's image-input path. |
| `src/app/api/edit-jobs/[jobId]/route.ts` | Rich Modal job polling: DB cache, S3 `resultKey` hydration, base64 GLB persist, Nano3D provenance (`provider`, `seed`, `inferenceSeconds`, `upstreamCommit`), graceful 404 while worker cold-starts. |
| `src/app/api/projects/[id]/edit-jobs/route.ts` | Passes `sourceImage` + `editedImage` bytes to Modal when GPU Nano3D is enabled. |
| `src/app/api/projects/[id]/publish/route.ts` | **New.** POST publishes project to community gallery, sets `PUBLISHED` status, records `PROJECT_PUBLISHED` research event. |

### Editor & export UI

| File | Change |
|------|--------|
| `src/components/editor/editor-workspace.tsx` | Source image lifecycle, separate source/edited captures for Nano3D, share dialog wiring, improved edit submit with image pair. |
| `src/components/editor/share-project-dialog.tsx` | **New.** Publish-to-community dialog with copy-link after success. |
| `src/components/editor/editor-header.tsx` | Removed placeholder Preview; Share opens publish dialog. |
| `src/components/editor/cam-model-viewer.tsx` | Camera refit after layout (meshes no longer appear off-screen on first load). |
| `src/components/editor/edit-preview-modal.tsx` | Distinguishes real AI preview vs illustrative local fallback; blocks 3D approval on local-only preview. |
| `src/components/editor/editor-case-panel.tsx` | Pilot case ordering and case-specific preset exposure. |
| `src/components/editor/editor-edit-presets-bar.tsx` | Cusp fracture uses `remove` operation with enamel-edge prompts. |
| `src/components/editor/editor-status-bar.tsx` | Shows edit provider / stage during Nano3D jobs. |
| `src/components/export/export-wizard-dialog.tsx` | Export targets grouped: Dental simulation, VR headsets, Presentations & teaching (PPT uses GLB). |

### Libraries & presets

| File | Change |
|------|--------|
| `src/lib/case-templates.ts` | Six ordered pilot cases; tooth-identification case in annotation-only mode. |
| `src/lib/edit-presets.ts` | Case-aware semantic presets including cusp fracture remove. |
| `src/lib/export-presets.ts` | Teaching-bundle and presentation export groups. |

---

## 2. Modal ML workers (`dentalsculptor-ml/`)

### Nano3D GPU image — crash-loop fix

| File | Change |
|------|--------|
| `modal_app/images/nano3d_gpu.py` | **New.** Isolated CUDA 11.8 image for Nano3D (separate from TRELLIS.2). Adds pinned `utils3d`, headless `bpy` X11 libs, kaolin/nvdiffrast/vox2seq, build-time import probe. |
| `modal_app/workers/nano3d_flowedit.py` | **New.** Adapter for Nano3D `inference2.py` image-input FlowEdit; stubs `inference` package to skip optional Qwen diffusers; letterboxes both inputs to 512² without aspect stretch. |
| `modal_app/app.py` | `Nano3DEditService` on A100-80GB; edit endpoint spawns GPU path when `NANO3D_GPU_ENABLED=1`; SDXL inpaint endpoint; `probe_nano3d_gpu_startup` + `modal run …::probe_nano3d` diagnostic. |

**Root causes fixed (were killing `@modal.enter()`):**

1. Missing `utils3d` (TRELLIS dependency inside Nano3D)
2. Missing `libSM.so.6` etc. for headless Blender Python
3. Nano3D `inference/__init__.py` importing Qwen pipelines not needed for image-input FlowEdit

**Verified:** startup probe loads `microsoft/TRELLIS-image-large` + sparse encoders in ~118s on A100-80GB.

### Benchmark & smoke scripts

| File | Purpose |
|------|---------|
| `scripts/cusp_fracture_smoke_test.py` | End-to-end Modal test: generate → inpaint → Nano3D edit → poll → GLB validation. |
| `scripts/benchmark_edit_pilot.py` | Skeleton for 20-case pilot benchmark batch. |

### Deploy (already live on Modal)

```powershell
cd dentalsculptor-ml
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'; chcp 65001 | Out-Null
python -m modal deploy -m modal_app.app
python -m modal run -m modal_app.app::probe_nano3d   # optional health check
```

Endpoints unchanged: `--generate`, `--edit`, `--inpaint`, `--job-status`.

---

## 3. Documentation (`docs/`)

| File | Purpose |
|------|---------|
| `REALTIME_EVALUATION_HANDOFF.md` | **New.** Single source of truth for pilot gates, architecture decisions, case order. |
| `benchmarks/CUSP_FRACTURE_SMOKE_TEST.md` | Manual UI checklist for cusp-fracture case. |
| `benchmarks/README.md` | Links smoke test + benchmark scripts. |
| `benchmarks/smoke-runs/` | Artifact folders from failed pre-fix runs (masks + previews; full `result.json` excluded — see `.gitignore`). |
| `SPRINT_ROADMAP.md` | Updated task tracker entries for this sprint. |
| **This file** | Release inventory for reviewers and Vercel/Modal operators. |

---

## 4. Research assets (`research/`)

| Path | Purpose |
|------|---------|
| `validation/trellis-teeth/` | 15 teaching tooth PNGs + `manifest.json` for TRELLIS/Nano3D benchmark; sync script from generation library. |
| `trueteethlab-workflows/` | Workflow analysis notes (reference). |

---

## 5. Design mockups (`stitch_dentalsculptor_xr_authoring_platform/`)

Stitch HTML mockups added for: clinical case wizard, edit-mode mask paint, export wizard, placement studio, clinical precision spec. Reference only — production UI is in `dentalsculptor-app/`.

---

## 6. Intentionally excluded from git

| Item | Reason |
|------|--------|
| `dentalsculptor-ml/modal-deploy.log` | Local deploy log |
| `docs/benchmarks/smoke-runs/**/result.json` | Multi-MB files with embedded base64 previews |
| Root tooth-chart JPG/WebP files | Reference images not wired into the app |
| `screen.png` | Ad-hoc screenshot |

---

## 7. Environment checklist (Vercel + Modal)

Ensure these match between app and Modal:

| Variable | Notes |
|----------|-------|
| `MODAL_WEBHOOK_SECRET` | Must match Modal secret `dentalsculptor-webhook` |
| `MODAL_EDIT_URL` | `https://dentalsculptor--edit.modal.run` |
| `MODAL_INPAINT_URL` | For real 2D SDXL preview |
| `MODAL_JOB_STATUS_URL` | Poll endpoint |
| `MODAL_GENERATE_URL` / async job URLs | TRELLIS generation |
| `NANO3D_GPU_ENABLED` | Set `1` on Modal app (default) for real FlowEdit |

HuggingFace secret `huggingface` with `HF_TOKEN` required for TRELLIS-image-large on Nano3D worker.

---

## 8. Suggested verification order

1. `python -m modal run -m modal_app.app::probe_nano3d` — GPU worker loads
2. `python scripts/cusp_fracture_smoke_test.py` — full Modal pipeline (10–20 min cold start)
3. Editor: upper molar library image → generate → cusp mask → 2D preview → approve → 3D edit
4. Export wizard → Simodont STL validate-only
5. Share → Publish → community gallery

---

## Related docs

- [REALTIME_EVALUATION_HANDOFF.md](./REALTIME_EVALUATION_HANDOFF.md) — pilot gates and case matrix
- [3D_EDITING_RESEARCH.md](./3D_EDITING_RESEARCH.md) — Nano3D/TRELLIS background
- [MODAL_SETUP_GUIDE.md](./MODAL_SETUP_GUIDE.md) — secrets and first deploy
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Vercel env vars
