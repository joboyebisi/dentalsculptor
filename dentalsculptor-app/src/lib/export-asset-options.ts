/**
 * Project assets available for export — educator picks what the target machine needs.
 */

import type { CaseAsset, CaseTemplate } from "@/lib/case-templates";
import type { CaseRecipe } from "@/lib/clinical-case-params";
import type { ExportTarget } from "@/lib/export-presets";

export type ExportAssetId =
  | "mesh-primary"
  | "mesh-stl"
  | "source-photo"
  | "reference-glb"
  | "jaw-lower"
  | "jaw-upper"
  | "readme";

export interface ExportAssetOption {
  id: ExportAssetId;
  label: string;
  description: string;
  /** File extension when downloaded individually. */
  extension?: string;
  /** Recommended for simulator targets. */
  recommendedFor?: ExportTarget[];
  defaultSelected: boolean;
  available: boolean;
  unavailableReason?: string;
}

export function listExportAssetOptions(input: {
  target: ExportTarget;
  outputFormat: string;
  hasModel: boolean;
  sourceImageUrl?: string | null;
  selectedCase?: CaseTemplate | null;
  caseRecipe?: CaseRecipe | null;
  jawPlaced?: boolean;
}): ExportAssetOption[] {
  const simTargets: ExportTarget[] = ["simodont", "simtocare", "virteasy"];
  const isSim = simTargets.includes(input.target);
  const templateAssets = input.selectedCase?.caseAssets ?? [];

  const hasJawLower = templateAssets.some((a) => a.kind === "jaw-lower");
  const hasJawUpper = templateAssets.some((a) => a.kind === "jaw-upper");

  return [
    {
      id: "mesh-primary",
      label: isSim ? "Tooth mesh (simulator format)" : "Tooth mesh (primary)",
      description: isSim
        ? `Single watertight ${input.outputFormat.toUpperCase()} for import — usually all you need.`
        : "Current edited tooth model in your chosen format.",
      extension: input.outputFormat,
      recommendedFor: simTargets,
      defaultSelected: true,
      available: input.hasModel,
      unavailableReason: "Generate or edit a model first.",
    },
    {
      id: "mesh-stl",
      label: "Tooth mesh (STL backup)",
      description: "Extra STL copy when the destination accepts STL only.",
      extension: "stl",
      recommendedFor: ["simodont", "simtocare", "virteasy", "teaching-bundle"],
      defaultSelected: input.target === "teaching-bundle",
      available: input.hasModel && input.outputFormat !== "stl",
      unavailableReason:
        input.outputFormat === "stl"
          ? "Primary export is already STL — included in the main download."
          : "Generate or edit a model first.",
    },
    {
      id: "source-photo",
      label: "Source clinical photo",
      description: "Original 2D upload — for LMS slides, not simulator import.",
      extension: "jpg",
      defaultSelected: false,
      available: Boolean(input.sourceImageUrl),
      unavailableReason: "No source photo on this project.",
    },
    {
      id: "reference-glb",
      label: "Reference GLB (viewer)",
      description: "Full GLB with materials for Quest / WebXR — skip for Simodont-only workflows.",
      extension: "glb",
      recommendedFor: ["meta-quest", "teaching-bundle"],
      defaultSelected: input.target === "meta-quest",
      available: input.hasModel,
    },
    {
      id: "jaw-lower",
      label: "Lower jaw template (STL)",
      description: "Mandible arch for placement context — optional for single-tooth prep.",
      extension: "stl",
      defaultSelected: false,
      available: hasJawLower && Boolean(input.jawPlaced),
      unavailableReason: hasJawLower
        ? "Place tooth on jaw in Placement Studio (E2) to include."
        : "Not part of this case template.",
    },
    {
      id: "jaw-upper",
      label: "Upper jaw template (STL)",
      description: "Maxilla arch — optional unless exporting arch context.",
      extension: "stl",
      defaultSelected: false,
      available: hasJawUpper && Boolean(input.jawPlaced),
      unavailableReason: hasJawUpper
        ? "Place tooth on jaw in Placement Studio (E2) to include."
        : "Not part of this case template.",
    },
    {
      id: "readme",
      label: "README (scale, FDI, haptic tier)",
      description: "Text file explaining units, FDI tooth, and uniform vs native haptics.",
      extension: "txt",
      defaultSelected: input.target === "teaching-bundle",
      available: true,
    },
  ];
}

export function assetKindFromTemplate(asset: CaseAsset): ExportAssetId | null {
  switch (asset.kind) {
    case "generated-tooth":
      return "mesh-primary";
    case "reference-clinical-photo":
      return "source-photo";
    case "jaw-lower":
      return "jaw-lower";
    case "jaw-upper":
      return "jaw-upper";
    default:
      return null;
  }
}
