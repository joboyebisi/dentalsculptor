/** Structured server-side logging for mesh generation — grep `[generation]`. */

export type GenerationLogPhase =
  | "start"
  | "accepted"
  | "complete"
  | "failed"
  | "fallback"
  | "poll"
  | "finalize";

export interface GenerationLogPayload {
  traceId: string;
  phase: GenerationLogPhase;
  provider?: string;
  jobId?: string;
  quality?: string;
  durationMs?: number;
  httpStatus?: number;
  error?: string;
  detail?: string;
  upstream?: string;
  [key: string]: unknown;
}

export function logGeneration(event: GenerationLogPayload): void {
  const { phase, traceId, error, ...rest } = event;
  const line = JSON.stringify({ phase, traceId, ...rest, ...(error ? { error } : {}) });
  if (phase === "failed") {
    console.error(`[generation] ${line}`);
  } else {
    console.info(`[generation] ${line}`);
  }
}

/** User-safe message; dev builds may include trace id for support. */
export function generationErrorMessage(
  error: unknown,
  traceId: string,
  fallback = "The 3D reconstruction service could not complete this request. Please try again."
): string {
  if (!(error instanceof Error)) return fallback;
  const msg = error.message.trim();
  if (msg.startsWith("The tooth could not be isolated")) return msg;
  if (process.env.NODE_ENV === "development") {
    return `${fallback} (trace: ${traceId.slice(0, 8)} — see terminal for [generation] logs)`;
  }
  return fallback;
}
