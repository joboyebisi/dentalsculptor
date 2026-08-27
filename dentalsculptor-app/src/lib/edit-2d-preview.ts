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

  const cornerSamples = [
    [px[0]!, px[1]!, px[2]!],
    [px[(canvas.width - 1) * 4]!, px[(canvas.width - 1) * 4 + 1]!, px[(canvas.width - 1) * 4 + 2]!],
  ];
  const background = [0, 1, 2].map((channel) =>
    Math.round(cornerSamples.reduce((sum, sample) => sum + sample[channel]!, 0) / cornerSamples.length)
  );

  for (let i = 0; i < px.length; i += 4) {
    if (mx[i]! < 128) continue;
    const x = (i / 4) % canvas.width;
    const y = Math.floor(i / 4 / canvas.width);

    if (isFracture && operation === "remove") {
      // A fracture preview must show actual missing silhouette, not merely a
      // darkened tooth. Replace the painted fragment with the viewer background
      // and retain a narrow dark irregular boundary at the surviving enamel.
      const left = x > 0 ? i - 4 : i;
      const right = x < canvas.width - 1 ? i + 4 : i;
      const up = y > 0 ? i - canvas.width * 4 : i;
      const down = y < canvas.height - 1 ? i + canvas.width * 4 : i;
      const boundary = mx[left]! < 128 || mx[right]! < 128 || mx[up]! < 128 || mx[down]! < 128;
      const jitter = ((x * 17 + y * 31) % 11) < 3;
      if (boundary && jitter) {
        px[i] = 56; px[i + 1] = 48; px[i + 2] = 44;
      } else {
        px[i] = background[0]!; px[i + 1] = background[1]!; px[i + 2] = background[2]!;
      }
    } else if (operation === "remove" || isCaries) {
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

  }

  ctx.putImageData(imageData, 0, 0);

  return new Promise((resolve) => canvas.toBlob((b) => resolve(b ?? referenceBlob), "image/png"));
}
