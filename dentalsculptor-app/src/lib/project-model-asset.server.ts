import { GetObjectCommand } from "@aws-sdk/client-s3";
import {
  extractStorageKeyFromUrl,
  getS3AssetUrl,
  getS3Config,
  isS3BackendSelected,
  isS3StorageConfigured,
} from "@/lib/storage";
import {
  getPublicStorageUrl,
  getStorageBucket,
  getSupabaseAdmin,
  isSupabaseStorageConfigured,
} from "@/lib/supabase-server";
import { guessModelContentType, isAllowedModelAssetUrl } from "@/lib/model-asset-url";
import { projectModelServePath, communityModelServePath } from "@/lib/project-model-path";

export type ProjectModelRecord = {
  generated3DUrl?: string | null;
  generated3DKey?: string | null;
  processingStage?: string | null;
};

export function resolveProjectModelStorageKey(model: ProjectModelRecord | null | undefined): string | null {
  if (!model) return null;
  if (model.generated3DKey?.trim()) return model.generated3DKey.trim();
  if (model.generated3DUrl) {
    return extractStorageKeyFromUrl(model.generated3DUrl);
  }
  return null;
}

export async function streamProjectModelAsset(model: ProjectModelRecord | null | undefined): Promise<{
  body: ReadableStream | ArrayBuffer;
  contentType: string;
  cacheControl: string;
} | null> {
  const key = resolveProjectModelStorageKey(model);
  if (key) {
    return streamStorageObjectByKey(key);
  }

  const remoteUrl = model?.generated3DUrl?.trim();
  if (!remoteUrl || remoteUrl.startsWith("local://")) return null;
  if (remoteUrl.includes("supabase.co/storage/")) {
    const parsedKey = extractStorageKeyFromUrl(remoteUrl);
    if (parsedKey) return streamStorageObjectByKey(parsedKey);
  }
  if (!isAllowedModelAssetUrl(remoteUrl)) return null;

  const upstream = await fetch(remoteUrl, {
    headers: { "User-Agent": "DentalSculptor/1.0" },
    cache: "no-store",
    signal: AbortSignal.timeout(120_000),
  });
  if (!upstream.ok) return null;

  const format = parseModelFormatHint(model?.processingStage);
  const buffer = await upstream.arrayBuffer();
  return {
    body: buffer,
    contentType: upstream.headers.get("content-type") ?? guessModelContentType(remoteUrl, format),
    cacheControl: "private, max-age=300",
  };
}

function parseModelFormatHint(processingStage: string | null | undefined): string | null {
  if (!processingStage) return null;
  try {
    const parsed = JSON.parse(processingStage) as { format?: string };
    return parsed.format ?? null;
  } catch {
    return null;
  }
}

export async function streamStorageObjectByKey(key: string): Promise<{
  body: ReadableStream | ArrayBuffer;
  contentType: string;
  cacheControl: string;
} | null> {
  if (isS3BackendSelected() && isS3StorageConfigured()) {
    const { client, bucket } = getS3Config();
    const response = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key }));
    if (!response.Body) return null;
    const body = response.Body.transformToWebStream();
    return {
      body,
      contentType: response.ContentType ?? guessModelContentType(key, "glb"),
      cacheControl: "private, max-age=300",
    };
  }

  if (!isSupabaseStorageConfigured()) return null;
  const supabase = getSupabaseAdmin();
  const bucket = getStorageBucket();
  const { data, error } = await supabase.storage.from(bucket).download(key);
  if (error || !data) return null;
  return {
    body: data.stream(),
    contentType: data.type || guessModelContentType(key, "glb"),
    cacheControl: "public, max-age=86400",
  };
}

/** Fresh signed URL when streaming is not required (e.g. export links). */
export async function resolveProjectModelUrl(model: ProjectModelRecord | null | undefined): Promise<string | null> {
  const key = resolveProjectModelStorageKey(model);
  if (key) {
    if (isS3BackendSelected() && isS3StorageConfigured()) {
      return getS3AssetUrl(key);
    }
    if (isSupabaseStorageConfigured()) {
      return getPublicStorageUrl(key);
    }
  }
  return model?.generated3DUrl ?? null;
}

export { projectModelServePath, communityModelServePath };
