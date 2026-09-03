import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { expandDentalPrompt } from "@/lib/dental-prompt-glossary";
import { trackResearchEvent } from "@/lib/research-events";
import { extractStorageKeyFromUrl, generateAssetKey, getAssetUrl, uploadAsset } from "@/lib/storage";
import { isValidGlbBuffer, glbValidationError } from "@/lib/glb-utils";
import { prisma } from "@/lib/prisma";
import { createEditJobRecord, updateEditJobProgress } from "@/lib/edit-jobs.server";
import { logEdit } from "@/lib/edit-log";
import type { EditProofMetrics } from "@/lib/edit-log";
import { validateCaseVariantRecipe, type CaseVariantRecipe } from "@/lib/case-variant-recipes";
import { projectModelServePath, resolveProjectModelUrl } from "@/lib/project-model-asset.server";

export const maxDuration = 300;

function isAllowedSourceModelUrl(url: string, storedUrl: string | null | undefined): boolean {
  if (!url) return false;
  if (storedUrl && url === storedUrl) return true;
  if (url.includes("supabase.co/storage") || url.includes(".amazonaws.com/")) return true;
  try {
    const parsed = new URL(url);
    const stored = storedUrl ? new URL(storedUrl) : null;
    if (stored && parsed.pathname === stored.pathname) return true;
  } catch {
    return false;
  }
  return false;
}

function parseJsonField(raw: string): unknown | undefined {
  if (!raw) return undefined;
  try {
    return JSON.parse(raw);
  } catch {
    return undefined;
  }
}

function isValidCameraPayload(value: unknown): boolean {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const camera = value as Record<string, unknown>;
  return (
    Array.isArray(camera.viewMatrix) &&
    camera.viewMatrix.length === 16 &&
    Array.isArray(camera.projectionMatrix) &&
    camera.projectionMatrix.length === 16 &&
    (camera.modelMatrix === undefined ||
      (Array.isArray(camera.modelMatrix) && camera.modelMatrix.length === 16)) &&
    Number(camera.width) > 0 &&
    Number(camera.height) > 0
  );
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
  const requestedSourceModelUrl = (formData.get("sourceModelUrl") as string) || "";
  const camera = (formData.get("camera") as string) || "";
  const selectedPartIds = (formData.get("selectedPartIds") as string) || "[]";
  const regionMarks = (formData.get("regionMarks") as string) || "";
  const referenceEdited = (formData.get("referenceEdited") as string) === "true";
  const referenceImage = formData.get("referenceImage");
  const sourceImage = formData.get("sourceImage");
  const editedImage = formData.get("editedImage");
  const variantRecipeRaw = (formData.get("variantRecipe") as string) || "";
  let variantRecipe: CaseVariantRecipe | undefined;
  if (variantRecipeRaw) {
    const validation = validateCaseVariantRecipe(parseJsonField(variantRecipeRaw), operation);
    if ("error" in validation) {
      return NextResponse.json({ error: validation.error }, { status: 400 });
    }
    variantRecipe = validation.recipe;
  }

  if (!instruction.trim()) {
    return NextResponse.json({ error: "Instruction is required." }, { status: 400 });
  }
  if (!requestedSourceModelUrl && !variantRecipe) {
    return NextResponse.json({ error: "sourceModelUrl is required." }, { status: 400 });
  }
  if (!["add", "remove", "replace"].includes(operation)) {
    return NextResponse.json({ error: "Unsupported edit operation." }, { status: 400 });
  }
  const maskImage = formData.get("maskImage");
  if (!(maskImage instanceof File) || maskImage.size < 64) {
    return NextResponse.json({ error: "A non-empty edit mask is required." }, { status: 400 });
  }
  if (!isValidCameraPayload(parseJsonField(camera))) {
    return NextResponse.json({ error: "A valid captured camera view is required." }, { status: 400 });
  }
  const usesGenerativePath = !variantRecipe || variantRecipe.technique === "generative";
  if (
    usesGenerativePath &&
    (!(sourceImage instanceof File) ||
      sourceImage.size < 64 ||
      !(editedImage instanceof File) ||
      editedImage.size < 64)
  ) {
    return NextResponse.json(
      { error: "Approve a localized 2D preview before running a generative 3D edit." },
      { status: 400 }
    );
  }

  const project = await prisma.project.findFirst({
    where: { id: projectId, ownerId: user.id },
    select: {
      dentalModel: { select: { generated3DUrl: true, generated3DKey: true, processingStage: true } },
      versions: { orderBy: { version: "desc" }, take: 20, select: { version: true, label: true, snapshot: true } },
    },
  });
  if (!project) {
    return NextResponse.json({ error: "Project not found." }, { status: 404 });
  }
  const masterVersion = project.versions.find((version) => version.label === "master-model");
  const masterSnapshot = masterVersion?.snapshot as { modelUrl?: string } | null;
  const isProjectProxy = requestedSourceModelUrl === projectModelServePath(projectId);
  // Case variants are always derived from server-owned project state. The browser
  // may display a proxy or stale signed URL, but it never chooses the master.
  let sourceModelUrl: string | null = variantRecipe
    ? masterSnapshot?.modelUrl ?? await resolveProjectModelUrl(project.dentalModel)
    : isProjectProxy
      ? await resolveProjectModelUrl(project.dentalModel)
      : requestedSourceModelUrl;
  if (!variantRecipe && !isProjectProxy && !isAllowedSourceModelUrl(requestedSourceModelUrl, project.dentalModel?.generated3DUrl)) {
    return NextResponse.json({ error: "Source model does not belong to this project." }, { status: 403 });
  }
  const sourceStorageKey = sourceModelUrl ? extractStorageKeyFromUrl(sourceModelUrl) : null;
  if (sourceStorageKey) sourceModelUrl = await getAssetUrl(sourceStorageKey);
  if (!sourceModelUrl) return NextResponse.json({ error: "Source model is unavailable." }, { status: 409 });

  const expanded = expandDentalPrompt(instruction);
  const stubJobId = `edit_${Date.now()}`;
  const t0 = Date.now();

  if (variantRecipe) {
    if (!masterVersion) {
      await prisma.projectVersion.create({
        data: {
          projectId,
          version: (project.versions[0]?.version ?? 0) + 1,
          label: "master-model",
          snapshot: { modelUrl: sourceModelUrl, format: "glb", immutable: true, capturedAt: new Date().toISOString() },
        },
      });
    }
  }

  logEdit({
    phase: "start",
    projectId,
    operation,
    detail: "edit-jobs POST",
  });

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
    if (variantRecipe) proxyForm.append("variantRecipe", JSON.stringify(variantRecipe));
    if (referenceEdited) proxyForm.append("referenceEdited", "true");
    proxyForm.append("maskImage", maskImage);
    if (referenceImage instanceof File) {
      proxyForm.append("referenceImage", referenceImage);
    }
    if (sourceImage instanceof File) proxyForm.append("sourceImage", sourceImage);
    if (editedImage instanceof File) proxyForm.append("editedImage", editedImage);

    const res = await fetch(modalEditUrl, {
      method: "POST",
      headers: { Authorization: `Bearer ${process.env.MODAL_WEBHOOK_SECRET ?? ""}` },
      body: proxyForm,
    });
    const raw = await res.text();
    let data: Record<string, unknown> = {};
    if (raw.trim()) {
      try {
        data = JSON.parse(raw) as Record<string, unknown>;
      } catch {
        return NextResponse.json(
          { error: "Modal edit worker returned invalid JSON.", detail: raw.slice(0, 200) },
          { status: 502 }
        );
      }
    } else if (!res.ok) {
      return NextResponse.json(
        { error: "Modal edit worker returned an empty response.", detail: `HTTP ${res.status}` },
        { status: 502 }
      );
    }
    if (!res.ok) {
      return NextResponse.json(
        { error: (data.error as string) ?? "Edit job failed." },
        { status: 502 }
      );
    }

    const jobId = (data.jobId as string | undefined) ?? stubJobId;

    let editJob: { revisionNumber: number };
    try {
      editJob = await createEditJobRecord({
        id: jobId,
        projectId,
        ownerId: user.id,
        operation,
        instruction: expanded.expanded,
        sourceModelUrl,
        camera: parseJsonField(camera),
        regionMarks: parseJsonField(regionMarks),
        selectedPartIds: parseJsonField(selectedPartIds),
        provider: variantRecipe && variantRecipe.technique !== "generative" ? "deterministic" : "modal",
        metadata: variantRecipe ? { variantRecipe, lineage: { source: "master-model" } } : undefined,
      });
    } catch (dbErr) {
      console.error("[edit-jobs] EditJob DB write failed — run prisma/sql/add_edit_job.sql", dbErr);
      return NextResponse.json(
        {
          error:
            "Edit job could not be saved. Ask your admin to run add_edit_job.sql in Supabase.",
          jobId,
          status: "failed",
        },
        { status: 503 }
      );
    }

    let modelUrl = data.modelUrl as string | undefined;
    let format = (data.format as string | undefined) ?? "glb";
    if (
      data.status === "completed" &&
      typeof data.modelBase64 === "string" &&
      data.modelBase64 &&
      !modelUrl
    ) {
      const buffer = Buffer.from(data.modelBase64, "base64");
      if (!isValidGlbBuffer(buffer)) {
        return NextResponse.json(
          { error: glbValidationError(buffer), jobId, status: "failed" },
          { status: 502 }
        );
      }
      const key = generateAssetKey(user.id, `edit-${jobId}.glb`);
      modelUrl = await uploadAsset(key, buffer, "model/gltf-binary");
      format = "glb";
    }

    if (modelUrl) {
      await updateEditJobProgress(jobId, {
        status: "COMPLETED",
        stage: "completed",
        progress: 100,
        resultModelUrl: modelUrl,
        resultFormat: format,
      });
    } else if (data.status === "queued") {
      await updateEditJobProgress(jobId, { status: "QUEUED", stage: "queued", progress: 0 });
    }

    await trackResearchEvent({
      userId: user.id,
      projectId,
      eventType: "AI_PROMPT_SUBMITTED",
      metadata: { jobId, provider: "modal", operation },
    });

    logEdit({
      phase: modelUrl ? "complete" : "submit",
      projectId,
      jobId,
      operation,
      provider: "modal",
      durationMs: Date.now() - t0,
      stage: modelUrl ? "completed" : String(data.status ?? "queued"),
      maskedVertexRatio: data.maskedVertexRatio as number | undefined,
    });

    return NextResponse.json({
      jobId,
      status: modelUrl ? "completed" : (data.status ?? "queued"),
      modelUrl,
      format,
      revisionNumber: editJob.revisionNumber,
      preview2dBase64: data.preview2dBase64 as string | undefined,
      maskedVertexRatio: data.maskedVertexRatio as number | undefined,
      stage: data.stage as string | undefined,
      regionMarkCount: data.regionMarkCount as number | undefined,
      metrics: data.metrics as EditProofMetrics | undefined,
    });
  }

  await trackResearchEvent({
    userId: user.id,
    projectId,
    eventType: "AI_PROMPT_SUBMITTED",
    metadata: {
      jobId: stubJobId,
      provider: "stub",
      operation,
      prompt: expanded.original,
      regionMarks: regionMarks || undefined,
    },
  });

  return NextResponse.json({
    jobId: stubJobId,
    status: "queued",
    message: "DentalSculptor editing is temporarily unavailable. Please export the generated model or try again later.",
  });
}
