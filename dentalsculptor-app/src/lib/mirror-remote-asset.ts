import { generateAssetKey, uploadAsset } from "@/lib/storage";
import { isAllowedModelAssetUrl, guessModelContentType } from "@/lib/model-asset-url";
import { isSupabaseStorageConfigured } from "@/lib/supabase-server";

/**
 * Copy a remote model/material URL (e.g. fal.media) into Supabase so the editor
 * loads a stable same-origin-friendly URL instead of an expiring third-party link.
 */
export async function mirrorRemoteAssetToStorage(
  remoteUrl: string,
  userId: string,
  filename: string,
  formatHint?: string | null
): Promise<string> {
  if (!isSupabaseStorageConfigured()) return remoteUrl;
  if (!remoteUrl || remoteUrl.startsWith("local://")) return remoteUrl;
  if (remoteUrl.includes("supabase.co/storage/")) return remoteUrl;
  if (!isAllowedModelAssetUrl(remoteUrl)) return remoteUrl;

  const res = await fetch(remoteUrl, {
    headers: { "User-Agent": "DentalSculptor/1.0" },
  });
  if (!res.ok) {
    throw new Error(`Could not download remote asset (${res.status})`);
  }

  const buffer = Buffer.from(await res.arrayBuffer());
  const contentType =
    res.headers.get("content-type") ?? guessModelContentType(remoteUrl, formatHint);
  const key = generateAssetKey(userId, filename);
  return uploadAsset(key, buffer, contentType);
}
