export type RemoteModelFormat = "glb" | "obj";

/** Infer model format from URL or explicit hint. */
export function detectModelFormat(
  url: string,
  hint?: string | null,
  mtlUrl?: string | null
): RemoteModelFormat {
  if (hint === "glb" || hint === "obj") return hint;
  if (mtlUrl) return "obj";
  const lower = url.split("?")[0]?.toLowerCase() ?? "";
  if (lower.endsWith(".obj")) return "obj";
  return "glb";
}
