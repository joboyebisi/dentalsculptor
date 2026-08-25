"use client";

import { BookOpen, Download } from "lucide-react";
import { FloatingEditorPanel } from "@/components/editor/floating-editor-panel";
import type { CaseRecipe } from "@/lib/clinical-case-params";
import type { CaseTemplate } from "@/lib/case-templates";
import { toothTypeLabel, fdiToothType } from "@/lib/tooth-taxonomy";

interface EditorCaseContextPanelProps {
  visible: boolean;
  minimized: boolean;
  onMinimize: () => void;
  onRestore: () => void;
  selectedCase: CaseTemplate | null;
  caseRecipe: CaseRecipe | null;
}

/** Shows the active teaching case — edit instructions come from the case wizard, not ad-hoc presets. */
export function EditorCaseContextPanel({
  visible,
  minimized,
  onMinimize,
  onRestore,
  selectedCase,
  caseRecipe,
}: EditorCaseContextPanelProps) {
  if (!visible || !selectedCase) return null;

  const fdi =
    typeof caseRecipe?.clinicalParameters?.fdiTooth === "string"
      ? caseRecipe.clinicalParameters.fdiTooth
      : undefined;
  const toothType = fdiToothType(fdi);

  return (
    <FloatingEditorPanel
      id="case-context"
      title="Teaching case"
      open
      minimized={minimized}
      onMinimize={onMinimize}
      onRestore={onRestore}
      defaultPosition={{ x: 16, y: 200 }}
      bodyClassName="w-64 space-y-2 p-3"
    >
      <p className="text-body-sm font-semibold text-on-surface">{selectedCase.title}</p>
      {fdi && (
        <p className="font-mono text-[11px] text-on-surface-variant">
          FDI {fdi}
          {toothType ? ` · ${toothTypeLabel(toothType)}` : ""}
        </p>
      )}
      <p className="text-[11px] leading-relaxed text-on-surface-variant">
        Case preset was set in the wizard. Paint the region, then preview the 3D model edit — we do not
        auto-detect tooth number from photos.
      </p>
      <div className="flex items-center gap-2 rounded-md bg-surface-container-low px-2 py-1.5 text-[10px] text-on-surface-variant">
        <BookOpen className="h-3.5 w-3.5 shrink-0" />
        <span>{selectedCase.learningObjectives[0]}</span>
      </div>
      <div className="flex items-center gap-2 text-[10px] text-on-surface-variant">
        <Download className="h-3.5 w-3.5 shrink-0" />
        Export: {selectedCase.exportRecommendation.replace(/-/g, " ")}
      </div>
    </FloatingEditorPanel>
  );
}
