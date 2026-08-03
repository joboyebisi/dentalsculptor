import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { trackResearchEvent } from "@/lib/research-events";

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ projectId: string }> }
) {
  const { projectId } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const source = await prisma.project.findUnique({
    where: { id: projectId },
    include: {
      dentalModel: true,
      annotations: true,
      learningObjectives: true,
      assessments: true,
    },
  });

  if (!source) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const cloned = await prisma.project.create({
    data: {
      ownerId: user.id,
      title: `${source.title} (Clone)`,
      description: source.description,
      status: "READY",
      instructions: source.instructions,
      hints: source.hints,
      feedback: source.feedback,
      category: source.category,
      dentalModel: source.dentalModel
        ? {
            create: {
              meshData: source.dentalModel.meshData ?? undefined,
              sourceImageUrl: source.dentalModel.sourceImageUrl,
              processingStage: "complete",
            },
          }
        : undefined,
      annotations: {
        create: source.annotations.map((a) => ({
          creatorId: user.id,
          text: a.text,
          position: a.position as object,
          type: a.type,
          color: a.color,
        })),
      },
      learningObjectives: {
        create: source.learningObjectives.map((o) => ({
          title: o.title,
          description: o.description,
          order: o.order,
        })),
      },
      assessments: {
        create: source.assessments.map((a) => ({
          question: a.question,
          answer: a.answer,
          type: a.type,
          order: a.order,
        })),
      },
    },
  });

  const community = await prisma.communityProject.findUnique({ where: { projectId } });
  if (community) {
    await prisma.communityProject.update({
      where: { projectId },
      data: { downloads: { increment: 1 } },
    });
  }

  await trackResearchEvent({
    userId: user.id,
    projectId: cloned.id,
    eventType: "PROJECT_CLONED",
    metadata: { sourceProjectId: projectId },
  });

  return NextResponse.redirect(new URL(`/editor/${cloned.id}`, process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"));
}
