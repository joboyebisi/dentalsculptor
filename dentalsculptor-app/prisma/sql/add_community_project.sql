-- CommunityProject gallery row (created on publish). Run if publish/like 404 on missing table.
-- Safe to re-run.

CREATE TABLE IF NOT EXISTS "CommunityProject" (
  "id"              TEXT NOT NULL,
  "projectId"       TEXT NOT NULL,
  "likes"           INTEGER NOT NULL DEFAULT 0,
  "downloads"       INTEGER NOT NULL DEFAULT 0,
  "studentsReached" INTEGER NOT NULL DEFAULT 0,
  "published"       BOOLEAN NOT NULL DEFAULT false,
  "featured"        BOOLEAN NOT NULL DEFAULT false,
  "rating"          DOUBLE PRECISION NOT NULL DEFAULT 0,
  "ratingCount"     INTEGER NOT NULL DEFAULT 0,
  "publishedAt"     TIMESTAMP(3),
  "createdAt"       TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt"       TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT "CommunityProject_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "CommunityProject_projectId_key"
  ON "CommunityProject"("projectId");

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'CommunityProject_projectId_fkey'
  ) THEN
    ALTER TABLE "CommunityProject"
      ADD CONSTRAINT "CommunityProject_projectId_fkey"
      FOREIGN KEY ("projectId") REFERENCES "Project"("id")
      ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END $$;

ALTER TABLE "CommunityProject" ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "CommunityProject_select_published" ON "CommunityProject";
CREATE POLICY "CommunityProject_select_published" ON "CommunityProject"
  FOR SELECT USING ("published" = true);

DROP POLICY IF EXISTS "CommunityProject_insert_owner" ON "CommunityProject";
CREATE POLICY "CommunityProject_insert_owner" ON "CommunityProject"
  FOR INSERT WITH CHECK (
    "projectId" IN (
      SELECT p."id" FROM "Project" p
      JOIN "User" u ON u."id" = p."ownerId"
      WHERE u."supabaseId" = auth.uid()::text
    )
  );

DROP POLICY IF EXISTS "CommunityProject_update_owner" ON "CommunityProject";
CREATE POLICY "CommunityProject_update_owner" ON "CommunityProject"
  FOR UPDATE USING (
    "projectId" IN (
      SELECT p."id" FROM "Project" p
      JOIN "User" u ON u."id" = p."ownerId"
      WHERE u."supabaseId" = auth.uid()::text
    )
  );
