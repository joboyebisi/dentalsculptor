/**
 * FDI tooth typing for edit-preset compatibility and case authoring.
 * Prevents molar-specific presets on incisor models (and vice versa).
 */

export type ToothType = "incisor" | "canine" | "premolar" | "molar";

export type ToothArch = "upper" | "lower";

/** Permanent dentition — FDI unit digit → morphological type. */
const FDI_UNIT_TO_TYPE: Record<string, ToothType> = {
  "1": "incisor",
  "2": "incisor",
  "3": "canine",
  "4": "premolar",
  "5": "premolar",
  "6": "molar",
  "7": "molar",
  "8": "molar",
};

export function fdiToothType(fdi: string | undefined | null): ToothType | null {
  if (!fdi || fdi.length < 2) return null;
  const unit = fdi.trim().slice(-1);
  return FDI_UNIT_TO_TYPE[unit] ?? null;
}

export function fdiToArch(fdi: string | undefined | null): ToothArch | null {
  if (!fdi || fdi.length < 2) return null;
  const quadrant = fdi.trim().charAt(0);
  if (["1", "2"].includes(quadrant)) return "upper";
  if (["3", "4"].includes(quadrant)) return "lower";
  return null;
}

export function toothTypeLabel(type: ToothType): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

/** Rough morphometry hint when no FDI is set — width/height of model bbox (mm). */
export function inferToothTypeFromAspect(aspectWidthOverHeight: number): ToothType | null {
  if (aspectWidthOverHeight > 0.85) return "molar";
  if (aspectWidthOverHeight > 0.65) return "premolar";
  if (aspectWidthOverHeight > 0.45) return "canine";
  if (aspectWidthOverHeight > 0) return "incisor";
  return null;
}

export function isPresetCompatibleWithToothType(
  compatibleTypes: ToothType[] | undefined,
  activeType: ToothType | null
): boolean {
  if (!compatibleTypes?.length) return true;
  if (!activeType) return true;
  return compatibleTypes.includes(activeType);
}
