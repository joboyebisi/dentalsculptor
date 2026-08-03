import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { trackResearchEvent } from "@/lib/research-events";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();

  const assignment = await prisma.studentAssignment.update({
    where: { id, studentId: user.id },
    data: {
      reflection: body.reflection,
      status: "SUBMITTED",
      completedAt: new Date(),
    },
  });

  await trackResearchEvent({
    userId: user.id,
    projectId: assignment.projectId,
    eventType: "REFLECTION_SUBMITTED",
    metadata: { assignmentId: id },
  });

  return NextResponse.json({ assignment });
}
