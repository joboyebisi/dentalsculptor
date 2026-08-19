import { createHash, randomUUID, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { finalizeModalGenerationJob } from "@/lib/ml-provider";
import { prisma } from "@/lib/prisma";

function tokenMatches(supplied: string, expectedHash: string | null): boolean {
  if (!supplied || !expectedHash) return false;
  const actual = Buffer.from(createHash("sha256").update(supplied).digest("hex"));
  const expected = Buffer.from(expectedHash);
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;
  const [user, job] = await Promise.all([
    getAuthUser(),
    prisma.generationJob.findUnique({ where: { id: jobId } }),
  ]);
  if (!job) {
    return NextResponse.json({ error: "Generation job not found." }, { status: 404 });
  }

  const jobToken = req.headers.get("x-generation-job-token") ?? "";
  const ownsJob = Boolean(user && job.ownerId === user.id);
  if (!ownsJob && !tokenMatches(jobToken, job.jobTokenHash)) {
    return NextResponse.json({ error: "Unauthorized." }, { status: 401 });
  }

  if (job.status !== "COMPLETED" || job.quality !== "preview") {
    return NextResponse.json(
      { error: "Only completed preview jobs can be enhanced." },
      { status: 409 }
    );
  }

  let body: { quality?: string } = {};
  try {
    body = (await req.json()) as { quality?: string };
  } catch {
    return NextResponse.json({ error: "Invalid request body." }, { status: 400 });
  }
  const quality = body.quality === "final" ? "final" : "standard";
  const traceId = randomUUID();

  try {
    await finalizeModalGenerationJob(jobId, quality, traceId);
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Could not start quality enhancement.",
      },
      { status: 502 }
    );
  }

  await prisma.generationJob.update({
    where: { id: jobId },
    data: {
      status: "QUEUED",
      stage: "queued",
      progress: 0,
      quality,
      error: null,
      completedAt: null,
    },
  });

  return NextResponse.json(
    {
      jobId,
      status: "queued",
      stage: "queued",
      quality,
    },
    { status: 202 }
  );
}
