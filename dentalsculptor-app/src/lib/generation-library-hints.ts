import type { ClinicalParameterField } from "@/lib/clinical-case-params";
import type { ClinicalParameterValues } from "@/lib/case-recipe-utils";
import type { GenerationLibraryItem } from "@/lib/generation-library";
import { fdiToothType } from "@/lib/tooth-taxonomy";

const STORAGE_KEY = "ds-generation-library-hints";

export type GenerationLibraryHints = {
  libraryId?: string;
  libraryTitle?: string;
  fdiTooth?: string;
  toothType?: GenerationLibraryItem["toothType"];
};

export function setGenerationLibraryHints(item: GenerationLibraryItem): void {
  if (typeof window === "undefined") return;
  const hints: GenerationLibraryHints = {
    libraryId: item.id,
    libraryTitle: item.title,
    fdiTooth: item.fdiHint,
    toothType: item.toothType,
  };
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(hints));
}

export function clearGenerationLibraryHints(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(STORAGE_KEY);
}

export function peekGenerationLibraryHints(): GenerationLibraryHints | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as GenerationLibraryHints;
  } catch {
    return null;
  }
}

export function applyLibraryHintsToClinicalValues(
  values: ClinicalParameterValues,
  fields: ClinicalParameterField[],
  hints: GenerationLibraryHints | null
): ClinicalParameterValues {
  if (!hints) return values;

  const next = { ...values };
  const hasFdiField = fields.some((f) => f.id === "fdiTooth");
  const hasTypeField = fields.some((f) => f.id === "toothType");

  if (hints.fdiTooth && hasFdiField) {
    next.fdiTooth = hints.fdiTooth;
    const inferred = fdiToothType(hints.fdiTooth);
    if (inferred && hasTypeField) next.toothType = inferred;
  }

  if (hints.toothType && hasTypeField && !next.toothType) {
    next.toothType = hints.toothType;
  }

  return next;
}
