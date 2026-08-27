"use client";

import { AlertTriangle, Check, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { EDIT_PRESETS, type EditPreset } from "@/lib/edit-presets";
import {
  filterPresetsForContext,
  type EditPresetContext,
} from "@/lib/edit-preset-context";
import { toothTypeLabel } from "@/lib/tooth-taxonomy";
import type { CaseTemplate } from "@/lib/case-templates";
import type { EditOperation } from "@/lib/edit-types";
import { operationLabel } from "@/lib/edit-workflow-steps";
import { FloatingEditorPanel } from "@/components/editor/floating-editor-panel";

interface EditorEditPresetsBarProps {
  visible: boolean;
  minimized: boolean;
  onMinimize: () => void;
  onRestore: () => void;
  context: EditPresetContext;
  selectedCase?: CaseTemplate | null;
  activePresetId?: string | null;
  selectedSuggestedPrompt?: string | null;
  activeOperation?: EditOperation;
  maskCoverage?: number;
  onSelect: (preset: EditPreset) => void;
  onSelectSuggestedPrompt?: (prompt: string) => void;
  className?: string;
}

/** Case-aware edit workflow — suggested edits + quick presets in the viewport. */
export function EditorEditPresetsBar({
  visible,
  minimized,
  onMinimize,
  onRestore,
  context,
  selectedCase,
  activePresetId,
  selectedSuggestedPrompt,
  activeOperation,
  maskCoverage = 0,
  onSelect,
  onSelectSuggestedPrompt,
  className,
}: EditorEditPresetsBarProps) {
  if (!visible) return null;

  const casePresets = selectedCase?.editPresetIds
    ? EDIT_PRESETS.filter((preset) => selectedCase.editPresetIds?.includes(preset.id))
    : EDIT_PRESETS;
  const filtered = filterPresetsForContext(casePresets, context);
  const compatible = filtered.filter((f) => f.compatible);
  const incompatible = filtered.filter((f) => !f.compatible);
  const suggestedPrompts = selectedCase?.editPresetIds?.length ? [] : selectedCase?.suggestedPrompts ?? [];
  const panelTitle = selectedCase ? `Case edits · ${selectedCase.title}` : "Edit presets";

  return (
    <FloatingEditorPanel
      id="edit-presets"
      title={panelTitle}
      open
      minimized={minimized}
      onMinimize={onMinimize}
      onRestore={onRestore}
      defaultPosition={{ x: 200, y: 400 }}
      className="border-primary-container/25 bg-[#eef1f6]/97 shadow-xl backdrop-blur-md"
      bodyClassName={cn("w-[min(420px,calc(100vw-2rem))] space-y-3 p-3", className)}
    >
      {selectedCase && (
        <div className="rounded-xl border border-primary-container/20 bg-gradient-to-br from-primary-container/8 to-surface-container-lowest px-3 py-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-label-caps text-[10px] font-bold tracking-wider text-primary-container">
              Step 2 · Choose the case action
            </p>
            {activeOperation && (
              <span className="rounded-full bg-tertiary-container/15 px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wide text-tertiary">
                {operationLabel(activeOperation)}
                {maskCoverage > 0 ? ` · ${Math.round(maskCoverage)}%` : ""}
              </span>
            )}
          </div>
          <p className="mt-1.5 text-body-sm leading-snug text-on-surface-variant">
            Mark or brush the target first, then choose one action. The operation and instruction
            are filled automatically; review them before previewing.
          </p>
        </div>
      )}

      {selectedCase?.requiresGeometryEdit === false && (
        <div className="rounded-xl border border-secondary/30 bg-secondary/10 px-3 py-2.5 text-body-sm text-on-surface">
          This case uses model rotation and annotations only. No generative geometry edit is required.
        </div>
      )}

      {suggestedPrompts.length > 0 && onSelectSuggestedPrompt && (
        <div className="space-y-2">
          <p className="text-label-caps text-[10px] font-bold tracking-wider text-on-surface-variant">
            Suggested for this case
          </p>
          <ul className="space-y-1.5">
            {suggestedPrompts.map((prompt) => {
              const selected = selectedSuggestedPrompt === prompt;
              return (
                <li key={prompt}>
                  <button
                    type="button"
                    onClick={() => onSelectSuggestedPrompt(prompt)}
                    className={cn(
                      "flex w-full items-start gap-2.5 rounded-xl border px-3 py-2 text-left transition-all",
                      selected
                        ? "border-primary-container bg-primary-container/10 text-on-surface shadow-sm ring-2 ring-primary-container/20"
                        : "border-outline-variant/80 bg-surface-container-lowest text-on-surface hover:border-primary-container/35 hover:bg-surface-container-low"
                    )}
                  >
                    <Check
                      className={cn(
                        "mt-0.5 h-4 w-4 shrink-0",
                        selected ? "text-primary-container" : "text-transparent"
                      )}
                      aria-hidden
                    />
                    <span className="text-body-sm leading-snug">{prompt}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-label-caps text-[10px] font-bold tracking-wider text-on-surface-variant">
            {selectedCase ? "Quick presets" : "Filtered for your tooth"}
          </p>
          <ContextBadge context={context} />
        </div>

        <div className="editor-scrollbar flex flex-wrap gap-1.5 pb-0.5">
          {compatible.map(({ preset, reason }) => (
            <PresetChip
              key={preset.id}
              preset={preset}
              active={activePresetId === preset.id}
              hint={reason}
              onSelect={() => onSelect(preset)}
            />
          ))}
        </div>
      </div>

      {incompatible.length > 0 && (
        <details className="text-[10px] text-on-surface-variant">
          <summary className="cursor-pointer hover:text-on-surface">
            {incompatible.length} preset{incompatible.length === 1 ? "" : "s"} hidden (wrong tooth type)
          </summary>
          <ul className="mt-1 space-y-0.5 pl-2">
            {incompatible.map(({ preset, reason }) => (
              <li key={preset.id}>
                {preset.label}: {reason}
              </li>
            ))}
          </ul>
        </details>
      )}
    </FloatingEditorPanel>
  );
}

function ContextBadge({ context }: { context: EditPresetContext }) {
  if (context.fdi && context.toothType) {
    return (
      <span className="rounded-md bg-surface-container-high px-2 py-0.5 font-mono text-[10px] text-on-surface">
        FDI {context.fdi} · {toothTypeLabel(context.toothType)}
        {context.surface ? ` · ${context.surface}` : ""}
      </span>
    );
  }
  if (context.toothType && context.inferredFromMesh) {
    return (
      <span className="flex items-center gap-1 rounded-md border border-amber-300/50 bg-amber-50 px-2 py-0.5 text-[10px] text-amber-950">
        <Info className="h-3 w-3" />
        Inferred {toothTypeLabel(context.toothType)} — set FDI in case wizard
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-[10px] text-amber-800">
      <AlertTriangle className="h-3 w-3" />
      Set FDI in case wizard for accurate presets
    </span>
  );
}

function PresetChip({
  preset,
  active,
  hint,
  onSelect,
}: {
  preset: EditPreset;
  active: boolean;
  hint?: string;
  onSelect: () => void;
}) {
  const opColor = {
    add: "text-tertiary",
    remove: "text-error",
    replace: "text-primary-container",
  }[preset.operation];

  return (
    <button
      type="button"
      onClick={onSelect}
      title={[preset.prompt, hint, preset.hapticNote].filter(Boolean).join(" — ")}
      className={cn(
        "shrink-0 rounded-xl border px-3 py-2 text-left transition-all",
        active
          ? "border-primary-container bg-primary-container/12 text-on-surface shadow-sm ring-2 ring-primary-container/25"
          : "border-outline-variant/80 bg-surface-container-lowest text-on-surface hover:border-outline"
      )}
    >
      <span className="block text-body-sm font-medium leading-tight">{preset.label}</span>
      <span className={cn("mt-1 block font-mono text-[9px] font-semibold uppercase tracking-wide", opColor)}>
        {preset.operation}
        {preset.editMode === "texture" ? " · look" : preset.editMode === "geometry" ? " · shape" : ""}
      </span>
    </button>
  );
}

interface EditPresetHapticNoticeProps {
  preset: EditPreset | null;
  className?: string;
}

/** Amber callout when a preset changes caries appearance but not simulator haptics. */
export function EditPresetHapticNotice({ preset, className }: EditPresetHapticNoticeProps) {
  if (!preset?.hapticNote) return null;
  return (
    <div
      className={cn(
        "flex gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] leading-snug text-amber-950",
        className
      )}
    >
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <p>{preset.hapticNote}</p>
    </div>
  );
}
