import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { getS3AssetUrl } from "@/lib/storage";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const project = await prisma.project.findFirst({
    where: { id, ownerId: user.id },
    include: {
      dentalModel: true,
      annotations: { orderBy: { createdAt: "desc" } },
      learningObjectives: { orderBy: { order: "asc" } },
      assessments: { orderBy: { order: "asc" } },
      communityProject: true,
      versions: {
        where: { label: "case-recipe" },
        orderBy: { version: "desc" },
        take: 1,
      },
    },
  });

  if (!project) return NextResponse.json({ error: "Not found" }, { status: 404 });

  if (project.dentalModel?.generated3DKey) {
    project.dentalModel.generated3DUrl = await getS3AssetUrl(
      project.dentalModel.generated3DKey
    );
  }

  return NextResponse.json({ project });
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();
  const project = await prisma.project.update({
    where: { id, ownerId: user.id },
    data: {
      title: body.title,
      description: body.description,
      instructions: body.instructions,
      hints: body.hints,
      feedback: body.feedback,
      status: body.status,
      publishingLevel: body.publishingLevel,
      category: body.category,
    },
  });

  return NextResponse.json({ project });
}
