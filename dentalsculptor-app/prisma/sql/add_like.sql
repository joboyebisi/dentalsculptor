-- Like table for community project hearts (one per user per project).
-- Run in Supabase SQL Editor after User + Project exist.
-- Safe to re-run: uses IF NOT EXISTS / guarded policies.

CREATE TABLE IF NOT EXISTS "Like" (
  "id"        TEXT NOT NULL,
  "projectId" TEXT NOT NULL,
  "userId"    TEXT NOT NULL,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT "Like_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "Like_projectId_userId_key"
  ON "Like"("projectId", "userId");

CREATE INDEX IF NOT EXISTS "Like_userId_idx"
  ON "Like"("userId");

CREATE INDEX IF NOT EXISTS "Like_projectId_idx"
  ON "Like"("projectId");

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'Like_userId_fkey'
  ) THEN
    ALTER TABLE "Like"
      ADD CONSTRAINT "Like_userId_fkey"
      FOREIGN KEY ("userId") REFERENCES "User"("id")
      ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END $$;

ALTER TABLE "Like" ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Like_select_all" ON "Like";
CREATE POLICY "Like_select_all" ON "Like"
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "Like_insert_own" ON "Like";
CREATE POLICY "Like_insert_own" ON "Like"
  FOR INSERT WITH CHECK (
    "userId" IN (
      SELECT "id" FROM "User"
      WHERE "supabaseId" = auth.uid()::text
    )
  );

DROP POLICY IF EXISTS "Like_delete_own" ON "Like";
CREATE POLICY "Like_delete_own" ON "Like"
  FOR DELETE USING (
    "userId" IN (
      SELECT "id" FROM "User"
      WHERE "supabaseId" = auth.uid()::text
    )
  );
