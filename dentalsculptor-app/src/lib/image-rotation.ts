/** Rotate an image file in 90° steps (client-side, before generation). */
export async function rotateImageFile(
  file: File,
  degrees: 90 | -90 | 180
): Promise<File> {
  const bitmap = await createImageBitmap(file);
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    bitmap.close();
    return file;
  }

  const swap = degrees === 90 || degrees === -90;
  canvas.width = swap ? bitmap.height : bitmap.width;
  canvas.height = swap ? bitmap.width : bitmap.height;

  ctx.translate(canvas.width / 2, canvas.height / 2);
  ctx.rotate((degrees * Math.PI) / 180);
  ctx.drawImage(bitmap, -bitmap.width / 2, -bitmap.height / 2);
  bitmap.close();

  const mime = file.type.startsWith("image/") ? file.type : "image/jpeg";
  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, mime === "image/png" ? "image/png" : "image/jpeg", 0.92);
  });

  if (!blob) return file;

  const baseName = file.name.replace(/\.[^.]+$/, "") || "dental-image";
  const ext = mime === "image/png" ? "png" : "jpg";
  return new File([blob], `${baseName}.${ext}`, { type: mime });
}
