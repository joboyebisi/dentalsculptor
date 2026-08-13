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
                 →  fal.ai (3D generation, server-side)
                 →  AWS S3 (optional — add later)
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
| `FAL_KEY` | [fal.ai Dashboard](https://fal.ai/dashboard/keys) | **Server-only** — powers Hunyuan 3D generation |
| `NEXT_PUBLIC_APP_URL` | — | Your Vercel URL, e.g. `https://dentalsculptor.vercel.app` |

#### Optional (can add later)

| Variable | Purpose |
|----------|---------|
| `AWS_*` | S3/CDN — deferred; Supabase Storage is used instead |
| `NEXT_PUBLIC_POSTHOG_KEY` / `NEXT_PUBLIC_POSTHOG_HOST` | Analytics |
| `ML_MESH_PROVIDER` | `fal` (default) or `custom` later |

### 3. Clerk production URLs

In Clerk Dashboard → **Configure → Paths / Domains**:

- Add your Vercel domain (e.g. `dentalsculptor.vercel.app`)
- Allowed redirect URLs: `https://your-domain/consent`

### 4. Supabase database

After first deploy, run migrations from your machine (or Vercel CLI):

```bash
cd dentalsculptor-app
DATABASE_URL="your-pooler-url" npx prisma db push
# or for production migrations:
DATABASE_URL="your-pooler-url" npx prisma migrate deploy
```

### 5. Deploy

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

## 3D generation (Hunyuan 3D via fal.ai)

Model: `fal-ai/hunyuan-3d/v3.1/rapid/image-to-3d`

Flow:
1. User uploads image in editor Source panel
2. Client POSTs image to `/api/generate/mesh`
3. Server uploads image to fal storage, calls Hunyuan 3D
4. Server returns GLB/OBJ URL to client
5. Viewer loads model via `modelUrl`

Requires `FAL_KEY` in server environment.

Without `FAL_KEY`, the app falls back to procedural mock mesh (dev only).

---

## Vercel checklist

- [ ] Root directory = `dentalsculptor-app`
- [ ] `UI_PREVIEW_MODE=false`
- [ ] Clerk keys + production domain configured
- [ ] `DATABASE_URL` uses Supabase pooler (port 6543)
- [ ] `FAL_KEY` set (server-only)
- [ ] `NEXT_PUBLIC_APP_URL` matches Vercel domain
- [ ] `prisma db push` or `migrate deploy` run against production DB
- [ ] Test sign-in → consent → dashboard → editor → Generate Model

---

## Cost estimate (pilot)

| Service | Typical cost |
|---------|--------------|
| Vercel Hobby | Free |
| Supabase Free | Free (500 MB DB) |
| Clerk Free | Free (~10k MAU) |
| fal.ai Hunyuan 3D | ~$0.02–0.10 per generation |
| AWS S3 / R2 | Free tier or ~$1–5/mo |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on Prisma | Ensure `postinstall` runs `prisma generate`; check `DATABASE_URL` at build time if needed |
| Clerk redirect loop | Match `NEXT_PUBLIC_APP_URL` and Clerk allowed URLs |
| DB connection timeout on Vercel | Use Supabase **pooler** URL, not direct port 5432 |
| Generate Model fails | Check `FAL_KEY` in Vercel env; view Vercel function logs |
| 404 on all routes | Wrong root directory — must be `dentalsculptor-app` |

---

See also: [PROJECT_WALKTHROUGH.md](./PROJECT_WALKTHROUGH.md) · [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)
