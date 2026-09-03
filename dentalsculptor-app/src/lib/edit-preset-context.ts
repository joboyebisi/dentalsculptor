import type { CaseRecipe } from "@/lib/clinical-case-params";
import type { CaseTemplate } from "@/lib/case-templates";
import {
  fdiToArch,
  fdiToothType,
  inferToothTypeFromAspect,
  type ToothArch,
  type ToothType,
} from "@/lib/tooth-taxonomy";
import type { EditPreset } from "@/lib/edit-presets";
import { isPresetCompatibleWithToothType } from "@/lib/tooth-taxonomy";

export interface EditPresetContext {
  fdi: string | null;
  toothType: ToothType | null;
  arch: ToothArch | null;
  surface: string | null;
  templateId: string | null;
  inferredFromMesh: boolean;
}

export function resolveEditPresetContext(
  caseRecipe: CaseRecipe | null,
  selectedCase: CaseTemplate | null,
  meshAspect?: number | null
): EditPresetContext {
  const fdi =
    typeof caseRecipe?.clinicalParameters?.fdiTooth === "string"
      ? caseRecipe.clinicalParameters.fdiTooth
      : null;
  const declaredType =
    typeof caseRecipe?.clinicalParameters?.toothType === "string"
      ? (caseRecipe.clinicalParameters.toothType as ToothType)
      : null;
  const fromFdi = fdiToothType(fdi);
  const inferred =
    !fromFdi && !declaredType && meshAspect != null
      ? inferToothTypeFromAspect(meshAspect)
      : null;

  return {
    fdi,
    toothType: fromFdi ?? declaredType ?? inferred,
    arch: fdiToArch(fdi),
    surface:
      typeof caseRecipe?.clinicalParameters?.surface === "string"
        ? caseRecipe.clinicalParameters.surface
        : null,
    templateId: selectedCase?.id ?? caseRecipe?.templateId ?? null,
    inferredFromMesh: Boolean(inferred && !fromFdi && !declaredType),
  };
}

export function filterPresetsForContext(
  presets: EditPreset[],
  ctx: EditPresetContext
): { preset: EditPreset; compatible: boolean; reason?: string }[] {
  return presets.map((preset) => {
    if (!isPresetCompatibleWithToothType(preset.compatibleToothTypes, ctx.toothType)) {
      return {
        preset,
        compatible: false,
        reason: `For ${preset.compatibleToothTypes?.map((t) => t + "s").join("/")} — your case is ${ctx.toothType ?? "unknown type"}`,
      };
    }
    if (
      preset.linkedTemplateIds?.length &&
      ctx.templateId &&
      !preset.linkedTemplateIds.includes(ctx.templateId)
    ) {
      return {
        preset,
        compatible: false,
        reason: "This edit is not validated for the selected case template.",
      };
    }
    if (preset.preferredSurfaces?.length && ctx.surface) {
      if (!preset.preferredSurfaces.includes(ctx.surface)) {
        return {
          preset,
          compatible: true,
          reason: `Best on ${preset.preferredSurfaces.join("/")} — case surface is ${ctx.surface}`,
        };
      }
    }
    return { preset, compatible: true };
  });
}
