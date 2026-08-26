/** Client-side masked 2D preview — mirrors Modal nano3d_utils stub inpaint with clinical cues. */

export type Preview2dMode = "add" | "remove" | "replace";

export async function applyMasked2dPreview(
  referenceBlob: Blob,
  maskBlob: Blob | null,
  operation: Preview2dMode,
  instruction = ""
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
  const lowerInstruction = instruction.toLowerCase();

  const isFracture =
    lowerInstruction.includes("fracture") ||
    lowerInstruction.includes("cusp") ||
    lowerInstruction.includes("chip");
  const isCaries =
    lowerInstruction.includes("caries") ||
    lowerInstruction.includes("cavity") ||
    lowerInstruction.includes("decay");

  for (let i = 0; i < px.length; i += 4) {
    if (mx[i]! < 128) continue;
    const x = (i / 4) % canvas.width;
    const y = Math.floor(i / 4 / canvas.width);

    if (operation === "remove" || isCaries) {
      px[i] = Math.round(px[i]! * 0.35 + 18);
      px[i + 1] = Math.round(px[i + 1]! * 0.32 + 12);
      px[i + 2] = Math.round(px[i + 2]! * 0.28 + 8);
    } else if (operation === "add") {
      px[i] = Math.min(255, Math.round(px[i]! * 1.05 + 38));
      px[i + 1] = Math.min(255, Math.round(px[i + 1]! * 1.02 + 22));
      px[i + 2] = Math.min(255, Math.round(px[i + 2]! * 0.9 + 10));
    } else {
      px[i] = Math.min(255, Math.round(px[i]! * 0.78 + 42));
      px[i + 1] = Math.min(255, Math.round(px[i + 1]! * 0.82 + 28));
      px[i + 2] = Math.min(255, Math.round(px[i + 2]! * 0.88 + 18));
    }

    if (isFracture && y > canvas.height * 0.35) {
      const edgeNoise = ((x * 7 + y * 13) % 5) - 2;
      const fractureLine = Math.abs((x + edgeNoise) % 24 - 12) < 2;
      if (fractureLine || y > canvas.height * 0.72) {
        px[i] = Math.min(255, px[i]! + 35);
        px[i + 1] = Math.min(255, px[i + 1]! + 28);
        px[i + 2] = Math.min(255, px[i + 2]! + 22);
      }
    }
  }

  ctx.putImageData(imageData, 0, 0);

  // Fracture gap line across masked bbox
  if (isFracture) {
    ctx.save();
    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = "rgba(40, 30, 25, 0.75)";
    ctx.lineWidth = Math.max(2, canvas.width * 0.004);
    ctx.beginPath();
    const startX = canvas.width * 0.42;
    const startY = canvas.height * 0.55;
    ctx.moveTo(startX, startY);
    ctx.lineTo(canvas.width * 0.58, canvas.height * 0.78);
    ctx.stroke();
    ctx.restore();
  }

  return new Promise((resolve) => canvas.toBlob((b) => resolve(b ?? referenceBlob), "image/png"));
}
