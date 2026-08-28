import { autoProjectTitle } from "@/lib/auto-project-title";
import type { PendingLandingProject } from "@/lib/landing-session";
import { dataUrlToFile } from "@/lib/landing-session";

export interface LandingProjectPayload {
  imageFile: File;
  modelUrl: string;
  modelKey?: string;
  previewImage?: Blob;
  thumbnailUrl?: string;
  mtlUrl?: string;
  format?: string;
  sourceFileName: string;
}

export function buildLandingProjectFormData(payload: LandingProjectPayload): FormData {
  const formData = new FormData();
  formData.append("title", autoProjectTitle(payload.sourceFileName));
  formData.append("image", payload.imageFile);
  formData.append("modelUrl", payload.modelUrl);
  if (payload.modelKey) formData.append("modelKey", payload.modelKey);
  if (payload.previewImage) {
    formData.append("previewImage", payload.previewImage, "preview.png");
  } else if (payload.thumbnailUrl) {
    formData.append("thumbnailUrl", payload.thumbnailUrl);
  }
  if (payload.mtlUrl) formData.append("mtlUrl", payload.mtlUrl);
  if (payload.format) formData.append("format", payload.format);
  return formData;
}

export async function createProjectFromLandingPayload(
  payload: LandingProjectPayload
): Promise<{ projectId: string }> {
  const res = await fetch("/api/projects", {
    method: "POST",
    body: buildLandingProjectFormData(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error ?? "Could not create project.");
  }
  return { projectId: data.project.id as string };
}

export function pendingToPayload(pending: PendingLandingProject): LandingProjectPayload {
  return {
    imageFile: dataUrlToFile(pending.imageDataUrl, pending.sourceFileName),
    modelUrl: pending.modelUrl,
    modelKey: pending.modelKey,
    thumbnailUrl: pending.thumbnailUrl,
    mtlUrl: pending.mtlUrl,
    format: pending.format,
    sourceFileName: pending.sourceFileName,
  };
}
