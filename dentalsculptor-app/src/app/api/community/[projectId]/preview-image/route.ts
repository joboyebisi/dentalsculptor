import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { streamProjectCardPreview } from "@/lib/project-card-preview.server";

export const maxDuration = 30;

/** Public card preview for published community projects. */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ projectId: string }> }
) {
  const { projectId } = await params;
  const entry = await prisma.communityProject.findFirst({
    where: { projectId, published: true },
    select: { id: true },
  });
  if (!entry) {
    return NextResponse.json({ error: "Published project not found." }, { status: 404 });
  }

  const asset = await streamProjectCardPreview(projectId);
  if (!asset) {
    return NextResponse.json({ error: "Preview not found." }, { status: 404 });
  }

  return new NextResponse(asset.body, {
    status: 200,
    headers: {
      "Content-Type": asset.contentType,
      "Cache-Control": "public, max-age=3600",
    },
  });
}
