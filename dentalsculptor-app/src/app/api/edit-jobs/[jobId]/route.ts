import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { generateAssetKey, uploadAsset } from "@/lib/storage";

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

async function persistEditedModelForProject(
  projectId: string,
  modelUrl: string,
  format: string
): Promise<void> {
  const { prisma } = await import("@/lib/prisma");
  const dentalModel = await prisma.dentalModel.findUnique({ where: { projectId } });
  if (!dentalModel) return;
  await prisma.dentalModel.update({
    where: { projectId },
    data: {
      generated3DUrl: modelUrl,
      processingStage: JSON.stringify({
        format,
        source: "nano3d",
        editedAt: new Date().toISOString(),
      }),
    },
  });
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
  const projectId = req.nextUrl.searchParams.get("projectId");
  const statusUrl = process.env.MODAL_JOB_STATUS_URL;
  if (!statusUrl) {
    return NextResponse.json({
      jobId,
      status: "completed",
      progress: 100,
      stage: "stub",
      message: "Deploy Modal workers — see docs/MODAL_SETUP_GUIDE.md",
    });
  }

  const res = await fetch(`${statusUrl}?jobId=${encodeURIComponent(jobId)}`, {
    headers: { Authorization: `Bearer ${process.env.MODAL_WEBHOOK_SECRET ?? ""}` },
  });
  const data = (await res.json()) as {
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
  };

  if (!res.ok) {
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

  if (data.status === "completed" && data.modelBase64 && !data.modelUrl) {
    const persisted = await persistModalModelBase64(data.modelBase64, jobId, user.id);
    if (projectId) {
      await persistEditedModelForProject(projectId, persisted.modelUrl, persisted.format);
    }
    return NextResponse.json({
      ...data,
      modelUrl: persisted.modelUrl,
      format: persisted.format,
      preview2dUrl: data.preview2dBase64
        ? `data:image/png;base64,${data.preview2dBase64}`
        : undefined,
    });
  }

  if (data.status === "completed" && data.modelUrl && projectId) {
    await persistEditedModelForProject(projectId, data.modelUrl, data.format ?? "glb");
  }

  return NextResponse.json(
    {
      ...data,
      preview2dUrl: data.preview2dBase64
        ? `data:image/png;base64,${data.preview2dBase64}`
        : undefined,
    },
    { status: res.status }
  );
}
