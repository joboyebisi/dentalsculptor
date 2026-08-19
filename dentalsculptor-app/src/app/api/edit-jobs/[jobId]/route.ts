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

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const user = await getAuthUser();
  if (!user) {
    return NextResponse.json({ error: "Sign in required." }, { status: 401 });
  }

  const { jobId } = await params;
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
    message?: string;
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
    return NextResponse.json({
      ...data,
      modelUrl: persisted.modelUrl,
      format: persisted.format,
    });
  }

  return NextResponse.json(data, { status: res.status });
}
