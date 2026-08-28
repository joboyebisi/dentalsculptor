/** Upload a client-captured 3D viewport preview for project cards. */
export async function uploadProjectPreviewImage(
  projectId: string,
  image: Blob,
  filename = "preview.png"
): Promise<boolean> {
  const formData = new FormData();
  formData.append("previewImage", image, filename);
  const res = await fetch(`/api/projects/${projectId}/preview-image`, {
    method: "POST",
    body: formData,
  });
  return res.ok;
}

export async function captureAndUploadCardPreview(
  projectId: string,
  capture: () => Promise<Blob | null>,
  options?: { delayMs?: number; retries?: number }
): Promise<boolean> {
  const delayMs = options?.delayMs ?? 500;
  const retries = options?.retries ?? 3;

  for (let attempt = 0; attempt < retries; attempt += 1) {
    if (delayMs > 0) {
      await new Promise((resolve) => window.setTimeout(resolve, delayMs * (attempt + 1)));
    }
    const blob = await capture();
    if (!blob || blob.size < 512) continue;
    const ok = await uploadProjectPreviewImage(projectId, blob);
    if (ok) return true;
  }
  return false;
}
