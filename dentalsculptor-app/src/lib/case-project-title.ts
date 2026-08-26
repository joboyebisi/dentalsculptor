import type { CaseTemplate } from "@/lib/case-templates";
import type { ClinicalParameterValues } from "@/lib/case-recipe-utils";
import { fdiToothType, toothTypeLabel } from "@/lib/tooth-taxonomy";

/** Auto-title from case template + FDI tooth selection. User can rename in editor header. */
export function buildCaseProjectTitle(
  template: CaseTemplate,
  clinicalParameters: ClinicalParameterValues
): string {
  const fdi =
    typeof clinicalParameters.fdiTooth === "string"
      ? clinicalParameters.fdiTooth.trim()
      : "";
  const toothType =
    typeof clinicalParameters.toothType === "string"
      ? clinicalParameters.toothType
      : fdi
        ? fdiToothType(fdi)
        : null;

  const date = new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const parts = [template.title];
  if (fdi) parts.push(`FDI ${fdi}`);
  if (toothType) parts.push(toothTypeLabel(toothType as Parameters<typeof toothTypeLabel>[0]));
  parts.push(date);

  return parts.join(" · ");
}
