import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { trackResearchEvent } from "@/lib/research-events";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: projectId } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();

  const annotation = await prisma.annotation.create({
    data: {
      projectId,
      creatorId: user.id,
      text: body.text,
      position: body.position,
      type: body.type ?? "point",
      color: body.color ?? "#0F3D91",
      region: body.region,
    },
  });

  await trackResearchEvent({
    userId: user.id,
    projectId,
    eventType: "ANNOTATION_CREATED",
    metadata: { annotationId: annotation.id },
  });

  return NextResponse.json({ annotation });
}
