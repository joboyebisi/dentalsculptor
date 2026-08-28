import type { FalMeshResult } from "@/lib/fal-mesh-generator";
import { uploadAsset, generateAssetKey } from "@/lib/storage";

export type MeshGenerationResult = FalMeshResult;

export type MlMeshProvider = "fal" | "modal" | "mock";

export function getMlMeshProvider(): MlMeshProvider {
  const raw = process.env.ML_MESH_PROVIDER?.toLowerCase();
  if (raw === "modal" && isModalConfigured()) return "modal";
  if (raw === "mock") return "mock";
  if (process.env.FAL_KEY) return "fal";
  return "mock";
}

export function isModalConfigured(): boolean {
  return Boolean(
    process.env.MODAL_TOKEN_ID &&
      process.env.MODAL_TOKEN_SECRET &&
      process.env.MODAL_GENERATE_URL
  );
}

function modalFormat(format?: string): "glb" | "obj" {
  return format === "obj" ? "obj" : "glb";
}

export interface ModalGenerateResponse {
  jobId?: string;
  modelUrl?: string;
  thumbnailUrl?: string;
  format?: string;
  status?: "queued" | "running" | "completed" | "failed";
  stage?: string;
  progress?: number;
  resultKey?: string;
  error?: string;
  detail?: string;
  timings?: Record<string, number>;
  metrics?: Record<string, unknown>;
  quality?: "preview" | "standard" | "final";
}

export type ModalQuality = "preview" | "standard" | "final";

function modalQuality(value?: string): ModalQuality {
  return value === "preview" || value === "final" ? value : "standard";
}

export function hasModalAsyncEndpoints(): boolean {
  return Boolean(
    process.env.MODAL_GENERATE_ASYNC_URL && process.env.MODAL_JOB_STATUS_URL
  );
}

export function isModalAsyncS3Enabled(): boolean {
  if (!hasModalAsyncEndpoints()) return false;
  // Sync Modal generation exceeds Vercel limits — async is mandatory in production.
  if (process.env.VERCEL) return process.env.MODAL_ASYNC_S3_ENABLED !== "false";
  if (process.env.MODAL_ASYNC_S3_ENABLED === "true") return true;
  return false;
}

export function isServerlessHost(): boolean {
  return Boolean(process.env.VERCEL || process.env.AWS_LAMBDA_FUNCTION_NAME);
}

/** Spin up Modal GPU container (load model + optional CUDA warmup). Fire-and-forget. */
export async function warmModalGpu(): Promise<void> {
  const url =
    process.env.MODAL_WARM_GPU_URL ??
    process.env.MODAL_GENERATE_ASYNC_URL?.replace("generate-job", "warm-gpu");
  if (!url) throw new Error("MODAL_WARM_GPU_URL is not configured.");

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.MODAL_WEBHOOK_SECRET ?? ""}`,
    },
    signal: AbortSignal.timeout(15_000),
  });
  if (res.status !== 202 && !res.ok) {
    const text = await res.text();
    throw new Error(`Modal warm-gpu failed (${res.status}): ${text.slice(0, 200)}`);
  }
}

export async function finalizeModalGenerationJob(
  jobId: string,
  quality: ModalQuality = "standard",
  traceId?: string
): Promise<ModalGenerateResponse> {
  const url =
    process.env.MODAL_FINALIZE_ASYNC_URL ??
    process.env.MODAL_GENERATE_ASYNC_URL?.replace("generate-job", "finalize-job");
  if (!url) throw new Error("MODAL_FINALIZE_ASYNC_URL is not configured.");

  const formData = new FormData();
  formData.append("jobId", jobId);
  formData.append("quality", modalQuality(quality));
  if (traceId) formData.append("traceId", traceId);

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.MODAL_WEBHOOK_SECRET ?? ""}`,
    },
    body: formData,
    signal: AbortSignal.timeout(60_000),
  });
  const responseText = await res.text();
  let data: ModalGenerateResponse;
  try {
    data = JSON.parse(responseText) as ModalGenerateResponse;
  } catch {
    throw new Error(`The reconstruction service failed (${res.status}).`);
  }
  if (!res.ok) {
    throw new Error(data.error ?? data.detail ?? `Modal finalize failed (${res.status})`);
  }
  if (!data.jobId || data.status !== "queued") {
    throw new Error("Modal did not accept the finalize job.");
  }
  return data;
}

export async function createModalGenerationJob(
  image: File,
  jobId: string,
  options: { quality?: string; seed?: number; traceId?: string } = {}
): Promise<ModalGenerateResponse> {
  const url = process.env.MODAL_GENERATE_ASYNC_URL;
  if (!url) throw new Error("MODAL_GENERATE_ASYNC_URL is not configured.");

  const formData = new FormData();
  formData.append("image", image);
  formData.append("jobId", jobId);
  formData.append("quality", modalQuality(options.quality));
  formData.append("submittedAtMs", Date.now().toString());
  if (options.traceId) formData.append("traceId", options.traceId);
  if (Number.isInteger(options.seed) && (options.seed ?? -1) >= 0) {
    formData.append("seed", String(options.seed));
  }

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.MODAL_WEBHOOK_SECRET ?? ""}`,
    },
    body: formData,
    signal: AbortSignal.timeout(60_000),
  });
  const responseText = await res.text();
  let data: ModalGenerateResponse;
  try {
    data = JSON.parse(responseText) as ModalGenerateResponse;
  } catch {
    throw new Error(`The reconstruction service failed (${res.status}): ${responseText.slice(0, 200)}`);
  }
  if (!res.ok) {
    const detail = data.error ?? data.detail ?? `Modal generate failed (${res.status})`;
    throw new Error(`${detail} (HTTP ${res.status})`);
  }
  if (!data.jobId || data.status !== "queued") {
    throw new Error("Modal did not accept the generation job.");
  }
  return data;
}

/** Call deployed Modal web endpoint for TRELLIS generation. */
export async function generateMeshViaModal(
  image: File,
  userId = "anonymous",
  options: { quality?: string; seed?: number; traceId?: string } = {}
): Promise<MeshGenerationResult> {
  const url = process.env.MODAL_GENERATE_URL;
  if (!url) throw new Error("MODAL_GENERATE_URL is not configured.");

  const formData = new FormData();
  formData.append("image", image);
  formData.append("quality", modalQuality(options.quality));
  formData.append("submittedAtMs", Date.now().toString());
  if (options.traceId) formData.append("traceId", options.traceId);
  if (Number.isInteger(options.seed) && (options.seed ?? -1) >= 0) {
    formData.append("seed", String(options.seed));
  }

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.MODAL_WEBHOOK_SECRET ?? ""}`,
    },
    body: formData,
    signal: AbortSignal.timeout(600_000),
  });

  const responseText = await res.text();
  let data: ModalGenerateResponse & {
    modelBase64?: string;
    source?: string;
    pipelineType?: string;
    message?: string;
  };
  try {
    data = JSON.parse(responseText) as typeof data;
  } catch {
    throw new Error(
      res.ok
        ? "The reconstruction service returned an unreadable response."
        : `The reconstruction service failed (${res.status}).`
    );
  }
  if (!res.ok) {
    throw new Error(data.error ?? data.detail ?? `Modal generate failed (${res.status})`);
  }

  if (data.modelBase64) {
    const buffer = Buffer.from(data.modelBase64, "base64");
    const key = generateAssetKey(userId, `generate-${data.jobId ?? Date.now()}.glb`);
    const modelUrl = await uploadAsset(key, buffer, "model/gltf-binary");
    console.info(
      `[ml-provider] modal generate source=${data.source ?? "unknown"} pipeline=${data.pipelineType ?? "—"} quality=${data.quality ?? "standard"} timings=${JSON.stringify(data.timings ?? {})} metrics=${JSON.stringify(data.metrics ?? {})}`
    );
    return {
      modelUrl,
      modelKey: key,
      format: "glb",
      requestId: data.jobId,
    };
  }

  if (data.status === "queued" && data.jobId) {
    return pollModalJob(data.jobId);
  }

  if (!data.modelUrl) {
    throw new Error("Modal returned no model URL.");
  }

  return {
    modelUrl: data.modelUrl,
    thumbnailUrl: data.thumbnailUrl,
    format: modalFormat(data.format),
    requestId: data.jobId,
  };
}

async function pollModalJob(jobId: string, maxAttempts = 120): Promise<MeshGenerationResult> {
  const statusUrl = process.env.MODAL_JOB_STATUS_URL;
  if (!statusUrl) {
    throw new Error("MODAL_JOB_STATUS_URL required for async Modal jobs.");
  }

  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    const res = await fetch(`${statusUrl}?jobId=${encodeURIComponent(jobId)}`, {
      headers: { Authorization: `Bearer ${process.env.MODAL_WEBHOOK_SECRET ?? ""}` },
    });
    const data = (await res.json()) as ModalGenerateResponse;
    if (data.status === "completed" && data.modelUrl) {
      return {
        modelUrl: data.modelUrl,
        thumbnailUrl: data.thumbnailUrl,
        format: modalFormat(data.format),
        requestId: jobId,
      };
    }
    if (data.status === "failed") {
      throw new Error(data.error ?? "Modal job failed.");
    }
  }
  throw new Error("Modal job timed out.");
}
