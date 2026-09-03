import type { RectMark } from "@/components/editor/cam-model-viewer";

/** Normalized screen rects (0–1) → binary mask PNG for geometry edits. */
export async function rasterizeRectMarksToMask(
  width: number,
  height: number,
  marks: Pick<RectMark, "x" | "y" | "width" | "height">[]
): Promise<Blob | null> {
  if (!marks.length || width < 1 || height < 1) return null;

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  ctx.fillStyle = "#ffffff";
  for (const mark of marks) {
    ctx.fillRect(
      mark.x * width,
      mark.y * height,
      mark.width * width,
      mark.height * height
    );
  }

  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), "image/png"));
}
