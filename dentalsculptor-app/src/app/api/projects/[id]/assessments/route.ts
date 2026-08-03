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
  const count = await prisma.assessment.count({ where: { projectId } });

  const assessment = await prisma.assessment.create({
    data: {
      projectId,
      question: body.question,
      answer: body.answer,
      type: body.type ?? "short_answer",
      order: count,
    },
  });

  return NextResponse.json({ assessment });
}
