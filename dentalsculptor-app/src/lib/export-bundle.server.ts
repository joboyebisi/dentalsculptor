/**
 * Build teaching / multi-asset export ZIP archives.
 */

import JSZip from "jszip";
import type { ExportAssetId } from "@/lib/export-asset-options";

export interface ExportBundleFile {
  path: string;
  buffer: Buffer;
}

export async function buildExportZip(files: ExportBundleFile[]): Promise<Buffer> {
  if (files.length === 0) {
    throw new Error("Export bundle has no files.");
  }
  const zip = new JSZip();
  for (const file of files) {
    zip.file(file.path, file.buffer);
  }
  return Buffer.from(await zip.generateAsync({ type: "arraybuffer", compression: "DEFLATE" }));
}

export function bundleFilename(projectTitle: string, target: string): string {
  const safe = projectTitle.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 64);
  return `${safe}-${target}-bundle.zip`;
}

export function assetFilename(
  projectTitle: string,
  assetId: ExportAssetId,
  extension: string
): string {
  const safe = projectTitle.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 48);
  const suffix: Record<ExportAssetId, string> = {
    "mesh-primary": "tooth",
    "mesh-stl": "tooth-backup",
    "source-photo": "source-photo",
    "reference-glb": "reference",
    "jaw-lower": "jaw-lower",
    "jaw-upper": "jaw-upper",
    readme: "README",
  };
  return `${safe}-${suffix[assetId]}.${extension}`;
}
