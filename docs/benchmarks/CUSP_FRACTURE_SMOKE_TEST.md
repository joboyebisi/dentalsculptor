# Cusp fracture — end-to-end smoke test

**Goal:** One fixed-seed path through generate → case → 2D AI preview → Nano3D image-input edit → valid GLB.

**Prerequisite:** Modal deploy succeeds (Nano3D GPU image builds). Vercel env vars set.

---

## 1. Modal deploy

```powershell
cd C:\Users\joboy\Desktop\DentalSculptor\dentalsculptor-ml
python -m modal deploy -m modal_app.app
python -m modal app list
```

Confirm endpoints exist:

| Env var | Expected endpoint |
|---------|-------------------|
| `MODAL_GENERATE_URL` | `https://dentalsculptor--generate.modal.run` (or GPU variant) |
| `MODAL_EDIT_URL` | `https://dentalsculptor--edit.modal.run` |
| `MODAL_JOB_STATUS_URL` | `https://dentalsculptor--job-status.modal.run` |
| `MODAL_INPAINT_URL` | `https://dentalsculptor--inpaint.modal.run` |
| `MODAL_WEBHOOK_SECRET` | Same value in Vercel + Modal secret |

If Nano3D image build fails on `mathutils` / `pysdf`, ensure `nano3d_gpu.py` includes `clang` and `libeigen3-dev`.

---

## 2. Vercel environment (production or preview)

Minimum for this smoke test:

```text
ML_MESH_PROVIDER=modal
MODAL_EDIT_URL=https://dentalsculptor--edit.modal.run
MODAL_JOB_STATUS_URL=https://dentalsculptor--job-status.modal.run
MODAL_INPAINT_URL=https://dentalsculptor--inpaint.modal.run
MODAL_WEBHOOK_SECRET=<secret>
STORAGE_BACKEND=supabase   # or s3 if configured
```

Redeploy Vercel after env changes.

---

## 3. Test inputs (fixed)

| Item | Value |
|------|--------|
| Source image | **Browse library** → `Upper molar — three roots` (FDI 16) |
| Case template | **Cusp & fracture** → `pathology-fracture-cusp` |
| FDI | Confirm **16** (pre-filled from library) |
| Edit preset | **Cusp fracture** (`remove`) |
| Seed | Note job `seed` from edit status JSON (for repeat runs) |

---

## 4. Click path (editor)

1. Landing or **New project** → **Browse library** → pick upper molar → **Generate 3D**
2. **Open in editor** → confirm model frames in viewport (no manual zoom)
3. **Case wizard** → Cusp & fracture → apply template
4. **Mask tool** → paint distobuccal cusp region (~5–15% coverage)
5. Preset **Cusp fracture** → instruction fills automatically
6. **Preview 2D** → wait for progress bar
7. **Gate:** banner must say **AI inpaint** (Modal SDXL or fal) — **not** “Illustrative local preview”
8. **Approve & run 3D edit** → poll job status until `completed`
9. Accept revision → reload model

---

## 5. Pass criteria

| Check | Pass |
|-------|------|
| 2D preview provider | `modal-sdxl` or `fal` (not local stub) |
| Edit job provider | `nano3d-flowedit` |
| Result GLB | Opens in viewer; valid header (no “incorrect GLB”) |
| Localized change | Masked cusp region visibly altered vs pre-edit |
| Protected surface | Mesial/distal crown outside mask largely unchanged |
| Provenance | Edit job record has operation `remove`, instruction, revision number |
| Source image persisted | Source panel still shows library photo after refresh |

---

## 6. Fail actions

| Symptom | Likely cause |
|---------|----------------|
| “Illustrative local preview” | `MODAL_INPAINT_URL` / `FAL_KEY` missing |
| Edit uses CPU stub | `sourceImage` + `editedImage` not sent; or FlowEdit image not deployed |
| GLB header error | Empty/corrupt upload; check S3/Supabase URL |
| Modal 502 | GPU image not built; check Modal dashboard build logs |
| Model off-screen | Camera fit regression — report with project ID |

---

## 7. Record results

Log in `docs/benchmarks/smoke-runs/` (create per run):

```json
{
  "date": "2026-08-27",
  "projectId": "...",
  "sourceImage": "upper-molar-three-roots-a.png",
  "previewProvider": "modal-sdxl",
  "editProvider": "nano3d-flowedit",
  "seed": 1,
  "passed": true,
  "notes": ""
}
```

Only promote **Cusp fracture** to live pilot after this pass.
