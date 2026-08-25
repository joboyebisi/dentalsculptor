# DentalSculptor — Sprint Roadmap (Aug 2026)

**Goal:** Research pilot → E0–E2 milestone with optimised UX, faster generation/edit, and multilayer editing research.

**Live app:** https://dentalsculptor.vercel.app  
**Invite test:** `/?invite=<RESEARCH_GENERATION_ACCESS_CODE>`

Test after each phase. Update checkboxes as you go.

---

## Phase 0 — Auth & pilot stability

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 0.1 | Supabase Google OAuth | ⬜ | [SUPABASE_OAUTH_SETUP.md](./SUPABASE_OAUTH_SETUP.md) |
| 0.2 | Supabase Microsoft (Azure) OAuth | ⬜ | Same doc |
| 0.3 | Vercel env: remove Clerk, confirm Supabase + Modal + S3 | ⬜ | |
| 0.4 | Production smoke: invite → generate → GLB | ⬜ | |
| 0.5 | Production smoke: sign-in → consent → onboarding | ⬜ | |

---

## Phase 1 — Research role gating

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 1.1 | `/research` layout — redirect non-RESEARCHER/ADMIN | ✅ | |
| 1.2 | Filter Research nav item by role | ✅ | |
| 1.3 | Lock `GET /api/research/surveys` to researchers | ✅ | |
| 1.4 | Remove client self-assign of RESEARCHER role in onboarding | ✅ | Educator/Student only |
| 1.5 | Hide public landing link to `/research` | ✅ | |

---

## Phase 2 — Generation speed & anatomical quality

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 2.1 | Session GPU warmup (invite/upload/generate) | ✅ | `gpu-warmup.ts`, `/api/ml/warm` |
| 2.2 | Async S3 job path (no 503 on Vercel) | ✅ | Modal `TRELLIS_ASYNC_S3_ENABLED` |
| 2.3 | Quality picker UI (preview → enhance) | ⬜ | Backend ready; wire `finalizeGenerationJob` |
| 2.4 | Benchmark GPU × quality presets | ⬜ | `scripts/benchmark_trellis_modal.py` |
| 2.5 | **Anatomical accuracy research** | ⬜ | See §Research tracks below |
| 2.6 | Dental quality gate (auto-reject bad meshes) | ⬜ | Metrics from TRELLIS job |
| 2.7 | Optional LoRA / fine-tune spike on teaching photos | ⬜ | E0 spike in MILESTONE_E0_E2 |

### Generation accuracy — methods to evaluate

| Method | Effort | Notes |
|--------|--------|-------|
| TRELLIS `standard` vs `final` preset | Low | Already in `trellis_config.py` |
| Stronger preprocess (crop, background removal) | Low | `prepare-generation-image.ts` |
| Fixed seed profiling for reproducibility | Low | Modal job metadata |
| Reference-image conditioning | Medium | Research |
| LoRA on de-identified dental photos | High | DTU / teaching dataset |
| Post-gen mesh repair + cusp refinement | Medium | trimesh / custom |

---

## Phase 3 — Nano3D edit (E0)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 3.1 | Mask paint UI | ✅ | `mask-paint-overlay.tsx` |
| 3.2 | 2D preview approve modal | ✅ | Stub after-image (same as before) |
| 3.3 | Real 2D masked inpaint worker | ✅ | fal SDXL inpaint + client stub fallback |
| 3.4 | Replace CPU trimesh stub with real Nano3D Case 3 | ⬜ | `nano3d_gpu.py` scaffold + `NANO3D_GPU` flag |
| 3.5 | Wire reference image + camera through API → Modal | ✅ | `edit-jobs/route.ts` + Modal `edit` |
| 3.6 | EditJob Prisma model + revision history | ✅ | `EditJob` model + `edit-jobs.server.ts` |
| 3.7 | Edit presets (add/remove/replace cusp, smooth, etc.) | ✅ | `edit-presets.ts` + presets bar |
| 3.8 | Before/after 3D compare + accept/reject | ✅ | `EditorRevisionReview` + `/resolve` |
| 3.9 | Protected-region metrics | ⬜ | Research auditability |

### Edit UX — reference experiences

| Pattern | Source | Apply to |
|---------|--------|----------|
| Mask → 2D preview → approve → 3D | Photoshop Generative Fill, Runway | Edit flow |
| Operation presets | Meshmixer, Blender modifiers | Toolbar |
| Non-destructive revisions | Figma versions | Revision stack |

---

## Phase 4 — Export wizard (E1)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 4.1 | Export wizard dialog | ✅ | `export-wizard-dialog.tsx` |
| 4.2 | Simodont / SimtoCARE / Virteasy / Quest presets | ✅ | `export-presets.ts` |
| 4.3 | Watertight check + STL export | ✅ | `export-mesh.ts` |
| 4.4 | PLY export | ⬜ | Preset lists it; not implemented |
| 4.5 | Teaching bundle ZIP (GLB + STL + README) | ⬜ | |
| 4.6 | Per-vendor axis/orientation (`upAxis`) | ⬜ | |
| 4.7 | Server-side mesh repair before export | ⬜ | |
| 4.8 | Multilayer export (separate tissue STLs) | ⬜ | Depends Phase 6 |

---

## Phase 5 — Placement studio (E2)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 5.1 | Jaw template assets (lower/upper STL) | ⬜ | [JAW_TEMPLATE_ASSETS.md](./JAW_TEMPLATE_ASSETS.md) |
| 5.2 | FDI socket map JSON | ⬜ | |
| 5.3 | Placement Studio UI (viewport + gizmo) | ⬜ | Stitch mockup exists |
| 5.4 | `PATCH /api/projects/[id]/placement` | ⬜ | |
| 5.5 | Prisma: jaw template, transform, FDI on model | ⬜ | |
| 5.6 | Merge tooth + jaw for export | ⬜ | |

---

## Phase 6 — Multilayer tissue editing (research)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 6.1 | Strategy doc | ✅ | [MULTILAYER_TOOTH_STRATEGY.md](./MULTILAYER_TOOTH_STRATEGY.md) |
| 6.2 | Unlock parts panel (remove “Coming soon”) | ⬜ | |
| 6.3 | Template-based enamel/dentin/pulp shells (photo teeth) | ⬜ | Warp to generated mesh |
| 6.4 | “Add layer” edit: user paints region → assign tissue | ⬜ | UX goal |
| 6.5 | Separate meshes per tissue in viewer | ⬜ | |
| 6.6 | Voxel label volume export | ⬜ | Simulators / research |
| 6.7 | CBCT/micro-CT path (E3+) | ⬜ | Out of E0–E2 scope |

### Multilayer — methods / hacks to research

| Approach | When |
|----------|------|
| Anatomical template warp (tooth-type LUT) | Photo-only input |
| Shell offset (enamel thickness param) | Quick hack |
| AI segmentation on rendered views | Medium |
| Nano3D edit per tissue mask | After 3.4 |
| TrueTeethLab / vendor tissue package | Simulator integration |

---

## Phase 7 — UX polish & testing (continuous)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 7.1 | E2E test plan execution | ⬜ | [E2E_TEST_PLAN_E0_E2.md](./E2E_TEST_PLAN_E0_E2.md) |
| 7.2 | Generation progress copy + ETA | ⬜ | `generation-copy.ts` |
| 7.3 | Hydration fixes on landing invite callout | ⬜ | |
| 7.4 | Undo/redo in editor (Zundo) | ⬜ | Phase A deferred |
| 7.5 | Update stale docs (Clerk → Supabase) | ⬜ | PROGRESS, DEPLOYMENT, README |

---

## Execution order (recommended)

```
0 Auth OAuth → 1 Role gate → 0.4 Pilot test
→ 2.3 Quality UI + 2.x speed/accuracy
→ 3 Nano3D edit (presets + real worker)
→ 4 Export gaps
→ 5 Placement
→ 6 Multilayer (incremental)
→ 7 Polish throughout
```

---

## Success criteria (milestone E0–E2)

From [MILESTONE_E0_E2.md](./MILESTONE_E0_E2.md):

- Upload → generate → edit → (optional) place → export without CLI
- STL watertight; Simodont preset validates
- Edit revisions auditable (mask, prompt, camera)
- Research events from upload through export
