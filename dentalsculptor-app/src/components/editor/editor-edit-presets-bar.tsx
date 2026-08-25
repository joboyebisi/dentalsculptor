"use client";

import { cn } from "@/lib/utils";
import { EDIT_PRESETS, type EditPreset } from "@/lib/edit-presets";
import type { EditOperation } from "@/lib/edit-types";

interface EditorEditPresetsBarProps {
  visible: boolean;
  activePresetId?: string | null;
  onSelect: (preset: EditPreset) => void;
  className?: string;
}

/** Quick dental edit presets — sets operation + prompt when a mask region is active. */
export function EditorEditPresetsBar({
  visible,
  activePresetId,
  onSelect,
  className,
}: EditorEditPresetsBarProps) {
  if (!visible) return null;

  return (
    <div
      className={cn(
        "pointer-events-auto absolute left-1/2 bottom-36 z-20 flex max-w-[min(720px,calc(100%-2rem))] -translate-x-1/2 flex-col gap-1.5 rounded-xl border border-outline-variant bg-surface-container-lowest/95 px-3 py-2 shadow-md backdrop-blur-md",
        className
      )}
    >
      <p className="px-0.5 font-mono text-[10px] uppercase tracking-wider text-on-surface-variant">
        Edit presets
      </p>
      <div className="editor-scrollbar flex gap-1.5 overflow-x-auto pb-0.5">
        {EDIT_PRESETS.map((preset) => (
          <PresetChip
            key={preset.id}
            preset={preset}
            active={activePresetId === preset.id}
            onSelect={() => onSelect(preset)}
          />
        ))}
      </div>
    </div>
  );
}

function PresetChip({
  preset,
  active,
  onSelect,
}: {
  preset: EditPreset;
  active: boolean;
  onSelect: () => void;
}) {
  const opColor: Record<EditOperation, string> = {
    add: "border-tertiary/50 text-tertiary",
    remove: "border-error/40 text-error",
    replace: "border-primary-container/50 text-primary-container",
  };

  return (
    <button
      type="button"
      onClick={onSelect}
      title={preset.prompt}
      className={cn(
        "shrink-0 rounded-lg border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors",
        active
          ? "border-primary-container bg-primary-container/15 text-on-surface"
          : "border-outline-variant bg-surface-container-highest text-on-surface hover:border-outline"
      )}
    >
      <span className="block leading-tight">{preset.label}</span>
      <span className={cn("mt-0.5 block font-mono text-[9px] uppercase", opColor[preset.operation])}>
        {preset.operation}
      </span>
    </button>
  );
}
