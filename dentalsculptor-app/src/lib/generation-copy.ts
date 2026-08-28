/** User-facing copy for 3D generation — no vendor or model names. */
export const GENERATION_COPY = {
  inProgressTitle: "Generating 3D model",
  inProgressDetail:
    "Reconstructing 3D anatomy from your photo — usually a few minutes on first use.",
  inProgressQueuedHint:
    "Preparing compute and loading the reconstruction model.",
  inProgressSlowHint:
    "First visit — loading the reconstruction model can take a few minutes. We started preparing compute when you opened this page; keep this tab open.",
  inProgressHint: "You can keep this tab open; we'll notify you when it's ready if you opt in below.",
  modelReadyHint:
    "Model ready — download an export or publish it. Create a teaching case only when you need one.",
  enhanceQualityLabel: "Enhance to full quality",
  enhancingQualityLabel: "Enhancing quality…",
  timeoutError:
    "Generation took longer than expected. Please try again; the model may now be warm and complete faster.",
  gatewayTimeoutError:
    "The server timed out before the 3D model finished. Retry in a moment — if this keeps happening, async GPU generation must be enabled on Vercel (MODAL_ASYNC_S3_ENABLED=true) and Modal redeployed with TRELLIS_ASYNC_S3_ENABLED=true.",
  serviceUnavailableError:
    "The reconstruction service is temporarily unavailable. Please wait a moment and try again.",
  notifyLabel: "Notify me when generation completes",
  notifyReadyTitle: "DentalSculptor",
  notifyReadyBody: "Your 3D model is ready to view.",
  notifyReadyBodyEditor: "Your 3D model is ready in the editor.",
  poseNotice:
    "The angle of your photo sets the 3D pose — rotate the image so the tooth faces the way you want it in the viewer, then generate.",
  completedIn: (seconds: number) => `Generated in ${seconds}s`,
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

/** Client poll budget — must exceed Modal GPU timeout (900s) plus cold start. */
export const GENERATION_POLL_INTERVAL_MS = 2500;
export const GENERATION_POLL_MAX_ATTEMPTS = 600;
