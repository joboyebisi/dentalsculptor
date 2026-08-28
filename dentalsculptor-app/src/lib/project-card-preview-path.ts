/** Deterministic storage key for a project's 3D viewport card preview. */
export function cardPreviewStorageKey(projectId: string): string {
  return `projects/${projectId}/card-preview.png`;
}

export function projectPreviewServePath(projectId: string): string {
  return `/api/projects/${projectId}/preview-image`;
}

export function communityPreviewServePath(projectId: string): string {
  return `/api/community/${projectId}/preview-image`;
}

export function isCardPreviewServeUrl(url: string): boolean {
  return (
    (url.includes("/api/projects/") && url.endsWith("/preview-image")) ||
    (url.includes("/api/community/") && url.endsWith("/preview-image"))
  );
}
