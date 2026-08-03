import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
} from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

const s3Client = new S3Client({
  region: process.env.AWS_REGION ?? "eu-west-1",
  credentials: process.env.AWS_ACCESS_KEY_ID
    ? {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
      }
    : undefined,
});

const BUCKET = process.env.AWS_S3_BUCKET ?? "dentalsculptor-assets";
const CDN_URL = process.env.AWS_CLOUDFRONT_URL;

export async function uploadToS3(
  key: string,
  body: Buffer | Uint8Array,
  contentType: string
): Promise<string> {
  if (!process.env.AWS_ACCESS_KEY_ID) {
    return `local://${key}`;
  }

  await s3Client.send(
    new PutObjectCommand({
      Bucket: BUCKET,
      Key: key,
      Body: body,
      ContentType: contentType,
    })
  );

  return CDN_URL ? `${CDN_URL}/${key}` : `https://${BUCKET}.s3.amazonaws.com/${key}`;
}

export async function getPresignedUploadUrl(
  key: string,
  contentType: string,
  expiresIn = 3600
): Promise<string> {
  if (!process.env.AWS_ACCESS_KEY_ID) {
    return `/api/upload/local?key=${encodeURIComponent(key)}`;
  }

  const command = new PutObjectCommand({
    Bucket: BUCKET,
    Key: key,
    ContentType: contentType,
  });

  return getSignedUrl(s3Client, command, { expiresIn });
}

export async function getPresignedDownloadUrl(
  key: string,
  expiresIn = 3600
): Promise<string> {
  if (!process.env.AWS_ACCESS_KEY_ID) {
    return `/api/upload/local?key=${encodeURIComponent(key)}`;
  }

  const command = new GetObjectCommand({ Bucket: BUCKET, Key: key });
  return getSignedUrl(s3Client, command, { expiresIn });
}

export function generateAssetKey(userId: string, filename: string): string {
  const ext = filename.split(".").pop() ?? "bin";
  const timestamp = Date.now();
  return `users/${userId}/${timestamp}.${ext}`;
}
