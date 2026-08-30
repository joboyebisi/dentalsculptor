import { GENERATION_COPY } from "@/lib/generation-copy";
import { logGeneration, type GenerationLogPhase } from "@/lib/generation-log";

/** Detect Modal/async misconfiguration (ops detail — never show verbatim to users). */
export function isModalAsyncDisabledError(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes("asynchronous s3 generation is disabled") ||
    (lower.includes("async s3") && lower.includes("disabled"))
  );
}

function isInfrastructureError(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    isModalAsyncDisabledError(message) ||
    lower.includes("modal_async") ||
    lower.includes("modal_generate") ||
    lower.includes("modal_job_status") ||
    lower.includes("aws_s3_bucket") ||
    lower.includes("not configured") ||
    lower.includes("http 503") ||
    lower.includes("http 502") ||
    lower.includes("job not found or expired") ||
    lower.includes("reconstruction service failed")
  );
}

function isColdStartFailure(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes("cuda") ||
    lower.includes("out of memory") ||
    lower.includes("oom") ||
    lower.includes("cold") ||
    lower.includes("timeout") ||
    lower.includes("timed out") ||
    lower.includes("container") ||
    lower.includes("starting")
  );
}

function isUserActionableError(message: string): boolean {
  return (
    message.startsWith("The tooth could not be isolated") ||
    message.startsWith("Could not isolate") ||
    message.includes("Image file is required") ||
    message.includes("Unsupported image")
  );
}

export type GenerationErrorContext = {
  traceId: string;
  phase?: GenerationLogPhase;
  jobId?: string;
  upstream?: string;
  httpStatus?: number;
};

/** Log the full internal error; return a short user-safe message. */
export function userFacingGenerationError(
  internalError: unknown,
  context: GenerationErrorContext
): string {
  const internal =
    internalError instanceof Error
      ? internalError.message.trim()
      : String(internalError ?? "Unknown generation error").trim();

  logGeneration({
    traceId: context.traceId,
    phase: context.phase ?? "failed",
    jobId: context.jobId,
    upstream: context.upstream,
    httpStatus: context.httpStatus,
    error: internal,
    detail: isModalAsyncDisabledError(internal)
      ? "Modal worker TRELLIS_ASYNC_S3_ENABLED=false — redeploy with deploy-scale-to-zero.ps1"
      : undefined,
  });

  if (isUserActionableError(internal)) return internal;

  if (isModalAsyncDisabledError(internal) || isInfrastructureError(internal)) {
    return GENERATION_COPY.serviceUnavailableError;
  }

  if (isColdStartFailure(internal)) {
    return GENERATION_COPY.coldStartRetryError;
  }

  if (process.env.NODE_ENV === "development") {
    return `${GENERATION_COPY.genericFailureError} (dev: ${internal.slice(0, 120)})`;
  }

  return GENERATION_COPY.genericFailureError;
}

export function generationErrorJson(
  internalError: unknown,
  context: GenerationErrorContext,
  status = 500
): { body: { error: string; traceId: string }; status: number } {
  return {
    body: {
      error: userFacingGenerationError(internalError, context),
      traceId: context.traceId,
    },
    status,
  };
}
