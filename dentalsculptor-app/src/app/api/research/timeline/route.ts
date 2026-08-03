import { NextResponse } from "next/server";
import { getAuthUser, isResearcherOrAdmin } from "@/lib/auth";
import { getEventTimeline } from "@/lib/research-events";

export async function GET() {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  if (!isResearcherOrAdmin(user.role)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const events = await getEventTimeline(100);
  return NextResponse.json({ events });
}
