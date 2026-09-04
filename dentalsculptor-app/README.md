# DentalSculptor application

The production Next.js application for DentalSculptor: an AI-aided 3D authoring platform where
dental educators create, edit, review, export, and share immersive teaching cases.

- Live app: <https://dentalsculptor.vercel.app>
- WebMCP diagnostics: <https://dentalsculptor.vercel.app/webmcp>
- WebMCP documentation: [`../docs/webmcp/`](../docs/webmcp/README.md)
- Root project documentation: [`../README.md`](../README.md)

## Stack

- Next.js 16, React 19, TypeScript, Tailwind CSS
- Three.js, React Three Fiber, Drei
- Supabase Auth, PostgreSQL, and Storage
- Prisma 7
- Modal TRELLIS/Nano3D services
- Optional AWS S3 object storage
- Vercel

## WebMCP

DentalSculptor exposes 29 non-duplicated, page-scoped tools through the browser's
`document.modelContext.registerTool(...)` API. Google Chrome Labs'
`use-webmcp-tool` hook manages registration and unregisters tools when their React surface
unmounts.

The tools cover:

- app/authentication inspection and safe navigation;
- curated image selection and image-to-3D generation;
- viewer-aware workflow continuation;
- teaching-case selection and clinical edit presets;
- normalized target marking, preview, and reversible 3D variants;
- confirmed export and privacy-controlled publishing;
- inspection and reuse of public community models.

Browsers without WebMCP retain the conventional interface.

## Local setup

### Prerequisites

- Node.js 20 or later
- npm
- PostgreSQL (Supabase recommended)
- Supabase project for full authentication/storage flows
- Modal deployment for production 3D generation/editing

### Install

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open <http://localhost:3000>.

For interface-only local work, set both `UI_PREVIEW_MODE=true` and
`NEXT_PUBLIC_UI_PREVIEW_MODE=true`. Full generation, persistence, authentication, editing, and
publishing require the corresponding services in `.env.local`.

### Database

```powershell
npm run db:push
npm run db:seed
```

Use a Supabase transaction-pooler URL on port 6543 for Vercel. Use migrations rather than
destructive reset commands for production data.

## Environment

`.env.example` is the single public template. Important groups are:

- application URL and research invite;
- Supabase Auth/database/storage;
- Modal generation/edit/status endpoints and webhook secret;
- optional S3 and PostHog settings.

Never commit `.env`, `.env.local`, invite codes, service-role keys, webhook secrets, or judge
credentials.

## Verification

```powershell
npm run test:webmcp
npm run test:viewer
npm run test:case-workflows
npx tsc --noEmit
npm run lint
npm run build
```

To test WebMCP manually, open `/webmcp` in ChatGPT's in-app browser or Chrome 149+ with
`chrome://flags/#enable-webmcp-testing` enabled.

## Main routes

- `/` — public image-to-3D workbench
- `/webmcp` — live WebMCP diagnostics and judge entry point
- `/dashboard` — authenticated educator dashboard
- `/editor/[id]` — 3D case-authoring workspace
- `/community` — published teaching models
- `/research` — role-gated research dashboard
- `/xr/[id]` — immersive model preview

## Deployment

The Vercel project root is `dentalsculptor-app`. Production builds run:

```powershell
prisma generate
next build
```

Set production secrets in Vercel—not in repository files. Modal workers are deployed separately
from `../dentalsculptor-ml/`.

## License

Licensed under the repository's [MIT License](../LICENSE).
