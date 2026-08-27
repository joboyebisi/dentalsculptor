/**
 * Export presets for simulator and VR targets.
 * Used by Export wizard (E1) and server-side mesh post-processing.
 */

export type ExportTarget =
  | "simodont"
  | "simtocare"
  | "virteasy"
  | "meta-quest"
  | "powerpoint"
  | "teaching-bundle";

export type ExportFormat = "stl" | "ply" | "glb" | "zip";

/** Whether custom export delivers multi-tissue haptic feel on that platform. */
export type HapticRealism = "visual-only" | "uniform-drill" | "multi-tissue-native";

export interface ExportPreset {
  id: ExportTarget;
  label: string;
  description: string;
  formats: ExportFormat[];
  /** Linear unit for STL/PLY — always mm for haptic sims. */
  units: "mm" | "meters";
  /** Multiply vertex positions after normalization (1 = real-world mm tooth). */
  scaleFactor: number;
  /** Max triangle count after decimation. */
  maxTriangles: number;
  requireWatertight: boolean;
  /** +Y or +Z up after reorientation — Simodont expects consistent clinical axis. */
  upAxis: "Y" | "Z";
  /** Include merged jaw when placement was used. */
  includeJawWhenPlaced: boolean;
  hapticRealism: HapticRealism;
  /** Shown in export wizard when custom mesh cannot deliver soft caries feel. */
  hapticDisclosure?: string;
  notes: string[];
}

export const EXPORT_PRESETS: Record<ExportTarget, ExportPreset> = {
  simodont: {
    id: "simodont",
    label: "Simodont",
    description: "Haptic dental trainer — STL or PLY, millimetres, watertight.",
    formats: ["stl", "ply"],
    units: "mm",
    scaleFactor: 1,
    maxTriangles: 500_000,
    requireWatertight: true,
    upAxis: "Y",
    includeJawWhenPlaced: true,
    hapticRealism: "uniform-drill",
    hapticDisclosure:
      "Imported STL uses uniform drill resistance. For soft caries tactile feedback, use Simodont native cariology cases or TrueTeethLab (CBCT).",
    notes: [
      "Crop to tooth (+ jaw if placed).",
      "Validate import in Simodont Teacher before class rollout.",
      "Reference: Simodont Courseware Teacher Manual v4.18.",
    ],
  },
  simtocare: {
    id: "simtocare",
    label: "SimtoCARE Dente",
    description: "Mixed-reality haptic simulator — STL/PLY intra-oral style import.",
    formats: ["stl", "ply"],
    units: "mm",
    scaleFactor: 1,
    maxTriangles: 500_000,
    requireWatertight: true,
    upAxis: "Y",
    includeJawWhenPlaced: true,
    hapticRealism: "uniform-drill",
    hapticDisclosure:
      "Custom STL/PLY is voxelized as drillable with uniform material feel — not enamel vs soft caries layers.",
    notes: [
      "Drillable model conversion happens inside SimtoCARE after import.",
    ],
  },
  virteasy: {
    id: "virteasy",
    label: "Virteasy Dental",
    description: "VR + haptic Unreal-based simulator — STL for exercises and 3D print.",
    formats: ["stl"],
    units: "mm",
    scaleFactor: 1,
    maxTriangles: 400_000,
    requireWatertight: true,
    upAxis: "Y",
    includeJawWhenPlaced: true,
    hapticRealism: "uniform-drill",
    notes: [
      "Clean manifold normals recommended.",
      "Desktop version also accepts DICOM — out of scope for photo-only workflow.",
    ],
  },
  "meta-quest": {
    id: "meta-quest",
    label: "Meta Quest (VR display)",
    description: "GLB for in-app WebXR or side-loaded Quest viewers.",
    formats: ["glb"],
    units: "meters",
    scaleFactor: 0.001,
    maxTriangles: 150_000,
    requireWatertight: false,
    upAxis: "Y",
    includeJawWhenPlaced: true,
    hapticRealism: "visual-only",
    notes: [
      "Use /xr/[id] for browser WebXR preview.",
    ],
  },
  powerpoint: {
    id: "powerpoint",
    label: "PowerPoint / Microsoft 365",
    description: "Portable GLB for interactive 3D models in desktop PowerPoint, Word and Excel.",
    formats: ["glb"],
    units: "meters",
    scaleFactor: 0.001,
    maxTriangles: 150_000,
    requireWatertight: false,
    upAxis: "Y",
    includeJawWhenPlaced: false,
    hapticRealism: "visual-only",
    notes: [
      "Insert with Insert > 3D Models > From a File in a supported desktop Microsoft 365 app.",
      "GLB is Microsoft's recommended portable 3D format; PowerPoint for the web cannot insert it directly.",
    ],
  },
  "teaching-bundle": {
    id: "teaching-bundle",
    label: "Teaching download (GLB + STL)",
    description: "ZIP with GLB for viewing and STL (mm) for print or LMS upload.",
    formats: ["zip", "glb", "stl"],
    units: "mm",
    scaleFactor: 1,
    maxTriangles: 500_000,
    requireWatertight: true,
    upAxis: "Y",
    includeJawWhenPlaced: false,
    hapticRealism: "uniform-drill",
    notes: ["Includes README with scale and FDI placement notes when applicable."],
  },
};

export const DEFAULT_EXPORT_TARGET: ExportTarget = "simodont";

export function getExportPreset(target: ExportTarget): ExportPreset {
  return EXPORT_PRESETS[target];
}

export function listExportPresets(): ExportPreset[] {
  return Object.values(EXPORT_PRESETS);
}

/** Primary file extension for download filename. */
export function primaryExtension(preset: ExportPreset): string {
  const fmt = preset.formats[0];
  if (fmt === "zip") return "zip";
  return fmt;
}
