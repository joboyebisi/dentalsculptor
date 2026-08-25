-- EditJob table for Nano3D revision tracking (Phase 3.6)

CREATE TYPE "EditJobStatus" AS ENUM ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');

CREATE TABLE "EditJob" (
    "id" TEXT NOT NULL,
    "projectId" TEXT NOT NULL,
    "ownerId" TEXT NOT NULL,
    "status" "EditJobStatus" NOT NULL DEFAULT 'QUEUED',
    "stage" TEXT NOT NULL DEFAULT 'queued',
    "progress" INTEGER NOT NULL DEFAULT 0,
    "operation" TEXT NOT NULL,
    "instruction" TEXT NOT NULL,
    "sourceModelUrl" TEXT NOT NULL,
    "resultModelUrl" TEXT,
    "resultFormat" TEXT,
    "provider" TEXT NOT NULL DEFAULT 'modal',
    "revisionNumber" INTEGER NOT NULL DEFAULT 1,
    "accepted" BOOLEAN,
    "camera" JSONB,
    "regionMarks" JSONB,
    "selectedPartIds" JSONB,
    "metadata" JSONB,
    "error" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "completedAt" TIMESTAMP(3),
    "acceptedAt" TIMESTAMP(3),
    "rejectedAt" TIMESTAMP(3),

    CONSTRAINT "EditJob_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "EditJob_projectId_idx" ON "EditJob"("projectId");
CREATE INDEX "EditJob_ownerId_idx" ON "EditJob"("ownerId");
CREATE INDEX "EditJob_status_idx" ON "EditJob"("status");
CREATE INDEX "EditJob_createdAt_idx" ON "EditJob"("createdAt");

ALTER TABLE "EditJob" ADD CONSTRAINT "EditJob_ownerId_fkey" FOREIGN KEY ("ownerId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "EditJob" ADD CONSTRAINT "EditJob_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "EditJob" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "EditJob" FROM anon, authenticated;
