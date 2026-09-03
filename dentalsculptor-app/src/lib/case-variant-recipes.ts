import type { EditOperation } from "@/lib/edit-types";
import type { CaseTemplate } from "@/lib/case-templates";

export type VariantTechnique = "boolean" | "deform" | "material" | "generative" | "annotation";
export type VariantCase = "anatomy" | "fracture" | "class-i" | "class-ii" | "endo" | "caries" | "crown" | "morphology" | "surface" | "cusp-restoration";
export type VariantSurface = "occlusal" | "buccal" | "lingual" | "mesial" | "distal" | "incisal";

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
  schemaVersion?: 1;
  presetId: string;
  caseId: VariantCase;
  technique: VariantTechnique;
  operation?: EditOperation;
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
  { id: "class2-standard", caseId: "class-ii", label: "Class II proximal box", description: "Localized proximal box preparation at the marked mesial or distal surface.", technique: "boolean", operation: "remove", instruction: "Create a conservative Class II proximal box inside the marked region", defaultSeverity: "moderate", requiresMask: true },
  { id: "endo-conservative", caseId: "endo", label: "Conservative access", description: "Small external access opening. Internal anatomy is not inferred.", technique: "boolean", operation: "remove", instruction: "Create a conservative endodontic access opening through the marked occlusal region", defaultSeverity: "small", requiresMask: true, requiresInternalAnatomy: true },
  { id: "endo-traditional", caseId: "endo", label: "Traditional access", description: "Larger external access outline for demonstration.", technique: "boolean", operation: "remove", instruction: "Create a traditional endodontic access opening through the marked occlusal region", defaultSeverity: "moderate", requiresMask: true, requiresInternalAnatomy: true },
  { id: "caries-visual", caseId: "caries", label: "Visual caries lesion", description: "Brown lesion appearance without changing geometry or haptics.", technique: "material", operation: "add", instruction: "Add a localized brown caries appearance only within the marked region", defaultSeverity: "moderate", requiresMask: true },
  { id: "caries-excavate", caseId: "caries", label: "Excavated lesion", description: "Localized cavity representing removed carious tissue.", technique: "boolean", operation: "remove", instruction: "Excavate a localized carious cavity inside the marked region", defaultSeverity: "moderate", requiresMask: true },
  { id: "crown-occlusal", caseId: "crown", label: "Occlusal reduction", description: "Localized measurable reduction of the marked occlusal surface.", technique: "boolean", operation: "remove", instruction: "Reduce the marked occlusal surface for crown clearance", defaultSeverity: "moderate", requiresMask: true },
  { id: "crown-full", caseId: "crown", label: "Full crown reduction", description: "Broad reduction; experimental until clearance validation passes.", technique: "boolean", operation: "remove", instruction: "Create broad crown reduction within the marked surface while preserving the root", defaultSeverity: "large", requiresMask: true },
  { id: "cusp-restore", caseId: "cusp-restoration", label: "Restore missing cusp", description: "Morphology reconstruction; uses the generative pathway.", technique: "generative", operation: "add", instruction: "Restore an anatomically compatible cusp only within the marked missing region", defaultSeverity: "moderate", requiresMask: true },
  { id: "cusp-reconstruct", caseId: "cusp-restoration", label: "Reconstruct cusp", description: "Replace marked cusp morphology through the validated generative pathway.", technique: "generative", operation: "replace", instruction: "Replace only the marked cusp with anatomically compatible enamel morphology", defaultSeverity: "moderate", requiresMask: true },
  { id: "incisal-reconstruct", caseId: "cusp-restoration", label: "Reconstruct incisal edge", description: "Replace the marked incisal edge through the validated generative pathway.", technique: "generative", operation: "replace", instruction: "Replace only the marked incisal edge with anatomically compatible enamel morphology", defaultSeverity: "moderate", requiresMask: true },
  { id: "cusp-build-up", caseId: "morphology", label: "Build up cusp", description: "Localized outward cusp build-up following surface normals.", technique: "deform", operation: "add", instruction: "Build up a sharper cusp only inside the marked region", defaultSeverity: "moderate", requiresMask: true },
  { id: "cusp-reduction", caseId: "morphology", label: "Reduce cusp", description: "Localized inward cusp reduction following surface normals.", technique: "deform", operation: "remove", instruction: "Reduce and flatten the cusp only inside the marked region", defaultSeverity: "moderate", requiresMask: true },
  { id: "surface-smooth", caseId: "surface", label: "Smooth enamel", description: "Localized conservative smoothing without reconstructing the whole tooth.", technique: "deform", operation: "replace", instruction: "Smooth rough enamel only inside the marked region", defaultSeverity: "small", requiresMask: true },
  { id: "surface-stain", caseId: "surface", label: "Extrinsic stain", description: "Localized yellow-brown appearance change.", technique: "material", operation: "add", instruction: "Add yellow-brown extrinsic stain only inside the marked region", defaultSeverity: "moderate", requiresMask: true },
  { id: "surface-whiten", caseId: "surface", label: "Whiten enamel", description: "Localized enamel shade lightening.", technique: "material", operation: "replace", instruction: "Lighten enamel shade only inside the marked region", defaultSeverity: "moderate", requiresMask: true },
];

export function getCaseVariantPreset(id: string): CaseVariantPreset | undefined {
  return CASE_VARIANT_PRESETS.find((preset) => preset.id === id);
}

export function defaultVariantPresetForCase(caseTemplate: CaseTemplate): CaseVariantPreset | null {
  const id = caseTemplate.procedure === "pathology-add" ? "fracture-oblique"
    : caseTemplate.procedure === "prep-class-1" ? "class1-standard"
    : caseTemplate.procedure === "prep-class-2" ? "class2-standard"
    : caseTemplate.id === "endo-access-molar" ? "endo-traditional"
    : caseTemplate.procedure === "endo-access" ? "endo-conservative"
    : caseTemplate.procedure === "caries-smooth-surface" ? "caries-visual"
    : caseTemplate.procedure === "caries-occlusal" ? "caries-excavate"
    : caseTemplate.procedure === "crown-prep" ? "crown-occlusal"
    : null;
  return id ? getCaseVariantPreset(id) ?? null : null;
}

/** Keep edit copy, operation, and deterministic 3D recipe in lockstep. */
export function variantPresetForEditPreset(editPresetId: string): CaseVariantPreset | null {
  const variantId: Record<string, string> = {
    "cusp-fracture": "fracture-oblique",
    "class1-prep": "class1-standard",
    "class2-prep": "class2-standard",
    "endo-access": "endo-conservative",
    "add-caries": "caries-visual",
    "remove-caries": "caries-excavate",
    "crown-prep": "crown-occlusal",
    "add-cusp": "cusp-build-up",
    "remove-cusp": "cusp-reduction",
    "replace-cusp": "cusp-reconstruct",
    "incisor-edge": "incisal-reconstruct",
    "smooth-surface": "surface-smooth",
    "stain-discoloration": "surface-stain",
    "whiten-enamel": "surface-whiten",
  };
  return getCaseVariantPreset(variantId[editPresetId] ?? "") ?? null;
}

export function recipeFromVariantPreset(preset: CaseVariantPreset): CaseVariantRecipe {
  return {
    schemaVersion: 1,
    presetId: preset.id,
    caseId: preset.caseId,
    technique: preset.technique,
    operation: preset.operation,
    severity: preset.defaultSeverity,
    angleDeg: preset.caseId === "fracture" ? 35 : 0,
    depthMm: preset.defaultSeverity === "small" ? 1 : preset.defaultSeverity === "large" ? 3 : 1.5,
    targetSurface: "occlusal",
    label: preset.label,
  };
}

const VARIANT_SURFACES = new Set<VariantSurface>([
  "occlusal",
  "buccal",
  "lingual",
  "mesial",
  "distal",
  "incisal",
]);

/** Treat the preset as authoritative and reject malformed or contradictory client recipes. */
export function validateCaseVariantRecipe(
  input: unknown,
  requestedOperation: string
): { recipe: CaseVariantRecipe; preset: CaseVariantPreset } | { error: string } {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    return { error: "Teaching variant recipe must be an object." };
  }
  const raw = input as Record<string, unknown>;
  const preset = typeof raw.presetId === "string" ? getCaseVariantPreset(raw.presetId) : undefined;
  if (!preset) return { error: "Unknown teaching variant preset." };
  if (raw.schemaVersion !== 1) return { error: "Unsupported teaching variant recipe version." };
  if (raw.caseId !== preset.caseId || raw.technique !== preset.technique) {
    return { error: "Teaching variant strategy does not match its preset." };
  }
  if (raw.operation !== preset.operation || requestedOperation !== preset.operation) {
    return { error: "Teaching variant operation does not match its preset." };
  }
  if (!["small", "moderate", "large"].includes(String(raw.severity))) {
    return { error: "Invalid teaching variant severity." };
  }
  const angleDeg = Number(raw.angleDeg);
  const depthMm = Number(raw.depthMm);
  if (
    !Number.isFinite(angleDeg) ||
    (preset.caseId === "fracture" && (angleDeg < 5 || angleDeg > 85))
  ) {
    return { error: "Fracture angle must be between 5° and 85°." };
  }
  if (!Number.isFinite(depthMm) || depthMm < 0.2 || depthMm > 6) {
    return { error: "Edit depth must be between 0.2 mm and 6 mm." };
  }
  const targetSurface = raw.targetSurface as VariantSurface;
  if (!VARIANT_SURFACES.has(targetSurface)) {
    return { error: "Invalid target surface." };
  }
  return {
    preset,
    recipe: {
      schemaVersion: 1,
      presetId: preset.id,
      caseId: preset.caseId,
      technique: preset.technique,
      operation: preset.operation,
      severity: raw.severity as CaseVariantRecipe["severity"],
      angleDeg,
      depthMm,
      targetSurface,
      label: preset.label,
    },
  };
}
