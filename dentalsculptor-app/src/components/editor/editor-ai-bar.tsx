"use client";

import { Wand2, ArrowUp } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const MAX_PROMPT_CHARS = 500;

interface EditorAiBarProps {
  value: string;
  onChange: (value: string) => void;
  onApply: () => void;
  loading?: boolean;
  canApply: boolean;
  maskMode?: boolean;
}

export function EditorAiBar({ value, onChange, onApply, loading, canApply, maskMode }: EditorAiBarProps) {
  const remaining = MAX_PROMPT_CHARS - value.length;
  const ready = canApply && value.trim().length > 0 && !loading;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && ready) {
      e.preventDefault();
      onApply();
    }
  };

  return (
    <div className="editor-chrome-panel z-20 shrink-0 border-t border-outline-variant px-3 py-3">
      <div className="relative w-full">
        <div className="mb-1.5 flex items-center gap-1.5 px-0.5">
          <Wand2 className="h-3.5 w-3.5 text-primary-container" />
          <span className="text-[11px] font-semibold uppercase tracking-wide text-on-surface-variant">
            {maskMode ? "Instruction for masked edit" : "Semantic edit"}
          </span>
        </div>

        <div className="relative rounded-xl border border-outline-variant bg-surface-container-low focus-within:border-primary-container/40 focus-within:ring-2 focus-within:ring-primary-container/15">
          <Textarea
            value={value}
            onChange={(e) => {
              if (e.target.value.length <= MAX_PROMPT_CHARS) onChange(e.target.value);
            }}
            onKeyDown={handleKeyDown}
            rows={3}
            placeholder={
              maskMode
                ? "e.g. remove decay from the painted occlusal fossa…"
                : "Describe the edit you want — select the model or parts above first…"
            }
            className="editor-scrollbar min-h-[80px] w-full resize-none border-0 bg-transparent py-3 pl-3 pr-14 text-body-sm leading-relaxed shadow-none focus-visible:ring-0"
          />

          <button
            type="button"
            onClick={onApply}
            disabled={!ready}
            title={
              canApply
                ? "Apply semantic edit (Ctrl+Enter)"
                : "Select the 3D model or one or more parts to edit"
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
          <span>
            {canApply
              ? "Model or parts selected — ready to edit"
              : "Select the 3D model or parts to enable Apply"}
          </span>
          <span>{remaining} left</span>
        </div>
      </div>
    </div>
  );
}
