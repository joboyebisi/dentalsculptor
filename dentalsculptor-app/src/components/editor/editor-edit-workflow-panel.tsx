"use client";

import { Check, Circle, Paintbrush, Wand2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EditOperation } from "@/lib/edit-types";
import type { CaseTemplate } from "@/lib/case-templates";
import { FloatingEditorPanel } from "@/components/editor/floating-editor-panel";

interface EditorEditWorkflowPanelProps {
  visible: boolean;
  minimized: boolean;
  onMinimize: () => void;
  onRestore: () => void;
  selectedCase: CaseTemplate | null;
  activeTool: string;
  editOperation: EditOperation;
  maskCoverage: number;
  hasInstruction: boolean;
  regionMarkCount?: number;
  className?: string;
}

const STEPS = [
  { id: "case", label: "Case preset", icon: Circle },
  { id: "mark", label: "Mark area", icon: Paintbrush },
  { id: "operation", label: "Add / Remove / Replace", icon: Circle },
  { id: "instruction", label: "Semantic edit", icon: Wand2 },
] as const;

function stepComplete(
  stepId: (typeof STEPS)[number]["id"],
  ctx: {
    hasCase: boolean;
    maskCoverage: number;
    hasInstruction: boolean;
    activeTool: string;
    regionMarkCount: number;
  }
): boolean {
  switch (stepId) {
    case "case":
      return ctx.hasCase;
    case "mark":
      return ctx.regionMarkCount > 0 || ctx.maskCoverage > 0;
    case "operation":
      return ctx.regionMarkCount > 0 || ctx.maskCoverage > 0;
    case "instruction":
      return ctx.hasInstruction && (ctx.regionMarkCount > 0 || ctx.maskCoverage > 0);
    default:
      return false;
  }
}

function stepActive(
  stepId: (typeof STEPS)[number]["id"],
  ctx: { hasCase: boolean; maskCoverage: number; activeTool: string; regionMarkCount: number }
): boolean {
  if (stepId === "case") return !ctx.hasCase;
  if (stepId === "mark")
    return (
      ctx.hasCase &&
      (ctx.activeTool === "mark" || ctx.activeTool === "mask") &&
      ctx.regionMarkCount === 0 &&
      ctx.maskCoverage === 0
    );
  if (stepId === "operation")
    return (ctx.regionMarkCount > 0 || ctx.maskCoverage > 0) && ctx.activeTool === "mask";
  if (stepId === "instruction") return ctx.regionMarkCount > 0 || ctx.maskCoverage > 0;
  return false;
}

export function EditorEditWorkflowPanel({
  visible,
  minimized,
  onMinimize,
  onRestore,
  selectedCase,
  activeTool,
  editOperation,
  maskCoverage,
  hasInstruction,
  regionMarkCount = 0,
  className,
}: EditorEditWorkflowPanelProps) {
  if (!visible) return null;

  const ctx = {
    hasCase: Boolean(selectedCase),
    maskCoverage,
    hasInstruction,
    activeTool,
    regionMarkCount,
  };

  return (
    <FloatingEditorPanel
      id="edit-workflow"
      title="Edit workflow"
      open
      minimized={minimized}
      onMinimize={onMinimize}
      onRestore={onRestore}
      defaultPosition={{ x: 16, y: 280 }}
      bodyClassName={cn("w-64 p-3", className)}
    >
      <ol className="space-y-2">
        {STEPS.map((step) => {
          const done = stepComplete(step.id, ctx);
          const active = stepActive(step.id, ctx);
          const Icon = step.icon;
          return (
            <li
              key={step.id}
              className={cn(
                "flex items-start gap-2 text-[11px] leading-snug",
                done ? "text-on-surface" : active ? "text-primary-container" : "text-on-surface-variant"
              )}
            >
              <span
                className={cn(
                  "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                  done
                    ? "border-tertiary bg-tertiary/15 text-tertiary"
                    : active
                      ? "border-primary-container bg-primary-container/10"
                      : "border-outline-variant"
                )}
              >
                {done ? <Check className="h-2.5 w-2.5" /> : <Icon className="h-2.5 w-2.5" />}
              </span>
              <span>
                {step.label}
                {step.id === "operation" && maskCoverage > 0 && (
                  <span className="ml-1 font-semibold uppercase text-tertiary">· {editOperation}</span>
                )}
              </span>
            </li>
          );
        })}
      </ol>
      {selectedCase && selectedCase.suggestedPrompts.length > 0 && (
        <p className="mt-3 border-t border-outline-variant/50 pt-2 text-[10px] leading-relaxed text-on-surface-variant">
          Suggested: &ldquo;{selectedCase.suggestedPrompts[0]}&rdquo;
        </p>
      )}
    </FloatingEditorPanel>
  );
}
