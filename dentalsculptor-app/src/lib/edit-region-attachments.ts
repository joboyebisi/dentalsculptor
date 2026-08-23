import type { RectMark } from "@/components/editor/cam-model-viewer";

/** Region mark surfaced as a dismissible chip in the semantic edit bar. */
export interface EditRegionAttachment {
  id: string;
  index: number;
  label: string;
  thumbnailUrl: string;
}

export function attachmentFromRectMark(mark: RectMark, index: number): EditRegionAttachment {
  return {
    id: mark.id,
    index,
    label: mark.label || mark.text || `Region ${index}`,
    thumbnailUrl: mark.thumbnailUrl ?? "",
  };
}

export function buildRegionMarksPayload(marks: RectMark[]) {
  return marks.map((m, i) => ({
    id: m.id,
    index: i + 1,
    label: m.label || m.text || `Region ${i + 1}`,
    x: m.x,
    y: m.y,
    width: m.width,
    height: m.height,
    corners3d: m.corners3d,
  }));
}

/** Append region references so Nano3D / inpaint workers know spatial targets. */
export function instructionWithRegionRefs(instruction: string, marks: RectMark[]): string {
  if (marks.length === 0) return instruction.trim();
  const refs = marks
    .map((m, i) => {
      const label = m.label || m.text || `Region ${i + 1}`;
      return `[${label}]`;
    })
    .join(" ");
  const base = instruction.trim();
  return base ? `${base}\n\nTarget regions: ${refs}` : `Edit target regions: ${refs}`;
}
