/** Mock dental segmentation parts shown after model generation. */
export interface SegmentPart {
  id: string;
  label: string;
  color: string;
  visible: boolean;
  confidence: number;
}

const DENTAL_PARTS: Omit<SegmentPart, "visible">[] = [
  { id: "enamel", label: "Enamel", color: "#f5e6d3", confidence: 0.94 },
  { id: "dentin", label: "Dentin", color: "#e8dcc8", confidence: 0.91 },
  { id: "pulp", label: "Pulp Chamber", color: "#fca5a5", confidence: 0.87 },
  { id: "crown", label: "Clinical Crown", color: "#bfdbfe", confidence: 0.92 },
  { id: "root", label: "Root Structure", color: "#cbd5e1", confidence: 0.89 },
  { id: "occlusal", label: "Occlusal Surface", color: "#fde68a", confidence: 0.85 },
  { id: "mesial", label: "Mesial Margin", color: "#c4b5fd", confidence: 0.83 },
  { id: "distal", label: "Distal Groove", color: "#86efac", confidence: 0.88 },
];

export function generateSegmentParts(): SegmentPart[] {
  return DENTAL_PARTS.map((p) => ({ ...p, visible: true }));
}

export function projectFileName(title: string): string {
  return `${title.replace(/\s+/g, "_").slice(0, 32)}.ds`;
}
