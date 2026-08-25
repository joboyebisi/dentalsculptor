import { prisma } from "@/lib/prisma";
import type { EditJobStatus } from "@/generated/prisma/client";

export interface CreateEditJobInput {
  id: string;
  projectId: string;
  ownerId: string;
  operation: string;
  instruction: string;
  sourceModelUrl: string;
  camera?: unknown;
  regionMarks?: unknown;
  selectedPartIds?: unknown;
  provider?: string;
}

export async function nextEditRevisionNumber(projectId: string): Promise<number> {
  const last = await prisma.editJob.findFirst({
    where: { projectId },
    orderBy: { revisionNumber: "desc" },
    select: { revisionNumber: true },
  });
  return (last?.revisionNumber ?? 0) + 1;
}

export async function createEditJobRecord(input: CreateEditJobInput) {
  const revisionNumber = await nextEditRevisionNumber(input.projectId);
  return prisma.editJob.create({
    data: {
      id: input.id,
      projectId: input.projectId,
      ownerId: input.ownerId,
      operation: input.operation,
      instruction: input.instruction,
      sourceModelUrl: input.sourceModelUrl,
      revisionNumber,
      provider: input.provider ?? "modal",
      camera: input.camera ?? undefined,
      regionMarks: input.regionMarks ?? undefined,
      selectedPartIds: input.selectedPartIds ?? undefined,
      status: "QUEUED",
      stage: "queued",
    },
  });
}

export async function updateEditJobProgress(
  jobId: string,
  data: {
    status?: EditJobStatus;
    stage?: string;
    progress?: number;
    resultModelUrl?: string;
    resultFormat?: string;
    error?: string;
    metadata?: unknown;
  }
) {
  const completed = data.status === "COMPLETED" || data.status === "FAILED";
  return prisma.editJob.update({
    where: { id: jobId },
    data: {
      ...data,
      metadata: data.metadata ?? undefined,
      completedAt: completed ? new Date() : undefined,
    },
  });
}

export async function acceptEditJob(jobId: string, ownerId: string) {
  const job = await prisma.editJob.findFirst({
    where: { id: jobId, ownerId, status: "COMPLETED", accepted: null },
  });
  if (!job?.resultModelUrl) {
    throw new Error("Edit job not found or not ready to accept.");
  }

  await prisma.$transaction([
    prisma.editJob.update({
      where: { id: jobId },
      data: { accepted: true, acceptedAt: new Date() },
    }),
    prisma.dentalModel.updateMany({
      where: { projectId: job.projectId },
      data: {
        generated3DUrl: job.resultModelUrl,
        processingStage: JSON.stringify({
          format: job.resultFormat ?? "glb",
          source: "nano3d",
          revisionNumber: job.revisionNumber,
          editJobId: job.id,
          acceptedAt: new Date().toISOString(),
        }),
      },
    }),
  ]);

  return job;
}

export async function rejectEditJob(jobId: string, ownerId: string) {
  const job = await prisma.editJob.findFirst({
    where: { id: jobId, ownerId, status: "COMPLETED", accepted: null },
  });
  if (!job) {
    throw new Error("Edit job not found or already resolved.");
  }

  await prisma.$transaction([
    prisma.editJob.update({
      where: { id: jobId },
      data: { accepted: false, rejectedAt: new Date() },
    }),
    prisma.dentalModel.updateMany({
      where: { projectId: job.projectId },
      data: {
        generated3DUrl: job.sourceModelUrl,
        processingStage: JSON.stringify({
          format: "glb",
          source: "nano3d-revert",
          revertedEditJobId: job.id,
          revertedAt: new Date().toISOString(),
        }),
      },
    }),
  ]);

  return job;
}
