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
      px[i] = Math.round(px[i]! * 0.45);
      px[i + 1] = Math.round(px[i + 1]! * 0.45);
      px[i + 2] = Math.round(px[i + 2]! * 0.45);
      px[i] = Math.min(255, px[i]! + 8);
    } else if (operation === "add") {
      px[i] = Math.min(255, Math.round(px[i]! * 1.08 + 42));
      px[i + 1] = Math.min(255, Math.round(px[i + 1]! * 1.05 + 28));
      px[i + 2] = Math.min(255, Math.round(px[i + 2]! * 0.92 + 12));
    } else {
      px[i] = Math.min(255, Math.round(px[i]! * 0.82 + 36));
      px[i + 1] = Math.min(255, Math.round(px[i + 1]! * 0.88 + 24));
      px[i + 2] = Math.min(255, Math.round(px[i + 2]! * 0.95 + 18));
    }
  }

  ctx.putImageData(imageData, 0, 0);

  // Light purple tint on the edited region so the preview difference is obvious.
  const tinted = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const tx = tinted.data;
  for (let i = 0; i < tx.length; i += 4) {
    if (mx[i]! < 128) continue;
    tx[i] = Math.min(255, Math.round(tx[i]! * 0.88 + 124 * 0.12));
    tx[i + 1] = Math.min(255, Math.round(tx[i + 1]! * 0.88 + 58 * 0.12));
    tx[i + 2] = Math.min(255, Math.round(tx[i + 2]! * 0.88 + 237 * 0.12));
  }
  ctx.putImageData(tinted, 0, 0);

  return new Promise((resolve) => canvas.toBlob((b) => resolve(b ?? referenceBlob), "image/png"));
}
