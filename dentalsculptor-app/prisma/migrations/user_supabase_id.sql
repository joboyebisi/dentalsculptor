-- Migrate User.clerkId → User.supabaseId (one-time)
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "supabaseId" TEXT;
UPDATE "User" SET "supabaseId" = "clerkId" WHERE "supabaseId" IS NULL AND "clerkId" IS NOT NULL;
UPDATE "User" SET "supabaseId" = "id" WHERE "supabaseId" IS NULL;
ALTER TABLE "User" DROP COLUMN IF EXISTS "clerkId";
ALTER TABLE "User" ALTER COLUMN "supabaseId" SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS "User_supabaseId_key" ON "User"("supabaseId");
