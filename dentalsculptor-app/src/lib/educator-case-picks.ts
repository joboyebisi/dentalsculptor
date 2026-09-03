/**
 * Educator-facing case categories for BDS Years 1–3.
 * Maps friendly labels to existing case templates + export targets.
 */

import type { CaseTemplate, StudentYearLevel } from "@/lib/case-templates";
import { CASE_TEMPLATES } from "@/lib/case-templates";
import type { ExportTarget } from "@/lib/export-presets";

export type EducatorCaseCategory =
  | "tooth-id"
  | "cusp"
  | "class-i"
  | "endo"
  | "caries"
  | "crown";

export interface EducatorCasePick {
  id: EducatorCaseCategory;
  label: string;
  subtitle: string;
  /** Primary template opened when educator picks this category. */
  primaryTemplateId: string;
  /** Alternate templates shown as “More options”. */
  alternateTemplateIds: string[];
  studentYearLevels: StudentYearLevel[];
  exportTargets: ExportTarget[];
  teachingUses: string[];
}

export const EDUCATOR_CASE_PICKS: EducatorCasePick[] = [
  {
    id: "tooth-id",
    label: "Tooth identification",
    subtitle: "Label cusps, fossae, and grooves on a single tooth.",
    primaryTemplateId: "anatomy-molar-id",
    alternateTemplateIds: [],
    studentYearLevels: [1, 2],
    exportTargets: ["meta-quest", "teaching-bundle", "simodont"],
    teachingUses: ["PowerPoint slides", "Meta Quest anatomy labs", "GLB/OBJ for LMS"],
  },
  {
    id: "cusp",
    label: "Cusp fracture / chipped enamel",
    subtitle: "Create a localized, visually obvious loss of enamel.",
    primaryTemplateId: "pathology-fracture-cusp",
    alternateTemplateIds: [],
    studentYearLevels: [2, 3],
    exportTargets: ["teaching-bundle", "meta-quest", "simodont"],
    teachingUses: ["Emergency dentistry scenarios", "Meta Quest VR case review", "OBJ/GLB for slides"],
  },
  {
    id: "class-i",
    label: "Simple Class I cavity",
    subtitle: "Create a localized occlusal preparation in the central fissure.",
    primaryTemplateId: "prep-class-1-amalgam",
    alternateTemplateIds: [],
    studentYearLevels: [2, 3],
    exportTargets: ["simodont", "simtocare", "teaching-bundle"],
    teachingUses: ["Operative teaching", "Simulator preparation practice", "Assessment demonstrations"],
  },
  {
    id: "endo",
    label: "Endodontic access opening",
    subtitle: "Open the pulp chamber roof at a clear anatomical target.",
    primaryTemplateId: "endo-access-intro",
    alternateTemplateIds: [],
    studentYearLevels: [2, 3, 4],
    exportTargets: ["simodont", "teaching-bundle", "meta-quest"],
    teachingUses: ["Pre-clinical endo labs", "Simulator access training", "Case walkthroughs"],
  },
  {
    id: "caries",
    label: "Caries appearance",
    subtitle: "Add a visual lesion, or choose excavation as a separate geometry case.",
    primaryTemplateId: "caries-smooth-surface",
    alternateTemplateIds: ["caries-occlusal-excavation"],
    studentYearLevels: [2, 3],
    exportTargets: ["simodont", "simtocare", "teaching-bundle"],
    teachingUses: ["Caries recognition", "Excavation discussion", "Visual case demonstrations"],
  },
  {
    id: "crown",
    label: "Crown reduction",
    subtitle: "Broad surface reduction for advanced evaluation only.",
    primaryTemplateId: "crown-prep-premolar",
    alternateTemplateIds: [],
    studentYearLevels: [4, 5],
    exportTargets: ["virteasy", "simodont", "teaching-bundle"],
    teachingUses: ["Crown preparation review", "Reduction assessment", "Advanced simulation"],
  },
];

export function getEducatorCasePick(id: EducatorCaseCategory): EducatorCasePick | undefined {
  return EDUCATOR_CASE_PICKS.find((p) => p.id === id);
}

export function templatesForEducatorPick(pick: EducatorCasePick): CaseTemplate[] {
  const ids = [pick.primaryTemplateId, ...pick.alternateTemplateIds];
  return ids
    .map((templateId) => CASE_TEMPLATES.find((t) => t.id === templateId))
    .filter((t): t is CaseTemplate => Boolean(t));
}
