import type { EditOperation } from "@/lib/edit-types";

export type VariantTechnique = "boolean" | "material" | "generative" | "annotation";
export type VariantCase = "anatomy" | "fracture" | "class-i" | "endo" | "caries" | "crown" | "cusp-restoration";

export interface CaseVariantPreset {
  id: string;
  caseId: VariantCase;
  label: string;
  description: string;
  technique: VariantTechnique;
  operation: EditOperation;
  instruction: string;
  defaultSeverity: "small" | "moderate" | "large";
  requiresMask: boolean;
  requiresInternalAnatomy?: boolean;
}

export interface CaseVariantRecipe {
  presetId: string;
  caseId: VariantCase;
  technique: VariantTechnique;
  severity: "small" | "moderate" | "large";
  angleDeg: number;
  depthMm: number;
  targetSurface: string;
  label: string;
}

export const CASE_VARIANT_PRESETS: CaseVariantPreset[] = [
  { id: "fracture-small-chip", caseId: "fracture", label: "Small cusp chip", description: "Small localized enamel loss at the marked cusp.", technique: "boolean", operation: "remove", instruction: "Create a small localized cusp chip with an irregular enamel edge in the marked region", defaultSeverity: "small", requiresMask: true },
  { id: "fracture-oblique", caseId: "fracture", label: "Oblique cusp fracture", description: "Angled fracture through a marked cusp or marginal ridge.", technique: "boolean", operation: "remove", instruction: "Create a moderate oblique cusp fracture through the marked region and preserve the remaining tooth", defaultSeverity: "moderate", requiresMask: true },
  { id: "fracture-large", caseId: "fracture", label: "Large crown fracture", description: "Larger missing fragment for emergency teaching.", technique: "boolean", operation: "remove", instruction: "Remove a large crown fragment inside the marked region with an irregular fracture boundary", defaultSeverity: "large", requiresMask: true },
  { id: "class1-small", caseId: "class-i", label: "Small Class I", description: "Conservative central-fossa preparation.", technique: "boolean", operation: "remove", instruction: "Create a small conservative Class I cavity at the marked central fossa", defaultSeverity: "small", requiresMask: true },
  { id: "class1-standard", caseId: "class-i", label: "Standard Class I", description: "Defined occlusal cavity with moderate depth.", technique: "boolean", operation: "remove", instruction: "Create a standard Class I occlusal preparation with defined margins in the marked region", defaultSeverity: "moderate", requiresMask: true },
  { id: "class1-deep", caseId: "class-i", label: "Deep Class I", description: "Advanced deeper preparation; educator review required.", technique: "boolean", operation: "remove", instruction: "Create a deeper Class I preparation in the marked region while preserving surrounding cusps", defaultSeverity: "large", requiresMask: true },
  { id: "endo-conservative", caseId: "endo", label: "Conservative access", description: "Small external access opening. Internal anatomy is not inferred.", technique: "boolean", operation: "remove", instruction: "Create a conservative endodontic access opening through the marked occlusal region", defaultSeverity: "small", requiresMask: true, requiresInternalAnatomy: true },
  { id: "endo-traditional", caseId: "endo", label: "Traditional access", description: "Larger external access outline for demonstration.", technique: "boolean", operation: "remove", instruction: "Create a traditional endodontic access opening through the marked occlusal region", defaultSeverity: "moderate", requiresMask: true, requiresInternalAnatomy: true },
  { id: "caries-visual", caseId: "caries", label: "Visual caries lesion", description: "Brown lesion appearance without changing geometry or haptics.", technique: "material", operation: "add", instruction: "Add a localized brown caries appearance only within the marked region", defaultSeverity: "moderate", requiresMask: true },
  { id: "caries-excavate", caseId: "caries", label: "Excavated lesion", description: "Localized cavity representing removed carious tissue.", technique: "boolean", operation: "remove", instruction: "Excavate a localized carious cavity inside the marked region", defaultSeverity: "moderate", requiresMask: true },
  { id: "crown-occlusal", caseId: "crown", label: "Occlusal reduction", description: "Localized measurable reduction of the marked occlusal surface.", technique: "boolean", operation: "remove", instruction: "Reduce the marked occlusal surface for crown clearance", defaultSeverity: "moderate", requiresMask: true },
  { id: "crown-full", caseId: "crown", label: "Full crown reduction", description: "Broad reduction; experimental until clearance validation passes.", technique: "boolean", operation: "remove", instruction: "Create broad crown reduction within the marked surface while preserving the root", defaultSeverity: "large", requiresMask: true },
  { id: "cusp-restore", caseId: "cusp-restoration", label: "Restore missing cusp", description: "Morphology reconstruction; uses the generative pathway.", technique: "generative", operation: "add", instruction: "Restore an anatomically compatible cusp only within the marked missing region", defaultSeverity: "moderate", requiresMask: true },
];

export function getCaseVariantPreset(id: string): CaseVariantPreset | undefined {
  return CASE_VARIANT_PRESETS.find((preset) => preset.id === id);
}
