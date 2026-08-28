"use client";

import { Factory, CheckCircle2, Paintbrush } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { GenerationNotifyOption } from "@/components/generation/generation-notify-option";
import { GenerationImagePicker } from "@/components/generation/generation-image-picker";

interface EditorSourcePanelProps {
  open: boolean;
  onToggle: () => void;
  sourcePreview?: string | null;
  hasSourceFile?: boolean;
  onSelectImage?: (file: File) => void | Promise<void>;
  onClearImage?: () => void;
  onRotateImage?: () => void | Promise<void>;
  onGenerateModel?: () => void;
  generating?: boolean;
  preparingImage?: boolean;
  hasModel?: boolean;
  caseTitle?: string | null;
  caseInstruction?: string | null;
  onStartEdit?: () => void;
}

export function EditorSourcePanel({
  open,
  onToggle,
  sourcePreview,
  hasSourceFile,
  onSelectImage,
  onClearImage,
  onRotateImage,
  onGenerateModel,
  generating,
  preparingImage,
  hasModel,
  caseTitle,
  caseInstruction,
  onStartEdit,
}: EditorSourcePanelProps) {
  return (
    <aside
      className={cn(
        "editor-chrome-panel editor-scrollbar flex h-full shrink-0 flex-col overflow-hidden border-r border-outline-variant transition-all duration-200",
        open ? "w-[280px]" : "w-10"
      )}
    >
      {open ? (
        <>
          <div className="flex items-center justify-between border-b border-outline-variant px-3 py-3">
            <span className="text-label-caps font-bold text-on-surface">Source</span>
            <button
              type="button"
              onClick={onToggle}
              className="rounded p-1 text-on-surface-variant hover:bg-surface-container"
              aria-label="Collapse source panel"
            >
              ‹
            </button>
          </div>

          <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-3">
            <GenerationImagePicker
              compact
              previewUrl={sourcePreview ?? null}
              hasFile={Boolean(hasSourceFile ?? sourcePreview)}
              disabled={generating}
              preparing={preparingImage}
              previewClassName="min-h-[160px] h-auto"
              emptyHint="Select, browse library, or upload"
              onSelectFile={(file) => void onSelectImage?.(file)}
              onClear={() => onClearImage?.()}
              onRotate={onRotateImage ? () => void onRotateImage() : undefined}
            />

            {hasModel && caseTitle ? (
              <div className="rounded-xl border border-outline-variant bg-surface-container-low p-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-secondary"><CheckCircle2 className="h-4 w-4" />3D master ready</div>
                <p className="mt-3 text-body-sm font-semibold text-on-surface">{caseTitle}</p>
                <p className="mt-1 text-xs leading-relaxed text-on-surface-variant">{caseInstruction}</p>
                <Button size="sm" className="mt-3 w-full bg-primary-container text-on-primary" onClick={onStartEdit}>
                  <Paintbrush className="mr-2 h-4 w-4" />Mark the area to change
                </Button>
              </div>
            ) : (
              <>
                <Button className="w-full bg-primary-container text-on-primary" onClick={onGenerateModel} disabled={generating || !(hasSourceFile ?? sourcePreview)}>
                  <Factory className="mr-2 h-4 w-4" />{generating ? "Generating…" : "Generate 3D model"}
                </Button>
                <GenerationNotifyOption disabled={generating} className="border-outline-variant bg-surface-container-lowest" />
              </>
            )}
          </div>
        </>
      ) : (
        <button
          type="button"
          onClick={onToggle}
          className="flex h-full w-full flex-col items-center gap-2 py-4 text-on-surface-variant hover:bg-surface-container-low hover:text-primary-container"
          aria-label="Expand source panel"
        >
          ›
          <span className="text-[10px] font-semibold uppercase tracking-wide [writing-mode:vertical-rl]">
            Source
          </span>
        </button>
      )}
    </aside>
  );
}
