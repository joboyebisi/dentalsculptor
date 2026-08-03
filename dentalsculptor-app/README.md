# DentalSculptor App

AI-Aided educational authoring platform for dental educators to create, edit, deploy, and share immersive 3D dental learning experiences. Built as a research-ready instrument for doctoral studies on pedagogical ownership, educator agency, and human-AI co-creation.

> **Full project documentation** (walkthrough, implementation plan, context): see [`../docs/`](../docs/) at the repository root.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Vercel (Hosting)                          │
├─────────────────────────────────────────────────────────────────┤
│  Next.js 15 App Router                                           │
│  ├── Public: Landing, Auth (Clerk), Community                   │
│  ├── Onboarding: Consent → Role → Institution                    │
│  ├── App Shell: Dashboard, Projects, Students, Research          │
│  └── Workspace: 3D Editor, WebXR (full-screen)                 │
├─────────────────────────────────────────────────────────────────┤
│  API Routes (/api/*)                                             │
│  ├── Projects, Annotations, Assessments                          │
│  ├── Research Events, Surveys, Export                            │
│  └── User, Community, Students                                   │
├─────────────────────────────────────────────────────────────────┤
│  Services                                                        │
│  ├── Clerk (Auth: Google, Microsoft, Email)                    │
│  ├── Supabase PostgreSQL + Prisma ORM                            │
│  ├── AWS S3 + CloudFront (asset storage)                         │
│  ├── PostHog (product analytics)                                 │
│  └── Three.js / R3F (3D viewer) + WebXR                          │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, TailwindCSS, Shadcn/UI, Framer Motion |
| Auth | Clerk (Google, Microsoft, Email OAuth) |
| Database | Supabase PostgreSQL, Prisma ORM 7 |
| Storage | AWS S3, CloudFront CDN |
| Analytics | PostHog + custom research event tracking |
| 3D | Three.js, React Three Fiber, Drei |
| XR | WebXR, Meta Quest Browser support |
| Hosting | Vercel |

## Design System

**Clinical Precision** — light-mode first, medical blue (#0F3D91), AI purple (#7C3AED), research indigo (#4F46E5). See `stitch_dentalsculptor_xr_authoring_platform/clinical_precision_fluidity/DESIGN.md`.

## Getting Started

### Prerequisites

- Node.js 20+
- PostgreSQL database (Supabase recommended)
- Clerk account
- AWS S3 bucket (optional for local dev)

### Installation

```bash
cd dentalsculptor-app
npm install
cp .env.example .env
# Fill in environment variables (see below)
npm run db:push
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/consent
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/consent

# Supabase PostgreSQL
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres

# AWS (optional locally — uses local:// paths without credentials)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=eu-west-1
AWS_S3_BUCKET=dentalsculptor-assets
AWS_CLOUDFRONT_URL=

# PostHog (optional)
NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com

NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Database Setup

```bash
# Push schema to Supabase
npm run db:push

# Run migrations (production)
npm run db:migrate

# Open Prisma Studio
npm run db:studio

# Seed platform metrics
npm run db:seed
```

## Application Routes

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/sign-in`, `/sign-up` | Clerk authentication |
| `/consent` | Research participation consent |
| `/onboarding` | Role & institution setup |
| `/dashboard` | Main hub with widgets |
| `/projects` | Project list |
| `/projects/new` | Upload → Generate 3D flow |
| `/editor/[id]` | 3D authoring workspace |
| `/community` | Community hub |
| `/students` | Student portal |
| `/research` | Research analytics dashboard |
| `/xr/[id]` | WebXR / Meta Quest preview |
| `/settings` | User profile |

## Research Event Tracking

All important interactions are logged to `ResearchEvent` table:

- **Project**: create, upload, generate, edit, annotate, publish, download, XR launch
- **AI**: prompt submitted, suggestion accepted/rejected, manual override
- **Community**: share, clone, comment, bookmark
- **Student**: assignment started/completed, reflection, assessment
- **Survey**: Likert scale responses

Events are also sent to PostHog when configured.

## Data Export

Researchers (RESEARCHER or ADMINISTRATOR role) can export from `/research`:

- **CSV** — research event logs
- **JSON** — full dataset (events, surveys, participants)
- **XLSX** — survey responses (TSV format)

API: `GET /api/research/export?format=CSV|JSON|XLSX`

## Clerk Setup

1. Create application at [clerk.com](https://clerk.com)
2. Enable Google, Microsoft, and Email authentication
3. Set redirect URLs to your domain + `/consent`
4. Copy publishable and secret keys to `.env`

## Supabase Setup

1. Create project at [supabase.com](https://supabase.com)
2. Copy connection string from Settings → Database
3. Use **Transaction** pooler URL for serverless (Vercel)
4. Set as `DATABASE_URL`

## AWS S3 Setup

1. Create S3 bucket with private access
2. Configure CORS for your domain
3. Create IAM user with `s3:PutObject`, `s3:GetObject`
4. Optional: CloudFront distribution for CDN

## Vercel Deployment

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard
# Run database migration
npx prisma migrate deploy
```

### Vercel Checklist

- [ ] All env vars configured in Vercel project settings
- [ ] `DATABASE_URL` uses Supabase pooler (port 6543)
- [ ] Clerk production keys with correct domain
- [ ] Build command: `prisma generate && next build`
- [ ] Run `prisma migrate deploy` post-deploy

## User Roles

| Role | Access |
|------|--------|
| EDUCATOR | Create projects, editor, publish |
| STUDENT | Assignments, simulations, reflections |
| RESEARCHER | Research dashboard, data export |
| ADMINISTRATOR | Full platform access |

## 3D Model Generation

The MVP includes a procedural dental mesh generator (`src/lib/model-generator.ts`) that creates editable tooth geometry from uploaded images. In production, replace with your AI reconstruction pipeline by updating `POST /api/projects`.

## Project Structure

```
dentalsculptor-app/
├── prisma/
│   └── schema.prisma          # Database schema
├── src/
│   ├── app/
│   │   ├── (app)/             # Authenticated app with sidebar
│   │   ├── (workspace)/       # Full-screen editor & XR
│   │   ├── api/               # REST API routes
│   │   ├── consent/           # Research consent
│   │   └── onboarding/        # User onboarding
│   ├── components/
│   │   ├── three/             # 3D viewer, WebXR
│   │   ├── ui/                # Shadcn components
│   │   └── layout/            # Navigation, sidebar
│   ├── lib/                   # Utilities, Prisma, S3, research
│   └── hooks/                 # Research tracking hook
└── stitch_dentalsculptor_xr_authoring_platform/  # Design specs
```

## License

Proprietary — DentalSculptor Research Programme
