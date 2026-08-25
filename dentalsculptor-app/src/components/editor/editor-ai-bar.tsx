"use client";

import { useEffect, useState } from "react";
import { Wand2, ArrowUp, X } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { EditRegionAttachment } from "@/lib/edit-region-attachments";
import type { EditWorkflowStep } from "@/lib/edit-workflow-steps";
import {
  canHighlightSend,
  editSendBlockReason,
  editWorkflowStepCopy,
} from "@/lib/edit-workflow-steps";

const MAX_PROMPT_CHARS = 500;

interface EditorAiBarProps {
  value: string;
  onChange: (value: string) => void;
  onApply: () => void;
  loading?: boolean;
  canApply: boolean;
  maskMode?: boolean;
  regionAttachments?: EditRegionAttachment[];
  onRemoveAttachment?: (id: string) => void;
  hasMask?: boolean;
  workflowStep?: EditWorkflowStep;
}

export function EditorAiBar({
  value,
  onChange,
  onApply,
  loading,
  canApply,
  maskMode,
  regionAttachments = [],
  onRemoveAttachment,
  hasMask = false,
  workflowStep,
}: EditorAiBarProps) {
  const remaining = MAX_PROMPT_CHARS - value.length;
  const hasSpatialTarget = regionAttachments.length > 0 || hasMask;
  const hasInstruction = Boolean(value.trim());
  const prerequisites = { hasMask, hasInstruction };
  const highlightSend = canHighlightSend(prerequisites);
  const ready = highlightSend && !loading;
  const [blockFlash, setBlockFlash] = useState<string | null>(null);

  useEffect(() => {
    if (!blockFlash) return;
    const id = window.setTimeout(() => setBlockFlash(null), 4000);
    return () => window.clearTimeout(id);
  }, [blockFlash]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSendClick();
    }
  };

  const handleSendClick = () => {
    const block = editSendBlockReason(prerequisites);
    if (block) {
      setBlockFlash(block);
      return;
    }
    setBlockFlash(null);
    onApply();
  };

  const statusMessage = (() => {
    if (blockFlash) return blockFlash;
    if (highlightSend && !loading) {
      return "Ready — click Send ↑ to preview your edit";
    }
    if (workflowStep === "preview" && hasSpatialTarget && hasInstruction) {
      return 'Send ↑ opens 2D preview · or use "Preview 2D" above';
    }
    if (workflowStep) {
      return editWorkflowStepCopy(workflowStep).cta;
    }
    if (maskMode && hasMask) return "Mask painted — add an instruction, then Send ↑";
    if (regionAttachments.length > 0) {
      return `${regionAttachments.length} region${regionAttachments.length === 1 ? "" : "s"} attached — describe the edit`;
    }
    if (canApply) return "Model or parts selected — ready to edit";
    return "Mark a region, paint a mask, or select the model to enable Send";
  })();

  return (
    <div className="editor-chrome-panel z-20 shrink-0 border-t border-outline-variant px-3 py-3">
      <div className="relative w-full">
        <div className="mb-1.5 flex items-center gap-1.5 px-0.5">
          <Wand2 className="h-3.5 w-3.5 text-primary-container" />
          <span className="text-[11px] font-semibold uppercase tracking-wide text-on-surface-variant">
            {maskMode || hasMask ? "Instruction for masked edit" : "Semantic edit"}
          </span>
          {highlightSend && (
            <span className="rounded-full bg-primary-container/15 px-2 py-0.5 text-[10px] font-semibold text-primary-container">
              Send ready
            </span>
          )}
        </div>

        <div
          className={cn(
            "relative rounded-xl border bg-surface-container-low transition-shadow",
            highlightSend
              ? "border-primary-container/50 ring-2 ring-primary-container/20"
              : "border-outline-variant",
            blockFlash && "border-amber-500/50 ring-2 ring-amber-500/20"
          )}
        >
          {regionAttachments.length > 0 && (
            <div className="flex flex-wrap gap-2 border-b border-outline-variant/60 px-3 py-2">
              {regionAttachments.map((att) => (
                <div
                  key={att.id}
                  className="flex items-center gap-1.5 rounded-lg border border-outline-variant bg-surface-container-highest py-1 pl-1 pr-2 shadow-sm"
                >
                  {att.thumbnailUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={att.thumbnailUrl}
                      alt=""
                      className="h-8 w-10 rounded object-cover"
                    />
                  ) : (
                    <span className="flex h-8 w-10 items-center justify-center rounded bg-surface-container-low text-[10px] text-on-surface-variant">
                      R{att.index}
                    </span>
                  )}
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-error text-[10px] font-bold text-white">
                    {att.index}
                  </span>
                  <span className="max-w-[120px] truncate text-[11px] font-medium text-on-surface">
                    {att.label}
                  </span>
                  <button
                    type="button"
                    onClick={() => onRemoveAttachment?.(att.id)}
                    className="rounded p-0.5 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                    aria-label={`Remove ${att.label}`}
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <Textarea
            value={value}
            onChange={(e) => {
              if (e.target.value.length <= MAX_PROMPT_CHARS) onChange(e.target.value);
            }}
            onKeyDown={handleKeyDown}
            rows={3}
            placeholder={
              !hasMask
                ? "First paint a mask on the tooth…"
                : !hasInstruction
                  ? "Pick a suggested edit in the Case panel, or type here…"
                  : "Instruction ready — click Send ↑ to preview"
            }
            className="editor-scrollbar min-h-[80px] w-full resize-none border-0 bg-transparent py-3 pl-3 pr-14 text-body-sm leading-relaxed shadow-none focus-visible:ring-0"
          />

          <button
            type="button"
            onClick={handleSendClick}
            disabled={loading}
            title={
              highlightSend
                ? "Preview edit (Ctrl+Enter)"
                : editSendBlockReason(prerequisites) ?? "Complete the steps above first"
            }
            className={cn(
              "absolute bottom-2.5 right-2.5 flex h-9 w-9 items-center justify-center rounded-lg transition-all",
              highlightSend && !loading
                ? "animate-pulse bg-primary-container text-on-primary shadow-md ring-2 ring-primary-container/40 hover:opacity-90"
                : loading
                  ? "bg-primary-container/60 text-on-primary cursor-wait"
                  : "bg-surface-container text-outline hover:bg-surface-container-high"
            )}
            aria-label="Send edit instruction"
          >
            <ArrowUp className="h-4 w-4" />
          </button>
        </div>

        <div
          className={cn(
            "mt-1.5 flex items-center justify-between px-0.5 text-[10px]",
            blockFlash ? "text-amber-800" : "text-on-surface-variant"
          )}
        >
          <span>{statusMessage}</span>
          <span>{remaining} left</span>
        </div>
      </div>
    </div>
  );
}
