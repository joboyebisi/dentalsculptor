export function projectModelServePath(projectId: string): string {
  return `/api/projects/${projectId}/model`;
}

export function communityModelServePath(projectId: string): string {
  return `/api/community/${projectId}/model`;
}

/** True when the URL is already served same-origin (no CORS proxy needed). */
export function isSameOriginModelServeUrl(url: string): boolean {
  return (
    (url.startsWith("/api/projects/") && url.endsWith("/model")) ||
    (url.startsWith("/api/community/") && url.endsWith("/model"))
  );
}
