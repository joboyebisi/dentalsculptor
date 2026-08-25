import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { acceptEditJob, rejectEditJob } from "@/lib/edit-jobs.server";
import { trackResearchEvent } from "@/lib/research-events";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const user = await getAuthUser();
  if (!user) {
    return NextResponse.json({ error: "Sign in required." }, { status: 401 });
  }

  const { jobId } = await params;
  const body = await req.json();
  const action = body.action as "accept" | "reject";

  if (action !== "accept" && action !== "reject") {
    return NextResponse.json({ error: "action must be accept or reject." }, { status: 400 });
  }

  try {
    const job =
      action === "accept"
        ? await acceptEditJob(jobId, user.id)
        : await rejectEditJob(jobId, user.id);

    await trackResearchEvent({
      userId: user.id,
      projectId: job.projectId,
      eventType: action === "accept" ? "AI_SUGGESTION_ACCEPTED" : "AI_SUGGESTION_REJECTED",
      metadata: { editJobId: jobId, revisionNumber: job.revisionNumber },
    });

    return NextResponse.json({
      ok: true,
      action,
      modelUrl: action === "accept" ? job.resultModelUrl : job.sourceModelUrl,
      revisionNumber: job.revisionNumber,
    });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Could not update revision." },
      { status: 400 }
    );
  }
}
