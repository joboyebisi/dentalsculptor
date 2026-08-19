CREATE TYPE "GenerationJobStatus" AS ENUM (
  'QUEUED',
  'RUNNING',
  'COMPLETED',
  'FAILED',
  'CANCELLED'
);

ALTER TABLE "DentalModel" ADD COLUMN "generated3DKey" TEXT;

CREATE TABLE "GenerationJob" (
  "id" TEXT NOT NULL,
  "ownerId" TEXT,
  "projectId" TEXT,
  "status" "GenerationJobStatus" NOT NULL DEFAULT 'QUEUED',
  "stage" TEXT NOT NULL DEFAULT 'queued',
  "progress" INTEGER NOT NULL DEFAULT 0,
  "quality" TEXT NOT NULL DEFAULT 'standard',
  "provider" TEXT NOT NULL DEFAULT 'modal',
  "resultKey" TEXT,
  "format" TEXT,
  "seed" INTEGER,
  "pipelineType" TEXT,
  "timings" JSONB,
  "metrics" JSONB,
  "error" TEXT,
  "jobTokenHash" TEXT,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL,
  "startedAt" TIMESTAMP(3),
  "completedAt" TIMESTAMP(3),

  CONSTRAINT "GenerationJob_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "GenerationJob_ownerId_idx" ON "GenerationJob"("ownerId");
CREATE INDEX "GenerationJob_projectId_idx" ON "GenerationJob"("projectId");
CREATE INDEX "GenerationJob_status_idx" ON "GenerationJob"("status");
CREATE INDEX "GenerationJob_createdAt_idx" ON "GenerationJob"("createdAt");

ALTER TABLE "GenerationJob"
  ADD CONSTRAINT "GenerationJob_ownerId_fkey"
  FOREIGN KEY ("ownerId") REFERENCES "User"("id")
  ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE "GenerationJob"
  ADD CONSTRAINT "GenerationJob_projectId_fkey"
  FOREIGN KEY ("projectId") REFERENCES "Project"("id")
  ON DELETE SET NULL ON UPDATE CASCADE;
