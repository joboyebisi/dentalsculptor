"use client";

import { Check, Eye, Paintbrush, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { EditWorkflowStep } from "@/lib/edit-workflow-steps";

export function GuidedCaseEditBar({
  caseTitle,
  instruction,
  step,
  previewLoading,
  editLoading,
  onPaint,
  onPreview,
  onCreate,
  markLabel,
  previewLabel,
  createLabel,
}: {
  caseTitle: string;
  instruction: string;
  step: EditWorkflowStep;
  previewLoading: boolean;
  editLoading: boolean;
  onPaint: () => void;
  onPreview: () => void;
  onCreate: () => void;
  markLabel: string;
  previewLabel: string;
  createLabel: string;
}) {
  const hasTarget = step !== "paint";
  const hasPreview = step === "submit";
  return (
    <div className="z-30 flex shrink-0 items-center gap-4 border-t border-outline-variant bg-surface px-4 py-3 shadow-[0_-8px_24px_rgba(15,61,145,0.08)]">
      <div className="min-w-0 flex-1">
        <p className="truncate text-body-sm font-semibold text-on-surface">{caseTitle}</p>
        <p className="truncate text-xs text-on-surface-variant">{instruction}</p>
      </div>
      <div className="hidden items-center gap-1.5 text-[11px] text-on-surface-variant lg:flex">
        <span className={hasTarget ? "text-secondary" : "font-semibold text-primary-container"}>{hasTarget ? <Check className="inline h-3.5 w-3.5" /> : "1"} Mark</span>
        <span>→</span>
        <span className={hasPreview ? "text-secondary" : hasTarget ? "font-semibold text-primary-container" : ""}>{hasPreview ? <Check className="inline h-3.5 w-3.5" /> : "2"} Preview</span>
        <span>→</span>
        <span className={hasPreview ? "font-semibold text-primary-container" : ""}>3 Create</span>
      </div>
      {!hasTarget ? (
        <Button onClick={onPaint} className="bg-primary-container text-on-primary"><Paintbrush className="mr-2 h-4 w-4" />{markLabel}</Button>
      ) : !hasPreview ? (
        <Button onClick={onPreview} disabled={previewLoading} className="bg-primary-container text-on-primary"><Eye className="mr-2 h-4 w-4" />{previewLoading ? "Preparing preview…" : previewLabel}</Button>
      ) : (
        <Button onClick={onCreate} disabled={editLoading} className="bg-primary-container text-on-primary"><Sparkles className="mr-2 h-4 w-4" />{editLoading ? "Creating…" : createLabel}</Button>
      )}
    </div>
  );
}
