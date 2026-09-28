export type JawArch = "upper" | "lower";

export interface JawPlacement {
  schemaVersion: 1;
  arch: JawArch;
  fdiTooth: number;
  templateId: string;
  positionMm: [number, number, number];
  rotationDeg: [number, number, number];
  scale: number;
  savedAt?: string;
}

export const DEFAULT_JAW_PLACEMENT: JawPlacement = {
  schemaVersion: 1,
  arch: "lower",
  fdiTooth: 46,
  templateId: "adult-standard-lower-v1",
  positionMm: [0, 0, 0],
  rotationDeg: [0, 0, 0],
  scale: 1,
};

export function teethForArch(arch: JawArch): number[] {
  return arch === "upper"
    ? [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]
    : [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38];
}

export function isJawPlacement(value: unknown): value is JawPlacement {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const p = value as Partial<JawPlacement>;
  return p.schemaVersion === 1 &&
    (p.arch === "upper" || p.arch === "lower") &&
    typeof p.fdiTooth === "number" &&
    teethForArch(p.arch).includes(p.fdiTooth) &&
    typeof p.templateId === "string" &&
    Array.isArray(p.positionMm) && p.positionMm.length === 3 && p.positionMm.every(Number.isFinite) &&
    Array.isArray(p.rotationDeg) && p.rotationDeg.length === 3 && p.rotationDeg.every(Number.isFinite) &&
    typeof p.scale === "number" && p.scale >= 0.7 && p.scale <= 1.3;
}

export function jawPlacementWarnings(placement: JawPlacement): string[] {
  const warnings: string[] = [];
  const radialOffset = Math.hypot(...placement.positionMm);
  const maxRotation = Math.max(...placement.rotationDeg.map(Math.abs));
  if (radialOffset > 3) warnings.push("Tooth is more than 3 mm from its calibrated socket pose; inspect gingival and adjacent-tooth overlap.");
  if (maxRotation > 20) warnings.push("Large rotation may break long-axis or occlusal-plane alignment.");
  if (placement.scale < 0.85 || placement.scale > 1.15) warnings.push("Tooth scale is outside the usual ±15% review range.");
  return warnings;
}

/** Canonical arch socket in millimetres. X=left/right, Y=occlusal height, Z=anterior/posterior. */
export function jawSocketPose(arch: JawArch, fdiTooth: number) {
  const teeth = teethForArch(arch);
  const index = Math.max(0, teeth.indexOf(fdiTooth));
  const t = index / Math.max(1, teeth.length - 1);
  const angle = Math.PI * (0.12 + t * 0.76);
  const radiusX = 31;
  const radiusZ = 24;
  return {
    positionMm: [Math.cos(angle) * radiusX, arch === "lower" ? 7 : -7, Math.sin(angle) * radiusZ - 13] as [number, number, number],
    yawDeg: (angle * 180) / Math.PI - 90,
  };
}
