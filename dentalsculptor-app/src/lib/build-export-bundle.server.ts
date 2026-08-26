/**
 * Assemble multi-asset export bundles from project data.
 */

import type { ExportAssetId } from "@/lib/export-asset-options";
import { buildExportReadme } from "@/lib/export-readme";
import type { CaseRecipe } from "@/lib/clinical-case-params";
import type { CaseTemplate } from "@/lib/case-templates";
import type { ExportTarget } from "@/lib/export-presets";
import { getExportPreset } from "@/lib/export-presets";
import {
  assetFilename,
  buildExportZip,
  type ExportBundleFile,
} from "@/lib/export-bundle.server";
import {
  exportMeshForPreset,
  type ExportScope,
  type MeshExportFormat,
} from "@/lib/export-mesh";

async function fetchRemoteBuffer(url: string): Promise<Buffer> {
  const res = await fetch(url, {
    headers: { "User-Agent": "DentalSculptor-Export/1.0" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Could not fetch asset (${res.status}).`);
  }
  return Buffer.from(await res.arrayBuffer());
}

function photoExtension(url: string): string {
  const lower = url.split("?")[0]?.toLowerCase() ?? "";
  if (lower.endsWith(".png")) return "png";
  if (lower.endsWith(".webp")) return "webp";
  return "jpg";
}

export async function buildProjectExportBundle(input: {
  projectTitle: string;
  target: ExportTarget;
  modelUrl: string;
  modelFormat: "glb" | "obj";
  outputFormat: MeshExportFormat;
  scope: ExportScope;
  assets: ExportAssetId[];
  sourceImageUrl?: string | null;
  selectedCase?: CaseTemplate | null;
  caseRecipe?: CaseRecipe | null;
}): Promise<{ buffer: Buffer; filename: string; contentType: string }> {
  const preset = getExportPreset(input.target);
  const files: ExportBundleFile[] = [];
  const want = new Set(input.assets);

  if (want.has("mesh-primary") || input.assets.length === 0) {
    const primary = await exportMeshForPreset(input.modelUrl, input.modelFormat, preset, {
      outputFormat: input.outputFormat,
      scope: input.scope,
    });
    if (!("buffer" in primary)) throw new Error("Primary mesh export failed.");
    files.push({
      path: assetFilename(input.projectTitle, "mesh-primary", primary.extension),
      buffer: primary.buffer,
    });
  }

  if (want.has("mesh-stl") && input.outputFormat !== "stl") {
    const stl = await exportMeshForPreset(input.modelUrl, input.modelFormat, preset, {
      outputFormat: "stl",
      scope: input.scope,
    });
    if ("buffer" in stl) {
      files.push({
        path: assetFilename(input.projectTitle, "mesh-stl", "stl"),
        buffer: stl.buffer,
      });
    }
  }

  if (want.has("reference-glb") && input.modelFormat === "glb") {
    files.push({
      path: assetFilename(input.projectTitle, "reference-glb", "glb"),
      buffer: await fetchRemoteBuffer(input.modelUrl),
    });
  }

  if (want.has("source-photo") && input.sourceImageUrl) {
    const ext = photoExtension(input.sourceImageUrl);
    files.push({
      path: assetFilename(input.projectTitle, "source-photo", ext),
      buffer: await fetchRemoteBuffer(input.sourceImageUrl),
    });
  }

  if (want.has("readme")) {
    files.push({
      path: assetFilename(input.projectTitle, "readme", "txt"),
      buffer: Buffer.from(
        buildExportReadme({
          projectTitle: input.projectTitle,
          target: input.target,
          outputFormat: input.outputFormat,
          caseRecipe: input.caseRecipe ?? null,
          selectedCase: input.selectedCase ?? null,
        }),
        "utf-8"
      ),
    });
  }

  if (files.length === 0) {
    throw new Error("No export assets selected.");
  }

  if (files.length === 1) {
    const only = files[0]!;
    const ext = only.path.split(".").pop() ?? "bin";
    return {
      buffer: only.buffer,
      filename: only.path,
      contentType:
        ext === "stl"
          ? "model/stl"
          : ext === "glb"
            ? "model/gltf-binary"
            : ext === "txt"
              ? "text/plain"
              : "application/octet-stream",
    };
  }

  const zip = await buildExportZip(files);
  const safe = input.projectTitle.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 64);
  return {
    buffer: zip,
    filename: `${safe}-${input.target}-bundle.zip`,
    contentType: "application/zip",
  };
}
