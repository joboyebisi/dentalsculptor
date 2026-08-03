import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { trackResearchEvent } from "@/lib/research-events";

export async function GET() {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const responses = await prisma.surveyResponse.findMany({
    where: { surveyType: "likert" },
  });

  const summary = Array.from(
    responses.reduce((map, r) => {
      const existing = map.get(r.question) ?? { total: 0, count: 0 };
      map.set(r.question, {
        total: existing.total + (r.scale ?? 0),
        count: existing.count + 1,
      });
      return map;
    }, new Map<string, { total: number; count: number }>())
  ).map(([question, { total, count }]) => ({
    question,
    avg: count > 0 ? Math.round((total / count) * 10) / 10 : 0,
  }));

  return NextResponse.json({ summary });
}

export async function POST(req: NextRequest) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();

  await prisma.surveyResponse.create({
    data: {
      userId: user.id,
      question: body.question,
      answer: body.answer,
      scale: body.scale,
      surveyType: "likert",
      sessionId: body.sessionId,
    },
  });

  await trackResearchEvent({
    userId: user.id,
    eventType: "SURVEY_COMPLETED",
    metadata: { question: body.question, scale: body.scale },
  });

  return NextResponse.json({ success: true });
}
