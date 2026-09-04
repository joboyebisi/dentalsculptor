# DentalSculptor

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

**AI-Aided 3D authoring for dental educators** — an academic research platform for creating, editing, and sharing immersive dental learning experiences. Part of a doctoral research programme investigating educator agency, pedagogical ownership, and human–AI co-creation in dental education.

**Live app:** [dentalsculptor.vercel.app](https://dentalsculptor.vercel.app)

**WebMCP diagnostics:** [dentalsculptor.vercel.app/webmcp](https://dentalsculptor.vercel.app/webmcp)

**Public source:** [github.com/joboyebisi/dentalsculptor](https://github.com/joboyebisi/dentalsculptor)

## Why WebMCP

Dental case authoring combines long-running generation, spatial 3D decisions, clinical presets,
reversible revisions, and simulator exports. UI automation has to guess whether a model is loaded
or which action is valid; full autonomy would hide decisions an educator needs to own.

DentalSculptor exposes 29 structured, page-scoped WebMCP tools from the same visible workspace.
The agent inspects state, coordinates generation and case setup, and prepares reuse. The educator
selects source material, marks anatomy, approves revisions, confirms privacy, and authorizes
release.

> **The agent coordinates the workflow. The educator owns the anatomy, approval, and release.**

Read the [WebMCP submission pack](./docs/webmcp/README.md), [project story](./docs/webmcp/PROJECT_STORY.md),
and [judge guide](./docs/webmcp/JUDGE_GUIDE.md).

## WebMCP challenge quick start

DentalSculptor keeps WebMCP inside the production application so tools share the
same authenticated project, 3D scene, revision history, and educator approvals as
the visible interface. A separate agent-only application would create a second
source of truth and weaken the human-in-the-loop workflow.

To try it:

1. Open the [live app](https://dentalsculptor.vercel.app) in ChatGPT's in-app browser; or enable `chrome://flags/#enable-webmcp-testing` in a compatible Chrome build and open the same URL.
2. Ask the agent to inspect DentalSculptor. On the landing page it can report generation readiness and navigate workspaces.
3. Select a dental image in the visible UI, then ask the agent to generate the 3D model.
4. Continue to a guided teaching case or Free Editor. The agent can synchronize a preset and open the marking tool; the educator marks the clinical target and approves the preview.
5. Ask the agent to create the reversible variant, then use the visible export or share flow.
6. Open the [diagnostics page](https://dentalsculptor.vercel.app/webmcp) to inspect the browser's
   live `document.modelContext.getTools()` result.

WebMCP is additive: browsers without `document.modelContext` retain the existing
DentalSculptor experience. Public or irreversible clinical actions remain under
explicit educator control. See [WebMCP implementation and verification](./docs/WEBMCP_IMPLEMENTATION.md).

| | |
|---|---|
| **App** | [`dentalsculptor-app/`](./dentalsculptor-app/) — Next.js 16 production application |
| **Design reference** | [`stitch_dentalsculptor_xr_authoring_platform/`](./stitch_dentalsculptor_xr_authoring_platform/) — Stitch UI specs |
| **3D generation prototype** | [`bloom-v0/`](./bloom-v0/) — fal.ai Hunyuan3D integration reference |
| **Logo** | [`logo.png`](./logo.png) — DS molar mark |

---

## Documentation index

| Document | Purpose |
|----------|---------|
| [**Project Walkthrough**](./docs/PROJECT_WALKTHROUGH.md) | Full context of work completed, architecture, file map, current state vs gaps |
| [**Implementation Plan**](./docs/IMPLEMENTATION_PLAN.md) | Future roadmap: Pascal polish, ML pipeline, research flows, infra |
| [**Clinical Authoring Workflows**](./docs/CLINICAL_AUTHORING_WORKFLOWS.md) | Recommended tooth, jaw, volume, segmentation, case-authoring and export UX |
| [**3D Editing Research**](./docs/3D_EDITING_RESEARCH.md) | Nano3D/TRELLIS evaluation, masked editing contract and Modal rollout |
| [**Deployment Guide**](./docs/DEPLOYMENT.md) | Vercel vs GitHub Pages, env vars, Clerk, Supabase, fal.ai |
| [**Supabase Setup**](./docs/SUPABASE_SETUP.md) | Database + Storage bucket configuration |
| [**Environment Variables**](./docs/ENV.md) | `.env` vs `.env.example`, full variable list |
| [**Sprint Roadmap**](./docs/SPRINT_ROADMAP.md) | **Active task tracker** — OAuth, edit, export, placement, multilayer |
| [**Pilot release (27 Aug 2026)**](./docs/PILOT_RELEASE_2026-08-27.md) | **Latest push inventory** — Nano3D Modal fix, evaluation UX, benchmarks |
| [**Real-time evaluation handoff**](./docs/REALTIME_EVALUATION_HANDOFF.md) | Pilot gates: generation → edit → export study path |
| [**WebMCP implementation**](./docs/webmcp/README.md) | Agent tool contract, human approval boundary and browser verification |
| [**WebMCP Challenge story**](./docs/webmcp/PROJECT_STORY.md) | Copy-ready Devpost narrative: inspiration, implementation and learning |
| [**WebMCP judge guide**](./docs/webmcp/JUDGE_GUIDE.md) | Private invite template, prompts, expected states and diagnostics |
| [**Supabase OAuth Setup**](./docs/SUPABASE_OAUTH_SETUP.md) | Google + Microsoft SSO configuration |
| [**Design System**](./DESIGN.md) | Clinical Precision design tokens |
| [App README](./dentalsculptor-app/README.md) | Setup, env vars, deployment |
| [Architecture](./dentalsculptor-app/ARCHITECTURE.md) | Database, auth, API overview |

---

## Quick start

```bash
cd dentalsculptor-app
npm install
cp .env.example .env.local
# Configure Supabase, DATABASE_URL and Modal endpoints as needed
npm run db:push
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

**UI preview mode** (no Clerk/DB): set `UI_PREVIEW_MODE=true` in `.env`, then visit `/editor/preview-project-1`.

---

## Repository structure

```
DentalSculptor/
├── dentalsculptor-app/          # Main Next.js app (deploy this)
├── bloom-v0/                    # fal.ai 3D generation reference
├── stitch_dentalsculptor_xr_authoring_platform/  # Design mockups & specs
├── docs/                        # Project documentation (start here)
│   └── PILOT_RELEASE_2026-08-27.md  # Latest unreleased-until-now change log
├── research/                    # Validation sets & workflow research
├── dentalsculptor-ml/           # Modal TRELLIS + Nano3D workers
└── README.md                    # This file
```

---

## Tech stack (summary)

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Auth | Supabase Auth |
| Database | Supabase PostgreSQL + Prisma 7 |
| Storage | AWS S3 (+ Cloudflare R2 planned) |
| 3D | Three.js, React Three Fiber, Drei |
| Analytics | PostHog + Prisma research events |
| Hosting | Vercel (recommended) |

---

## Research programme

DentalSculptor is funded as part of EPSRC CDT in Data-Centric Engineering research at Queen Mary University of London. The platform is designed as a **research instrument**: participant interactions are logged (with consent) for quantitative and qualitative analysis. The supervisor research dashboard at `/research` is role-gated — not shown to general participants.

See [Implementation Plan § Research](./docs/IMPLEMENTATION_PLAN.md#7-research-participant-flow) for participant vs researcher flows.

---

## License

Licensed under the [MIT License](./LICENSE).
