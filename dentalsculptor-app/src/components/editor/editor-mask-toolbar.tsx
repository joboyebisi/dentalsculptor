"use client";

import { Brush, Eraser, Undo2, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EditOperation } from "@/lib/edit-types";
import type { MaskBrushMode } from "@/components/editor/mask-paint-overlay";
import { FloatingEditorPanel } from "@/components/editor/floating-editor-panel";
import { operationLabel } from "@/lib/edit-workflow-steps";

interface EditorMaskToolbarProps {
  visible: boolean;
  open: boolean;
  onClose: () => void;
  brushMode: MaskBrushMode;
  onBrushModeChange: (mode: MaskBrushMode) => void;
  brushSize: number;
  onBrushSizeChange: (size: number) => void;
  operation: EditOperation;
  onOperationChange: (op: EditOperation) => void;
  onUndo: () => void;
  onClear: () => void;
}

const OPERATIONS: EditOperation[] = ["add", "remove", "replace"];

export function EditorMaskToolbar({
  visible,
  open,
  onClose,
  brushMode,
  onBrushModeChange,
  brushSize,
  onBrushSizeChange,
  operation,
  onOperationChange,
  onUndo,
  onClear,
}: EditorMaskToolbarProps) {
  if (!visible) return null;

  return (
    <FloatingEditorPanel
      id="mask-toolbar"
      title="Mask brush"
      open={open}
      onClose={onClose}
      defaultPosition={{ x: 200, y: 560 }}
      bodyClassName="p-1.5"
    >
      <div className="flex flex-wrap items-center gap-1">
        <button
          type="button"
          title="Paint"
          onClick={() => onBrushModeChange("paint")}
          className={cn(
            "rounded-md p-1.5 transition-colors",
            brushMode === "paint"
              ? "bg-primary-container/15 text-primary-container"
              : "text-on-surface-variant hover:bg-surface-container-high"
          )}
        >
          <Brush className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          title="Erase"
          onClick={() => onBrushModeChange("erase")}
          className={cn(
            "rounded-md p-1.5 transition-colors",
            brushMode === "erase"
              ? "bg-primary-container/15 text-primary-container"
              : "text-on-surface-variant hover:bg-surface-container-high"
          )}
        >
          <Eraser className="h-3.5 w-3.5" />
        </button>

        <span className="mx-0.5 h-5 w-px bg-outline-variant/60" />

        <span className="rounded-md bg-tertiary-container/15 px-2 py-1 font-mono text-[10px] font-semibold uppercase text-tertiary">
          {operationLabel(operation)}
        </span>

        <select
          value={operation}
          onChange={(e) => onOperationChange(e.target.value as EditOperation)}
          className="rounded-md border border-outline-variant bg-surface-container-lowest px-1.5 py-1 text-[10px] text-on-surface"
          aria-label="Edit operation"
        >
          {OPERATIONS.map((op) => (
            <option key={op} value={op}>
              {operationLabel(op)}
            </option>
          ))}
        </select>

        <span className="mx-0.5 h-5 w-px bg-outline-variant/60" />

        <input
          type="range"
          min={8}
          max={64}
          value={brushSize}
          onChange={(e) => onBrushSizeChange(Number(e.target.value))}
          className="h-1 w-16 cursor-pointer accent-primary-container"
          aria-label="Brush size"
        />

        <button type="button" title="Undo" onClick={onUndo} className="rounded-md p-1.5 text-on-surface-variant hover:bg-surface-container-high">
          <Undo2 className="h-3.5 w-3.5" />
        </button>
        <button type="button" title="Clear" onClick={onClear} className="rounded-md p-1.5 text-on-surface-variant hover:bg-surface-container-high">
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </FloatingEditorPanel>
  );
}
