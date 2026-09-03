/**
 * Structured clinical parameters for case templates.
 * Templates collect these fields before optional text/AI refinement —
 * not prompts alone (TrueTeethLab-inspired authoring).
 */

/** How the educator enters this case authoring path. */
export type AuthoringWorkflow =
  | "from-existing-model" // TrueTeethLab "Model from snapshot"
  | "single-tooth-clinical" // µCT / photo / IOS single tooth
  | "arch-multi-tooth"; // CBCT partial/full jaw

/** Assessment-aware anatomy role (generalises TTL drillable vs contextual). */
export type AnatomyPartRole =
  | "target" // learner modifies / drills here
  | "protected" // must not be damaged; scored on violation
  | "context" // visible reference; non-drillable neighbour/arch
  | "hidden-scoring-reference"; // invisible ideal prep / tolerance mesh for auto-assessment

export type ClinicalFieldType =
  | "fdi-tooth"
  | "surface"
  | "site"
  | "depth"
  | "tissue-involvement"
  | "pulp-proximity"
  | "select"
  | "multiselect"
  | "number"
  | "text"
  | "boolean";

export interface ClinicalParameterField {
  id: string;
  label: string;
  type: ClinicalFieldType;
  required: boolean;
  /** Options for select / multiselect. */
  options?: { value: string; label: string }[];
  helpText?: string;
  /** Maps to assessment zones or edit constraints when confirmed. */
  mapsTo?: "pathology" | "assessment" | "learner-task" | "anatomy-label";
}

export interface AnatomyRoleAssignment {
  partLabel: string;
  role: AnatomyPartRole;
  fdi?: string;
  tissue?: "enamel" | "dentin" | "pulp" | "bone" | "gingiva" | "caries" | "restoration";
}

export interface LearnerStartState {
  defaultView: "occlusal" | "buccal" | "lingual" | "mesial" | "distal" | "free";
  visibleReferences: ("odontogram" | "slice-sync" | "neighbours" | "prep-outline")[];
  instrumentsAllowed?: string[];
  timeLimitMinutes?: number;
}

export interface AssessmentCriteria {
  targetRegions: string[];
  protectedRegions: string[];
  toleranceMm?: number;
  criticalErrors: string[];
  rubricItems: string[];
}

/** Persisted case recipe — saved with project, not ephemeral wizard state. */
export interface CaseRecipe {
  workflow: AuthoringWorkflow;
  templateId: string;
  clinicalParameters: Record<string, string | number | boolean | string[]>;
  anatomyRoles: AnatomyRoleAssignment[];
  learnerStartState: LearnerStartState;
  assessment: AssessmentCriteria;
  /** Optional free-text refinement after structured fields. */
  promptRefinement?: string;
}

/** Caries template — structured fields (example from product spec). */
export const CARIES_CLINICAL_FIELDS: ClinicalParameterField[] = [
  {
    id: "fdiTooth",
    label: "Tooth (FDI)",
    type: "fdi-tooth",
    required: true,
    mapsTo: "anatomy-label",
    helpText:
      "Confirm the FDI number matches the tooth in your uploaded photo. We do not auto-detect tooth identity from images yet.",
  },
  {
    id: "surface",
    label: "Surface",
    type: "surface",
    required: false,
    options: [
      { value: "occlusal", label: "Occlusal" },
      { value: "buccal", label: "Buccal" },
      { value: "lingual", label: "Lingual" },
      { value: "mesial", label: "Mesial" },
      { value: "distal", label: "Distal" },
      { value: "cervical", label: "Cervical" },
    ],
    mapsTo: "pathology",
  },
  {
    id: "site",
    label: "Site / location detail",
    type: "site",
    required: false,
    helpText: "e.g. central fissure, buccal pit, proximal box",
    mapsTo: "pathology",
  },
  {
    id: "depth",
    label: "Lesion depth",
    type: "depth",
    required: false,
    options: [
      { value: "enamel-only", label: "Enamel only" },
      { value: "outer-dentin", label: "Outer dentin" },
      { value: "deep-dentin", label: "Deep dentin" },
      { value: "cavitated", label: "Cavitated" },
    ],
    mapsTo: "pathology",
  },
  {
    id: "tissueInvolvement",
    label: "Tissue involvement",
    type: "tissue-involvement",
    required: false,
    options: [
      { value: "enamel", label: "Enamel" },
      { value: "dentin", label: "Dentin" },
      { value: "enamel-dentin", label: "Enamel + dentin" },
    ],
    mapsTo: "pathology",
  },
  {
    id: "pulpProximity",
    label: "Pulp proximity",
    type: "pulp-proximity",
    required: false,
    options: [
      { value: "not-involved", label: "Not involved" },
      { value: "near", label: "Near pulp" },
      { value: "exposed-risk", label: "Exposure risk if over-prepared" },
    ],
    mapsTo: "assessment",
  },
];

export const ANATOMY_CLINICAL_FIELDS: ClinicalParameterField[] = [
  {
    id: "fdiTooth",
    label: "Tooth (FDI)",
    type: "fdi-tooth",
    required: true,
    mapsTo: "anatomy-label",
    helpText:
      "Confirm the FDI number matches the tooth in your uploaded photo. We do not auto-detect tooth identity from images yet.",
  },
  {
    id: "toothType",
    label: "Tooth type",
    type: "select",
    required: false,
    options: [
      { value: "incisor", label: "Incisor" },
      { value: "canine", label: "Canine" },
      { value: "premolar", label: "Premolar" },
      { value: "molar", label: "Molar" },
    ],
  },
  {
    id: "structuresToLabel",
    label: "Structures to identify",
    type: "multiselect",
    required: false,
    options: [
      { value: "cusps", label: "Cusps" },
      { value: "fossae", label: "Fossae" },
      { value: "grooves", label: "Grooves / fissures" },
      { value: "marginal-ridge", label: "Marginal ridge" },
      { value: "cervical-line", label: "CEJ / cervical line" },
    ],
    mapsTo: "learner-task",
  },
];

/** Pathology add-on — FDI required for edit presets; other fields optional for teaching. */
export const PATHOLOGY_CLINICAL_FIELDS: ClinicalParameterField[] = [
  {
    id: "fdiTooth",
    label: "Tooth (FDI)",
    type: "fdi-tooth",
    required: true,
    mapsTo: "anatomy-label",
    helpText:
      "Required — confirms edit presets and suggested prompts match your model. We do not auto-detect tooth number from photos.",
  },
  {
    id: "toothType",
    label: "Tooth type",
    type: "select",
    required: false,
    options: [
      { value: "incisor", label: "Incisor" },
      { value: "canine", label: "Canine" },
      { value: "premolar", label: "Premolar" },
      { value: "molar", label: "Molar" },
    ],
    helpText: "Auto-filled from FDI — adjust only if the photo shows a different tooth type.",
  },
  {
    id: "structuresToLabel",
    label: "Structures to identify",
    type: "multiselect",
    required: false,
    options: [
      { value: "cusps", label: "Cusps" },
      { value: "fossae", label: "Fossae" },
      { value: "grooves", label: "Grooves / fissures" },
      { value: "marginal-ridge", label: "Marginal ridge" },
      { value: "cervical-line", label: "CEJ / cervical line" },
    ],
    mapsTo: "learner-task",
    helpText: "Optional — for learner checklists, not required to run mask edits.",
  },
];

export const CROWN_PREP_CLINICAL_FIELDS: ClinicalParameterField[] = [
  {
    id: "fdiTooth",
    label: "Tooth (FDI)",
    type: "fdi-tooth",
    required: true,
    mapsTo: "anatomy-label",
    helpText:
      "Confirm the FDI number matches the tooth in your uploaded photo. We do not auto-detect tooth identity from images yet.",
  },
  {
    id: "archContext",
    label: "Arch context",
    type: "select",
    required: false,
    options: [
      { value: "lower", label: "Lower jaw" },
      { value: "upper", label: "Upper jaw" },
    ],
  },
  {
    id: "marginType",
    label: "Margin design",
    type: "select",
    required: false,
    options: [
      { value: "chamfer", label: "Chamfer" },
      { value: "shoulder", label: "Shoulder" },
      { value: "feather-edge", label: "Feather edge" },
    ],
    mapsTo: "assessment",
  },
  {
    id: "occlusalReductionMm",
    label: "Target occlusal reduction (mm)",
    type: "number",
    required: false,
    helpText: "Typical full crown: 1.5–2.0 mm",
    mapsTo: "assessment",
  },
  {
    id: "protectedTissues",
    label: "Protected tissues",
    type: "multiselect",
    required: false,
    options: [
      { value: "pulp", label: "Pulp chamber" },
      { value: "neighbours", label: "Adjacent contacts" },
      { value: "gingiva", label: "Gingival margin" },
    ],
    mapsTo: "assessment",
  },
];

export const ENDO_ACCESS_INTRO_FIELDS: ClinicalParameterField[] = [
  {
    id: "fdiTooth",
    label: "Tooth (FDI)",
    type: "fdi-tooth",
    required: true,
    mapsTo: "anatomy-label",
    helpText:
      "Confirm the FDI number matches the tooth in your uploaded photo. We do not auto-detect tooth identity from images yet.",
  },
  {
    id: "accessType",
    label: "Access type",
    type: "select",
    required: false,
    options: [
      { value: "molars", label: "Molar (trapezoidal)" },
      { value: "premolars", label: "Premolar" },
      { value: "anterior", label: "Anterior" },
    ],
    mapsTo: "pathology",
  },
];

export const ENDO_ACCESS_CLINICAL_FIELDS: ClinicalParameterField[] = [
  {
    id: "fdiTooth",
    label: "Tooth (FDI)",
    type: "fdi-tooth",
    required: true,
    mapsTo: "anatomy-label",
    helpText:
      "Confirm the FDI number matches the tooth in your uploaded photo. We do not auto-detect tooth identity from images yet.",
  },
  {
    id: "accessType",
    label: "Access type",
    type: "select",
    required: false,
    options: [
      { value: "molars", label: "Molar (trapezoidal)" },
      { value: "premolars", label: "Premolar" },
      { value: "anterior", label: "Anterior" },
    ],
    mapsTo: "pathology",
  },
  {
    id: "canalsExpected",
    label: "Canals to locate",
    type: "multiselect",
    required: false,
    options: [
      { value: "mb", label: "MB" },
      { value: "db", label: "DB" },
      { value: "p", label: "Palatal / lingual" },
      { value: "ml", label: "ML" },
      { value: "dl", label: "DL" },
    ],
    mapsTo: "learner-task",
  },
  {
    id: "pulpProximity",
    label: "Pulp chamber status",
    type: "pulp-proximity",
    required: false,
    options: [
      { value: "vital", label: "Vital — roof intact" },
      { value: "partial-calc", label: "Partially calcified chamber" },
    ],
    mapsTo: "assessment",
  },
];
