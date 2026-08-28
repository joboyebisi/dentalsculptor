export type ProjectPreviewSources = {
  thumbnailUrl?: string | null;
  dentalModel?: {
    sourceImageUrl?: string | null;
    thumbnailUrl?: string | null;
  } | null;
};

/** Prefer a 2.5D viewport capture of the generated 3D model (not the source photo). */
export function getProjectPreviewImageUrl(project: ProjectPreviewSources): string | null {
  return project.dentalModel?.thumbnailUrl ?? project.thumbnailUrl ?? null;
}
