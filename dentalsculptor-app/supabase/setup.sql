-- DentalSculptor — Supabase setup SQL
-- Run in: Supabase Dashboard → SQL Editor → New query → Run
--
-- NOTE: App database tables (User, Project, etc.) are created by Prisma, NOT this file.
-- After setting DATABASE_URL in .env, run:  npm run db:push

-- =============================================================================
-- 1. Storage bucket (uploaded images, future GLB/thumbnails)
-- =============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'dentalsculptor-assets',
  'dentalsculptor-assets',
  true,
  52428800,  -- 50 MB max per file
  ARRAY['image/jpeg', 'image/png', 'image/webp', 'model/gltf-binary', 'model/stl', 'application/octet-stream']
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- =============================================================================
-- 2. Storage policies (public read for MVP; uploads via service role on server)
-- =============================================================================

-- Anyone can read files in the public bucket (for displaying images/GLB URLs)
DROP POLICY IF EXISTS "Public read dentalsculptor assets" ON storage.objects;
CREATE POLICY "Public read dentalsculptor assets"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'dentalsculptor-assets');

-- Service role uploads bypass RLS — no INSERT policy required for server-side API.
-- If you later add direct browser uploads with anon key, add authenticated INSERT policies.

-- =============================================================================
-- Done. Next steps:
--   1. Fill Supabase keys in dentalsculptor-app/.env
--   2. cd dentalsculptor-app && npm run db:push
-- =============================================================================
