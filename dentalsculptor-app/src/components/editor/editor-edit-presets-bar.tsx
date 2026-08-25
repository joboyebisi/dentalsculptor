"use client";

import { AlertTriangle, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { EDIT_PRESETS, type EditPreset } from "@/lib/edit-presets";
import {
  filterPresetsForContext,
  type EditPresetContext,
} from "@/lib/edit-preset-context";
import { toothTypeLabel } from "@/lib/tooth-taxonomy";

interface EditorEditPresetsBarProps {
  visible: boolean;
  context: EditPresetContext;
  activePresetId?: string | null;
  onSelect: (preset: EditPreset) => void;
  className?: string;
}

/** Quick dental edit presets — filtered by FDI tooth type from the active case. */
export function EditorEditPresetsBar({
  visible,
  context,
  activePresetId,
  onSelect,
  className,
}: EditorEditPresetsBarProps) {
  if (!visible) return null;

  const filtered = filterPresetsForContext(EDIT_PRESETS, context);
  const compatible = filtered.filter((f) => f.compatible);
  const incompatible = filtered.filter((f) => !f.compatible);

  return (
    <div
      className={cn(
        "pointer-events-auto absolute left-1/2 bottom-36 z-20 flex max-w-[min(760px,calc(100%-2rem))] -translate-x-1/2 flex-col gap-2 rounded-xl border border-outline-variant bg-surface-container-lowest/95 px-3 py-2 shadow-md backdrop-blur-md",
        className
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 px-0.5">
        <p className="font-mono text-[10px] uppercase tracking-wider text-on-surface-variant">
          Edit presets
        </p>
        <ContextBadge context={context} />
      </div>

      <div className="editor-scrollbar flex gap-1.5 overflow-x-auto pb-0.5">
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
    </div>
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
        Inferred {toothTypeLabel(context.toothType)} — set FDI in case wizard for accuracy
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-[10px] text-amber-800">
      <AlertTriangle className="h-3 w-3" />
      No tooth type — open case wizard to pick FDI before cusp/molar presets
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
        "shrink-0 rounded-lg border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors",
        active
          ? "border-primary-container bg-primary-container/15 text-on-surface"
          : "border-outline-variant bg-surface-container-highest text-on-surface hover:border-outline"
      )}
    >
      <span className="block leading-tight">{preset.label}</span>
      <span className={cn("mt-0.5 block font-mono text-[9px] uppercase", opColor)}>
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
