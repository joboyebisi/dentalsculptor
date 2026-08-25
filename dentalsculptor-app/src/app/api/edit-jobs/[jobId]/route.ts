import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { generateAssetKey, uploadAsset } from "@/lib/storage";
import { updateEditJobProgress } from "@/lib/edit-jobs.server";
import { prisma } from "@/lib/prisma";

async function persistModalModelBase64(
  modelBase64: string,
  jobId: string,
  userId: string
): Promise<{ modelUrl: string; format: string }> {
  const buffer = Buffer.from(modelBase64, "base64");
  const key = generateAssetKey(userId, `edit-${jobId}.glb`);
  const modelUrl = await uploadAsset(key, buffer, "model/gltf-binary");
  return { modelUrl, format: "glb" };
}

function mapModalStatus(status?: string): "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" {
  if (status === "completed") return "COMPLETED";
  if (status === "failed") return "FAILED";
  if (status === "running") return "RUNNING";
  return "QUEUED";
}

function mapDbStatus(status: string): string {
  if (status === "COMPLETED") return "completed";
  if (status === "FAILED") return "failed";
  if (status === "RUNNING") return "running";
  return "queued";
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const user = await getAuthUser();
  if (!user) {
    return NextResponse.json({ error: "Sign in required." }, { status: 401 });
  }

  const { jobId } = await params;
  const projectId = req.nextUrl.searchParams.get("projectId") ?? undefined;

  const dbJob = await prisma.editJob.findFirst({
    where: {
      id: jobId,
      ownerId: user.id,
      ...(projectId ? { projectId } : {}),
    },
  });

  if (dbJob?.status === "COMPLETED" && dbJob.resultModelUrl) {
    return NextResponse.json({
      jobId,
      status: "completed",
      progress: 100,
      stage: dbJob.stage ?? "completed",
      modelUrl: dbJob.resultModelUrl,
      format: dbJob.resultFormat ?? "glb",
      revisionNumber: dbJob.revisionNumber,
    });
  }

  if (dbJob?.status === "FAILED") {
    return NextResponse.json({
      jobId,
      status: "failed",
      progress: 100,
      stage: dbJob.stage ?? "error",
      error: dbJob.error ?? "Edit job failed.",
      revisionNumber: dbJob.revisionNumber,
    });
  }

  const statusUrl = process.env.MODAL_JOB_STATUS_URL;
  if (!statusUrl) {
    return NextResponse.json({
      jobId,
      status: dbJob ? mapDbStatus(dbJob.status) : "queued",
      progress: dbJob?.progress ?? 0,
      stage: dbJob?.stage ?? "stub",
      message: "Deploy Modal workers — see docs/MODAL_SETUP_GUIDE.md",
    });
  }

  const res = await fetch(`${statusUrl}?jobId=${encodeURIComponent(jobId)}`, {
    headers: { Authorization: `Bearer ${process.env.MODAL_WEBHOOK_SECRET ?? ""}` },
  });

  const raw = await res.text();
  let data: {
    jobId?: string;
    status?: string;
    progress?: number;
    stage?: string;
    modelUrl?: string;
    modelBase64?: string;
    format?: string;
    error?: string;
    detail?: string;
    preview2dBase64?: string;
    maskedVertexRatio?: number;
    regionMarkCount?: number;
  } = {};

  if (raw.trim()) {
    try {
      data = JSON.parse(raw) as typeof data;
    } catch {
      return NextResponse.json(
        {
          jobId,
          status: "failed",
          error: "Modal job status returned invalid JSON.",
          detail: raw.slice(0, 200),
        },
        { status: 502 }
      );
    }
  } else if (!res.ok) {
    return NextResponse.json(
      {
        jobId,
        status: "failed",
        error: "Modal job status returned an empty response.",
        detail: `HTTP ${res.status}`,
      },
      { status: 502 }
    );
  }

  if (!res.ok) {
    await updateEditJobProgress(jobId, {
      status: "FAILED",
      stage: "error",
      progress: 100,
      error: data.error ?? data.detail ?? "Edit job status is unavailable.",
    }).catch(() => undefined);

    return NextResponse.json(
      {
        jobId,
        status: "failed",
        progress: 100,
        stage: "error",
        error: data.error ?? data.detail ?? "Edit job status is unavailable.",
      },
      { status: res.status }
    );
  }

  if (data.status === "running" || data.status === "queued") {
    await updateEditJobProgress(jobId, {
      status: mapModalStatus(data.status),
      stage: data.stage,
      progress: data.progress,
    }).catch(() => undefined);
  }

  if (data.status === "completed" && data.modelBase64 && !data.modelUrl) {
    const persisted = await persistModalModelBase64(data.modelBase64, jobId, user.id);
    await updateEditJobProgress(jobId, {
      status: "COMPLETED",
      stage: data.stage ?? "completed",
      progress: 100,
      resultModelUrl: persisted.modelUrl,
      resultFormat: persisted.format,
      metadata: {
        maskedVertexRatio: data.maskedVertexRatio,
        regionMarkCount: data.regionMarkCount,
      },
    }).catch(() => undefined);

    return NextResponse.json({
      ...data,
      status: "completed",
      modelUrl: persisted.modelUrl,
      format: persisted.format,
      revisionNumber: dbJob?.revisionNumber,
      preview2dUrl: data.preview2dBase64
        ? `data:image/png;base64,${data.preview2dBase64}`
        : undefined,
    });
  }

  if (data.status === "completed" && data.modelUrl) {
    await updateEditJobProgress(jobId, {
      status: "COMPLETED",
      stage: data.stage ?? "completed",
      progress: 100,
      resultModelUrl: data.modelUrl,
      resultFormat: data.format ?? "glb",
      metadata: {
        maskedVertexRatio: data.maskedVertexRatio,
        regionMarkCount: data.regionMarkCount,
      },
    }).catch(() => undefined);
  }

  if (data.status === "failed") {
    await updateEditJobProgress(jobId, {
      status: "FAILED",
      stage: "error",
      progress: 100,
      error: data.error ?? "Edit job failed.",
    }).catch(() => undefined);
  }

  return NextResponse.json(
    {
      ...data,
      revisionNumber: dbJob?.revisionNumber,
      preview2dUrl: data.preview2dBase64
        ? `data:image/png;base64,${data.preview2dBase64}`
        : undefined,
    },
    { status: res.status }
  );
}
