import {
  getPublicStorageUrl,
  getStorageBucket,
  getSupabaseAdmin,
  isSupabaseStorageConfigured,
} from "@/lib/supabase-server";
import { normalizeStorageContentType } from "@/lib/model-asset-url";
import { GetObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

function getS3Config(): { client: S3Client; bucket: string } {
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
