/** Parse fetch bodies without throwing on empty or non-JSON responses. */
export async function readJsonResponse<T = Record<string, unknown>>(
  res: Response
): Promise<{ data: T | null; raw: string }> {
  const raw = await res.text();
  if (!raw.trim()) return { data: null, raw: "" };
  try {
    return { data: JSON.parse(raw) as T, raw };
  } catch {
    return { data: null, raw };
  }
}

export function jsonResponseError(
  res: Response,
  raw: string,
  fallback = "Unexpected server response."
): string {
  if (raw.trim()) return raw.slice(0, 200);
  return `${fallback} (HTTP ${res.status})`;
}
