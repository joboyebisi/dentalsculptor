# Environment Variables Guide

## `.env` vs `.env.example`

| File | Purpose | Commit to Git? |
|------|---------|----------------|
| **`.env.example`** | Template with placeholder values and comments | ✅ Yes |
| **`.env`** | Your **real secrets** — read by Next.js at runtime | ❌ Never |

**Which one to use:** Edit **`.env`** only. Copy once from the template:

```bash
cd dentalsculptor-app
cp .env.example .env
```

---

## Full Supabase credentials (database + storage)

All from **one** Supabase project dashboard:

| Variable | Required | Where in Supabase |
|----------|----------|-------------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Settings → API → Project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Settings → API → anon public |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Settings → API → service_role (**server only**) |
| `SUPABASE_STORAGE_BUCKET` | Yes | Storage → bucket name you create |
| `DATABASE_URL` | Yes | Settings → Database → URI |

Setup walkthrough: [SUPABASE_SETUP.md](./SUPABASE_SETUP.md)

---

## Minimum variables for live demo

Upload image → store in Supabase → generate 3D → login → edit:

| Variable | Required? |
|----------|-----------|
| `UI_PREVIEW_MODE` | `false` |
| `NEXT_PUBLIC_UI_PREVIEW_MODE` | `false` |
| Clerk keys (6 vars) | Yes |
| Supabase (5 vars above) | Yes |
| `FAL_KEY` | Yes (3D generation) |
| `NEXT_PUBLIC_APP_URL` | Yes |

### Generation speed (fal.ai)

Hunyuan 3D with **PBR textures** (current default) typically takes **30–90 seconds** on fal’s queue — that is expected for image→3D, not a bug in the app.

Optional server vars in `.env`:

| Variable | Effect |
|----------|--------|
| `FAL_ENABLE_GEOMETRY=true` | Geometry-only white **GLB** — faster previews, no textures |
| `FAL_ENABLE_PBR=false` | Skip PBR material pass — slightly faster, lower quality |

The app also resizes large photos client-side before upload (max 1536px) to reduce upload + queue time.

Check server logs for timings: `[fal] mesh generation complete upload=…ms inference=…ms`.

**AWS:** Not needed — Supabase Storage handles uploads.

**PostHog:** Optional.

---

## Vercel

Add the same variables in **Project → Settings → Environment Variables**.

Use the **pooler** `DATABASE_URL` (port 6543) for production.

See [DEPLOYMENT.md](./DEPLOYMENT.md).
