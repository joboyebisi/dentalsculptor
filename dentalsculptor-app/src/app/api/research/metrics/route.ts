import { NextResponse } from "next/server";
import { getAuthUser, isResearcherOrAdmin } from "@/lib/auth";
import { getResearchMetrics, getEventTimeline } from "@/lib/research-events";

export async function GET() {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const global = isResearcherOrAdmin(user.role);
  const metrics = await getResearchMetrics(global ? undefined : user.id);

  return NextResponse.json({ metrics });
}
