/**
 * Educator-facing case categories for BDS Years 1–3.
 * Maps friendly labels to existing case templates + export targets.
 */

import type { CaseTemplate, StudentYearLevel } from "@/lib/case-templates";
import { CASE_TEMPLATES } from "@/lib/case-templates";
import type { ExportTarget } from "@/lib/export-presets";

export type EducatorCaseCategory = "tooth-id" | "cavity" | "endo" | "cusp";

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
    id: "cavity",
    label: "Cavity & caries",
    subtitle: "Excavate lesions and practice operative prep form.",
    primaryTemplateId: "caries-occlusal-excavation",
    alternateTemplateIds: ["caries-smooth-surface", "prep-class-1-amalgam"],
    studentYearLevels: [2, 3],
    exportTargets: ["simodont", "simtocare", "teaching-bundle"],
    teachingUses: ["Dental simulators (Simodont / SimToCare)", "STL for bench demos", "PLY teaching bundles"],
  },
  {
    id: "endo",
    label: "Endodontic access",
    subtitle: "Open the pulp chamber and locate canal orifices.",
    primaryTemplateId: "endo-access-intro",
    alternateTemplateIds: ["endo-access-molar"],
    studentYearLevels: [2, 3, 4],
    exportTargets: ["simodont", "teaching-bundle", "meta-quest"],
    teachingUses: ["Pre-clinical endo labs", "Simulator access training", "PowerPoint case walkthroughs"],
  },
  {
    id: "cusp",
    label: "Cusp & fracture",
    subtitle: "Add or assess cusp fracture for emergency/restorative cases.",
    primaryTemplateId: "pathology-fracture-cusp",
    alternateTemplateIds: [],
    studentYearLevels: [2, 3],
    exportTargets: ["teaching-bundle", "meta-quest", "simodont"],
    teachingUses: ["Emergency dentistry scenarios", "Meta Quest VR case review", "OBJ/GLB for slides"],
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
