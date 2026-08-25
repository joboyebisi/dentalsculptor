"use client";

import { BookOpen, Target, Shield, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CaseRecipe } from "@/lib/clinical-case-params";
import type { CaseTemplate } from "@/lib/case-templates";
import type { EditOperation } from "@/lib/edit-types";
import { operationLabel } from "@/lib/edit-workflow-steps";

interface EditorCasePanelProps {
  open: boolean;
  onToggle: () => void;
  caseRecipe: CaseRecipe | null;
  selectedCase: CaseTemplate | null;
  instructions: string | null;
  learningObjectives: Array<{ id: string; title: string }>;
  onSelectPrompt?: (prompt: string) => void;
  selectedPrompt?: string | null;
  activeOperation?: EditOperation;
  onStartMaskEdit?: () => void;
}

export function EditorCasePanel({
  open,
  onToggle,
  caseRecipe,
  selectedCase,
  instructions,
  learningObjectives,
  onSelectPrompt,
  selectedPrompt,
  activeOperation,
  onStartMaskEdit,
}: EditorCasePanelProps) {
  if (!open) {
    return (
      <button
        type="button"
        onClick={onToggle}
        className="editor-chrome-panel flex h-10 w-10 shrink-0 items-center justify-center border-l border-outline-variant text-on-surface-variant hover:bg-surface-container-low"
        title="Open case panel"
      >
        <BookOpen className="h-4 w-4" />
      </button>
    );
  }

  return (
    <aside className="editor-chrome-panel flex h-full w-64 shrink-0 flex-col border-l border-outline-variant bg-surface-container-lowest">
      <div className="flex items-center justify-between border-b border-outline-variant px-3 py-2">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-primary-container" />
          <span className="text-label-caps font-bold text-on-surface">Case</span>
        </div>
        <button type="button" onClick={onToggle} className="text-xs text-on-surface-variant hover:underline">
          Hide
        </button>
      </div>

      <div className="editor-scrollbar flex-1 overflow-y-auto p-3 text-body-sm">
        {selectedCase ? (
          <>
            <p className="font-semibold text-on-surface">{selectedCase.title}</p>
            <p className="mt-1 text-[11px] text-on-surface-variant">{selectedCase.shortDescription}</p>
          </>
        ) : (
          <p className="text-on-surface-variant">No case template applied yet.</p>
        )}

        {caseRecipe && (
          <div className="mt-4 space-y-3">
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
                Clinical parameters
              </p>
              <ul className="space-y-0.5 text-[11px] text-on-surface">
                {Object.entries(caseRecipe.clinicalParameters).map(([k, v]) => (
                  <li key={k}>
                    <span className="text-on-surface-variant">{k}:</span>{" "}
                    {Array.isArray(v) ? v.join(", ") : String(v)}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
                Anatomy roles
              </p>
              <ul className="space-y-1">
                {caseRecipe.anatomyRoles.map((r) => (
                  <li key={r.partLabel} className="flex items-start gap-1.5 text-[11px]">
                    {r.role === "target" ? (
                      <Target className="mt-0.5 h-3 w-3 shrink-0 text-tertiary" />
                    ) : r.role === "protected" ? (
                      <Shield className="mt-0.5 h-3 w-3 shrink-0 text-secondary" />
                    ) : (
                      <span className="mt-0.5 h-3 w-3 shrink-0 rounded-full bg-outline-variant" />
                    )}
                    <span>
                      {r.partLabel}{" "}
                      <span className="text-on-surface-variant">({r.role})</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {selectedCase && selectedCase.suggestedPrompts.length > 0 && (
          <div className="mt-4">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
              Suggested edits
            </p>
            <ul className="space-y-1.5">
              {selectedCase.suggestedPrompts.map((prompt) => {
                const selected = selectedPrompt === prompt;
                return (
                  <li key={prompt}>
                    <button
                      type="button"
                      onClick={() => onSelectPrompt?.(prompt)}
                      className={cn(
                        "flex w-full items-start gap-2 rounded-md border px-2 py-1.5 text-left text-[11px] transition-all",
                        selected
                          ? "border-primary-container bg-primary-container/10 text-on-surface ring-2 ring-primary-container/25"
                          : "border-outline-variant bg-surface-container-low text-on-surface hover:border-primary-container/40 hover:bg-surface-container"
                      )}
                    >
                      <Check
                        className={cn(
                          "mt-0.5 h-3.5 w-3.5 shrink-0",
                          selected ? "text-primary-container" : "text-transparent"
                        )}
                        aria-hidden
                      />
                      <span>{prompt}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
            {activeOperation && (
              <p className="mt-2 text-[10px] text-on-surface-variant">
                Operation:{" "}
                <span className="font-semibold uppercase text-tertiary">
                  {operationLabel(activeOperation)}
                </span>
              </p>
            )}
          </div>
        )}

        {selectedCase && selectedCase.studentHints.length > 0 && (
          <div className="mt-4">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
              Hints
            </p>
            <ul className="list-inside list-disc space-y-1 text-[11px] text-on-surface-variant">
              {selectedCase.studentHints.map((hint) => (
                <li key={hint}>{hint}</li>
              ))}
            </ul>
          </div>
        )}

        {selectedCase && onStartMaskEdit && (
          <button
            type="button"
            onClick={onStartMaskEdit}
            className="mt-4 w-full rounded-lg bg-primary-container px-3 py-2 text-[11px] font-semibold text-on-primary hover:opacity-90"
          >
            Start mask edit ({selectedCase.defaultOperation})
          </button>
        )}

        {learningObjectives.length > 0 && (
          <div className="mt-4">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
              Learning objectives
            </p>
            <ul className="list-inside list-disc space-y-1 text-[11px] text-on-surface">
              {learningObjectives.map((lo) => (
                <li key={lo.id}>{lo.title}</li>
              ))}
            </ul>
          </div>
        )}

        {instructions && (
          <div className="mt-4">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
              Clinical notes
            </p>
            <pre className="whitespace-pre-wrap rounded-lg border border-outline-variant bg-surface-container-low p-2 text-[10px] leading-relaxed text-on-surface">
              {instructions}
            </pre>
          </div>
        )}
      </div>
    </aside>
  );
}
