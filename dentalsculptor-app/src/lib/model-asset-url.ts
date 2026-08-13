const PROXY_PATH = "/api/models/proxy";

/** Hosts we allow the server proxy to fetch (fal output + our storage). */
export const ALLOWED_MODEL_ASSET_HOSTS = [
  "fal.media",
  "fal.ai",
  "fal.run",
  "supabase.co",
] as const;

export function isAllowedModelAssetUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return ALLOWED_MODEL_ASSET_HOSTS.some(
      (host) => parsed.hostname === host || parsed.hostname.endsWith(`.${host}`)
    );
  } catch {
    return false;
  }
}

/** Same-origin URL for browser loaders (avoids CORS on fal.media). */
export function resolveModelFetchUrl(url: string): string {
  if (!url || url.startsWith("local://") || url.startsWith("blob:")) return url;
  if (url.startsWith(PROXY_PATH)) return url;

  try {
    if (typeof window !== "undefined") {
      const parsed = new URL(url, window.location.origin);
      if (parsed.origin === window.location.origin) return url;
      if (parsed.hostname.endsWith("supabase.co")) return url;
    }
  } catch {
    return url;
  }

  return `${PROXY_PATH}?url=${encodeURIComponent(url)}`;
}

export function guessModelContentType(url: string, format?: string | null): string {
  const lower = url.split("?")[0]?.toLowerCase() ?? "";
  if (lower.endsWith(".obj") || format === "obj") return "model/obj";
  if (lower.endsWith(".mtl")) return "model/mtl";
  if (lower.endsWith(".glb") || format === "glb") return "model/gltf-binary";
  return "application/octet-stream";
}
