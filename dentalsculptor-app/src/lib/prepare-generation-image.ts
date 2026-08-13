/** fal.ai input limits — see Hunyuan 3D docs (max ~8MB, 128–5000px). */
const MAX_DIMENSION = 1536;
const MAX_BYTES = 4 * 1024 * 1024;
const JPEG_QUALITY = 0.88;

/**
 * Downscale large clinical photos before upload so fal queue + inference start sooner.
 * Returns the original file when already small enough.
 */
export async function prepareGenerationImage(file: File): Promise<File> {
  if (!file.type.startsWith("image/")) return file;
  if (file.size <= MAX_BYTES / 2 && !file.type.includes("png")) {
    // Small JPEG/WebP — likely fine; still check dimensions below.
  }

  const bitmap = await createImageBitmap(file);
  const { width, height } = bitmap;

  const longest = Math.max(width, height);
  const needsResize = longest > MAX_DIMENSION;
  const likelyTooLarge = file.size > MAX_BYTES;

  if (!needsResize && !likelyTooLarge) {
    bitmap.close();
    return file;
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
    return file;
  }

  ctx.drawImage(bitmap, 0, 0, targetW, targetH);
  bitmap.close();

  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY);
  });

  if (!blob) return file;

  const baseName = file.name.replace(/\.[^.]+$/, "") || "dental-image";
  return new File([blob], `${baseName}.jpg`, { type: "image/jpeg" });
}
