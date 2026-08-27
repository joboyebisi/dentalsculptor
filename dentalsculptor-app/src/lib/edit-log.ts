/** Structured logging for Nano3D edit jobs — grep `[edit]`. */

export type EditLogPhase =
  | "start"
  | "submit"
  | "poll"
  | "complete"
  | "failed"
  | "accept"
  | "reject";

export interface EditLogPayload {
  phase: EditLogPhase;
  projectId?: string;
  jobId?: string;
  operation?: string;
  durationMs?: number;
  httpStatus?: number;
  error?: string;
  detail?: string;
  stage?: string;
  progress?: number;
  maskedVertexRatio?: number;
  provider?: string;
  [key: string]: unknown;
}

export function logEdit(event: EditLogPayload): void {
  const { phase, error, ...rest } = event;
  const line = JSON.stringify({ phase, ...rest, ...(error ? { error } : {}) });
  if (phase === "failed") {
    console.error(`[edit] ${line}`);
  } else {
    console.info(`[edit] ${line}`);
  }
}

/** Client-side mirror for browser devtools. */
export function logEditClient(event: EditLogPayload): void {
  if (typeof window === "undefined") return;
  logEdit(event);
}

export function editErrorMessage(error: unknown, fallback = "Edit job failed."): string {
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export function formatEditProofDetail(input: {
  maskedVertexRatio?: number;
  regionMarkCount?: number;
  stage?: string;
}): string | null {
  const parts: string[] = [];
  if (input.stage) parts.push(`DentalSculptor ${input.stage}`);
  if (typeof input.maskedVertexRatio === "number") {
    const pct = (input.maskedVertexRatio * 100).toFixed(1);
    parts.push(
      input.maskedVertexRatio > 0
        ? `${pct}% mesh vertices in mask — deformation applied`
        : "0% vertices in mask — try repainting or adjusting the view"
    );
  }
  if (input.regionMarkCount) {
    parts.push(`${input.regionMarkCount} region mark${input.regionMarkCount === 1 ? "" : "s"}`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}
