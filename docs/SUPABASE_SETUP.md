# Supabase Setup — Database + Storage

One Supabase project powers **PostgreSQL** (Prisma) and **file storage** (uploaded images, future GLB/thumbnails).

---

## 1. Create project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard)
2. **New project** → choose org, name (`dentalsculptor`), password, region
3. Save the **database password** — you need it for `DATABASE_URL`

---

## 2. Copy API credentials

**Settings → API**

| Variable | Where |
|----------|--------|
| `NEXT_PUBLIC_SUPABASE_URL` | Project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `anon` `public` key |
| `SUPABASE_SERVICE_ROLE_KEY` | `service_role` key (**secret — server only**) |

Add these to `dentalsculptor-app/.env`.

---

## 3. Database connection string

**Settings → Database → Connection string → URI**

For **local development** (`npm run db:push`):

```
DATABASE_URL=postgresql://postgres:[YOUR_DB_PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```

For **Vercel production** (use **Transaction pooler**, port **6543**):

```
DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[YOUR_DB_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true
```

Then run:

```bash
cd dentalsculptor-app
npm run db:push
```

---

## 4. Create storage bucket

**Option A — SQL (recommended):**

1. Supabase → **SQL Editor** → **New query**
2. Paste contents of [`dentalsculptor-app/supabase/setup.sql`](../dentalsculptor-app/supabase/setup.sql)
3. Click **Run**

**Option B — Dashboard:**

1. **Storage** → **New bucket**
2. Name: `dentalsculptor-assets`
3. Enable **Public bucket** for MVP

Set in `.env`:

```
SUPABASE_STORAGE_BUCKET=dentalsculptor-assets
```

---

## 5. App database tables (Prisma — not manual SQL)

Tables like `User`, `Project`, `DentalModel`, `ResearchEvent` are defined in `prisma/schema.prisma`.

After `DATABASE_URL` is correct in `.env`:

```bash
cd dentalsculptor-app
npm run db:push
```

This creates all app tables in your Supabase Postgres. **You do not need to write CREATE TABLE SQL by hand.**

Verify in Supabase → **Table Editor** — you should see `User`, `Project`, etc.

---

## 6. Storage policies

If the bucket is **public**, uploads still use the **service role** from the Next.js API — no extra policy needed for server uploads.

Optional RLS for direct client uploads later:

```sql
-- Example: authenticated users upload to their own folder
-- (not required for current server-side upload flow)
```

---

## 7. Row Level Security (RLS) — required for production

Supabase **Security Advisor** flags any `public` table without RLS. Our app tables are created by Prisma but are visible to PostgREST unless locked down.

**Architecture:** The browser never queries these tables via Supabase Data API. All reads/writes go through **Next.js API routes + Prisma** (`DATABASE_URL`). Supabase client in the browser is used for **Auth** (and optionally Storage) only.

**Fix:** Enable RLS on every app table with **no permissive policies** for `anon` / `authenticated`. That blocks public REST access; Prisma (postgres superuser) is unaffected.

### Apply once per environment

**Option A — Supabase SQL Editor (production)**

1. Dashboard → **SQL** → New query  
2. Paste contents of `dentalsculptor-app/prisma/sql/enable_rls.sql`  
3. Run  
4. **Advisors → Security** → **Rerun linter** — 17 RLS errors should clear  

**Option B — CLI (local or CI with `DATABASE_URL` set)**

```bash
cd dentalsculptor-app
npm run db:rls
```

### If you add direct Supabase table access later

Add explicit policies, e.g. users read their own `User` row where `"supabaseId" = auth.uid()::text`. Until then, keep server-only access.

See [Supabase RLS docs](https://supabase.com/docs/guides/database/postgres/row-level-security).

---

## 8. Verify upload

1. Set all Supabase vars in `.env`
2. Set `UI_PREVIEW_MODE=false`, configure Supabase Auth
3. Sign in → create project with image
4. Check **Storage → dentalsculptor-assets → users/** in Supabase dashboard

---

## 9. AWS later

When you add AWS S3, you can switch the backend in `src/lib/storage.ts` without changing API routes. Supabase Storage remains the default until then.

---

See also: [ENV.md](./ENV.md) · [DEPLOYMENT.md](./DEPLOYMENT.md)
