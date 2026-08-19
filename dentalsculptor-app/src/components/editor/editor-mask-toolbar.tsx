"use client";

import { Brush, Eraser, Undo2, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EditOperation } from "@/lib/edit-types";
import type { MaskBrushMode } from "@/components/editor/mask-paint-overlay";

interface EditorMaskToolbarProps {
  brushMode: MaskBrushMode;
  onBrushModeChange: (mode: MaskBrushMode) => void;
  brushSize: number;
  onBrushSizeChange: (size: number) => void;
  operation: EditOperation;
  onOperationChange: (op: EditOperation) => void;
  onUndo: () => void;
  onClear: () => void;
}

const OPERATIONS: { id: EditOperation; label: string }[] = [
  { id: "add", label: "Add" },
  { id: "remove", label: "Remove" },
  { id: "replace", label: "Replace" },
];

export function EditorMaskToolbar({
  brushMode,
  onBrushModeChange,
  brushSize,
  onBrushSizeChange,
  operation,
  onOperationChange,
  onUndo,
  onClear,
}: EditorMaskToolbarProps) {
  return (
    <div className="pointer-events-auto absolute bottom-6 left-1/2 z-20 flex -translate-x-1/2 flex-col items-center gap-2">
      <div className="flex items-center gap-1 rounded-full border border-outline-variant/80 bg-surface-container-lowest/90 px-3 py-2 shadow-lg backdrop-blur-md">
        <button
          type="button"
          title="Paint mask"
          onClick={() => onBrushModeChange("paint")}
          className={cn(
            "flex flex-col items-center gap-0.5 rounded-lg px-3 py-1.5 transition-colors",
            brushMode === "paint"
              ? "bg-primary-container/15 text-primary-container"
              : "text-on-surface-variant hover:bg-surface-container-high"
          )}
        >
          <Brush className="h-4 w-4" />
          <span className="text-[10px] font-semibold uppercase tracking-wide">Brush</span>
        </button>
        <button
          type="button"
          title="Erase mask"
          onClick={() => onBrushModeChange("erase")}
          className={cn(
            "flex flex-col items-center gap-0.5 rounded-lg px-3 py-1.5 transition-colors",
            brushMode === "erase"
              ? "bg-primary-container/15 text-primary-container"
              : "text-on-surface-variant hover:bg-surface-container-high"
          )}
        >
          <Eraser className="h-4 w-4" />
          <span className="text-[10px] font-semibold uppercase tracking-wide">Erase</span>
        </button>

        <div className="mx-2 h-8 w-px bg-outline-variant/60" />

        {OPERATIONS.map((op) => (
          <button
            key={op.id}
            type="button"
            onClick={() => onOperationChange(op.id)}
            className={cn(
              "rounded-lg px-3 py-2 text-[11px] font-semibold uppercase tracking-wide transition-colors",
              operation === op.id
                ? "bg-tertiary-container/20 text-tertiary"
                : "text-on-surface-variant hover:bg-surface-container-high"
            )}
          >
            {op.label}
          </button>
        ))}

        <div className="mx-2 h-8 w-px bg-outline-variant/60" />

        <div className="flex items-center gap-2 pr-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
            Size
          </span>
          <input
            type="range"
            min={8}
            max={80}
            value={brushSize}
            onChange={(e) => onBrushSizeChange(Number(e.target.value))}
            className="h-1 w-20 cursor-pointer accent-primary-container"
            aria-label="Brush size"
          />
        </div>

        <button
          type="button"
          title="Undo stroke"
          onClick={onUndo}
          className="rounded-lg p-2 text-on-surface-variant hover:bg-surface-container-high"
        >
          <Undo2 className="h-4 w-4" />
        </button>
        <button
          type="button"
          title="Clear mask"
          onClick={onClear}
          className="rounded-lg p-2 text-on-surface-variant hover:bg-surface-container-high"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      <p className="rounded-md bg-surface-container-lowest/90 px-3 py-1 text-[11px] text-on-surface-variant shadow-sm backdrop-blur">
        Paint the region to edit · purple overlay = editable area
      </p>
    </div>
  );
}
