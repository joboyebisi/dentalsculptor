# DentalSculptor

**AI-Aided 3D authoring for dental educators** — an academic research platform for creating, editing, and sharing immersive dental learning experiences. Part of a doctoral research programme investigating educator agency, pedagogical ownership, and human–AI co-creation in dental education.

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
| [**Supabase OAuth Setup**](./docs/SUPABASE_OAUTH_SETUP.md) | Google + Microsoft SSO configuration |
| [**Design System**](./DESIGN.md) | Clinical Precision design tokens |
| [App README](./dentalsculptor-app/README.md) | Setup, env vars, deployment |
| [Architecture](./dentalsculptor-app/ARCHITECTURE.md) | Database, auth, API overview |

---

## Quick start

```bash
cd dentalsculptor-app
npm install
cp .env.example .env
# Configure Clerk, DATABASE_URL, optional AWS/PostHog
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
├── logo.png                     # Brand mark
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

Proprietary — DentalSculptor Research Programme. Contact the research team for reuse permissions.
