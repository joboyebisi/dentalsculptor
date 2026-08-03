# DentalSculptor — Project Walkthrough

> **Purpose of this document:** Preserve full context of what has been built, why decisions were made, and what remains incomplete. Read this before starting any new development session.

**Last updated:** August 2026  
**Repository:** [github.com/joboyebisi/dentalsculptor](https://github.com/joboyebisi/dentalsculptor)

---

## Table of contents

1. [Project vision](#1-project-vision)
2. [Research context](#2-research-context)
3. [Design references & decisions](#3-design-references--decisions)
4. [What has been built](#4-what-has-been-built)
5. [Editor architecture (detailed)](#5-editor-architecture-detailed)
6. [3D viewer & visual design](#6-3d-viewer--visual-design)
7. [Authentication & onboarding flow](#7-authentication--onboarding-flow)
8. [Database & API](#8-database--api)
9. [Research tracking](#9-research-tracking)
10. [Community & sharing](#10-community--sharing)
11. [Branding & assets](#11-branding--assets)
12. [UI preview mode](#12-ui-preview-mode)
13. [External references analysed](#13-external-references-analysed)
14. [Current gaps (honest status)](#14-current-gaps-honest-status)
15. [File map](#15-file-map)
16. [Development commands](#16-development-commands)
17. [Known issues & fixes](#17-known-issues--fixes)

---

## 1. Project vision

DentalSculptor enables **dental educators** to:

1. Upload a clinical image or scan
2. Generate or load a 3D dental model
3. Segment anatomical parts (enamel, dentin, teeth, jaw structures)
4. Annotate and apply AI-aided semantic edits
5. Export to STL for simulators / VR
6. Publish and share with students or the community

The platform doubles as a **doctoral research instrument** measuring educator ownership, agency, personalisation, and confidence when co-creating with AI.

**Terminology rule:** Always use **"AI-Aided"** (not "AI-assisted") across the app.

---

## 2. Research context

| Item | Detail |
|------|--------|
| Institution | Queen Mary University of London |
| Funding | EPSRC CDT in Data-Centric Engineering |
| Research themes | Pedagogical ownership, educator agency, human–AI co-creation |
| Consent | Required at `/consent` before app access |
| Information sheet | `/research-information-sheet.pdf` (referenced; file to be added to `public/`) |
| Supervisor dashboard | `/research` — RESEARCHER and ADMINISTRATOR roles only (to be fully gated) |
| Participant flow | Consent → onboarding → use app → passive event logging → periodic surveys |

---

## 3. Design references & decisions

### Stitch design system

Location: `stitch_dentalsculptor_xr_authoring_platform/`

The editor layout follows **Advanced Authoring Workspace v3** from Stitch mockups:
- Hamburger opens dashboard sidebar (leftmost)
- Collapsible source panel (upload / generate) beside dashboard
- Central 3D viewport
- Floating tools on the **right** of viewport
- **Model Parts** panel (was "Properties") with segmentation checkboxes
- Full-width AI edit bar at bottom

### Pascal Editor inspiration

Reference: [github.com/pascalorg/editor](https://github.com/pascalorg/editor) / [editor.pascal.app](https://editor.pascal.app/)

Borrowed concepts (UI shell level):
- Cream/neutral 3D canvas vs dark authoring chrome
- Floating tool rail with active tool states
- Selection sync between panel and 3D (planned, not fully wired)
- Export as primary header action
- Community showcase cards
- SFX micro-interactions (planned)
- Scene registry pattern for part picking (planned)

**Not adopted:** Pascal's CSG/wall-building node graph, WebGPU requirement, architectural domain model.

### Bloom / fal.ai reference

Location: `bloom-v0/`

Reference implementation for photo → 3D mesh via **fal.ai Hunyuan3D Turbo**:
- `bloom-v0/src/app/api/generate/route.ts`
- Upload image → `fal.storage.upload` → `fal.subscribe("fal-ai/hunyuan3d/v2/turbo")` → GLB URL

This is the **interim mesh generation path** until a custom dental model is trained.

---

## 4. What has been built

### Landing page (`dentalsculptor-app/src/app/page.tsx`)

Section order (as requested):
1. Hero (with AppLogo)
2. Workbench preview
3. How it works (Step 3 mentions STL export to simulators/VR)
4. Community spotlights
5. Research context (QMUL/EPSRC — no public dashboard link planned)

### Authenticated app shell

Routes under `(app)/` with sidebar navigation:
- Dashboard, Projects, Community, Students, Settings
- Research (to be role-gated — currently in nav for all)

### Editor workspace (major rebuild)

Full-screen workspace under `(workspace)/editor/[id]/`:

| Component | File | Status |
|-----------|------|--------|
| Layout orchestrator | `editor-workspace.tsx` | ✅ Shell complete |
| Header (tabs, Export) | `editor-header.tsx` | ⚠️ Export mock; Share/Preview unwired |
| Dashboard sidebar | `editor-dashboard-sidebar.tsx` | ✅ Toggle nav |
| Source panel | `editor-source-panel.tsx` | ✅ Upload + Generate UI |
| 3D viewer | `cam-model-viewer.tsx` | ✅ Orbit, grid, rect marks, raycast |
| Tool palette | `editor-tool-palette.tsx` | ⚠️ Several tools unwired |
| AI edit bar | `editor-ai-bar.tsx` | ⚠️ Apply is mocked (1.2s timeout) |
| Model Parts panel | `editor-properties-panel.tsx` | ✅ Checkboxes; no 3D sync yet |
| Status bar | `editor-status-bar.tsx` | ✅ |

### 3D generation

- `src/lib/model-generator.ts` — procedural tooth mesh from image (mock)
- No fal.ai wired into main app yet (exists only in `bloom-v0/`)

### Segmentation (mock)

- `src/lib/editor-segmentation.ts` — 8 mock parts (Enamel, Dentin, Pulp, etc.)
- Generated after "Generate" button; not connected to real ML

### Branding

- `src/components/brand/app-logo.tsx` — `AppLogo` / `AppLogoMark`
- Logo copied to `public/logo.png`, `src/app/icon.png`, `apple-icon.png`, favicons
- Replaced generic Sparkles icons with DS logo where appropriate

### Community

- `/community` page lists published projects
- `POST /api/community/[projectId]/clone` — deep clone works, tracks `PROJECT_CLONED`
- Publish UI/API not fully wired

### Research instrumentation

- 25+ `ResearchEventType` enums in Prisma
- Client hook: `src/hooks/use-research-tracker.ts`
- Server: `src/lib/research-events.ts`
- Dashboard: `src/app/(app)/research/page.tsx` (metrics, timeline, surveys, export)
- PostHog parallel tracking when configured

---

## 5. Editor architecture (detailed)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ EditorHeader — Save | Export (primary) | Preview | Share | Tabs            │
├──────┬──────────┬───────────────────────────────────────┬──────────┬───────┤
│ Dash │ Source   │                                       │ Tools  │ Parts │
│ Side │ Panel    │         CamModelViewer                │ (float)│ Panel │
│ bar  │ upload/  │         cream viewport #e8ecf0         │ right  │ 220px │
│      │ generate │                                       │        │       │
├──────┴──────────┴───────────────────────────────────────┴──────────┴───────┤
│ EditorAiBar — multiline prompt + in-box Apply (disabled until part selected)│
├─────────────────────────────────────────────────────────────────────────────┤
│ EditorStatusBar                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Layout order:** Dashboard sidebar | Source panel | Viewport + tools | Parts panel

**Tools implemented in UI:**
- Select — mesh click callback exists
- Rect Mark — drag rectangle (not point click)
- Edit — sets AI bar mode
- Undo/Redo, Pan, Zoom, Wireframe, Texture — UI only, no handlers

**Camera:** `src/lib/camera-utils.ts` — bounding-sphere fit, McCleery/Anneal-style math

---

## 6. 3D viewer & visual design

### Cream viewport / dark chrome (intentional)

This mirrors Pascal Editor's scene-vs-UI contrast:

| Zone | Colors | Rationale |
|------|--------|-----------|
| Viewport background | `#e8ecf0` | Clinical, neutral — the "specimen" |
| Mesh material | `#e8dcc8` / `#f5e6d3` (cream) | Anatomical warmth |
| Tools, AI bar, panels | Dark surfaces (`#0a0a0a`–`#111827`) | Focused instrument UI |
| Primary action | `#0F3D91` (medical blue) | Not indigo for Apply/Export |
| Rect marks | `#0F3D91` | Annotation overlay |

Defined in:
- `cam-model-viewer.tsx` — viewport + mesh
- `globals.css` — design tokens
- `src/lib/constants.ts` — `COLORS`

**Rule for future work:** Never revert editor panels to white/light inside the workspace. Keep the cream viewport + dark chrome split.

---

## 7. Authentication & onboarding flow

```
/ (landing)
  → /sign-in or /sign-up (Clerk)
  → /consent (research consent — required checkbox)
  → /onboarding (role, institution)
  → /dashboard
```

| File | Role |
|------|------|
| `src/middleware.ts` | Clerk; public: `/`, sign-in/up, webhooks, `/community` |
| `src/lib/auth.ts` | `getAuthUser()` syncs Clerk → Prisma User |
| `src/lib/preview-mode.ts` | Bypasses auth when `UI_PREVIEW_MODE=true` |

**Roles:** EDUCATOR, STUDENT, RESEARCHER, ADMINISTRATOR

---

## 8. Database & API

### Prisma schema highlights

File: `dentalsculptor-app/prisma/schema.prisma`

Key models: `User`, `Project`, `DentalModel`, `Annotation`, `CommunityProject`, `ResearchEvent`, `SurveyResponse`, `StudentAssignment`, `ProjectVersion`

### API routes

```
/api/projects                          POST create + upload + mesh gen
/api/projects/[id]                     GET/PATCH
/api/projects/[id]/annotations         POST
/api/projects/[id]/assessments
/api/projects/[id]/learning-objectives
/api/community/[projectId]/clone       POST clone
/api/research/events                   POST log event
/api/research/metrics                  GET
/api/research/timeline                 GET (researcher/admin)
/api/research/surveys                  GET/POST
/api/research/export                   GET CSV/JSON/XLSX (researcher/admin)
/api/user/consent                      POST
/api/user/onboarding                   POST
/api/user/profile                      GET/PATCH
/api/students/assignments              ...
```

**Missing APIs (planned):**
- `POST /api/projects/[id]/publish`
- `POST /api/projects/[id]/duplicate`
- `POST /api/projects/[id]/export`
- `POST /api/projects/[id]/segment`
- Clerk webhook `/api/webhooks/clerk`

### Storage

- AWS S3 via `@aws-sdk/client-s3`
- Falls back to `local://` keys without AWS credentials in dev

---

## 9. Research tracking

### Quantitative (automatic)

Every important action should fire `track()` via `useResearchTracker` or server-side `trackResearchEvent`.

**Editor events already tracked:**
- `ANNOTATION_CREATED`, `MODEL_EDITED`, `AI_PROMPT_SUBMITTED`, `AI_SUGGESTION_ACCEPTED`, `MODEL_GENERATED`

**Metrics computed** (`getResearchMetrics`):
- Ownership, Agency, Personalisation, Confidence scores

### Qualitative (prompted)

- Likert survey (5 questions in `constants.ts`) — UI on `/research`, needs participant trigger
- Student reflections via `/students` assignments
- Planned: open-text prompts, exit interview opt-in

### Export

Researchers export from `/api/research/export?format=CSV|JSON|XLSX`

---

## 10. Community & sharing

| Feature | Status |
|---------|--------|
| Browse published projects | ✅ |
| Clone / remix | ✅ API works |
| Publish to community | ❌ No UI; schema ready |
| Share link | ❌ Header button unwired |
| Thumbnails | ❌ Not generated |
| Likes | Schema exists; UI minimal |

---

## 11. Branding & assets

| Asset | Path |
|-------|------|
| Source logo | `logo.png` (repo root) |
| App icon | `dentalsculptor-app/src/app/icon.png` |
| Apple icon | `dentalsculptor-app/src/app/apple-icon.png` |
| Public logo | `dentalsculptor-app/public/logo.png` |
| Favicon | `dentalsculptor-app/public/favicon.png`, `favicon.ico` |

Tagline: **"AI-Aided 3D authoring for dental educators"** (`APP_TAGLINE` in constants)

---

## 12. UI preview mode

For UI development without Clerk or database:

```env
UI_PREVIEW_MODE=true
NEXT_PUBLIC_UI_PREVIEW_MODE=true
```

- Mock user injected via `preview-mode.ts`
- Preview editor: `/editor/preview-project-1`
- Data from `src/lib/preview-data.ts`

**Turn off before production pilot.**

---

## 13. External references analysed

### Pascal Editor
- SFX bus, selection registry, STL/GLB export, community cards, preview/duplicate/share
- Infra: Vercel + Supabase + Cloudflare R2
- See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

### SlicerDentalSegmentator
- [github.com/gaudot/SlicerDentalSegmentator](https://github.com/gaudot/SlicerDentalSegmentator)
- Input: CT/CBCT volumes → 5 classes (maxilla, mandible, upper/lower teeth, mandibular canal)
- nnU-Net v2; weights on Zenodo; needs CUDA + ~32GB RAM

### SlicerDentalModelSeg
- [github.com/DCBIA-OrthoLab/SlicerDentalModelSeg](https://github.com/DCBIA-OrthoLab/SlicerDentalModelSeg)
- Input: IOS jaw scans (.vtk) → per-tooth FDI/Universal labels
- Linux + CUDA only currently

Both planned as **FastAPI GPU workers** — see Implementation Plan §6.

---

## 14. Current gaps (honest status)

| Area | Status |
|------|--------|
| 3D mesh | Procedural mock; fal.ai not wired |
| Part selection → 3D | UI checkboxes only; no highlight/hide |
| Export STL | Mock delay only |
| Share / Preview header | UI only |
| Undo/redo, pan, zoom tools | No handlers |
| AI Apply | Mocked timeout |
| Annotations persist | API exists; rect marks client-side only |
| Publish to community | Schema only |
| Research dashboard in nav | Visible to all — should be role-gated |
| SFX | None |
| WebXR | Placeholder at `/xr/[id]` |
| Real segmentation | Mock parts only |
| Clerk webhook | Not implemented |
| Research info sheet PDF | Not in public/ |

---

## 15. File map

### Editor components
```
dentalsculptor-app/src/components/editor/
├── editor-workspace.tsx       # Main layout
├── editor-header.tsx
├── editor-dashboard-sidebar.tsx
├── editor-source-panel.tsx
├── cam-model-viewer.tsx       # Primary 3D canvas
├── editor-tool-palette.tsx
├── editor-ai-bar.tsx
├── editor-properties-panel.tsx  # Model Parts
└── editor-status-bar.tsx
```

### Core libraries
```
dentalsculptor-app/src/lib/
├── constants.ts
├── auth.ts
├── prisma.ts
├── model-generator.ts         # Procedural mesh
├── editor-segmentation.ts     # Mock parts
├── camera-utils.ts
├── research-events.ts
├── preview-mode.ts
└── preview-data.ts
```

### Routes
```
dentalsculptor-app/src/app/
├── page.tsx                   # Landing
├── consent/page.tsx
├── onboarding/page.tsx
├── (app)/                     # Sidebar app
│   ├── dashboard/
│   ├── projects/
│   ├── community/
│   ├── students/
│   ├── research/
│   └── settings/
└── (workspace)/
    ├── editor/[id]/
    └── xr/[id]/
```

---

## 16. Development commands

```bash
cd dentalsculptor-app
npm install
npm run dev          # localhost:3000
npm run build        # prisma generate + next build
npm run db:push      # push schema to Supabase
npm run db:studio    # Prisma Studio
npm run db:seed      # seed platform metrics
```

---

## 17. Known issues & fixes

### Corrupted `.next` cache
**Symptom:** ENOENT on `build-manifest.json`  
**Fix:** Stop dev server → kill node → delete `.next/` → `npm run dev`

### Clerk keys
Publishable key must start with `pk_test_` or `pk_live_`. Do not use `ssk_` keys.

### Prisma generated client
Output at `src/generated/prisma/` — gitignored; regenerated on `npm install` / `prisma generate`.

---

## Conversation history

Detailed AI pair-programming sessions are stored in Cursor agent transcripts. Search for filenames like `editor-workspace.tsx`, `cam-model-viewer.tsx`, or task keywords when resuming work.

---

*Next: read [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for the full roadmap.*
