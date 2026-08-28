import { GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";
import { cardPreviewStorageKey } from "@/lib/project-card-preview-path";
import {
  getS3Config,
  isS3BackendSelected,
  isS3StorageConfigured,
} from "@/lib/storage";
import { normalizeStorageContentType } from "@/lib/model-asset-url";
import {
  getStorageBucket,
  getSupabaseAdmin,
  isSupabaseStorageConfigured,
} from "@/lib/supabase-server";

/** Card previews use a deterministic storage key — no DB column required. */
export async function saveProjectCardPreview(
  projectId: string,
  buffer: Buffer,
  contentType = "image/png"
): Promise<string> {
  const key = cardPreviewStorageKey(projectId);

  if (isS3BackendSelected() && isS3StorageConfigured()) {
    const { client, bucket } = getS3Config();
    await client.send(
      new PutObjectCommand({
        Bucket: bucket,
        Key: key,
        Body: buffer,
        ContentType: normalizeStorageContentType(contentType),
        ServerSideEncryption: "AES256",
      })
    );
  } else if (isSupabaseStorageConfigured()) {
    const supabase = getSupabaseAdmin();
    const bucket = getStorageBucket();
    const { error } = await supabase.storage.from(bucket).upload(key, buffer, {
      contentType: normalizeStorageContentType(contentType),
      upsert: true,
    });
    if (error) throw new Error(`Preview upload failed: ${error.message}`);
  } else {
    throw new Error("Storage is not configured for card previews.");
  }

  return key;
}

export async function streamProjectCardPreview(projectId: string): Promise<{
  body: ReadableStream | ArrayBuffer;
  contentType: string;
} | null> {
  const key = cardPreviewStorageKey(projectId);

  if (isS3BackendSelected() && isS3StorageConfigured()) {
    try {
      const { client, bucket } = getS3Config();
      const response = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key }));
      if (!response.Body) return null;
      return {
        body: response.Body.transformToWebStream(),
        contentType: response.ContentType ?? "image/png",
      };
    } catch {
      return null;
    }
  }

  if (!isSupabaseStorageConfigured()) return null;
  const supabase = getSupabaseAdmin();
  const bucket = getStorageBucket();
  const { data, error } = await supabase.storage.from(bucket).download(key);
  if (error || !data) return null;
  return {
    body: data.stream(),
    contentType: data.type || "image/png",
  };
}

export async function projectHasCardPreview(projectId: string): Promise<boolean> {
  const key = cardPreviewStorageKey(projectId);
  if (isS3BackendSelected() && isS3StorageConfigured()) {
    try {
      const { client, bucket } = getS3Config();
      const response = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key }));
      return Boolean(response.Body);
    } catch {
      return false;
    }
  }

  if (!isSupabaseStorageConfigured()) return false;
  const supabase = getSupabaseAdmin();
  const bucket = getStorageBucket();
  const folder = key.split("/").slice(0, -1).join("/");
  const filename = key.split("/").pop() ?? "";
  const { data, error } = await supabase.storage.from(bucket).list(folder, {
    search: filename,
    limit: 1,
  });
  return !error && Boolean(data?.some((item) => item.name === filename));
}
