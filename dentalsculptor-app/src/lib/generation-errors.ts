/** Detect Modal/async misconfiguration so the app can fall back or surface a clear fix. */

export function isModalAsyncDisabledError(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes("asynchronous s3 generation is disabled") ||
    lower.includes("async s3") && lower.includes("disabled")
  );
}

export function modalAsyncDisabledHint(): string {
  return (
    "Modal async S3 is off on the deployed worker. Redeploy with TRELLIS_ASYNC_S3_ENABLED=true " +
    "or set MODAL_ASYNC_S3_ENABLED=false locally to use sync generation."
  );
}
