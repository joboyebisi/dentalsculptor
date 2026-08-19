/**
 * Client-safe case recipe helpers (no Prisma / Node-only imports).
 */

import type { CaseTemplate } from "@/lib/case-templates";
import type {
  AnatomyRoleAssignment,
  CaseRecipe,
  ClinicalParameterField,
} from "@/lib/clinical-case-params";

export type ClinicalParameterValues = Record<
  string,
  string | number | boolean | string[]
>;

export interface ApplyCaseTemplateInput {
  templateId: string;
  clinicalParameters: ClinicalParameterValues;
  promptRefinement?: string;
}

export function validateClinicalParameters(
  fields: ClinicalParameterField[],
  values: ClinicalParameterValues
): string | null {
  for (const field of fields) {
    if (!field.required) continue;
    const v = values[field.id];
    if (v === undefined || v === null || v === "") {
      return `${field.label} is required.`;
    }
    if (Array.isArray(v) && v.length === 0) {
      return `${field.label} is required.`;
    }
  }
  return null;
}

export function buildAnatomyRoles(
  template: CaseTemplate,
  clinicalParameters: ClinicalParameterValues
): AnatomyRoleAssignment[] {
  const fdi =
    typeof clinicalParameters.fdiTooth === "string"
      ? clinicalParameters.fdiTooth
      : undefined;

  return template.defaultAnatomyRoles.map((r) => ({
    partLabel: r.partLabel,
    role: r.role,
    tissue: r.tissue as AnatomyRoleAssignment["tissue"],
    fdi: r.role !== "context" ? fdi : undefined,
  }));
}

export function buildAssessmentFromTemplate(
  template: CaseTemplate,
  clinicalParameters: ClinicalParameterValues
): CaseRecipe["assessment"] {
  const protectedLabels = template.defaultAnatomyRoles
    .filter((r) => r.role === "protected")
    .map((r) => r.partLabel);

  const targetLabels = template.defaultAnatomyRoles
    .filter((r) => r.role === "target")
    .map((r) => r.partLabel);

  if (Array.isArray(clinicalParameters.protectedTissues)) {
    protectedLabels.push(
      ...clinicalParameters.protectedTissues.map((t) => String(t))
    );
  }

  return {
    targetRegions: targetLabels,
    protectedRegions: protectedLabels,
    toleranceMm:
      typeof clinicalParameters.occlusalReductionMm === "number"
        ? clinicalParameters.occlusalReductionMm
        : undefined,
    criticalErrors: [
      "Damage to protected pulp or gingival margin",
      "Prep extends beyond marked target region",
    ],
    rubricItems: template.assessmentPrompts,
  };
}

export function buildCaseRecipe(
  template: CaseTemplate,
  clinicalParameters: ClinicalParameterValues,
  promptRefinement?: string
): CaseRecipe {
  return {
    workflow: template.workflow,
    templateId: template.id,
    clinicalParameters,
    anatomyRoles: buildAnatomyRoles(template, clinicalParameters),
    learnerStartState: {
      defaultView: "occlusal",
      visibleReferences: ["odontogram"],
    },
    assessment: buildAssessmentFromTemplate(template, clinicalParameters),
    promptRefinement: promptRefinement?.trim() || undefined,
  };
}

export function buildEditPromptFromRecipe(recipe: CaseRecipe, template: CaseTemplate): string {
  if (recipe.promptRefinement) return recipe.promptRefinement;

  const p = recipe.clinicalParameters;
  const fdi = p.fdiTooth ?? "tooth";

  if (template.procedure.startsWith("caries")) {
    return `remove carious tissue on ${p.surface ?? "occlusal"} surface at ${p.site ?? "lesion site"}, depth ${p.depth ?? "cavitated"}, preserving pulp (${p.pulpProximity ?? "not involved"}) on FDI ${fdi}`;
  }
  if (template.procedure === "crown-prep") {
    return `reduce FDI ${fdi} for full crown: ${p.marginType ?? "chamfer"} margin, target occlusal reduction ${p.occlusalReductionMm ?? 1.5} mm`;
  }
  if (template.procedure === "endo-access") {
    return `create endodontic access on FDI ${fdi}, ${p.accessType ?? "molar"} access, locate canals ${Array.isArray(p.canalsExpected) ? p.canalsExpected.join(", ") : "as marked"}`;
  }
  if (template.procedure === "anatomy-identification") {
    return template.suggestedPrompts[0] ?? `identify structures on FDI ${fdi}`;
  }

  return template.suggestedPrompts[0] ?? "";
}

export function formatInstructionsFromRecipe(recipe: CaseRecipe, template: CaseTemplate): string {
  const lines = [
    `Case template: ${template.title}`,
    "",
    "Clinical parameters:",
    ...Object.entries(recipe.clinicalParameters).map(([k, v]) => {
      const label = template.clinicalParameterFields.find((f) => f.id === k)?.label ?? k;
      const display = Array.isArray(v) ? v.join(", ") : String(v);
      return `• ${label}: ${display}`;
    }),
    "",
    "Anatomy roles:",
    ...recipe.anatomyRoles.map((r) => `• ${r.partLabel} — ${r.role}${r.fdi ? ` (FDI ${r.fdi})` : ""}`),
  ];
  return lines.join("\n");
}

export function parseCaseRecipeFromProject(project: {
  category?: string | null;
  versions?: { label: string | null; snapshot: unknown }[];
}): CaseRecipe | null {
  const version = project.versions?.[0];
  if (version?.label === "case-recipe" && version.snapshot && typeof version.snapshot === "object") {
    return version.snapshot as CaseRecipe;
  }
  return null;
}
