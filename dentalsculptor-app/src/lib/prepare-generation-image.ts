/** Provider input limits — fal interim; Modal TRELLIS prefers ~512–1536px longest side. */
const MAX_DIMENSION = 1536;
const MIN_DIMENSION = 256;
const MAX_BYTES = 4 * 1024 * 1024;
const JPEG_QUALITY = 0.88;

/** Wide aspect ratios often indicate full arch — single-tooth milestone warns only. */
const ARCH_ASPECT_THRESHOLD = 2.2;

export type GenerationImageWarning =
  | "aspect-may-be-full-arch"
  | "very-small-image"
  | "converted-to-jpeg";

export interface PreparedGenerationImage {
  file: File;
  warnings: GenerationImageWarning[];
  width: number;
  height: number;
}

const ALLOWED_MIME = new Set(["image/png", "image/jpeg", "image/jpg"]);

export function isAllowedGenerationImageType(type: string): boolean {
  return ALLOWED_MIME.has(type.toLowerCase());
}

/**
 * Downscale large clinical photos before upload so inference queues start sooner.
 * Applies light dental-oriented normalization (contrast stretch) when resizing.
 */
export async function prepareGenerationImageDetailed(
  file: File
): Promise<PreparedGenerationImage> {
  const warnings: GenerationImageWarning[] = [];

  if (!file.type.startsWith("image/")) {
    return { file, warnings, width: 0, height: 0 };
  }

  const bitmap = await createImageBitmap(file);
  const { width, height } = bitmap;

  if (Math.max(width, height) < MIN_DIMENSION) {
    warnings.push("very-small-image");
  }

  const aspect = Math.max(width, height) / Math.min(width, height);
  if (aspect >= ARCH_ASPECT_THRESHOLD) {
    warnings.push("aspect-may-be-full-arch");
  }

  const longest = Math.max(width, height);
  const needsResize = longest > MAX_DIMENSION;
  const likelyTooLarge = file.size > MAX_BYTES;
  const shouldNormalize =
    needsResize || likelyTooLarge || !isAllowedGenerationImageType(file.type);

  if (!shouldNormalize) {
    bitmap.close();
    return { file, warnings, width, height };
  }

  const scale = needsResize ? MAX_DIMENSION / longest : 1;
  const targetW = Math.max(1, Math.round(width * scale));
  const targetH = Math.max(1, Math.round(height * scale));

  const canvas = document.createElement("canvas");
  canvas.width = targetW;
  canvas.height = targetH;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    bitmap.close();
    return { file, warnings, width, height };
  }

  ctx.drawImage(bitmap, 0, 0, targetW, targetH);
  bitmap.close();

  applyLightDentalNormalization(ctx, targetW, targetH);

  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY);
  });

  if (!blob) {
    return { file, warnings, width, height };
  }

  if (file.type !== "image/jpeg") {
    warnings.push("converted-to-jpeg");
  }

  const baseName = file.name.replace(/\.[^.]+$/, "") || "dental-image";
  const prepared = new File([blob], `${baseName}.jpg`, { type: "image/jpeg" });
  return { file: prepared, warnings, width: targetW, height: targetH };
}

/** Simple contrast stretch — helps isolated teeth on grey clinical backgrounds. */
function applyLightDentalNormalization(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number
): void {
  const imageData = ctx.getImageData(0, 0, w, h);
  const { data } = imageData;
  let min = 255;
  let max = 0;
  for (let i = 0; i < data.length; i += 4) {
    const lum = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    if (lum < min) min = lum;
    if (lum > max) max = lum;
  }
  const range = max - min;
  if (range < 20) return;
  const scale = 255 / range;
  for (let i = 0; i < data.length; i += 4) {
    data[i] = clampByte((data[i] - min) * scale);
    data[i + 1] = clampByte((data[i + 1] - min) * scale);
    data[i + 2] = clampByte((data[i + 2] - min) * scale);
  }
  ctx.putImageData(imageData, 0, 0);
}

function clampByte(v: number): number {
  return Math.max(0, Math.min(255, Math.round(v)));
}

/**
 * Downscale large clinical photos before upload so fal queue + inference start sooner.
 * Returns the original file when already small enough.
 */
export async function prepareGenerationImage(file: File): Promise<File> {
  const { file: prepared } = await prepareGenerationImageDetailed(file);
  return prepared;
}
