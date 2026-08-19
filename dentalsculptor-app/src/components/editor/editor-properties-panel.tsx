"use client";

import { Settings, CheckCircle2, ChevronLeft, ChevronRight, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SegmentPart } from "@/lib/editor-segmentation";

interface EditorPropertiesPanelProps {
  open: boolean;
  onToggle: () => void;
  hasModel: boolean;
  segmentParts: SegmentPart[];
  onTogglePart: (id: string) => void;
  onPartActivate?: (id: string) => void;
  activePartId?: string | null;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  segmenting?: boolean;
  /** When true, panel is read-only — segmentation coming in a later milestone. */
  disabled?: boolean;
}

export function EditorPropertiesPanel({
  open,
  onToggle,
  hasModel,
  segmentParts,
  onTogglePart,
  onPartActivate,
  activePartId,
  onSelectAll,
  onDeselectAll,
  segmenting,
  disabled = false,
}: EditorPropertiesPanelProps) {
  const selectedCount = segmentParts.filter((p) => p.visible).length;

  return (
    <aside
      className={cn(
        "editor-chrome-panel editor-scrollbar flex h-full shrink-0 flex-col overflow-hidden border-l border-outline-variant transition-all duration-200",
        open ? "w-[220px]" : "w-10",
        disabled && "opacity-60"
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

          <div className="relative editor-scrollbar flex-1 overflow-y-auto p-3">
            {disabled && (
              <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-surface-container-lowest/80 px-4 text-center backdrop-blur-[1px]">
                <Lock className="mb-2 h-6 w-6 text-on-surface-variant" />
                <p className="text-body-sm font-medium text-on-surface">Coming soon</p>
                <p className="mt-1 text-[11px] leading-relaxed text-on-surface-variant">
                  Anatomical part selection and IOS/CBCT segmentation arrive in a later release.
                </p>
              </div>
            )}

            {!hasModel ? (
              <div className="rounded-lg border border-dashed border-outline-variant bg-surface-container-lowest p-4 text-center">
                <Settings className="mx-auto mb-2 h-7 w-7 text-outline" />
                <p className="text-body-sm font-medium text-on-surface">No model yet</p>
                <p className="mt-1 text-[11px] leading-relaxed text-on-surface-variant">
                  Generate a 3D model to prepare segmented parts here.
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
                      disabled={disabled}
                      className="text-[10px] font-medium text-primary-container hover:underline disabled:pointer-events-none disabled:opacity-50"
                    >
                      All
                    </button>
                    <button
                      type="button"
                      onClick={onDeselectAll}
                      disabled={disabled}
                      className="text-[10px] font-medium text-on-surface-variant hover:underline disabled:pointer-events-none disabled:opacity-50"
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
                          "flex items-center gap-2 rounded-lg border px-2.5 py-2 transition-colors",
                          disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
                          activePartId === part.id
                            ? "border-primary-container bg-primary-container/20 ring-1 ring-primary-container/50"
                            : part.visible
                              ? "border-border-subtle bg-surface-container-lowest hover:bg-surface-container-low"
                              : "border-transparent bg-surface-container/40 opacity-55 hover:opacity-75"
                        )}
                        onClick={() => !disabled && onPartActivate?.(part.id)}
                      >
                        <input
                          type="checkbox"
                          checked={part.visible}
                          disabled={disabled}
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
              <CheckCircle2 className="h-3 w-3 text-outline" />
              Segmentation — upcoming
            </div>
          </div>
        </>
      ) : (
        <button
          type="button"
          onClick={onToggle}
          className="flex h-full w-full flex-col items-center gap-2 py-4 text-on-surface-variant hover:bg-surface-container-low hover:text-primary-container"
          aria-label="Expand parts panel"
          title="Model parts (coming soon)"
        >
          <ChevronLeft className="h-4 w-4" />
          <Settings className="h-4 w-4 opacity-60" />
        </button>
      )}
    </aside>
  );
}
