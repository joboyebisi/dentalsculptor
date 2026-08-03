import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { trackResearchEvent } from "@/lib/research-events";
import type { ResearchEventType } from "@/generated/prisma/client";

export async function POST(req: NextRequest) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();

  await trackResearchEvent({
    userId: user.id,
    projectId: body.projectId,
    eventType: body.eventType as ResearchEventType,
    metadata: body.metadata,
    sessionId: body.sessionId,
  });

  return NextResponse.json({ success: true });
}
