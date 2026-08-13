/** Parse optional model metadata stored in DentalModel.processingStage. */
export function parseModelProcessingStage(processingStage?: string | null): {
  mtlUrl?: string;
  format?: "glb" | "obj";
} {
  if (!processingStage) return {};
  if (processingStage.startsWith("{")) {
    try {
      const parsed = JSON.parse(processingStage) as { mtlUrl?: string; format?: "glb" | "obj" };
      return { mtlUrl: parsed.mtlUrl, format: parsed.format };
    } catch {
      return {};
    }
  }
  return {};
}

export function serializeModelProcessingStage(meta: {
  mtlUrl?: string | null;
  format?: string | null;
}): string {
  return JSON.stringify({
    stage: "complete",
    mtlUrl: meta.mtlUrl ?? undefined,
    format: meta.format ?? undefined,
  });
}
