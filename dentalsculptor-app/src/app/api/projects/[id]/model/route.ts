import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { streamProjectModelAsset } from "@/lib/project-model-asset.server";

export const maxDuration = 60;

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized." }, { status: 401 });

  const project = await prisma.project.findFirst({
    where: { id, ownerId: user.id },
    select: { dentalModel: true },
  });
  if (!project?.dentalModel) {
    return NextResponse.json({ error: "Model not found." }, { status: 404 });
  }

  const asset = await streamProjectModelAsset(project.dentalModel);
  if (!asset) {
    return NextResponse.json(
      { error: "Could not load the 3D model. Try regenerating this project." },
      { status: 502 }
    );
  }

  return new NextResponse(asset.body, {
    status: 200,
    headers: {
      "Content-Type": asset.contentType,
      "Cache-Control": asset.cacheControl,
    },
  });
}

export async function HEAD(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  const response = await GET(req, context);
  return new NextResponse(null, {
    status: response.status,
    headers: response.headers,
  });
}
