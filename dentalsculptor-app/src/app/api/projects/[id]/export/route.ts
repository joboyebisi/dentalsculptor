import { NextRequest, NextResponse } from "next/server";
import "@/lib/ensure-browser-globals";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { getExportPreset, type ExportTarget } from "@/lib/export-presets";
import { exportMeshForPreset, type ExportScope, type MeshExportFormat } from "@/lib/export-mesh";
import { trackResearchEvent } from "@/lib/research-events";
import { parseModelProcessingStage } from "@/lib/model-processing-stage";
import type { ExportAssetId } from "@/lib/export-asset-options";
import { buildProjectExportBundle } from "@/lib/build-export-bundle.server";
import { resolveProjectModelUrl } from "@/lib/project-model-asset.server";

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
  const assets = (body.assets as ExportAssetId[] | undefined) ?? ["mesh-primary"];
  const bundle = Boolean(body.bundle);

  if (!target) {
    return NextResponse.json({ error: "target is required." }, { status: 400 });
  }

  const project = await prisma.project.findFirst({
    where: { id: projectId, ownerId: user.id },
    include: { dentalModel: true },
  });

  if (!project) {
    return NextResponse.json({ error: "Project not found." }, { status: 404 });
  }

  // Never pass the browser's same-origin `/api/projects/.../model` path to
  // server-side loaders. Resolve a fresh URL from the authenticated project
  // record, which also avoids expired signed URLs and arbitrary URL fetching.
  const modelUrl = await resolveProjectModelUrl(project.dentalModel);

  if (!modelUrl) {
    return NextResponse.json({ error: "No generated model to export." }, { status: 400 });
  }

  const meta = parseModelProcessingStage(project?.dentalModel?.processingStage ?? null);
  const format = (meta.format === "obj" ? "obj" : "glb") as "glb" | "obj";
  const preset = getExportPreset(target);
  const resolvedFormat: MeshExportFormat =
    outputFormat ?? (preset.formats.find((f) => f !== "zip") as MeshExportFormat) ?? "stl";

  try {
    if (validateOnly) {
      const result = await exportMeshForPreset(modelUrl, format, preset, {
        validateOnly: true,
        outputFormat: resolvedFormat,
        scope,
      });
      if ("validation" in result) {
        return NextResponse.json({ validation: result.validation, preset: target });
      }
      return NextResponse.json({ error: "Validation failed." }, { status: 500 });
    }

    const useBundle =
      bundle ||
      assets.length > 1 ||
      assets.includes("source-photo") ||
      assets.includes("reference-glb") ||
      assets.includes("readme") ||
      assets.includes("mesh-stl") ||
      target === "teaching-bundle";

    if (useBundle) {
      const bundleResult = await buildProjectExportBundle({
        projectTitle: project.title,
        target,
        modelUrl,
        modelFormat: format,
        outputFormat: resolvedFormat,
        scope,
        assets: assets.includes("mesh-primary") ? assets : ["mesh-primary", ...assets],
        sourceImageUrl: project.dentalModel?.sourceImageUrl,
      });

      await trackResearchEvent({
        userId: user.id,
        projectId,
        eventType: "EXPORT_REQUESTED",
        metadata: {
          target,
          bundle: true,
          assets,
          hapticRealism: preset.hapticRealism,
        },
      });

      return new NextResponse(new Uint8Array(bundleResult.buffer), {
        status: 200,
        headers: {
          "Content-Type": bundleResult.contentType,
          "Content-Disposition": `attachment; filename="${bundleResult.filename}"`,
        },
      });
    }

    const result = await exportMeshForPreset(modelUrl, format, preset, {
      outputFormat: resolvedFormat,
      scope,
    });

    if (!("buffer" in result)) {
      return NextResponse.json({ error: "Export failed." }, { status: 500 });
    }

    const safeTitle = project.title.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 64);
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
        boundingBoxMm: result.validation.boundingBoxMm,
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
