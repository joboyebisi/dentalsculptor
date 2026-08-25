import { NextRequest, NextResponse } from "next/server";
import "@/lib/ensure-browser-globals";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { getExportPreset, type ExportTarget } from "@/lib/export-presets";
import { exportMeshForPreset, type ExportScope, type MeshExportFormat } from "@/lib/export-mesh";
import { trackResearchEvent } from "@/lib/research-events";
import { parseModelProcessingStage } from "@/lib/model-processing-stage";

export const maxDuration = 120;
export const runtime = "nodejs";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { id: projectId } = await params;
  const body = await req.json();
  const target = body.target as ExportTarget;
  const validateOnly = Boolean(body.validateOnly);
  const outputFormat = body.outputFormat as MeshExportFormat | undefined;
  const scope = (body.scope as ExportScope | undefined) ?? "full";
  const modelUrlOverride = body.modelUrl as string | undefined;

  if (!target) {
    return NextResponse.json({ error: "target is required." }, { status: 400 });
  }

  const project = await prisma.project.findFirst({
    where: { id: projectId, ownerId: user.id },
    include: { dentalModel: true },
  });

  const modelUrl = modelUrlOverride ?? project?.dentalModel?.generated3DUrl;
  if (!modelUrl) {
    return NextResponse.json({ error: "No generated model to export." }, { status: 400 });
  }

  const meta = parseModelProcessingStage(project?.dentalModel?.processingStage ?? null);
  const format = (meta.format === "obj" ? "obj" : "glb") as "glb" | "obj";
  const preset = getExportPreset(target);

  try {
    const result = await exportMeshForPreset(modelUrl, format, preset, {
      validateOnly,
      outputFormat,
      scope,
    });

    if (validateOnly && "validation" in result) {
      return NextResponse.json({ validation: result.validation, preset: target });
    }

    if (!("buffer" in result)) {
      return NextResponse.json({ error: "Export failed." }, { status: 500 });
    }

    const safeTitle = (project?.title ?? "model").replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 64);
    const filename = `${safeTitle}-${target}.${result.extension}`;

    await trackResearchEvent({
      userId: user.id,
      projectId,
      eventType: "EXPORT_REQUESTED",
      metadata: {
        target,
        hapticRealism: preset.hapticRealism,
        triangleCount: result.validation.triangleCount,
        watertight: result.validation.watertight,
      },
    });

    return new NextResponse(new Uint8Array(result.buffer), {
      status: 200,
      headers: {
        "Content-Type": result.contentType,
        "Content-Disposition": `attachment; filename="${filename}"`,
        "X-Export-Watertight": String(result.validation.watertight),
        "X-Export-Triangles": String(result.validation.triangleCount),
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Export failed.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
