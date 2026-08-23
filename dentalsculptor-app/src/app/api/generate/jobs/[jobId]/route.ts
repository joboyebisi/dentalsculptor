import { createHash, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { getS3AssetUrl } from "@/lib/storage";
import type { Prisma } from "@/generated/prisma/client";

function tokenMatches(supplied: string, expectedHash: string | null): boolean {
  if (!supplied || !expectedHash) return false;
  const actual = Buffer.from(createHash("sha256").update(supplied).digest("hex"));
  const expected = Buffer.from(expectedHash);
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

function asJson(value: unknown): Prisma.InputJsonValue | undefined {
  return value == null
    ? undefined
    : (JSON.parse(JSON.stringify(value)) as Prisma.InputJsonValue);
}

export async function GET(
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

  let current = job;
  if (job.status === "QUEUED" || job.status === "RUNNING") {
    const statusUrl = process.env.MODAL_JOB_STATUS_URL;
    if (!statusUrl) {
      return NextResponse.json(
        { error: "MODAL_JOB_STATUS_URL is not configured." },
        { status: 503 }
      );
    }
    const modalRes = await fetch(
      `${statusUrl}?jobId=${encodeURIComponent(jobId)}`,
      {
        headers: {
          Authorization: `Bearer ${process.env.MODAL_WEBHOOK_SECRET ?? ""}`,
        },
        cache: "no-store",
      }
    );
    const raw = await modalRes.text();
    let modalData: {
      status?: string;
      stage?: string;
      progress?: number;
      quality?: string;
      resultKey?: string;
      format?: string;
      seed?: number;
      pipelineType?: string;
      timings?: unknown;
      metrics?: unknown;
      error?: string;
      detail?: string;
      canFinalize?: boolean;
      phase?: string;
    };
    try {
      modalData = JSON.parse(raw) as typeof modalData;
    } catch {
      return NextResponse.json(
        { error: `Generation status service failed (${modalRes.status}).` },
        { status: 502 }
      );
    }
    if (!modalRes.ok) {
      return NextResponse.json(
        { error: modalData.error ?? modalData.detail ?? "Job status unavailable." },
        { status: 502 }
      );
    }

    const status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" =
      modalData.status === "completed"
        ? "COMPLETED"
        : modalData.status === "failed"
          ? "FAILED"
          : modalData.status === "running"
            ? "RUNNING"
            : "QUEUED";

    current = await prisma.generationJob.update({
      where: { id: jobId },
      data: {
        status,
        stage: modalData.stage ?? job.stage,
        progress: modalData.progress ?? job.progress,
        resultKey: modalData.resultKey ?? job.resultKey,
        format: modalData.format ?? job.format,
        seed: modalData.seed ?? job.seed,
        pipelineType: modalData.pipelineType ?? job.pipelineType,
        quality: modalData.quality ?? job.quality,
        timings: asJson(modalData.timings),
        metrics: asJson(modalData.metrics),
        error: modalData.error,
        startedAt: status === "RUNNING" ? (job.startedAt ?? new Date()) : job.startedAt,
        completedAt:
          status === "COMPLETED" || status === "FAILED" ? new Date() : undefined,
      },
    });

    if (status === "COMPLETED" && modalData.resultKey && current.projectId) {
      await prisma.dentalModel.updateMany({
        where: { projectId: current.projectId },
        data: { generated3DKey: modalData.resultKey },
      });
      await prisma.project.updateMany({
        where: { id: current.projectId },
        data: { status: "READY" },
      });
    }
  }

  const modelUrl =
    current.status === "COMPLETED" && current.resultKey
      ? await getS3AssetUrl(current.resultKey)
      : undefined;

  return NextResponse.json({
    jobId: current.id,
    status: current.status.toLowerCase(),
    stage: current.stage,
    progress: current.progress,
    quality: current.quality,
    modelUrl,
    modelKey: current.resultKey,
    format: current.format,
    seed: current.seed,
    pipelineType: current.pipelineType,
    timings: current.timings,
    metrics: current.metrics,
    error: current.error,
  });
}
