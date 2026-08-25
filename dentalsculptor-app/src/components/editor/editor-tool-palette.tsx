"use client";

import {
  MousePointerClick,
  BoxSelect,
  Layers,
  Hand,
  Paintbrush,
  ZoomIn,
  ZoomOut,
  Undo2,
  Redo2,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type EditorTool =
  | "select"
  | "mark"
  | "mask"
  | "edit"
  | "pan"
  | "texture"
  | "zoom-in"
  | "zoom-out"
  | "undo"
  | "redo";

/** Tool icons aligned with stitch Material Symbols (v3 workspace). */
const tools: { id: EditorTool; icon: typeof MousePointerClick; label: string; dividerAfter?: boolean }[] = [
  { id: "select", icon: MousePointerClick, label: "Select" },
  { id: "mark", icon: BoxSelect, label: "Region mark" },
  { id: "mask", icon: Paintbrush, label: "Mask paint" },
  { id: "edit", icon: Layers, label: "Mesh view" },
  { id: "pan", icon: Hand, label: "Pan", dividerAfter: true },
  { id: "zoom-in", icon: ZoomIn, label: "Zoom in" },
  { id: "zoom-out", icon: ZoomOut, label: "Zoom out" },
  { id: "undo", icon: Undo2, label: "Undo" },
  { id: "redo", icon: Redo2, label: "Redo" },
];

interface EditorToolPaletteProps {
  activeTool: EditorTool;
  onToolChange: (tool: EditorTool) => void;
  className?: string;
}

export function EditorToolPalette({ activeTool, onToolChange, className }: EditorToolPaletteProps) {
  return (
    <div
      className={cn(
        "glass-panel z-30 flex flex-col items-center gap-1 rounded-xl border border-border-subtle p-2 shadow-lg",
        className
      )}
    >
      {tools.map((tool) => (
        <div key={tool.id} className="flex flex-col items-center">
          <button
            type="button"
            title={tool.label}
            onClick={() => onToolChange(tool.id)}
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-lg transition-colors",
              activeTool === tool.id
                ? "bg-primary-container text-on-primary shadow-sm"
                : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
            )}
          >
            <tool.icon className="h-4 w-4" />
          </button>
          {tool.dividerAfter && <div className="my-1.5 h-px w-7 bg-outline-variant" />}
        </div>
      ))}
    </div>
  );
}
