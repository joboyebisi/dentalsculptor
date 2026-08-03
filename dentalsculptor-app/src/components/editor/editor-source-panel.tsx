"use client";

import { useRef } from "react";
import Image from "next/image";
import { ImagePlus, Factory, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface EditorSourcePanelProps {
  open: boolean;
  onToggle: () => void;
  sourcePreview?: string | null;
  onSourceUpload?: (file: File) => void;
  onGenerateModel?: () => void;
  generating?: boolean;
}

export function EditorSourcePanel({
  open,
  onToggle,
  sourcePreview,
  onSourceUpload,
  onGenerateModel,
  generating,
}: EditorSourcePanelProps) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <aside
      className={cn(
        "editor-scrollbar flex h-full shrink-0 flex-col overflow-hidden border-r border-outline-variant bg-panel-bg transition-all duration-200",
        open ? "w-[260px]" : "w-10"
      )}
    >
      {open ? (
        <>
          <div className="flex items-center justify-between border-b border-outline-variant px-3 py-3">
            <div className="flex items-center gap-2">
              <ImagePlus className="h-4 w-4 text-on-surface-variant" />
              <span className="text-label-caps font-bold text-on-surface">Source</span>
            </div>
            <button
              type="button"
              onClick={onToggle}
              className="rounded p-1 text-on-surface-variant hover:bg-surface-container"
              aria-label="Collapse source panel"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          </div>

          <div className="flex flex-1 flex-col gap-3 p-3">
            <input
              ref={fileRef}
              type="file"
              accept="image/*,.dcm"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file && onSourceUpload) onSourceUpload(file);
              }}
            />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="group flex min-h-[180px] flex-1 flex-col items-center justify-center rounded-lg border-2 border-dashed border-outline-variant bg-surface-container-lowest transition-colors hover:border-primary-container/30 hover:bg-surface-container-low"
            >
              {sourcePreview ? (
                <div className="relative h-full min-h-[160px] w-full p-2">
                  <Image src={sourcePreview} alt="Source scan" fill className="rounded object-contain" />
                </div>
              ) : (
                <>
                  <ImagePlus className="mb-2 h-9 w-9 text-outline transition-colors group-hover:text-primary-container" />
                  <span className="text-center text-body-sm font-medium text-on-surface-variant group-hover:text-primary-container">
                    Upload scan or image
                  </span>
                  <span className="mt-1 text-[10px] text-outline">PNG, JPG, CBCT slice</span>
                </>
              )}
            </button>

            <Button
              className="w-full bg-primary-container text-on-primary"
              onClick={onGenerateModel}
              disabled={generating}
            >
              <Factory className="mr-2 h-4 w-4" />
              {generating ? "Generating…" : "Generate Model"}
            </Button>
          </div>
        </>
      ) : (
        <button
          type="button"
          onClick={onToggle}
          className="flex h-full w-full flex-col items-center gap-2 py-4 text-on-surface-variant hover:bg-surface-container-low hover:text-primary-container"
          aria-label="Expand source panel"
        >
          <ChevronRight className="h-4 w-4" />
          <ImagePlus className="h-4 w-4" />
        </button>
      )}
    </aside>
  );
}
