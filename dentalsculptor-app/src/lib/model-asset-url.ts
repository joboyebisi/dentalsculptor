import { isSameOriginModelServeUrl } from "@/lib/project-model-path";

const PROXY_PATH = "/api/models/proxy";

/** Hosts we allow the server proxy to fetch (fal output + our storage). */
export const ALLOWED_MODEL_ASSET_HOSTS = [
  "fal.media",
  "fal.ai",
  "fal.run",
  "supabase.co",
  "amazonaws.com",
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
  if (url.startsWith(PROXY_PATH) || isSameOriginModelServeUrl(url)) return url;

  try {
    if (typeof window !== "undefined") {
      const parsed = new URL(url, window.location.origin);
      if (parsed.origin === window.location.origin) return url;
    }
  } catch {
    return url;
  }

  return `${PROXY_PATH}?url=${encodeURIComponent(url)}`;
}

export function guessModelContentType(url: string, format?: string | null): string {
  const lower = url.split("?")[0]?.toLowerCase() ?? "";
  if (lower.endsWith(".obj") || format === "obj") return "application/octet-stream";
  if (lower.endsWith(".mtl")) return "text/plain";
  if (lower.endsWith(".glb") || format === "glb") return "model/gltf-binary";
  if (lower.endsWith(".stl") || format === "stl") return "model/stl";
  return "application/octet-stream";
}

/** Map upstream MIME to Supabase bucket allowlist (see supabase/setup.sql). */
export function normalizeStorageContentType(contentType: string): string {
  const allowed = new Set([
    "image/jpeg",
    "image/png",
    "image/webp",
    "model/gltf-binary",
    "model/stl",
    "application/octet-stream",
    "text/plain",
  ]);
  const base = contentType.split(";")[0]?.trim().toLowerCase() ?? "application/octet-stream";
  if (allowed.has(base)) return base;
  if (base.startsWith("image/")) return base;
  if (base.startsWith("model/")) return "application/octet-stream";
  return "application/octet-stream";
}
