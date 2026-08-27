import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { trackResearchEvent } from "@/lib/research-events";

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  const { id } = await params;
  const project = await prisma.project.findFirst({
    where: { id, ownerId: user.id },
    include: { dentalModel: true },
  });
  if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });
  if (!project.dentalModel?.generated3DUrl && !project.dentalModel?.generated3DKey) {
    return NextResponse.json({ error: "Generate a 3D model before publishing." }, { status: 400 });
  }

  const publishedAt = new Date();
  await prisma.$transaction([
    prisma.project.update({
      where: { id },
      data: {
        status: "PUBLISHED",
        publishingLevel: "COMMUNITY",
        thumbnailUrl: project.thumbnailUrl ?? project.dentalModel.thumbnailUrl,
      },
    }),
    prisma.communityProject.upsert({
      where: { projectId: id },
      create: { projectId: id, published: true, publishedAt },
      update: { published: true, publishedAt },
    }),
  ]);

  await trackResearchEvent({
    userId: user.id,
    projectId: id,
    eventType: "PROJECT_PUBLISHED",
    metadata: { destination: "community" },
  });

  return NextResponse.json({ published: true, communityUrl: "/community" });
}
