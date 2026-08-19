# E2E test plan — Milestone E0–E2

**Purpose:** Repeatable validation before marking E0–E2 complete.  
**Updated:** 17 August 2026

---

## Prerequisites

| Item | Value |
|------|-------|
| Environment | Staging with `MODAL_TOKEN`, `FAL_KEY` (inpaint fallback), Clerk, Supabase, R2 |
| Test user | Educator role, consent accepted |
| Fixtures | `docs/fixtures/single-tooth/` — 3 PNG/JPG de-identified teaching photos |
| Hardware (optional) | Simodont or SimtoCARE import station; Meta Quest for `/xr/[id]` |

---

## Test cases

### TC-01 — Upload scope gate

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open landing | Single-tooth beta banner visible |
| 2 | Upload 4000×3000 JPG | Preprocessor downscales; upload succeeds |
| 3 | Upload PDF | Rejected with clear error |
| 4 | Upload full-arch photo | Warning shown; generation allowed with disclaimer |

### TC-02 — Case wizard

| Step | Action | Expected |
|------|--------|----------|
| 1 | Pick "Class I prep" + Year 3 | Title + LOs pre-filled |
| 2 | Complete wizard | `CASE_TEMPLATE_SELECTED` research event |
| 3 | Custom case (no template) | Empty LOs; ownership flag `custom` |

### TC-03 — TRELLIS generation (Modal)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Generate from fixture `molar-occlusal.jpg` | Job queued; progress UI |
| 2 | Wait for completion | GLB loads in editor; watertight or fixable |
| 3 | Check revision | v1 revision; `MODEL_GENERATED` event |
| 4 | Fail Modal (simulate) | fal fallback if configured; else error message |

**Pass metrics:** GLB loads &lt;60 s after GPU start; mesh visible with correct lighting.

### TC-04 — Mask + text edit (Nano3D)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Capture view; paint mask on occlusal fossa | Mask PNG stored |
| 2 | Prompt: "remove decay"; operation `remove` | 2D preview shown |
| 3 | Approve preview | 3D edit job starts |
| 4 | Compare before/after | Visible change in masked region only |
| 5 | Accept | v2 revision; v1 preserved |
| 6 | Reject + retry | No v2; can re-edit |

**Pass metrics:** Protected region displacement &lt;0.5 mm (sample measurement); educator blind rating ≥3/5 on 5 fixtures.

### TC-05 — Export wizard — Simodont

| Step | Action | Expected |
|------|--------|----------|
| 1 | Export → Simodont preset | Watertight check passes |
| 2 | Download STL | Binary STL, mm units |
| 3 | Import in Simodont Teacher | Model visible; drillable (manual confirm) |

### TC-06 — Export — SimtoCARE / Virteasy

| Step | Action | Expected |
|------|--------|----------|
| 1 | Export SimtoCARE (STL/PLY) | File downloads |
| 2 | Export Virteasy STL | Manifold mesh; documentation notes import path |

*Manual:* Partner lab confirms import if simulators available.

### TC-07 — Meta Quest / WebXR

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open `/xr/[projectId]` | GLB renders in WebXR viewer |
| 2 | Export Quest GLB preset | Scale in meters; &lt;20 MB |
| 3 | Side-load on Quest (optional) | Model viewable in GLB viewer app |

### TC-08 — Placement Studio

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open Placement from editor | Lower jaw template loads |
| 2 | Select FDI 36 socket | Tooth snaps approximately |
| 3 | Adjust rotation/scale | Transform saved |
| 4 | Merge + export STL | Single file; tooth fused to jaw mesh |

### TC-09 — Full journey (golden path)

1. Sign in as educator.  
2. Upload `premolar-caries.jpg`.  
3. Case: "Occlusal caries" Year 2.  
4. Generate → edit (remove caries) → accept.  
5. Place on jaw FDI 14.  
6. Export Simodont STL.  
7. Assign to test student; verify project link.

**Duration target:** &lt;15 min wall clock (excluding GPU queue).

### TC-10 — Research audit trail

| Event | Must fire |
|-------|-----------|
| Upload | `IMAGE_UPLOADED` |
| Generate | `MODEL_GENERATED` |
| Edit submit | `AI_PROMPT_SUBMITTED` |
| Accept edit | `AI_SUGGESTION_ACCEPTED` |
| Export | `EXPORT_REQUESTED` |

Export research CSV; verify row count matches actions.

### TC-11 — Storage limits

| Step | Action | Expected |
|------|--------|----------|
| 1 | Generate 10 projects | No Supabase bucket overflow |
| 2 | Verify GLB URLs | Point to R2 or Modal-signed URLs |

---

## Regression (existing features)

- Landing → auth → editor flow still works (`/auth/continue`).
- Project rename in editor.
- Model proxy loads external GLB.
- Consent checkbox contrast.

---

## Sign-off

| Role | Name | Date | E0 | E1 | E2 |
|------|------|------|----|----|-----|
| Engineering | | | ☐ | ☐ | ☐ |
| Educator pilot | | | ☐ | ☐ | ☐ |
| Research lead | | | ☐ | ☐ | ☐ |

**Milestone complete when:** TC-01 through TC-10 pass; TC-05 or TC-06 manually confirmed on at least one haptic platform.
