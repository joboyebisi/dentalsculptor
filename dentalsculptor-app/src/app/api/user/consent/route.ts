import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { trackResearchEvent } from "@/lib/research-events";

export async function POST(req: NextRequest) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json();

  await prisma.user.update({
    where: { id: user.id },
    data: {
      consentAccepted: body.consentAccepted,
      researchContactOptIn: body.researchContactOptIn ?? false,
    },
  });

  await trackResearchEvent({
    userId: user.id,
    eventType: "SESSION_STARTED",
    metadata: { consent: true },
  });

  return NextResponse.json({ success: true });
}
