"use client";

import { Wand2, ArrowUp, X } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { EditRegionAttachment } from "@/lib/edit-region-attachments";

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
}: EditorAiBarProps) {
  const remaining = MAX_PROMPT_CHARS - value.length;
  const hasSpatialTarget = regionAttachments.length > 0 || hasMask;
  const ready = canApply && value.trim().length > 0 && !loading;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && ready) {
      e.preventDefault();
      onApply();
    }
  };

  const statusMessage = (() => {
    if (maskMode && hasMask) return "Mask painted — ready to preview or apply";
    if (regionAttachments.length > 0) {
      return `${regionAttachments.length} region${regionAttachments.length === 1 ? "" : "s"} attached — describe the edit`;
    }
    if (canApply) return "Model or parts selected — ready to edit";
    return "Mark a region, paint a mask, or select the model to enable Apply";
  })();

  return (
    <div className="editor-chrome-panel z-20 shrink-0 border-t border-outline-variant px-3 py-3">
      <div className="relative w-full">
        <div className="mb-1.5 flex items-center gap-1.5 px-0.5">
          <Wand2 className="h-3.5 w-3.5 text-primary-container" />
          <span className="text-[11px] font-semibold uppercase tracking-wide text-on-surface-variant">
            {maskMode || hasMask ? "Instruction for masked edit" : "Semantic edit"}
          </span>
        </div>

        <div className="relative rounded-xl border border-outline-variant bg-surface-container-low focus-within:border-primary-container/40 focus-within:ring-2 focus-within:ring-primary-container/15">
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
              regionAttachments.length > 0
                ? "Describe what to change in the attached region(s)…"
                : maskMode || hasMask
                  ? "e.g. remove decay from the painted occlusal fossa…"
                  : "Describe the edit — mark regions or paint a mask to target specific areas…"
            }
            className="editor-scrollbar min-h-[80px] w-full resize-none border-0 bg-transparent py-3 pl-3 pr-14 text-body-sm leading-relaxed shadow-none focus-visible:ring-0"
          />

          <button
            type="button"
            onClick={onApply}
            disabled={!ready}
            title={
              hasSpatialTarget || canApply
                ? "Apply semantic edit (Ctrl+Enter)"
                : "Mark a region, paint a mask, or select the model first"
            }
            className={cn(
              "absolute bottom-2.5 right-2.5 flex h-8 w-8 items-center justify-center rounded-lg transition-all",
              ready
                ? "bg-primary-container text-on-primary shadow-sm hover:opacity-90"
                : "bg-surface-container text-outline cursor-not-allowed"
            )}
            aria-label="Apply semantic edit"
          >
            <ArrowUp className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-1.5 flex items-center justify-between px-0.5 text-[10px] text-on-surface-variant">
          <span>{statusMessage}</span>
          <span>{remaining} left</span>
        </div>
      </div>
    </div>
  );
}
