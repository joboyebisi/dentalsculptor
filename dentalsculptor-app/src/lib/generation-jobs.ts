import {
  GENERATION_POLL_INTERVAL_MS,
  GENERATION_POLL_MAX_ATTEMPTS,
} from "@/lib/generation-copy";

export interface GenerationJobResult {
  jobId: string;
  status: "queued" | "running" | "completed" | "failed";
  stage?: string;
  progress?: number;
  quality?: string;
  canFinalize?: boolean;
  modelUrl?: string;
  modelKey?: string;
  format?: string;
  seed?: number;
  error?: string;
}

export type GenerationJobPollOptions = {
  intervalMs?: number;
  maxAttempts?: number;
  onUpdate?: (job: GenerationJobResult) => void;
};

export async function pollGenerationJob(
  jobId: string,
  jobToken: string,
  options: GenerationJobPollOptions = {}
): Promise<GenerationJobResult> {
  const intervalMs = options.intervalMs ?? GENERATION_POLL_INTERVAL_MS;
  const maxAttempts = options.maxAttempts ?? GENERATION_POLL_MAX_ATTEMPTS;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    if (attempt > 0) {
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
    const response = await fetch(
      `/api/generate/jobs/${encodeURIComponent(jobId)}`,
      {
        headers: { "x-generation-job-token": jobToken },
        cache: "no-store",
      }
    );
    const data = (await response.json()) as GenerationJobResult & {
      error?: string;
    };
    if (!response.ok) {
      throw new Error(data.error ?? "Generation status is unavailable.");
    }
    options.onUpdate?.(data);
    if (data.status === "completed") {
      if (!data.modelUrl) throw new Error("Completed job has no model URL.");
      return data;
    }
    if (data.status === "failed") {
      throw new Error(data.error ?? "Generation failed.");
    }
  }

  throw new Error("Generation job timed out.");
}

export async function finalizeGenerationJob(
  jobId: string,
  jobToken: string,
  quality: "standard" | "final" = "standard",
  options: GenerationJobPollOptions = {}
): Promise<GenerationJobResult> {
  const response = await fetch(
    `/api/generate/jobs/${encodeURIComponent(jobId)}/finalize`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-generation-job-token": jobToken,
      },
      body: JSON.stringify({ quality }),
    }
  );
  const data = (await response.json()) as GenerationJobResult & { error?: string };
  if (!response.ok) {
    throw new Error(data.error ?? "Could not start quality enhancement.");
  }
  return pollGenerationJob(jobId, jobToken, { intervalMs: 1500, ...options });
}
