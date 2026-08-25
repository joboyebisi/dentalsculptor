import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { expandDentalPrompt } from "@/lib/dental-prompt-glossary";
import { isFalInpaintConfigured, runFalMaskedInpaint } from "@/lib/fal-inpaint";
import { isModalInpaintConfigured, runModalMaskedInpaint } from "@/lib/modal-inpaint";
import { trackResearchEvent } from "@/lib/research-events";
import { prisma } from "@/lib/prisma";
import type { EditOperation } from "@/lib/edit-types";

export const maxDuration = 120;

async function trackInpaint(
  userId: string,
  projectId: string,
  provider: string,
  operation: string,
  prompt: string
) {
  await trackResearchEvent({
    userId,
    projectId,
    eventType: "AI_PROMPT_SUBMITTED",
    metadata: { stage: "2d-inpaint", provider, operation, prompt },
  });
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const user = await getAuthUser();
  if (!user) {
    return NextResponse.json({ error: "Sign in required." }, { status: 401 });
  }

  const { id: projectId } = await params;
  const project = await prisma.project.findFirst({
    where: { id: projectId, ownerId: user.id },
    select: { id: true },
  });
  if (!project) {
    return NextResponse.json({ error: "Project not found." }, { status: 404 });
  }

  const formData = await req.formData();
  const instruction = (formData.get("instruction") as string) || "";
  const operation = (formData.get("operation") as string) || "replace";
  const referenceImage = formData.get("referenceImage");
  const maskImage = formData.get("maskImage");

  if (!instruction.trim()) {
    return NextResponse.json({ error: "Instruction is required." }, { status: 400 });
  }
  if (!(referenceImage instanceof File)) {
    return NextResponse.json({ error: "referenceImage is required." }, { status: 400 });
  }
  if (!(maskImage instanceof File)) {
    return NextResponse.json({ error: "maskImage is required." }, { status: 400 });
  }
  if (!["add", "remove", "replace"].includes(operation)) {
    return NextResponse.json({ error: "Unsupported edit operation." }, { status: 400 });
  }

  const expanded = expandDentalPrompt(instruction);
  const op = operation as EditOperation;

  // 1) Self-hosted Modal SDXL (preferred — no fal token burn)
  if (isModalInpaintConfigured()) {
    try {
      const result = await runModalMaskedInpaint({
        referenceBlob: referenceImage,
        maskBlob: maskImage,
        instruction: expanded.expanded,
        operation: op,
      });
      await trackInpaint(user.id, projectId, "modal-sdxl", operation, expanded.original);
      return NextResponse.json({ provider: "modal-sdxl", ...result });
    } catch (err) {
      console.error("[edit-preview] Modal inpaint failed, trying fal:", err);
    }
  }

  // 2) fal.ai pay-per-use fallback (~$0.03–0.04 per 1024² preview)
  if (isFalInpaintConfigured()) {
    try {
      const { imageUrl, prompt } = await runFalMaskedInpaint({
        referenceBlob: referenceImage,
        maskBlob: maskImage,
        instruction: expanded.expanded,
        operation: op,
      });
      const imageRes = await fetch(imageUrl);
      if (!imageRes.ok) throw new Error("Could not download inpaint result.");
      const buffer = Buffer.from(await imageRes.arrayBuffer());
      await trackInpaint(user.id, projectId, "fal", operation, expanded.original);
      return NextResponse.json({
        provider: "fal",
        previewBase64: buffer.toString("base64"),
        contentType: imageRes.headers.get("content-type") ?? "image/png",
        promptUsed: prompt,
      });
    } catch (err) {
      console.error("[edit-preview] fal inpaint failed:", err);
    }
  }

  // 3) Client-side stub (free, instant)
  return NextResponse.json({
    fallback: true,
    reason:
      "No inpaint worker configured — set MODAL_INPAINT_URL (self-hosted) or FAL_KEY (paid fallback). Using client stub.",
  });
}
