import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: projectId } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();
  const count = await prisma.learningObjective.count({ where: { projectId } });

  const objective = await prisma.learningObjective.create({
    data: {
      projectId,
      title: body.title,
      description: body.description,
      order: count,
    },
  });

  return NextResponse.json({ objective });
}
