"use client";

import { useEffect, useMemo, useState } from "react";
import { X, Sparkles, ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  CASE_TEMPLATES,
  listCaseTemplates,
  listPrimaryCaseTemplates,
  studentYearLabel,
  type CaseTemplate,
  type StudentYearLevel,
} from "@/lib/case-templates";
import {
  EDUCATOR_CASE_PICKS,
  type EducatorCaseCategory,
  getEducatorCasePick,
  templatesForEducatorPick,
} from "@/lib/educator-case-picks";
import type { ClinicalParameterValues } from "@/lib/case-recipe-utils";
import { validateClinicalParameters } from "@/lib/case-recipe-utils";
import {
  CaseWizardClinicalForm,
  defaultClinicalValues,
} from "@/components/case-wizard/case-wizard-clinical-form";
import { cn } from "@/lib/utils";
import { peekGenerationLibraryHints } from "@/lib/generation-library-hints";

export interface CaseWizardContinuePayload {
  template: CaseTemplate | null;
  clinicalParameters: ClinicalParameterValues;
  promptRefinement?: string;
}

interface CaseWizardDialogProps {
  open: boolean;
  onClose: () => void;
  onContinue: (payload: CaseWizardContinuePayload) => void | Promise<void>;
  applying?: boolean;
}

const PROCEDURE_FILTERS = [
  "All",
  "Anatomy",
  "Caries",
  "Operative",
  "Crown",
  "Endo",
  "Pathology",
] as const;

type WizardStep = "category" | "pick" | "params";

function matchesProcedureFilter(template: CaseTemplate, filter: string): boolean {
  if (filter === "All") return true;
  const map: Record<string, string[]> = {
    Anatomy: ["anatomy-identification"],
    Caries: ["caries-occlusal", "caries-smooth-surface"],
    Operative: ["prep-class-1", "prep-class-2"],
    Crown: ["crown-prep"],
    Endo: ["endo-access"],
    Pathology: ["pathology-add"],
  };
  return map[filter]?.includes(template.procedure) ?? false;
}

export function CaseWizardDialog({ open, onClose, onContinue, applying = false }: CaseWizardDialogProps) {
  const [step, setStep] = useState<WizardStep>("category");
  const [years, setYears] = useState<StudentYearLevel[]>([1, 2, 3]);
  const [educatorCategory, setEducatorCategory] = useState<EducatorCaseCategory | null>(null);
  const [procedureFilter, setProcedureFilter] = useState<string>("All");
  const [selectedId, setSelectedId] = useState<string | null>(
    listPrimaryCaseTemplates()[0]?.id ?? CASE_TEMPLATES[0]?.id ?? null
  );
  const [clinicalParameters, setClinicalParameters] = useState<ClinicalParameterValues>({});
  const [promptRefinement, setPromptRefinement] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const selectedTemplate = useMemo(
    () => CASE_TEMPLATES.find((x) => x.id === selectedId) ?? null,
    [selectedId]
  );

  const filtered = useMemo(() => {
    if (educatorCategory) {
      const pick = getEducatorCasePick(educatorCategory);
      if (pick) return templatesForEducatorPick(pick);
    }
    return listCaseTemplates().filter((t) => {
      const yearOk = years.length === 0 || t.studentYearLevels.some((y) => years.includes(y));
      return yearOk && matchesProcedureFilter(t, procedureFilter);
    });
  }, [years, procedureFilter, educatorCategory]);

  useEffect(() => {
    if (!open) {
      setStep("category");
      setEducatorCategory(null);
      setFormError(null);
    }
  }, [open]);

  useEffect(() => {
    if (selectedTemplate) {
      setClinicalParameters(defaultClinicalValues(selectedTemplate.clinicalParameterFields));
    }
  }, [selectedTemplate?.id]);

  if (!open) return null;

  const libraryHints = peekGenerationLibraryHints();

  const toggleYear = (y: StudentYearLevel) => {
    setYears((prev) => (prev.includes(y) ? prev.filter((x) => x !== y) : [...prev, y]));
  };

  const pickEducatorCategory = (category: EducatorCaseCategory) => {
    const pick = getEducatorCasePick(category);
    setEducatorCategory(category);
    setYears(pick?.studentYearLevels ?? [1, 2, 3]);
    setSelectedId(pick?.primaryTemplateId ?? null);
    setStep("pick");
  };

  const goToParams = () => {
    if (!selectedTemplate) return;
    setClinicalParameters(defaultClinicalValues(selectedTemplate.clinicalParameterFields));
    setFormError(null);
    setStep("params");
  };

  const handleApply = () => {
    if (!selectedTemplate) return;
    const err = validateClinicalParameters(
      selectedTemplate.clinicalParameterFields,
      clinicalParameters
    );
    if (err) {
      setFormError(err);
      return;
    }
    setFormError(null);
    void onContinue({
      template: selectedTemplate,
      clinicalParameters,
      promptRefinement: promptRefinement.trim() || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-[90] flex bg-on-surface/50 backdrop-blur-sm">
      <div className="flex h-full w-full flex-col bg-background md:flex-row">
        <aside className="w-full shrink-0 border-b border-outline-variant bg-surface-container-lowest p-6 md:w-72 md:border-b-0 md:border-r">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="font-mono text-xs uppercase tracking-wider text-on-surface-variant">Filters</h2>
            <button type="button" onClick={onClose} className="rounded-full p-1 hover:bg-surface-container-high md:hidden">
              <X className="h-5 w-5" />
            </button>
          </div>

          {step === "category" && (
            <div className="space-y-4 text-body-sm text-on-surface-variant">
              <p className="font-medium text-on-surface">Educator quick picks</p>
              <p>
                We do not auto-detect tooth number from photos yet — confirm FDI in the next step.
                {libraryHints?.libraryTitle ? (
                  <>
                    {" "}
                    Your library image (
                    <span className="font-medium text-on-surface">{libraryHints.libraryTitle}</span>
                    ) may pre-fill tooth number — please verify.
                  </>
                ) : null}
              </p>
            </div>
          )}

          {step === "pick" && (
            <>
              <div className="mb-6">
                <h3 className="mb-2 text-body-sm font-semibold text-on-surface">Study year</h3>
                <div className="space-y-2">
                  {([1, 2, 3, 4, 5] as StudentYearLevel[]).map((y) => (
                    <label key={y} className="flex cursor-pointer items-center gap-2">
                      <input
                        type="checkbox"
                        checked={years.includes(y)}
                        onChange={() => toggleYear(y)}
                        className="rounded border-outline-variant text-primary-container focus:ring-primary-container"
                      />
                      <span className={cn("text-body-sm", years.includes(y) && "font-medium text-primary-container")}>
                        {studentYearLabel(y)}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-body-sm font-semibold text-on-surface">Procedure</h3>
                <div className="flex flex-wrap gap-2">
                  {PROCEDURE_FILTERS.map((f) => (
                    <button
                      key={f}
                      type="button"
                      onClick={() => setProcedureFilter(f)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                        procedureFilter === f
                          ? "border-primary-container bg-primary-container/10 text-primary-container"
                          : "border-outline-variant text-on-surface-variant hover:bg-surface-container-low"
                      )}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          {step === "params" && selectedTemplate && (
            <div className="space-y-4 text-body-sm text-on-surface-variant">
              <p>
                <span className="font-semibold text-on-surface">{selectedTemplate.title}</span>
              </p>
              <p>{selectedTemplate.shortDescription}</p>
              <ul className="space-y-1 text-[11px]">
                {selectedTemplate.learningObjectives.map((lo) => (
                  <li key={lo}>• {lo}</li>
                ))}
              </ul>
            </div>
          )}
        </aside>

        <main className="flex min-h-0 flex-1 flex-col">
          <div className="border-b border-outline-variant bg-surface-container-low px-6 py-4">
            <div className="mx-auto flex max-w-3xl items-center justify-between gap-4">
              <div className="flex flex-1 items-center justify-between">
                {["Upload", "Case", "Generate", "Edit", "Export"].map((label, i) => (
                  <div key={label} className="flex flex-col items-center gap-1">
                    <div
                      className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold",
                        i === 0 || i === 1
                          ? i === 1 && step === "params"
                            ? "bg-primary-container text-on-primary"
                            : i <= 1
                              ? "bg-primary-container/20 text-primary-container"
                              : "bg-surface-container-high text-on-surface-variant"
                          : i === 2
                            ? "bg-primary-container/20 text-primary-container"
                            : "bg-surface-container-high text-on-surface-variant"
                      )}
                    >
                      {i === 0 ? "✓" : i === 2 ? "✓" : i + 1}
                    </div>
                    <span
                      className={cn(
                        "text-[10px] font-semibold uppercase",
                        i === 1 ? "text-primary-container" : "text-on-surface-variant"
                      )}
                    >
                      {label}
                    </span>
                  </div>
                ))}
              </div>
              <button type="button" onClick={onClose} className="hidden rounded-full p-2 hover:bg-surface-container-high md:block">
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {step === "category" ? (
              <>
                <h1 className="mb-2 text-headline-md font-semibold text-on-surface">
                  Choose a teaching case
                </h1>
                <p className="mb-6 max-w-2xl text-body-sm text-on-surface-variant">
                  For BDS Years 1–3: pick a case type, confirm the FDI tooth matches your uploaded
                  photo, then export to simulators, Meta Quest, or PowerPoint-friendly bundles.
                </p>
                <div className="grid gap-4 sm:grid-cols-2">
                  {EDUCATOR_CASE_PICKS.map((pick) => (
                    <button
                      key={pick.id}
                      type="button"
                      onClick={() => pickEducatorCategory(pick.id)}
                      className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5 text-left transition-all hover:border-primary-container/40 hover:shadow-md"
                    >
                      <h3 className="font-semibold text-on-surface">{pick.label}</h3>
                      <p className="mt-1 text-body-sm text-on-surface-variant">{pick.subtitle}</p>
                      <p className="mt-3 text-[11px] text-on-surface-variant">
                        Years {pick.studentYearLevels.join(", ")} ·{" "}
                        {pick.exportTargets.map((t) => t.replace(/-/g, " ")).join(" · ")}
                      </p>
                    </button>
                  ))}
                </div>
              </>
            ) : step === "pick" ? (
              <>
                <h1 className="mb-2 text-headline-md font-semibold text-on-surface">Choose a clinical case</h1>
                <p className="mb-6 max-w-2xl text-body-sm text-on-surface-variant">
                  Pick a teaching template, then enter structured clinical parameters — tooth, site, depth,
                  protected tissues — before optional AI refinement.
                </p>

                {filtered.length === 0 ? (
                  <p className="text-body-sm text-on-surface-variant">No templates match — clear filters or use a custom case.</p>
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    {filtered.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setSelectedId(t.id)}
                        className={cn(
                          "rounded-xl border p-4 text-left transition-all hover:shadow-md",
                          selectedId === t.id
                            ? "border-primary-container bg-primary-container/5 ring-2 ring-primary-container/20"
                            : "border-outline-variant bg-surface-container-lowest hover:border-primary-container/30"
                        )}
                      >
                        <div className="mb-2 flex items-start justify-between gap-2">
                          <h3 className="font-semibold text-on-surface">{t.title}</h3>
                          {selectedId === t.id && <Sparkles className="h-4 w-4 shrink-0 text-tertiary" />}
                        </div>
                        <p className="mb-3 text-body-sm text-on-surface-variant">{t.shortDescription}</p>
                        <div className="flex flex-wrap gap-1.5">
                          {t.primaryTemplate && (
                            <Badge className="border-0 bg-tertiary/15 text-[10px] text-tertiary">Recommended</Badge>
                          )}
                          <Badge variant="outline" className="text-[10px] capitalize">
                            {t.difficulty}
                          </Badge>
                          <Badge variant="outline" className="text-[10px]">
                            {t.clinicalParameterFields.length} fields
                          </Badge>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </>
            ) : (
              selectedTemplate && (
                <>
                  <h1 className="mb-2 text-headline-md font-semibold text-on-surface">Clinical parameters</h1>
                  <p className="mb-2 max-w-2xl text-body-sm text-on-surface-variant">
                    Fields marked <span className="text-error">*</span> are required. For mask edits, confirming{" "}
                    <strong>Tooth (FDI)</strong> is enough — other fields enrich teaching notes and assessment.
                  </p>
                  <p className="mb-6 max-w-2xl text-[11px] text-on-surface-variant">
                    We do not auto-detect tooth number from photos; FDI drives edit presets and suggested prompts.
                  </p>

                  <CaseWizardClinicalForm
                    fields={selectedTemplate.clinicalParameterFields}
                    values={clinicalParameters}
                    onChange={setClinicalParameters}
                    className="relative z-10 max-w-2xl"
                  />

                  <div className="mt-8 max-w-2xl">
                    <label className="mb-1.5 block text-body-sm font-medium text-on-surface">
                      Optional AI edit refinement
                    </label>
                    <textarea
                      rows={3}
                      className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-body-sm"
                      placeholder={
                        selectedTemplate.suggestedPrompts[0] ??
                        "Additional detail for generative edit (optional)…"
                      }
                      value={promptRefinement}
                      onChange={(e) => setPromptRefinement(e.target.value)}
                    />
                  </div>

                  {formError && (
                    <p className="mt-4 text-body-sm text-error" role="alert">
                      {formError}
                    </p>
                  )}

                  <div className="mt-6 max-w-2xl rounded-xl border border-outline-variant bg-surface-container-low p-4">
                    <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
                      Anatomy roles (from template)
                    </p>
                    <ul className="space-y-1 text-[11px] text-on-surface-variant">
                      {selectedTemplate.defaultAnatomyRoles.map((r) => (
                        <li key={r.partLabel}>
                          <span className="font-medium text-on-surface">{r.partLabel}</span> · {r.role}
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )
            )}
          </div>

          <div className="flex justify-between gap-2 border-t border-outline-variant bg-surface-container-lowest px-6 py-4">
            <div>
              {step === "pick" && (
                <Button type="button" variant="ghost" onClick={() => setStep("category")} disabled={applying}>
                  <ChevronLeft className="mr-1 h-4 w-4" />
                  Back
                </Button>
              )}
              {step === "params" && (
                <Button type="button" variant="ghost" onClick={() => setStep("pick")} disabled={applying}>
                  <ChevronLeft className="mr-1 h-4 w-4" />
                  Back
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="ghost"
                disabled={applying}
                onClick={() =>
                  onContinue({ template: null, clinicalParameters: {}, promptRefinement: undefined })
                }
              >
                Skip — custom case
              </Button>
              {step === "pick" ? (
                <Button
                  type="button"
                  className="bg-primary-container text-on-primary"
                  disabled={!selectedTemplate}
                  onClick={goToParams}
                >
                  Next — clinical parameters
                </Button>
              ) : (
                <Button
                  type="button"
                  className="bg-primary-container text-on-primary"
                  disabled={applying || !selectedTemplate}
                  onClick={handleApply}
                >
                  {applying ? "Saving case…" : "Apply template & continue"}
                </Button>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
