import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { expandDentalPrompt } from "@/lib/dental-prompt-glossary";
import { trackResearchEvent } from "@/lib/research-events";
import { generateAssetKey, uploadAsset } from "@/lib/storage";
import { prisma } from "@/lib/prisma";

export const maxDuration = 300;

function isAllowedSourceModelUrl(url: string, storedUrl: string | null | undefined): boolean {
  if (!url) return false;
  if (storedUrl && url === storedUrl) return true;
  // Allow revised models uploaded to our asset storage between DB updates.
  if (url.includes("supabase.co/storage") || url.includes(".amazonaws.com/")) return true;
  return false;
}

async function persistEditedModel(
  projectId: string,
  modelUrl: string,
  format: string
): Promise<void> {
  const dentalModel = await prisma.dentalModel.findUnique({ where: { projectId } });
  if (!dentalModel) return;

  const stage = {
    format,
    source: "nano3d",
    editedAt: new Date().toISOString(),
  };

  await prisma.dentalModel.update({
    where: { projectId },
    data: {
      generated3DUrl: modelUrl,
      processingStage: JSON.stringify(stage),
    },
  });
}

/**
 * Submit a masked 3D edit job (Nano3D on Modal when deployed).
 */
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const user = await getAuthUser();
  if (!user) {
    return NextResponse.json({ error: "Sign in required." }, { status: 401 });
  }

  const { id: projectId } = await params;
  const formData = await req.formData();
  const instruction = (formData.get("instruction") as string) || "";
  const operation = (formData.get("operation") as string) || "replace";
  const sourceModelUrl = (formData.get("sourceModelUrl") as string) || "";
  const camera = (formData.get("camera") as string) || "";
  const selectedPartIds = (formData.get("selectedPartIds") as string) || "[]";
  const regionMarks = (formData.get("regionMarks") as string) || "";
  const referenceImage = formData.get("referenceImage");

  if (!instruction.trim()) {
    return NextResponse.json({ error: "Instruction is required." }, { status: 400 });
  }
  if (!sourceModelUrl) {
    return NextResponse.json({ error: "sourceModelUrl is required." }, { status: 400 });
  }
  if (!["add", "remove", "replace"].includes(operation)) {
    return NextResponse.json({ error: "Unsupported edit operation." }, { status: 400 });
  }

  const project = await prisma.project.findFirst({
    where: { id: projectId, ownerId: user.id },
    select: { dentalModel: { select: { generated3DUrl: true } } },
  });
  if (!project) {
    return NextResponse.json({ error: "Project not found." }, { status: 404 });
  }
  if (!isAllowedSourceModelUrl(sourceModelUrl, project.dentalModel?.generated3DUrl)) {
    return NextResponse.json({ error: "Source model does not belong to this project." }, { status: 403 });
  }

  const expanded = expandDentalPrompt(instruction);
  const jobId = `edit_${Date.now()}`;

  const modalEditUrl = process.env.MODAL_EDIT_URL;
  if (modalEditUrl) {
    const proxyForm = new FormData();
    proxyForm.append("instruction", expanded.expanded);
    proxyForm.append("operation", operation);
    proxyForm.append("sourceModelUrl", sourceModelUrl);
    proxyForm.append("projectId", projectId);
    if (camera) proxyForm.append("camera", camera);
    proxyForm.append("selectedPartIds", selectedPartIds);
    if (regionMarks) proxyForm.append("regionMarks", regionMarks);
    const mask = formData.get("maskImage");
    if (mask instanceof File) proxyForm.append("maskImage", mask);
    if (referenceImage instanceof File) {
      proxyForm.append("referenceImage", referenceImage);
    }

    const res = await fetch(modalEditUrl, {
      method: "POST",
      headers: { Authorization: `Bearer ${process.env.MODAL_WEBHOOK_SECRET ?? ""}` },
      body: proxyForm,
    });
    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json({ error: data.error ?? "Edit job failed." }, { status: 502 });
    }

    let modelUrl = data.modelUrl as string | undefined;
    let format = (data.format as string | undefined) ?? "glb";
    if (data.status === "completed" && data.modelBase64 && !modelUrl) {
      const buffer = Buffer.from(data.modelBase64, "base64");
      const key = generateAssetKey(user.id, `edit-${data.jobId ?? jobId}.glb`);
      modelUrl = await uploadAsset(key, buffer, "model/gltf-binary");
      format = "glb";
    }

    if (modelUrl) {
      await persistEditedModel(projectId, modelUrl, format);
    }

    await trackResearchEvent({
      userId: user.id,
      projectId,
      eventType: "AI_PROMPT_SUBMITTED",
      metadata: { jobId: data.jobId ?? jobId, provider: "modal", operation },
    });
    return NextResponse.json({
      jobId: data.jobId ?? jobId,
      status: data.status ?? "queued",
      modelUrl,
      format,
      preview2dBase64: data.preview2dBase64 as string | undefined,
    });
  }

  await trackResearchEvent({
    userId: user.id,
    projectId,
    eventType: "AI_PROMPT_SUBMITTED",
    metadata: { jobId, provider: "stub", operation, prompt: expanded.original, regionMarks: regionMarks || undefined },
  });

  return NextResponse.json({
    jobId,
    status: "queued",
    message: "Modal Nano3D not deployed — set MODAL_EDIT_URL in Vercel. See docs/MODAL_SETUP_GUIDE.md",
  });
}
