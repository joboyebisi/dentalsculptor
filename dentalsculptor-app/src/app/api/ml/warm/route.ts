import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { getMlMeshProvider, isModalConfigured, warmModalGpu } from "@/lib/ml-provider";
import { isUiPreviewMode } from "@/lib/preview-mode";
import { timingSafeEqual } from "node:crypto";

function hasValidResearchInvite(req: NextRequest): boolean {
  const expected = process.env.RESEARCH_GENERATION_ACCESS_CODE ?? "";
  const supplied =
    req.headers.get("x-research-invite")?.trim() ??
    req.nextUrl.searchParams.get("invite")?.trim() ??
    "";
  if (!expected || !supplied) return false;
  const expectedBytes = Buffer.from(expected);
  const suppliedBytes = Buffer.from(supplied);
  return (
    expectedBytes.length === suppliedBytes.length &&
    timingSafeEqual(expectedBytes, suppliedBytes)
  );
}

export async function POST(req: NextRequest) {
  if (getMlMeshProvider() !== "modal" || !isModalConfigured()) {
    return NextResponse.json({ status: "skipped", reason: "modal-not-configured" });
  }

  const user = await getAuthUser();
  if (!user && !isUiPreviewMode() && !hasValidResearchInvite(req)) {
    return NextResponse.json({ error: "Unauthorized." }, { status: 403 });
  }

  const reason = req.headers.get("x-gpu-warm-reason") ?? "unknown";
  try {
    await warmModalGpu();
    console.info(`[gpu-warm] requested reason=${reason}`);
    return NextResponse.json({ status: "warming" }, { status: 202 });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Warmup failed.";
    console.warn(`[gpu-warm] failed reason=${reason} error=${message}`);
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
