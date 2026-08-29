import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { streamProjectModelAsset } from "@/lib/project-model-asset.server";

export const maxDuration = 60;

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ projectId: string }> }
) {
  const { projectId } = await params;
  const entry = await prisma.communityProject.findFirst({
    where: { projectId, published: true },
    select: { project: { select: { dentalModel: true } } },
  });
  if (!entry?.project.dentalModel) {
    return NextResponse.json({ error: "Published model not found." }, { status: 404 });
  }

  const asset = await streamProjectModelAsset(entry.project.dentalModel);
  if (!asset) {
    return NextResponse.json({ error: "Could not load the published model." }, { status: 502 });
  }

  const download = req.nextUrl.searchParams.get("download") === "1";
  if (download) {
    await prisma.communityProject.update({
      where: { projectId },
      data: { downloads: { increment: 1 } },
    });
  }
  return new NextResponse(asset.body, {
    status: 200,
    headers: {
      "Content-Type": asset.contentType,
      "Cache-Control": "public, max-age=3600",
      ...(download
        ? { "Content-Disposition": `attachment; filename="dentalsculptor-${projectId}.glb"` }
        : {}),
    },
  });
}
