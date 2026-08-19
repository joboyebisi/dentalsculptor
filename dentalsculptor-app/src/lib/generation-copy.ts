/** User-facing copy for 3D generation — no vendor or model names. */
export const GENERATION_COPY = {
  inProgressTitle: "Generating 3D model",
  inProgressDetail:
    "Building a fast preview first — warm runs usually finish in under a minute.",
  inProgressQueuedHint:
    "Preparing compute and loading the reconstruction model.",
  inProgressSlowHint:
    "Still processing. The first request after idle can take several minutes; keep this tab open.",
  inProgressHint: "You can keep this tab open; we'll notify you when it's ready if you opt in below.",
  previewReadyHint:
    "Preview ready. Enhance to full quality before export or teaching-case creation.",
  enhanceQualityLabel: "Enhance to full quality",
  enhancingQualityLabel: "Enhancing quality…",
  timeoutError:
    "Generation took longer than expected. Please try again; the model may now be warm and complete faster.",
  notifyLabel: "Notify me when generation completes",
  notifyReadyTitle: "DentalSculptor",
  notifyReadyBody: "Your 3D model is ready to view.",
  notifyReadyBodyEditor: "Your 3D model is ready in the editor.",
} as const;

/** Stage labels shown while polling async jobs. */
export const GENERATION_STAGE_LABELS: Record<string, string> = {
  queued: "Queued",
  starting: "Starting",
  preprocessing: "Preparing image",
  generating_shape: "Building shape",
  generating_material: "Applying surface detail",
  extracting_mesh: "Extracting mesh",
  uploading: "Saving result",
  completed: "Complete",
  failed: "Failed",
};

/** Allows for a cold GPU container plus first-time model download/load. */
export const GENERATION_FETCH_TIMEOUT_MS = 10 * 60_000;
