import {
  getPublicStorageUrl,
  getStorageBucket,
  getSupabaseAdmin,
  isSupabaseStorageConfigured,
} from "@/lib/supabase-server";

export function generateAssetKey(userId: string, filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "bin";
  const safeName = filename.replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 64);
  return `users/${userId}/${Date.now()}-${safeName.endsWith(`.${ext}`) ? safeName : `${safeName}.${ext}`}`;
}

/**
 * Upload a file to Supabase Storage (primary) or return a local placeholder when unconfigured.
 * AWS S3 can be added later as an alternate backend.
 */
export async function uploadAsset(
  key: string,
  body: Buffer | Uint8Array,
  contentType: string
): Promise<string> {
  if (!isSupabaseStorageConfigured()) {
    console.warn("[storage] Supabase not configured — using local:// placeholder for", key);
    return `local://${key}`;
  }

  const supabase = getSupabaseAdmin();
  const bucket = getStorageBucket();

  const { error } = await supabase.storage.from(bucket).upload(key, body, {
    contentType,
    upsert: false,
  });

  if (error) {
    console.error("[storage] Supabase upload failed:", error.message);
    throw new Error(`Upload failed: ${error.message}`);
  }

  return getPublicStorageUrl(key);
}

/** Download URL — public bucket or signed URL for private buckets. */
export async function getAssetUrl(key: string, expiresIn = 3600): Promise<string> {
  if (!isSupabaseStorageConfigured()) {
    return `/api/upload/local?key=${encodeURIComponent(key)}`;
  }

  const supabase = getSupabaseAdmin();
  const bucket = getStorageBucket();

  // Try signed URL first (works for private buckets)
  const { data, error } = await supabase.storage.from(bucket).createSignedUrl(key, expiresIn);
  if (!error && data?.signedUrl) {
    return data.signedUrl;
  }

  return getPublicStorageUrl(key);
}

/** @deprecated Use uploadAsset — kept for imports during migration */
export const uploadToS3 = uploadAsset;
