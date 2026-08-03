import { prisma } from "@/lib/prisma";
import type { ResearchEventType, Prisma } from "@/generated/prisma/client";

export async function trackResearchEvent({
  userId,
  projectId,
  eventType,
  metadata,
  sessionId,
}: {
  userId: string;
  projectId?: string;
  eventType: ResearchEventType;
  metadata?: Record<string, unknown>;
  sessionId?: string;
}) {
  try {
    await prisma.researchEvent.create({
      data: {
        userId,
        projectId,
        eventType,
        metadata: (metadata ?? {}) as Prisma.InputJsonValue,
        sessionId,
      },
    });
  } catch (error) {
    console.error("[ResearchEvent]", eventType, error);
  }
}

export async function getResearchMetrics(userId?: string) {
  const where = userId ? { userId } : {};

  const [
    totalEvents,
    projectsCreated,
    modelsGenerated,
    aiAccepted,
    aiRejected,
    annotations,
    published,
  ] = await Promise.all([
    prisma.researchEvent.count({ where }),
    prisma.researchEvent.count({
      where: { ...where, eventType: "PROJECT_CREATED" },
    }),
    prisma.researchEvent.count({
      where: { ...where, eventType: "MODEL_GENERATED" },
    }),
    prisma.researchEvent.count({
      where: { ...where, eventType: "AI_SUGGESTION_ACCEPTED" },
    }),
    prisma.researchEvent.count({
      where: { ...where, eventType: "AI_SUGGESTION_REJECTED" },
    }),
    prisma.researchEvent.count({
      where: { ...where, eventType: "ANNOTATION_CREATED" },
    }),
    prisma.researchEvent.count({
      where: { ...where, eventType: "PROJECT_PUBLISHED" },
    }),
  ]);

  const aiTotal = aiAccepted + aiRejected;
  const ownershipScore = Math.min(
    100,
    Math.round(
      (annotations * 5 + published * 10 + (aiTotal > 0 ? (aiRejected / aiTotal) * 30 : 15)) /
        Math.max(1, projectsCreated)
    )
  );
  const agencyScore = Math.min(100, Math.round(annotations * 8 + published * 12));
  const personalisationScore = Math.min(100, Math.round(modelsGenerated * 5 + annotations * 6));
  const confidenceScore = Math.min(
    100,
    Math.round(published * 15 + (aiTotal > 0 ? (aiAccepted / aiTotal) * 40 : 20))
  );

  return {
    totalEvents,
    projectsCreated,
    modelsGenerated,
    aiAccepted,
    aiRejected,
    aiAcceptRate: aiTotal > 0 ? Math.round((aiAccepted / aiTotal) * 100) : 0,
    annotations,
    published,
    ownershipScore,
    agencyScore,
    personalisationScore,
    confidenceScore,
  };
}

export async function getEventTimeline(limit = 50) {
  return prisma.researchEvent.findMany({
    take: limit,
    orderBy: { timestamp: "desc" },
    include: {
      user: { select: { name: true, email: true, role: true } },
      project: { select: { title: true } },
    },
  });
}
