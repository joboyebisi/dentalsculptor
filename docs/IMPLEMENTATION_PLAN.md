# DentalSculptor — Implementation Plan

> **Purpose:** Roadmap for all remaining work — editor polish, ML pipeline, research flows, infrastructure, and integrations. Pair with [PROJECT_WALKTHROUGH.md](./PROJECT_WALKTHROUGH.md) for current state.

**Last updated:** August 2026

---

## Table of contents

1. [Overview & priorities](#1-overview--priorities)
2. [Phase A — Editor polish (Pascal-inspired)](#2-phase-a--editor-polish-pascal-inspired)
3. [Phase B — Core workflows](#3-phase-b--core-workflows)
4. [Phase C — Community & landing](#4-phase-c--community--landing)
5. [Phase D — Mesh generation (fal.ai → custom)](#5-phase-d--mesh-generation-falai--custom)
6. [Phase E — Segmentation (Slicer → FastAPI)](#6-phase-e--segmentation-slicer--fastapi)
7. [Phase F — Research participant flow](#7-phase-f--research-participant-flow)
8. [Phase G — Auth, DB & production hardening](#8-phase-g--auth-db--production-hardening)
9. [Infrastructure & cost guide](#9-infrastructure--cost-guide)
10. [Pascal polish checklist](#10-pascal-polish-checklist)
11. [Schema additions](#11-schema-additions)
12. [Sprint schedule (12 weeks)](#12-sprint-schedule-12-weeks)
13. [Success criteria](#13-success-criteria)

---

## 1. Overview & priorities

### Active milestone: E0–E2 (single tooth → sim export)

**Primary doc:** [MILESTONE_E0_E2.md](./MILESTONE_E0_E2.md)  
**E2E tests:** [E2E_TEST_PLAN_E0_E2.md](./E2E_TEST_PLAN_E0_E2.md)  
**Later work:** [MILESTONE_E3_PLUS.md](./MILESTONE_E3_PLUS.md)  
**Multilayer anatomy:** [MULTILAYER_TOOTH_STRATEGY.md](./MULTILAYER_TOOTH_STRATEGY.md)

| Phase | Deliverable | Weeks |
|-------|-------------|-------|
| **E0** | Modal TRELLIS generate + Nano3D edit; mask + text UI | 2–3 |
| **E1** | Export wizard (Simodont, SimtoCARE, Virteasy, Quest presets; watertight check) | 1 |
| **E2** | Placement Studio (template jaw + transform + merge) | 2 |

**User journey:** PNG/JPG single tooth → preprocess → case template → Modal generate → mask/prompt edit → optional jaw placement → export STL/GLB.

**ML host:** Modal (`dentalsculptor-ml/`). fal.ai remains fallback until Modal deploys.  
**Storage:** Supabase Postgres + **Amazon S3** for GLB/STL; Supabase bucket for thumbnails only.

### Critical research problems

These three workstreams are release gates and must be measured independently:

1. **Generation:** reduce time-to-first-preview and accepted GLB latency by up to 10× without losing the 1024-cascade anatomical quality. Split SLat generation from GLB extraction, persist job state, profile fixed seeds, test warm containers and GPU variants, and prevent duplicate paid jobs.
2. **Editing:** replace the current placeholder with captured-view masked 2D approval, a real Nano3D Case 3 worker, protected-region metrics, before/after review, and immutable accepted revisions.
3. **Multilayer anatomy:** represent enamel, dentin and pulp as separate watertight, non-overlapping tissue regions with explicit material IDs. A single photograph cannot reveal patient-specific internal anatomy; photo-generated teeth may use validated tooth-type templates, while anatomically measured layers require CBCT/micro-CT segmentation. Standard STL/PLY imports generally remain uniform-haptic, so native multi-tissue haptics require a simulator-specific material/voxel contract or TrueTeethLab integration.

### Architecture target

```mermaid
flowchart TB
  subgraph client [Next.js on Vercel]
    Landing[Landing / Community]
    Editor[Editor Workspace]
    Preview[Preview /preview/id]
    ResearchAPI[/api/research/*]
  end

  subgraph auth [Auth & Data]
    Clerk[Clerk]
    Supabase[(Supabase Postgres)]
    R2[Cloudflare R2 / S3]
    PostHog[PostHog]
  end

  subgraph ml [ML Service - GPU]
    FastAPI[FastAPI Worker]
    Fal[fal.ai Hunyuan3D - interim]
    SegCT[DentalSegmentator - CT/CBCT]
    SegIOS[DentalModelSeg - IOS]
    Custom[Custom dental model - future]
  end

  Editor --> Clerk
  Editor --> Supabase
  Editor --> R2
  Editor --> FastAPI
  FastAPI --> Fal
  FastAPI --> SegCT
  FastAPI --> SegIOS
  FastAPI --> Custom
  ResearchAPI --> Supabase
  Editor --> PostHog
```

### Priority order

| Priority | Theme | Why |
|----------|-------|-----|
| P0 | Generation latency and reliability | Current multi-minute wait blocks recruitment and repeats can waste GPU spend |
| P0 | Real masked editing + revisions | Core research promise; placeholder output is not clinically auditable |
| P0 | Multilayer anatomy contract | Enamel/dentin/pulp geometry and simulator material compatibility |
| P0 | Role-gate research dashboard | Ethics / UX — participants must not see supervisor tools |
| P0 | Selection ↔ 3D sync | Core editor promise |
| P1 | STL export | Already promised on landing page |
| P1 | fal.ai mesh generation | Replace procedural mock |
| P1 | Participant survey triggers | Research data collection |
| P2 | FastAPI segmentation | Real Model Parts panel |
| P2 | Publish / share / preview | Complete project lifecycle |
| P3 | SFX + undo/redo | Pascal-level polish |
| P3 | Custom model swap | Research differentiation |

---

## 2. Phase A — Editor polish (Pascal-inspired)

**Reference:** [github.com/pascalorg/editor](https://github.com/pascalorg/editor) / [editor.pascal.app](https://editor.pascal.app/)

**Duration:** 1–2 weeks

### A1. Codify design tokens

Add to `src/lib/constants.ts`:

```typescript
export const VIEWPORT_THEME = {
  background: "#e8ecf0",
  meshDefault: "#e8dcc8",
  meshHighlight: "#f5e6d3",
  grid: "#CBD5E1",
} as const;

export const CHROME_THEME = {
  surface: "#0a0a0a",
  panel: "#111827",
  border: "#1f2937",
} as const;
```

Apply consistently across `editor-workspace.tsx`, panels, AI bar, tool palette.

### A2. Scene registry + selection

| Task | File(s) | Detail |
|------|---------|--------|
| Registry | `cam-model-viewer.tsx` | `Map<partId, THREE.Mesh>` |
| Highlight | same | Emissive material or `@react-three/drei` Outline |
| Visibility | same | Unchecked part → `visible = false` |
| Panel sync | `editor-workspace.tsx` | Click mesh → select part in panel |
| Click sound | `src/lib/sfx-bus.ts` | Howler + `public/audios/sfx/select.mp3` |

### A3. SFX bus (Pascal pattern)

```
src/lib/sfx-bus.ts
public/audios/sfx/
  menu-click.mp3
  item-pick.mp3
  export-done.mp3
```

Trigger on: tool change, part toggle, export success, checkbox click.

### A4. Tools pane polish

- Tooltips on all tools
- Active state ring (primary blue)
- Wire `resetHome` to camera home button
- Hover SFX

### A5. Undo/redo (Zundo)

- Add `zustand` + `zundo` dependencies
- History stack: annotations, part visibility toggles, AI apply actions
- Wire header Undo/Redo buttons

**Done when:** Selecting a part visibly updates 3D; tools feel responsive; cream/dark theme is locked.

---

## 3. Phase B — Core workflows

**Duration:** 2–3 weeks

### B1. STL / GLB export

| Task | Detail |
|------|--------|
| `src/lib/export-mesh.ts` | `STLExporter`, `GLTFExporter` from Three.js |
| Export modal | Format, selected parts, filename |
| Header Export | Select all parts → export → download |
| API (optional) | `POST /api/projects/[id]/export` → store in R2 |
| Event | `EXPORT_REQUESTED` + format metadata |

### B2. Preview route

| Route | Behaviour |
|-------|-----------|
| `/preview/[id]` | Read-only `CamModelViewer`, annotations visible, no tools/AI |
| Header Preview button | Opens new tab |

### B3. Duplicate project

```
POST /api/projects/[id]/duplicate
```

Reuse logic from `/api/community/[projectId]/clone/route.ts` for own projects.

### B4. Share + publish

```
POST /api/projects/[id]/publish
  → creates/updates CommunityProject
  → sets publishingLevel, status PUBLISHED
  → fires PROJECT_PUBLISHED, COMMUNITY_SHARED
```

Share modal: copy link, choose publishing level.

### B5. Persist annotations

Wire rect marks from `editor-workspace.tsx` → `POST /api/projects/[id]/annotations`.

**Done when:** User downloads real `.stl`; can preview, duplicate, publish, share.

---

## 4. Phase C — Community & landing

**Duration:** 1 week

| Task | Detail |
|------|--------|
| Thumbnail capture | Canvas snapshot on publish → upload R2/S3 |
| Landing grid | Fetch featured `CommunityProject` with images, likes, downloads |
| Community filters | Category badges (already in constants) |
| Clone button | "Duplicate" on cards |
| Likes API | `POST /api/community/[projectId]/like` |

**Done when:** Landing shows real published projects with actions.

---

## 5. Phase D — Mesh generation (fal.ai → custom)

**Duration:** 2–4 weeks (interim); ongoing for custom model

### D0. Route by clinical source and authoring intent

Do not send every upload through image-to-3D. The new project flow first chooses
`single tooth`, `tooth in jaw`, `partial/full arch`, or `CT/CBCT anatomy`, then
detects photo, IOS/surface, CT/CBCT, X-ray, or existing case input. See
[`CLINICAL_AUTHORING_WORKFLOWS.md`](./CLINICAL_AUTHORING_WORKFLOWS.md).

TRELLIS/Nano3D on Modal becomes the preferred experimental generation/editing
provider after it passes the dental benchmark. Keep FAL Hunyuan as a server-side
fallback; educators do not choose infrastructure providers.

### D1. Wire Bloom pattern into main app

Reference: `bloom-v0/src/app/api/generate/route.ts`

```typescript
// src/lib/ml-client.ts
interface MeshGenerationResult {
  meshUrl: string;
  format: "glb" | "stl";
}

async function generateMeshFromPhoto(
  file: File,
  provider: "fal" | "custom" = "fal"
): Promise<MeshGenerationResult>
```

**Env vars to add:**
```env
FAL_KEY=
ML_MESH_PROVIDER=fal   # later: custom
ML_SERVICE_URL=        # later: your FastAPI endpoint
```

**Flow:**
1. Educator uploads photo in source panel
2. `POST /api/projects` uploads to S3/R2
3. Call fal.ai Hunyuan3D Turbo (~$0.02–0.10/generation)
4. Download GLB → store as `generated3DUrl`
5. Load in `CamModelViewer` via GLTFLoader
6. Track `MODEL_GENERATED`

### D2. Custom model migration

| Stage | Provider | Notes |
|-------|----------|-------|
| Now | Procedural mock | Dev only |
| Stage 1 | fal.ai | Demo + pilot |
| Stage 2 | Custom FastAPI endpoint | Same `MeshGenerationResult` interface |
| Stage 3 | End-to-end custom | Photo → mesh + parts in one pass |

**Design rule:** Never call fal.ai directly from client — always via Next.js API route.

---

## 6. Phase E — Segmentation (Slicer → FastAPI)

**Duration:** 4–6 weeks

Phase E also introduces the confirmed anatomy contract used by placement,
editing, case authoring and export. IOS, CT/CBCT, µCT and generated meshes route
to different pipelines; there is no universal dental segmenter.

### E0. Localised generative editing bridge

Before anatomical segmentation is wired into the editor, run the Nano3D/Modal
spike described in [`3D_EDITING_RESEARCH.md`](./3D_EDITING_RESEARCH.md). Editing
and segmentation remain separate jobs, but share selected part IDs and a common
editable-region mask. The first editing UI is: captured model view + painted 2D
mask + text instruction + add/remove/replace operation + preview approval.

All accepted edits create a new immutable model revision. The original mesh,
mask, camera, prompt, seed, provider/checkpoint version, and validation metrics
must be retained for undo, research audit, and future custom-model training.

### Tool comparison

| Tool | Input | Output | Best for |
|------|-------|--------|----------|
| [DentalSegmentator](https://github.com/gaudot/SlicerDentalSegmentator) | CT/CBCT DICOM/NIfTI | 5 anatomical classes | Jaw/skull teaching |
| [DentalModelSeg](https://github.com/DCBIA-OrthoLab/SlicerDentalModelSeg) | IOS .vtk jaw scan | FDI/Universal per-tooth labels | Crown-level teaching |

### Input routing

| User uploads | Pipeline |
|--------------|----------|
| Clinical photo | fal.ai → mesh → (optional) mock parts until IOS pipeline |
| STL/OBJ/VTK jaw | DentalModelSeg |
| DICOM/ZIP CBCT | DentalSegmentator |
| Custom model (future) | Unified endpoint |

### FastAPI service structure

```
dentalsculptor-ml/                 # Separate repo or monorepo folder
├── app/
│   ├── main.py
│   ├── routers/
│   │   ├── segment_volume.py    # nnU-Net / DentalSegmentator
│   │   ├── segment_mesh.py      # DentalModelSeg
│   │   └── jobs.py
│   └── workers/
│       ├── nnunet_runner.py
│       └── mesh_postprocess.py  # marching cubes → GLB per label
├── docker/
│   ├── Dockerfile.segmentator   # CUDA + nnUNet + Zenodo weights
│   └── Dockerfile.modelseg      # Linux CUDA
└── requirements.txt
```

### API contract

```
POST /jobs/segment
  Body: { projectId, inputUrl, inputType: "ct" | "ios" }
  → { jobId, status: "queued" }

GET /jobs/{jobId}
  → { status, progress, parts: [{ id, label, meshUrl, color, fdiNumber?, confidence }] }
```

Next.js callback: `PATCH /api/projects/[id]/segmentation` → populate `segmentData` JSON.

### Post-processing pipeline

1. Run inference → label map (volume) or vertex scalars (mesh)
2. Extract surface per label
3. Export each part as GLB → R2/S3
4. Return parts array → Model Parts panel + scene registry
5. Track `SEGMENTATION_COMPLETED` (add to enum)

### Deployment options

| Option | Cost | Notes |
|--------|------|-------|
| University lab GPU | Free | Best for PHI/de-identified clinical data |
| Modal.com | Pay per job | Serverless GPU; good for burst |
| RunPod spot | ~$0.20/hr | Always-on option |
| Replicate | Per run | Easiest; less control |

**Requirements:** DentalSegmentator needs CUDA + ~32GB RAM. DentalModelSeg is Linux+CUDA only.

### PHI / ethics

- Add upload consent: "I confirm this scan is de-identified or I have permission"
- Prefer on-prem GPU for real clinical CBCT
- Use Slicer sample data for demos

**Done when:** Model Parts panel shows real labels; export selected parts to STL.

---

## 7. Phase F — Research participant flow

### F1. Hide supervisor dashboard from participants

| Location | Change |
|----------|--------|
| `constants.ts` `NAV_ITEMS` | Remove `/research` from default list |
| `app-sidebar.tsx` | Show Research only if `RESEARCHER \|\| ADMINISTRATOR` |
| `editor-dashboard-sidebar.tsx` | Same gate |
| `page.tsx` landing | Remove "Research dashboard" button; keep EPSRC context section |
| `(app)/research/layout.tsx` | **New** — redirect non-researchers to `/dashboard` |

Researchers access `/research` via direct URL or role-assigned sidebar.

### F2. Participant journey

```
Sign up → Consent (required) → Onboarding → Use app
  → Passive event logging (quantitative)
  → Survey modal (after N sessions or on publish)
  → Optional open reflection
  → Optional interview opt-in (if researchContactOptIn)
```

### F3. Quantitative data (automatic)

Ensure these events fire with `sessionId`:

| Event | Trigger |
|-------|---------|
| `SESSION_STARTED` / `SESSION_ENDED` | Editor mount/unmount |
| `MODEL_GENERATED` | Mesh pipeline complete |
| `SEGMENTATION_COMPLETED` | FastAPI job done |
| `ANNOTATION_CREATED` | Rect mark saved |
| `AI_PROMPT_SUBMITTED` / `ACCEPTED` / `REJECTED` | AI bar |
| `EXPORT_REQUESTED` | STL download |
| `PROJECT_PUBLISHED` | Community publish |
| `SURVEY_COMPLETED` | Likert submit |

Export: `/api/research/export` → CSV/JSON/XLSX (supervisor only).

### F4. Qualitative data (prompted)

| Method | Implementation |
|--------|----------------|
| Likert survey | Modal after 3rd session or project publish |
| Open reflection | Textarea on assignment completion / editor exit |
| AI rejection notes | Optional text when rejecting AI suggestion |
| Interview booking | Link for `researchContactOptIn` users |
| New model | `QualitativeResponse` table (see §11) |

### F5. New route: `/participate`

Public-facing page explaining the study, linking to information sheet — **not** the dashboard.

### F6. Missing asset

Add `public/research-information-sheet.pdf` (referenced in consent page).

---

## 8. Phase G — Auth, DB & production hardening

| Task | Detail |
|------|--------|
| Disable preview mode | `UI_PREVIEW_MODE=false` in production |
| Clerk webhook | `/api/webhooks/clerk` — user delete/update sync |
| Session tracking | UUID `sessionId` on all research events |
| Prisma migrations | Replace `db:push` with proper migrations for production |
| Env on Vercel | All vars from `.env.example` + `FAL_KEY`, `ML_SERVICE_URL` |
| R2 migration | Optional: move public assets from S3 to Cloudflare R2 (Pascal pattern) |
| Error monitoring | Sentry free tier |
| Rate limiting | On ML proxy routes |

---

## 9. Infrastructure & cost guide

### Pascal Editor stack (reference)

| Layer | Pascal uses | DentalSculptor |
|-------|-------------|----------------|
| Hosting | Vercel | Vercel ✓ |
| Auth | Better Auth + Supabase | Clerk ✓ |
| DB | Supabase Postgres | Supabase Postgres ✓ |
| Assets | Amazon S3 (+ CloudFront optional) | S3 ✓ (AWS credits) |
| ML | None | FastAPI GPU worker |
| Analytics | — | PostHog ✓ |

### Recommended free/cheap stack (research pilot)

| Service | Tier | Use |
|---------|------|-----|
| Vercel | Hobby | App hosting |
| Supabase | Free → Pro $25/mo | Postgres |
| Clerk | Free ~10k MAU | Auth |
| Cloudflare R2 | 10 GB free | Meshes, thumbnails |
| PostHog | 1M events/mo free | Analytics mirror |
| Modal / RunPod | Credits / spot | GPU inference |
| Upstash Redis | Free | Job queue |
| Resend | Free | Participant emails |

**Estimated pilot cost:** $0–30/mo without GPU; +$50–150/mo with always-on T4.

### Environment variables (complete list)

See `dentalsculptor-app/.env.example` plus:

```env
# ML (add to .env.example)
FAL_KEY=
ML_MESH_PROVIDER=fal
ML_SERVICE_URL=http://localhost:8000
ML_SERVICE_API_KEY=

# Optional R2 (replace or supplement S3)
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
NEXT_PUBLIC_ASSETS_CDN_URL=
```

---

## 10. Pascal polish checklist

| Item | Priority |
|------|----------|
| Click/hover SFX | High |
| Selection outline in 3D | High |
| Export success toast + sound | High |
| Tool tooltips | Medium |
| Panel collapse animation (Framer Motion) | Medium |
| Keyboard shortcuts (V/M/E/Ctrl+Z) | Medium |
| Loading progress during generate | Medium |
| Empty state in cream viewport | Medium |
| Community card hover effects | Low |
| Status bar part count | Low |

---

## 11. Schema additions

Add to `prisma/schema.prisma`:

```prisma
// Extend DentalModel
model DentalModel {
  // ... existing fields
  inputType         String?   // "photo" | "ct_volume" | "ios_mesh" | "stl"
  segmentationJobId String?
  segmentData       Json?     // [{ id, label, meshUrl, color, confidence, fdiNumber? }]
}

model SegmentationJob {
  id        String   @id @default(cuid())
  projectId String
  status    String   // queued | running | complete | failed
  modelType String   // dental_segmentator | dental_model_seg | custom
  inputUrl  String
  outputUrl String?
  progress  Int      @default(0)
  error     String?
  createdAt DateTime @default(now())
}

model QualitativeResponse {
  id         String   @id @default(cuid())
  userId     String
  projectId  String?
  promptType String   // exit_reflection | usability_note | ai_rejection_note | interview_request
  response   String
  sessionId  String?
  createdAt  DateTime @default(now())
  user       User     @relation(fields: [userId], references: [id])
}

// Add to ResearchEventType enum:
// SEGMENTATION_COMPLETED
// SEGMENTATION_FAILED
// CONSENT_GIVEN
```

---

## 12. Sprint schedule (12 weeks)

| Sprint | Weeks | Focus | Deliverable |
|--------|-------|-------|-------------|
| 1 | 1–2 | Design tokens + selection + SFX + research nav gate | Parts highlight in 3D; dashboard hidden from participants |
| 2 | 3–4 | STL export + export modal | Real `.stl` download |
| 3 | 5–6 | fal.ai mesh gen + GLTFLoader | Photo → real 3D mesh |
| 4 | 7–8 | Preview + duplicate + publish + share | Full project lifecycle |
| 5 | 9–10 | Participant surveys + session tracking | Research data flows remotely |
| 6 | 11–12 | FastAPI v1 (DentalModelSeg) | IOS → real tooth parts |
| 7 | 13–14 | FastAPI v2 (DentalSegmentator) | CBCT → anatomical parts |
| 8 | 15–16 | Community thumbnails + landing grid | Pascal-style showcase |
| 9 | 17–18 | Undo/redo + annotation persist | Editor maturity |
| 10 | 19–20 | Custom model swap | Replace fal.ai |
| 11–12 | 21–24 | XR + student pilot | End-to-end research collection |

---

## 13. Success criteria

### MVP (pilot-ready)

- [ ] Educator uploads photo → receives 3D mesh (fal.ai)
- [ ] Model Parts panel shows segmented regions with 3D highlight/hide
- [ ] Export selected parts to STL
- [ ] Publish to community with thumbnail
- [ ] Participant consent + passive event logging + survey trigger
- [ ] Supervisor exports CSV/JSON from `/research`
- [ ] Research dashboard not visible to EDUCATOR/STUDENT roles

### Research-ready

- [ ] Session-level metrics with sessionId
- [ ] Qualitative reflections stored
- [ ] Real segmentation for at least one input type (IOS or CT)
- [ ] De-identification consent on clinical uploads
- [ ] Information sheet PDF published

### Production

- [ ] Preview mode off; Clerk + Supabase fully configured
- [ ] Prisma migrations deployed
- [ ] Custom dental model replaces fal.ai
- [ ] WebXR loads exported mesh

---

## References

| Resource | URL |
|----------|-----|
| Pascal Editor | https://github.com/pascalorg/editor |
| Pascal live demo | https://editor.pascal.app/ |
| DentalSegmentator | https://github.com/gaudot/SlicerDentalSegmentator |
| DentalModelSeg | https://github.com/DCBIA-OrthoLab/SlicerDentalModelSeg |
| nnU-Net weights (Zenodo) | https://zenodo.org/doi/10.5281/zenodo.10829674 |
| fal.ai Hunyuan3D | https://fal.ai/models/fal-ai/hunyuan3d/v2/turbo |
| Bloom reference (local) | `../bloom-v0/` |

---

*Maintained alongside [PROJECT_WALKTHROUGH.md](./PROJECT_WALKTHROUGH.md). Update both when completing a sprint or making architectural decisions.*
