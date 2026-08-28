export type ProjectPreviewSources = {
  id: string;
  thumbnailUrl?: string | null;
  dentalModel?: {
    sourceImageUrl?: string | null;
    thumbnailUrl?: string | null;
    previewImageKey?: string | null;
    generated3DUrl?: string | null;
    generated3DKey?: string | null;
    meshData?: unknown;
  } | null;
};

function projectHasGeneratedModel(project: ProjectPreviewSources): boolean {
  const model = project.dentalModel;
  if (!model) return false;
  return Boolean(model.generated3DKey || model.generated3DUrl || model.meshData);
}

/** Same-origin PNG of the 3D viewport capture for project cards. */
export function getProjectPreviewImageUrl(project: ProjectPreviewSources): string | null {
  if (!project.id) return null;
  if (project.dentalModel?.previewImageKey || projectHasGeneratedModel(project)) {
    return `/api/projects/${project.id}/preview-image`;
  }
  const staticThumb = project.dentalModel?.thumbnailUrl ?? project.thumbnailUrl;
  if (staticThumb?.startsWith("/")) return staticThumb;
  return null;
}

export function getCommunityPreviewImageUrl(project: {
  id: string;
  thumbnailUrl?: string | null;
  dentalModel?: {
    previewImageKey?: string | null;
    thumbnailUrl?: string | null;
    generated3DUrl?: string | null;
    generated3DKey?: string | null;
    meshData?: unknown;
  } | null;
}): string | null {
  if (!project.id) return null;
  const model = project.dentalModel;
  if (model?.previewImageKey || model?.generated3DKey || model?.generated3DUrl || model?.meshData) {
    return `/api/community/${project.id}/preview-image`;
  }
  const staticThumb = model?.thumbnailUrl ?? project.thumbnailUrl;
  if (staticThumb?.startsWith("/")) return staticThumb;
  return null;
}
