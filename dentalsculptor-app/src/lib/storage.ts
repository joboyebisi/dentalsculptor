import {
  getPublicStorageUrl,
  getStorageBucket,
  getSupabaseAdmin,
  isSupabaseStorageConfigured,
} from "@/lib/supabase-server";
import { normalizeStorageContentType } from "@/lib/model-asset-url";
import { GetObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

export function getS3Config(): { client: S3Client; bucket: string } {
  const bucket = process.env.AWS_S3_BUCKET?.trim();
  const region = process.env.AWS_REGION?.trim() || "eu-west-1";
  const accessKeyId = process.env.AWS_ACCESS_KEY_ID?.trim();
  const secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY?.trim();
  if (!bucket) throw new Error("AWS_S3_BUCKET is required for S3 storage.");
  return {
    client: new S3Client({
      region,
      ...(accessKeyId && secretAccessKey
        ? { credentials: { accessKeyId, secretAccessKey } }
        : {}),
    }),
    bucket,
  };
}

export function isS3BackendSelected(): boolean {
  return process.env.STORAGE_BACKEND?.toLowerCase() === "s3";
}

export function isS3StorageConfigured(): boolean {
  return Boolean(
    isS3BackendSelected() &&
      process.env.AWS_S3_BUCKET &&
      process.env.AWS_ACCESS_KEY_ID &&
      process.env.AWS_SECRET_ACCESS_KEY
  );
}

export async function getS3AssetUrl(
  key: string,
  expiresIn = 3600
): Promise<string> {
  const { client, bucket } = getS3Config();
  return getSignedUrl(client, new GetObjectCommand({ Bucket: bucket, Key: key }), {
    expiresIn,
  });
}

export function generateAssetKey(userId: string, filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "bin";
  const safeName = filename.replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 64);
  return `users/${userId}/${Date.now()}-${safeName.endsWith(`.${ext}`) ? safeName : `${safeName}.${ext}`}`;
}

/** Recover storage object key from a Supabase public/signed URL or S3 presigned URL. */
export function extractStorageKeyFromUrl(url: string): string | null {
  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname.toLowerCase();

    if (hostname.endsWith("supabase.co")) {
      const publicMatch = parsed.pathname.match(/\/storage\/v1\/object\/public\/[^/]+\/(.+)/);
      if (publicMatch?.[1]) return decodeURIComponent(publicMatch[1]);
      const signedMatch = parsed.pathname.match(/\/storage\/v1\/object\/sign\/[^/]+\/(.+)/);
      if (signedMatch?.[1]) return decodeURIComponent(signedMatch[1].split("?")[0] ?? signedMatch[1]);
    }

    if (hostname.includes("amazonaws.com")) {
      const bucket = process.env.AWS_S3_BUCKET?.trim();
      if (!bucket) return null;
      const hostParts = hostname.split(".");
      if (hostParts[0] === bucket && hostParts[1] === "s3") {
        const key = parsed.pathname.replace(/^\//, "");
        return key ? decodeURIComponent(key) : null;
      }
      const pathParts = parsed.pathname.replace(/^\//, "").split("/");
      if (pathParts[0] === bucket && pathParts.length > 1) {
        return decodeURIComponent(pathParts.slice(1).join("/"));
      }
    }
  } catch {
    return null;
  }
  return null;
}

/**
 * Upload a file to S3 (large 3D assets) or Supabase Storage (thumbnails / legacy).
 * Postgres metadata always lives in Supabase regardless of file backend.
 */
export async function uploadAsset(
  key: string,
  body: Buffer | Uint8Array,
  contentType: string
): Promise<string> {
  if (isS3BackendSelected()) {
    const { client, bucket } = getS3Config();
    await client.send(
      new PutObjectCommand({
        Bucket: bucket,
        Key: key,
        Body: body,
        ContentType: normalizeStorageContentType(contentType),
        ServerSideEncryption: "AES256",
      })
    );
    return getS3AssetUrl(key);
  }

  if (!isSupabaseStorageConfigured()) {
    console.warn("[storage] Supabase not configured — using local:// placeholder for", key);
    return `local://${key}`;
  }

  const supabase = getSupabaseAdmin();
  const bucket = getStorageBucket();
  const normalizedType = normalizeStorageContentType(contentType);

  const { error } = await supabase.storage.from(bucket).upload(key, body, {
    contentType: normalizedType,
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
  if (isS3BackendSelected()) {
    return getS3AssetUrl(key, expiresIn);
  }

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
