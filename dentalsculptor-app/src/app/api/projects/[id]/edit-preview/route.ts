import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { expandDentalPrompt } from "@/lib/dental-prompt-glossary";
import { isFalInpaintConfigured, runFalMaskedInpaint } from "@/lib/fal-inpaint";
import { trackResearchEvent } from "@/lib/research-events";
import { prisma } from "@/lib/prisma";
import type { EditOperation } from "@/lib/edit-types";

export const maxDuration = 120;

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

  if (!isFalInpaintConfigured()) {
    return NextResponse.json({
      fallback: true,
      reason: "FAL_KEY not configured — use client stub preview.",
    });
  }

  try {
    const { imageUrl, prompt } = await runFalMaskedInpaint({
      referenceBlob: referenceImage,
      maskBlob: maskImage,
      instruction: expanded.expanded,
      operation: operation as EditOperation,
    });

    const imageRes = await fetch(imageUrl);
    if (!imageRes.ok) {
      throw new Error("Could not download inpaint result.");
    }
    const buffer = Buffer.from(await imageRes.arrayBuffer());
    const previewBase64 = buffer.toString("base64");
    const contentType = imageRes.headers.get("content-type") ?? "image/png";

    await trackResearchEvent({
      userId: user.id,
      projectId,
      eventType: "AI_PROMPT_SUBMITTED",
      metadata: {
        stage: "2d-inpaint-fal",
        provider: "fal",
        operation,
        prompt: expanded.original,
      },
    });

    return NextResponse.json({
      provider: "fal",
      previewBase64,
      contentType,
      promptUsed: prompt,
    });
  } catch (err) {
    console.error("[edit-preview] fal inpaint failed:", err);
    return NextResponse.json({
      fallback: true,
      reason: err instanceof Error ? err.message : "Inpaint failed.",
    });
  }
}
