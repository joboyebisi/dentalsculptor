/**
 * Clinical case templates for pedagogical ownership research.
 * Educators pick a template in the case wizard; metrics track custom vs template authoring.
 *
 * TrueTeethLab-derived: templates collect structured clinical parameters (see
 * clinical-case-params.ts) before optional AI text refinement.
 */

import type { ExportTarget } from "@/lib/export-presets";
import type {
  AnatomyPartRole,
  AuthoringWorkflow,
  ClinicalParameterField,
} from "@/lib/clinical-case-params";
import {
  ANATOMY_CLINICAL_FIELDS,
  PATHOLOGY_CLINICAL_FIELDS,
  CARIES_CLINICAL_FIELDS,
  CROWN_PREP_CLINICAL_FIELDS,
  ENDO_ACCESS_CLINICAL_FIELDS,
  ENDO_ACCESS_INTRO_FIELDS,
} from "@/lib/clinical-case-params";

export type StudentYearLevel = 1 | 2 | 3 | 4 | 5;

export type CaseProcedure =
  | "anatomy-identification"
  | "caries-occlusal"
  | "caries-smooth-surface"
  | "prep-class-1"
  | "prep-class-2"
  | "crown-prep"
  | "endo-access"
  | "pathology-add"
  | "custom";

export type CaseAssetKind =
  | "generated-tooth"
  | "jaw-upper"
  | "jaw-lower"
  | "jaw-quadrant"
  | "fdi-socket-map"
  | "reference-clinical-photo"
  | "prep-outline-mesh"
  | "simodont-native-ref"
  | "export-preset"
  | "learning-objectives"
  | "assessment-rubric";

export interface CaseAsset {
  kind: CaseAssetKind;
  label: string;
  /** Included automatically when case is created. */
  auto: boolean;
  description: string;
}

export interface CaseTemplate {
  id: string;
  procedure: CaseProcedure;
  title: string;
  shortDescription: string;
  /** TrueTeethLab-derived authoring path. */
  workflow: AuthoringWorkflow;
  /** First four recommended templates for E0–E2 launch. */
  primaryTemplate?: boolean;
  studentYearLevels: StudentYearLevel[];
  /** Structured fields collected in case wizard before optional prompt refinement. */
  clinicalParameterFields: ClinicalParameterField[];
  /** Default anatomy role assignments (target / protected / context / hidden-scoring). */
  defaultAnatomyRoles: { partLabel: string; role: AnatomyPartRole; tissue?: string }[];
  /** Bundled assets for Placement Studio + export workflow. */
  caseAssets: CaseAsset[];
  /** Pre-filled learning objectives for the project. */
  learningObjectives: string[];
  /** Suggested Nano3D / inpaint prompts for the edit step. */
  suggestedPrompts: string[];
  defaultOperation: "add" | "remove" | "replace";
  exportRecommendation: ExportTarget;
  /** Hints shown in editor sidebar for students. */
  studentHints: string[];
  /** Rubric prompts for assessment authoring. */
  assessmentPrompts: string[];
  difficulty: "introductory" | "intermediate" | "advanced";
  /** Tags for community search / filtering. */
  tags: string[];
}

function caseAssets(
  jaw: "none" | "lower" | "upper" | "both",
  extras: CaseAsset[] = []
): CaseAsset[] {
  const base: CaseAsset[] = [
    {
      kind: "generated-tooth",
      label: "Generated tooth (GLB)",
      auto: true,
      description: "Single tooth from your uploaded PNG/JPG.",
    },
    {
      kind: "reference-clinical-photo",
      label: "Source clinical photo",
      auto: true,
      description: "Original 2D image attached to the project.",
    },
    {
      kind: "learning-objectives",
      label: "Learning objectives",
      auto: true,
      description: "Pre-filled from the case template.",
    },
    {
      kind: "export-preset",
      label: "Recommended export preset",
      auto: true,
      description: "Default Sim/VR target for this case type.",
    },
  ];
  if (jaw === "lower" || jaw === "both") {
    base.push({
      kind: "jaw-lower",
      label: "Lower jaw template (STL)",
      auto: true,
      description: "Open-Full-Jaw mandible for Placement Studio (E2).",
    });
  }
  if (jaw === "upper" || jaw === "both") {
    base.push({
      kind: "jaw-upper",
      label: "Upper jaw template (STL)",
      auto: true,
      description: "Open-Full-Jaw maxilla for Placement Studio (E2).",
    });
  }
  if (jaw !== "none") {
    base.push({
      kind: "fdi-socket-map",
      label: "FDI socket map (JSON)",
      auto: true,
      description: "Snap points for tooth placement on the jaw arch.",
    });
  }
  return [...base, ...extras];
}

export const CASE_TEMPLATES: CaseTemplate[] = [
  {
    id: "anatomy-molar-id",
    procedure: "anatomy-identification",
    title: "Dental anatomy — single tooth",
    shortDescription: "Generate or import a tooth; label cusps, fossae and ridges.",
    workflow: "single-tooth-clinical",
    primaryTemplate: true,
    studentYearLevels: [1, 2],
    clinicalParameterFields: ANATOMY_CLINICAL_FIELDS,
    defaultAnatomyRoles: [
      { partLabel: "Tooth crown", role: "context", tissue: "enamel" },
      { partLabel: "Structures to label", role: "target" },
    ],
    caseAssets: caseAssets("none", [
      {
        kind: "assessment-rubric",
        label: "Anatomy labelling rubric",
        auto: true,
        description: "Cusp and fossa identification prompts.",
      },
    ]),
    learningObjectives: [
      "Identify major cusps and occlusal landmarks on a permanent molar.",
      "Relate 2D clinical appearance to 3D morphology.",
    ],
    suggestedPrompts: [],
    defaultOperation: "replace",
    exportRecommendation: "meta-quest",
    studentHints: ["Rotate the model and annotate each cusp before submitting."],
    assessmentPrompts: ["Name the mesiobuccal cusp and one adjacent fossa."],
    difficulty: "introductory",
    tags: ["anatomy", "year-1", "year-2", "no-edit"],
  },
  {
    id: "caries-occlusal-excavation",
    procedure: "caries-occlusal",
    title: "Caries — single tooth",
    shortDescription:
      "Define lesion site, depth and pulp proximity; shape cavity for operative practice. Uniform drill feel on Simodont import.",
    workflow: "single-tooth-clinical",
    primaryTemplate: true,
    studentYearLevels: [2, 3],
    clinicalParameterFields: CARIES_CLINICAL_FIELDS,
    defaultAnatomyRoles: [
      { partLabel: "Carious lesion", role: "target", tissue: "caries" },
      { partLabel: "Sound enamel rim", role: "protected", tissue: "enamel" },
      { partLabel: "Pulp chamber", role: "protected", tissue: "pulp" },
      { partLabel: "Ideal prep outline", role: "hidden-scoring-reference" },
    ],
    caseAssets: caseAssets("lower", [
      {
        kind: "prep-outline-mesh",
        label: "Ideal prep outline (optional)",
        auto: false,
        description: "Reference mesh for comparing cavity form after edit.",
      },
      {
        kind: "simodont-native-ref",
        label: "Simodont cariology ref (optional)",
        auto: false,
        description: "Link to native Simodont case for soft caries haptics.",
      },
    ]),
    learningObjectives: [
      "Recognize occlusal caries extent on a 3D tooth model.",
      "Perform selective removal of carious tissue while preserving sound enamel.",
    ],
    suggestedPrompts: [
      "remove dark decay from the occlusal fissure area",
      "excavate carious dentin in the central fossa, keep enamel rim intact",
    ],
    defaultOperation: "remove",
    exportRecommendation: "simodont",
    studentHints: ["Extend removal only within the marked decay region."],
    assessmentPrompts: ["Describe how you judged the extent of caries removal."],
    difficulty: "intermediate",
    tags: ["caries", "operative", "simodont"],
  },
  {
    id: "caries-smooth-surface",
    procedure: "caries-smooth-surface",
    title: "Smooth-surface early lesion",
    shortDescription: "Prepare a smooth-surface lesion for preventive and restorative discussion.",
    workflow: "single-tooth-clinical",
    studentYearLevels: [2, 3],
    clinicalParameterFields: CARIES_CLINICAL_FIELDS,
    defaultAnatomyRoles: [
      { partLabel: "Demineralized enamel", role: "target", tissue: "caries" },
      { partLabel: "Adjacent sound enamel", role: "protected", tissue: "enamel" },
    ],
    caseAssets: caseAssets("lower"),
    learningObjectives: [
      "Differentiate incipient demineralization from cavitation.",
      "Plan minimal intervention for smooth-surface caries.",
    ],
    suggestedPrompts: [
      "remove chalky demineralized enamel on the buccal surface",
      "create a small cavitation for resin infiltration simulation",
    ],
    defaultOperation: "remove",
    exportRecommendation: "simtocare",
    studentHints: ["Compare lesion depth before and after your edit."],
    assessmentPrompts: ["When would you monitor vs restore this lesion?"],
    difficulty: "intermediate",
    tags: ["caries", "preventive"],
  },
  {
    id: "prep-class-1-amalgam",
    procedure: "prep-class-1",
    title: "Class I cavity preparation",
    shortDescription: "Ideal Class I prep form for amalgam or composite simulation.",
    workflow: "from-existing-model",
    studentYearLevels: [3],
    clinicalParameterFields: CARIES_CLINICAL_FIELDS,
    defaultAnatomyRoles: [
      { partLabel: "Prep cavity", role: "target" },
      { partLabel: "Class I outline reference", role: "hidden-scoring-reference" },
      { partLabel: "Pulp", role: "protected", tissue: "pulp" },
    ],
    caseAssets: caseAssets("lower", [
      { kind: "prep-outline-mesh", label: "Class I prep outline", auto: false, description: "Target prep shape for comparison." },
    ]),
    learningObjectives: [
      "Outline and prepare a Class I cavity with proper depth and retention.",
      "Maintain pulpal protection and isthmus width appropriate to material.",
    ],
    suggestedPrompts: [
      "remove enamel and dentin to form a conservative Class I preparation",
      "extend preparation depth uniformly in the central fissure",
    ],
    defaultOperation: "remove",
    exportRecommendation: "simodont",
    studentHints: ["Follow the template outline; check pulpal depth before export."],
    assessmentPrompts: ["List three criteria for an acceptable Class I outline."],
    difficulty: "intermediate",
    tags: ["operative", "class-1", "year-3"],
  },
  {
    id: "prep-class-2-box",
    procedure: "prep-class-2",
    title: "Class II proximal box",
    shortDescription: "Mesial or distal box preparation for Class II restoration training.",
    workflow: "from-existing-model",
    studentYearLevels: [3, 4],
    clinicalParameterFields: CARIES_CLINICAL_FIELDS,
    defaultAnatomyRoles: [
      { partLabel: "Proximal box", role: "target" },
      { partLabel: "Neighbour contact", role: "protected" },
      { partLabel: "Quadrant arch", role: "context", tissue: "bone" },
    ],
    caseAssets: caseAssets("lower", [
      { kind: "jaw-quadrant", label: "Quadrant context mesh", auto: false, description: "Partial arch for proximal contact training." },
    ]),
    learningObjectives: [
      "Design a proximal box with appropriate clearance and line angles.",
      "Connect box to occlusal isthmus for resistance form.",
    ],
    suggestedPrompts: [
      "remove dentin to create a proximal box with straight walls",
      "open contact area and form a conservative Class II preparation",
    ],
    defaultOperation: "remove",
    exportRecommendation: "simodont",
    studentHints: ["Verify proximal clearance in the placement view if on a jaw."],
    assessmentPrompts: ["Explain how your prep achieves resistance and retention."],
    difficulty: "advanced",
    tags: ["operative", "class-2"],
  },
  {
    id: "crown-prep-premolar",
    procedure: "crown-prep",
    title: "Crown preparation — tooth in jaw",
    shortDescription: "Reduce axial and occlusal surfaces; place in arch context.",
    workflow: "arch-multi-tooth",
    primaryTemplate: true,
    studentYearLevels: [4, 5],
    clinicalParameterFields: CROWN_PREP_CLINICAL_FIELDS,
    defaultAnatomyRoles: [
      { partLabel: "Prep tooth", role: "target" },
      { partLabel: "Adjacent teeth", role: "context" },
      { partLabel: "Gingival margin", role: "protected", tissue: "gingiva" },
      { partLabel: "Ideal reduction reference", role: "hidden-scoring-reference" },
    ],
    caseAssets: caseAssets("both"),
    learningObjectives: [
      "Achieve adequate occlusal and axial reduction for a full crown.",
      "Create a visible chamfer or shoulder margin consistently.",
    ],
    suggestedPrompts: [
      "reduce occlusal surface evenly for crown clearance",
      "create axial reduction with a continuous chamfer margin",
    ],
    defaultOperation: "remove",
    exportRecommendation: "virteasy",
    studentHints: ["Check reduction depth from multiple views before merging to jaw."],
    assessmentPrompts: ["Document margin location and occlusal clearance achieved."],
    difficulty: "advanced",
    tags: ["prosthodontics", "crown", "year-4", "year-5"],
  },
  {
    id: "endo-access-intro",
    procedure: "endo-access",
    title: "Endodontic access — introductory",
    shortDescription: "Year 2–3 intro: open pulp chamber roof and locate orifices on a single tooth.",
    workflow: "single-tooth-clinical",
    primaryTemplate: true,
    studentYearLevels: [2, 3],
    clinicalParameterFields: ENDO_ACCESS_INTRO_FIELDS,
    defaultAnatomyRoles: [
      { partLabel: "Access cavity", role: "target" },
      { partLabel: "Canal orifices", role: "target", tissue: "pulp" },
      { partLabel: "Peripheral dentin", role: "protected", tissue: "dentin" },
    ],
    caseAssets: caseAssets("none"),
    learningObjectives: [
      "Outline an endodontic access cavity on a 3D tooth model.",
      "Relate occlusal anatomy to pulp chamber orientation.",
    ],
    suggestedPrompts: [
      "Open pulp chamber roof through occlusal surface, expose canal orifices",
      "remove pulp chamber roof to create endodontic access opening",
    ],
    defaultOperation: "remove",
    exportRecommendation: "simodont",
    studentHints: ["Use mesial-distal and buccal-lingual views to confirm chamber exposure."],
    assessmentPrompts: ["Which orifices should be visible after access?"],
    difficulty: "introductory",
    tags: ["endo", "access", "year-2", "year-3"],
  },
  {
    id: "endo-access-molar",
    procedure: "endo-access",
    title: "Endodontic access — single tooth",
    shortDescription: "Open pulp chamber roof; locate canal orifices.",
    workflow: "single-tooth-clinical",
    primaryTemplate: true,
    studentYearLevels: [4, 5],
    clinicalParameterFields: ENDO_ACCESS_CLINICAL_FIELDS,
    defaultAnatomyRoles: [
      { partLabel: "Access cavity", role: "target" },
      { partLabel: "Canal orifices", role: "target", tissue: "pulp" },
      { partLabel: "Chamber roof reference", role: "hidden-scoring-reference" },
      { partLabel: "Peripheral dentin", role: "protected", tissue: "dentin" },
    ],
    caseAssets: caseAssets("upper"),
    learningObjectives: [
      "Identify canal orifice positions after access.",
    ],
    suggestedPrompts: [
      "remove pulp chamber roof to create endodontic access opening",
      "extend access through occlusal surface into pulp chamber",
    ],
    defaultOperation: "remove",
    exportRecommendation: "simodont",
    studentHints: ["Use mesial-distal and buccal-lingual views to confirm chamber exposure."],
    assessmentPrompts: ["Which orifices are visible after your access cavity?"],
    difficulty: "advanced",
    tags: ["endo", "access"],
  },
  {
    id: "pathology-fracture-cusp",
    procedure: "pathology-add",
    title: "Cusp fracture (pathology add-on)",
    shortDescription: "Add a fractured cusp for emergency and restorative teaching.",
    workflow: "from-existing-model",
    studentYearLevels: [3, 4, 5],
    clinicalParameterFields: PATHOLOGY_CLINICAL_FIELDS,
    defaultAnatomyRoles: [
      { partLabel: "Fractured cusp", role: "target" },
      { partLabel: "Remaining tooth", role: "context" },
    ],
    caseAssets: caseAssets("none"),
    learningObjectives: [
      "Assess structural loss from cusp fracture.",
      "Plan provisional and definitive restoration options.",
    ],
    suggestedPrompts: [
      "add a fractured missing cusp on the distobuccal cusp",
      "create an oblique fracture line through the marginal ridge",
    ],
    defaultOperation: "add",
    exportRecommendation: "teaching-bundle",
    studentHints: ["Compare intact vs fractured models using revision history."],
    assessmentPrompts: ["What interim management would you recommend?"],
    difficulty: "intermediate",
    tags: ["pathology", "emergency"],
  },
];

export function getCaseTemplate(id: string): CaseTemplate | undefined {
  return CASE_TEMPLATES.find((t) => t.id === id);
}

/** First four recommended templates (E0–E2 launch). */
export function listPrimaryCaseTemplates(): CaseTemplate[] {
  return CASE_TEMPLATES.filter((t) => t.primaryTemplate);
}

export function listCaseTemplates(filters?: {
  year?: StudentYearLevel;
  procedure?: CaseProcedure;
}): CaseTemplate[] {
  return CASE_TEMPLATES.filter((t) => {
    if (filters?.year && !t.studentYearLevels.includes(filters.year)) return false;
    if (filters?.procedure && t.procedure !== filters.procedure) return false;
    return true;
  });
}

export function studentYearLabel(year: StudentYearLevel): string {
  if (year === 5) return "Year 5 / MFDS";
  return `Year ${year}`;
}

/** Research payload when educator selects a template vs custom case. */
export function ownershipMetricsFromTemplate(
  templateId: string | null,
  customTitle: boolean
): Record<string, string | boolean> {
  return {
    templateId: templateId ?? "custom",
    usedTemplate: Boolean(templateId),
    customTitle,
    pedagogicalOwnershipTrack: "case-authoring-v1",
  };
}
