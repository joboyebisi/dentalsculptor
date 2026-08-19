# DentalSculptor — Deployment Guide

**Last updated:** August 2026

---

## GitHub Pages vs Vercel — use Vercel

| Requirement | GitHub Pages | Vercel |
|-------------|--------------|--------|
| Next.js App Router + API routes | ❌ Static only | ✅ |
| Clerk authentication | ❌ Needs server | ✅ |
| Prisma / Supabase (server DB) | ❌ | ✅ |
| `FAL_KEY` (secret, server-only) | ❌ Would leak if client-side | ✅ Env vars |
| File uploads / S3 | ❌ | ✅ |
| WebXR / dynamic editor | ❌ | ✅ |
| Free tier for research pilot | ✅ | ✅ Hobby tier |

**Conclusion:** Do **not** use GitHub Pages. GitHub hosts your **source code** at [github.com/joboyebisi/dentalsculptor](https://github.com/joboyebisi/dentalsculptor). **Vercel** builds and runs the live app.

GitHub Pages only serves static HTML — it cannot run `/api/*`, Clerk, Prisma, or fal.ai proxy calls.

---

## Recommended setup

```
GitHub (code)  →  Vercel (build + host)  →  Supabase (Postgres + Storage)
                 →  Clerk (auth)
                 →  Modal (TRELLIS generation + editing workers)
                 →  AWS S3 (private large assets and job I/O)
                 →  fal.ai (optional fallback only)
```

---

## Vercel deployment steps

### 1. Connect repository

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import `joboyebisi/dentalsculptor`
3. **Root Directory:** set to `dentalsculptor-app` (important — app is not at repo root)
4. **Framework Preset:** Next.js
5. **Build Command:** `prisma generate && next build` (default from `package.json`)
6. **Install Command:** `npm install`

### 2. Environment variables (Vercel dashboard)

Add these under **Project → Settings → Environment Variables** for **Production** and **Preview**:

#### Required for live app

| Variable | Where to get it | Notes |
|----------|-----------------|-------|
| `UI_PREVIEW_MODE` | Set manually | `false` in production |
| `NEXT_PUBLIC_UI_PREVIEW_MODE` | Set manually | `false` in production |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | [Clerk Dashboard](https://dashboard.clerk.com) → API Keys | Starts with `pk_test_` or `pk_live_` |
| `CLERK_SECRET_KEY` | Clerk Dashboard | Starts with `sk_test_` or `sk_live_` — **never expose client-side** |
| `NEXT_PUBLIC_CLERK_SIGN_IN_URL` | — | `/sign-in` |
| `NEXT_PUBLIC_CLERK_SIGN_UP_URL` | — | `/sign-up` |
| `NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL` | — | `/consent` |
| `NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL` | — | `/consent` |
| `DATABASE_URL` | [Supabase](https://supabase.com) → Settings → Database | Use **Transaction pooler** URL (port **6543**) for serverless |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase → Settings → API | Project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase → Settings → API | anon public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API | service_role — **server only** |
| `SUPABASE_STORAGE_BUCKET` | Supabase → Storage | e.g. `dentalsculptor-assets` — see [SUPABASE_SETUP.md](./SUPABASE_SETUP.md) |
| `ML_MESH_PROVIDER` | Set manually | `modal` |
| `MODAL_GENERATE_URL` | Modal deployment output | TRELLIS sync endpoint (legacy/fallback) |
| `MODAL_GENERATE_ASYNC_URL` | Modal deployment output | Async job create (`generate-job`) |
| `MODAL_FINALIZE_ASYNC_URL` | Modal deployment output | Two-phase GLB extraction (`finalize-job`) |
| `MODAL_ASYNC_S3_ENABLED` | Set manually | `true` when async S3 path is live |
| `MODAL_EDIT_URL` | Modal deployment output | Nano3D endpoint |
| `MODAL_JOB_STATUS_URL` | Modal deployment output | Async job polling |
| `MODAL_WEBHOOK_SECRET` | Generate securely | Must match Modal `dentalsculptor-webhook` secret |
| `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` | Modal account settings | Server-only deployment/config credentials |
| `RESEARCH_GENERATION_ACCESS_CODE` | Generate securely | Educator invite code; share as `?invite=CODE` on landing |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | AWS IAM | Least-privilege S3 credentials; server-only |
| `AWS_REGION` / `AWS_S3_BUCKET` | AWS S3 | Prefer `eu-west-1` and a private bucket |
| `STORAGE_BACKEND` | Set manually | `s3` after the S3 backend is wired |
| `NEXT_PUBLIC_APP_URL` | — | Your Vercel URL, e.g. `https://dentalsculptor.vercel.app` |

#### Optional (can add later)

| Variable | Purpose |
|----------|---------|
| `FAL_KEY` / `ML_ALLOW_FAL_FALLBACK` | Optional Hunyuan fallback |
| `NEXT_PUBLIC_POSTHOG_KEY` / `NEXT_PUBLIC_POSTHOG_HOST` | Analytics |
| `NEXT_PUBLIC_ASSETS_CDN_URL` | Optional CloudFront URL in front of S3 |

### 3. Clerk production URLs

In Clerk Dashboard → **Configure → Paths / Domains**:

- Add your Vercel domain (e.g. `dentalsculptor.vercel.app`)
- Allowed redirect URLs: `https://your-domain/consent`

### 4. Supabase database

**You do not need a separate “Vercel database”.** Vercel runs the same Next.js app against the same Supabase Postgres project. Copy `DATABASE_URL` into Vercel — for Production/Preview use the **Transaction pooler** URI (port **6543**, includes `?pgbouncer=true`). Keep port **5432** (session pooler or direct) for local dev and running migrations from your laptop.

Migrations were already applied to your Supabase project (`GenerationJob` table exists). After deploy, no migration step is required unless the schema changes again:

```bash
cd dentalsculptor-app
npx prisma migrate deploy
```

### 5. Clerk (development instance on Vercel)

You do **not** need a custom Clerk domain for the research pilot. Your development instance (`aware-treefrog-86.clerk.accounts.dev`) works with any Vercel URL.

In [Clerk Dashboard](https://dashboard.clerk.com) → **Configure → Domains** (or **Paths**):

1. Add your Vercel deployment URL, e.g. `https://dentalsculptor.vercel.app`
2. Add preview URLs if needed: `https://*.vercel.app` (or each preview URL Clerk accepts)

Use the **same** `pk_test_…` and `sk_test_…` keys in Vercel as in local `.env`. No `pk_live_` until you switch Clerk to production.

### 6. Hybrid storage (Supabase + S3)

| Data | Where |
|------|--------|
| Users, projects, jobs, research events | Supabase Postgres (`DATABASE_URL`) |
| Source images on project create | S3 when `STORAGE_BACKEND=s3` |
| Generated GLB + job outputs | S3 (`jobs/…`, signed URLs) |
| Thumbnails (optional) | Supabase Storage bucket |

Set `STORAGE_BACKEND=s3` plus `AWS_*` on Vercel. Postgres stays on Supabase — they are complementary, not either/or.

### 7. Deploy

Push to `main` on GitHub — Vercel auto-deploys.

---

## Local development with real credentials

1. Copy `.env.example` → `.env` in `dentalsculptor-app/`
2. Fill in Clerk, Supabase, and `FAL_KEY`
3. Set `UI_PREVIEW_MODE=false` to test full auth + DB flow
4. Run:

```bash
cd dentalsculptor-app
npm install
npm run db:push
npm run dev
```

---

## Security — credentials

- **Never commit** `.env` — it is gitignored
- **Never paste** `CLERK_SECRET_KEY`, `FAL_KEY`, or database passwords in GitHub issues, chat, or screenshots
- **Never call fal.ai from the browser** — always via `/api/generate/mesh` (server route)
- Add secrets only in:
  - Local `.env` (your machine)
  - Vercel **Environment Variables** dashboard

---

## 3D generation (TRELLIS.2 via Modal)

Model: `microsoft/TRELLIS.2-4B`

Flow:
1. User uploads image in editor Source panel
2. Client POSTs image to `/api/generate/mesh`
3. Vercel validates Clerk or research access and submits an authenticated Modal job
4. Modal preprocesses, generates TRELLIS SLat/mesh and extracts the GLB
5. Production target: Modal writes the GLB directly to private S3 and returns an object key
6. Vercel stores job/model metadata in Supabase Postgres
7. Browser receives a short-lived signed S3 URL for the viewer

Do not keep the current synchronous base64 response for production: cold
1024-cascade jobs can exceed several minutes and GLBs can exceed practical
serverless response/memory limits. Use an asynchronous job record and direct
Modal-to-S3 upload before public deployment.

---

## Vercel checklist

- [ ] Root directory = `dentalsculptor-app`
- [ ] `UI_PREVIEW_MODE=false`
- [ ] Clerk keys + production domain configured
- [ ] `DATABASE_URL` uses Supabase pooler (port 6543)
- [ ] Modal URLs and matching webhook secret configured
- [ ] Invite access code, rate limit and spend cap configured
- [ ] Private S3 bucket, IAM policy, CORS and lifecycle rules configured
- [ ] Modal writes large outputs directly to S3; no base64 GLB through Vercel
- [ ] Async generation/edit job records survive browser navigation and Vercel timeouts
- [ ] `NEXT_PUBLIC_APP_URL` matches Vercel domain
- [ ] `prisma db push` or `migrate deploy` run against production DB
- [ ] Test sign-in → consent → dashboard → editor → Generate Model

---

## Cost estimate (pilot)

| Service | Typical cost |
|---------|--------------|
| Vercel | Pro recommended for the pilot until ML routes are fully asynchronous |
| Supabase Free | Free (500 MB DB) |
| Clerk Free | Free (~10k MAU) |
| Modal TRELLIS | Usage-based GPU cost; warm capacity trades idle cost for lower latency |
| AWS S3 / R2 | Free tier or ~$1–5/mo |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on Prisma | Ensure `postinstall` runs `prisma generate`; check `DATABASE_URL` at build time if needed |
| Clerk redirect loop | Match `NEXT_PUBLIC_APP_URL` and Clerk allowed URLs |
| DB connection timeout on Vercel | Use Supabase **pooler** URL, not direct port 5432 |
| Generate Model fails | Check Modal URLs/webhook secret, then inspect Vercel and Modal logs using the trace ID |
| 404 on all routes | Wrong root directory — must be `dentalsculptor-app` |

---

See also: [PROJECT_WALKTHROUGH.md](./PROJECT_WALKTHROUGH.md) · [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)
