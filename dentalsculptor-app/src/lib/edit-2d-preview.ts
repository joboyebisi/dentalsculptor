/** Client-side masked 2D preview — mirrors Modal nano3d_utils stub inpaint. */

export async function applyMasked2dPreview(
  referenceBlob: Blob,
  maskBlob: Blob | null,
  operation: "add" | "remove" | "replace"
): Promise<Blob> {
  const refBitmap = await createImageBitmap(referenceBlob);
  const canvas = document.createElement("canvas");
  canvas.width = refBitmap.width;
  canvas.height = refBitmap.height;
  const ctx = canvas.getContext("2d");
  if (!ctx) return referenceBlob;

  ctx.drawImage(refBitmap, 0, 0);
  refBitmap.close();

  if (!maskBlob) {
    return new Promise((resolve) => canvas.toBlob((b) => resolve(b ?? referenceBlob), "image/png"));
  }

  const maskBitmap = await createImageBitmap(maskBlob);
  const maskCanvas = document.createElement("canvas");
  maskCanvas.width = canvas.width;
  maskCanvas.height = canvas.height;
  const maskCtx = maskCanvas.getContext("2d");
  if (!maskCtx) {
    maskBitmap.close();
    return new Promise((resolve) => canvas.toBlob((b) => resolve(b ?? referenceBlob), "image/png"));
  }
  maskCtx.drawImage(maskBitmap, 0, 0, canvas.width, canvas.height);
  maskBitmap.close();

  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const maskData = maskCtx.getImageData(0, 0, canvas.width, canvas.height);
  const px = imageData.data;
  const mx = maskData.data;

  for (let i = 0; i < px.length; i += 4) {
    if (mx[i]! < 128) continue;
    if (operation === "remove") {
      px[i] = Math.round(px[i]! * 0.72);
      px[i + 1] = Math.round(px[i + 1]! * 0.72);
      px[i + 2] = Math.round(px[i + 2]! * 0.72);
    } else if (operation === "add") {
      px[i] = Math.min(255, Math.round(px[i]! * 1.12 + 18));
      px[i + 1] = Math.min(255, Math.round(px[i + 1]! * 1.12 + 18));
      px[i + 2] = Math.min(255, Math.round(px[i + 2]! * 1.12 + 18));
    } else {
      px[i] = Math.min(255, Math.round(px[i]! * 0.95 + 12));
      px[i + 1] = Math.min(255, Math.round(px[i + 1]! * 0.95 + 12));
      px[i + 2] = Math.min(255, Math.round(px[i + 2]! * 0.95 + 12));
    }
  }

  ctx.putImageData(imageData, 0, 0);
  return new Promise((resolve) => canvas.toBlob((b) => resolve(b ?? referenceBlob), "image/png"));
}
