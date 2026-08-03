"use client";

import { Settings, CheckCircle2, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SegmentPart } from "@/lib/editor-segmentation";

interface EditorPropertiesPanelProps {
  open: boolean;
  onToggle: () => void;
  hasModel: boolean;
  segmentParts: SegmentPart[];
  onTogglePart: (id: string) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  segmenting?: boolean;
}

export function EditorPropertiesPanel({
  open,
  onToggle,
  hasModel,
  segmentParts,
  onTogglePart,
  onSelectAll,
  onDeselectAll,
  segmenting,
}: EditorPropertiesPanelProps) {
  const selectedCount = segmentParts.filter((p) => p.visible).length;

  return (
    <aside
      className={cn(
        "editor-scrollbar flex h-full shrink-0 flex-col overflow-hidden border-l border-outline-variant bg-panel-bg transition-all duration-200",
        open ? "w-[220px]" : "w-10"
      )}
    >
      {open ? (
        <>
          <div className="flex items-center justify-between border-b border-outline-variant px-3 py-3">
            <div className="flex items-center gap-2">
              <Settings className="h-4 w-4 text-on-surface-variant" />
              <span className="text-label-caps font-bold text-on-surface">Parts</span>
            </div>
            <button
              type="button"
              onClick={onToggle}
              className="rounded p-1 text-on-surface-variant hover:bg-surface-container"
              aria-label="Collapse parts panel"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <div className="editor-scrollbar flex-1 overflow-y-auto p-3">
            {!hasModel ? (
              <div className="rounded-lg border border-dashed border-outline-variant bg-surface-container-lowest p-4 text-center">
                <Settings className="mx-auto mb-2 h-7 w-7 text-outline" />
                <p className="text-body-sm font-medium text-on-surface">No model yet</p>
                <p className="mt-1 text-[11px] leading-relaxed text-on-surface-variant">
                  Generate a 3D model to see segmented parts here.
                </p>
              </div>
            ) : segmenting ? (
              <div className="space-y-3 py-6 text-center">
                <div className="mx-auto h-7 w-7 animate-spin rounded-full border-2 border-primary-container border-t-transparent" />
                <p className="text-body-sm text-on-surface-variant">Segmenting…</p>
              </div>
            ) : (
              <>
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-[11px] text-on-surface-variant">
                    {selectedCount}/{segmentParts.length} selected
                  </p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={onSelectAll}
                      className="text-[10px] font-medium text-primary-container hover:underline"
                    >
                      All
                    </button>
                    <button
                      type="button"
                      onClick={onDeselectAll}
                      className="text-[10px] font-medium text-on-surface-variant hover:underline"
                    >
                      None
                    </button>
                  </div>
                </div>

                <ul className="space-y-1">
                  {segmentParts.map((part) => (
                    <li key={part.id}>
                      <label
                        className={cn(
                          "flex cursor-pointer items-center gap-2 rounded-lg border px-2.5 py-2 transition-colors",
                          part.visible
                            ? "border-border-subtle bg-surface-container-lowest hover:bg-surface-container-low"
                            : "border-transparent bg-surface-container/40 opacity-55 hover:opacity-75"
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={part.visible}
                          onChange={() => onTogglePart(part.id)}
                          className="h-3.5 w-3.5 rounded border-outline-variant accent-primary-container"
                        />
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-sm border border-border-subtle"
                          style={{ backgroundColor: part.color }}
                        />
                        <span className="min-w-0 flex-1 truncate text-body-sm font-medium text-on-surface">
                          {part.label}
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>

          <div className="border-t border-outline-variant bg-surface-container-lowest px-3 py-2">
            <div className="flex items-center gap-1 text-[10px] text-on-surface-variant">
              <CheckCircle2 className="h-3 w-3 text-secondary" />
              Segmentation
            </div>
          </div>
        </>
      ) : (
        <button
          type="button"
          onClick={onToggle}
          className="flex h-full w-full flex-col items-center gap-2 py-4 text-on-surface-variant hover:bg-surface-container-low hover:text-primary-container"
          aria-label="Expand parts panel"
        >
          <ChevronLeft className="h-4 w-4" />
          <Settings className="h-4 w-4" />
        </button>
      )}
    </aside>
  );
}
