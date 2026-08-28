import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import {
  resolveProjectModelStorageKey,
  streamProjectModelAsset,
} from "@/lib/project-model-asset.server";
import { projectModelServePath } from "@/lib/project-model-path";

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
        where: { label: { in: ["case-recipe", "master-model"] } },
        orderBy: { version: "desc" },
        take: 10,
      },
    },
  });

  if (!project) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const dentalModel = project.dentalModel
    ? {
        ...project.dentalModel,
        modelServeUrl:
          project.dentalModel.generated3DUrl || project.dentalModel.generated3DKey
            ? projectModelServePath(id)
            : null,
      }
    : null;

  if (dentalModel && !dentalModel.generated3DKey && dentalModel.generated3DUrl) {
    const recoveredKey = resolveProjectModelStorageKey(dentalModel);
    if (recoveredKey && recoveredKey !== dentalModel.generated3DKey) {
      await prisma.dentalModel.updateMany({
        where: { projectId: id },
        data: { generated3DKey: recoveredKey },
      });
      dentalModel.generated3DKey = recoveredKey;
    }
  }

  return NextResponse.json({ project: { ...project, dentalModel } });
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

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const existing = await prisma.project.findFirst({
    where: { id, ownerId: user.id },
    select: { id: true },
  });
  if (!existing) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  await prisma.project.delete({ where: { id } });
  return NextResponse.json({ success: true });
}
