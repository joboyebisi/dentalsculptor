/** Upload a client-captured 3D viewport preview for project cards. */
export async function uploadProjectPreviewImage(
  projectId: string,
  image: Blob,
  filename = "preview.png"
): Promise<string | null> {
  const formData = new FormData();
  formData.append("previewImage", image, filename);
  const res = await fetch(`/api/projects/${projectId}/preview-image`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { previewUrl?: string };
  return data.previewUrl ?? null;
}
