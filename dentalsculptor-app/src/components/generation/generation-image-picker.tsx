"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { BookOpen, ImagePlus, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GenerationImageControls } from "@/components/generation/generation-image-controls";
import { GenerationLibraryDialog } from "@/components/generation/generation-library-dialog";
import { cn } from "@/lib/utils";
import type { GenerationLibraryItem } from "@/lib/generation-library";

export interface GenerationImagePickerProps {
  previewUrl: string | null;
  hasFile: boolean;
  disabled?: boolean;
  preparing?: boolean;
  prepLabel?: string | null;
  compact?: boolean;
  previewClassName?: string;
  onSelectFile: (file: File) => void | Promise<void>;
  onClear: () => void;
  onRotate?: () => void | Promise<void>;
  accept?: string;
  emptyHint?: string;
  className?: string;
}

async function fetchLibraryItemAsFile(item: GenerationLibraryItem): Promise<File> {
  const res = await fetch(item.path, { cache: "no-store" });
  if (!res.ok) throw new Error("Could not load library image.");
  const blob = await res.blob();
  const ext = item.path.split(".").pop()?.split("?")[0] ?? "png";
  const safeName = `${item.id}.${ext}`;
  return new File([blob], safeName, { type: blob.type || "image/png" });
}

export function GenerationImagePicker({
  previewUrl,
  hasFile,
  disabled,
  preparing,
  prepLabel,
  compact,
  previewClassName,
  onSelectFile,
  onClear,
  onRotate,
  accept = "image/png,image/jpeg,image/jpg",
  emptyHint = "PNG or JPG · single tooth",
  className,
}: GenerationImagePickerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [libraryLoading, setLibraryLoading] = useState(false);

  const openFilePicker = useCallback(() => {
    if (!disabled && !preparing) fileInputRef.current?.click();
  }, [disabled, preparing]);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) void onSelectFile(file);
      e.target.value = "";
    },
    [onSelectFile]
  );

  const handleLibraryPick = useCallback(
    async (item: GenerationLibraryItem) => {
      setLibraryLoading(true);
      try {
        const file = await fetchLibraryItemAsFile(item);
        await onSelectFile(file);
        setLibraryOpen(false);
      } finally {
        setLibraryLoading(false);
      }
    },
    [onSelectFile]
  );

  useEffect(() => {
    if (!libraryOpen) setLibraryLoading(false);
  }, [libraryOpen]);

  const previewHeight = compact ? "h-[140px] lg:h-[150px]" : "h-48";

  return (
    <div className={cn("space-y-3", className)}>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={handleFileChange}
      />

      {preparing ? (
        <div
          className={cn(
            "flex w-full flex-col items-center justify-center rounded-lg border border-border-subtle bg-surface-container-low text-on-surface-variant",
            previewHeight,
            previewClassName
          )}
        >
          <Loader2 className="mb-2 h-7 w-7 animate-spin text-primary-container" />
          <span className="text-body-sm">{prepLabel ?? "Preparing image…"}</span>
        </div>
      ) : previewUrl ? (
        <div
          className={cn(
            "relative w-full overflow-hidden rounded-lg border border-border-subtle bg-surface-container-low",
            previewHeight,
            previewClassName
          )}
        >
          {previewUrl.startsWith("blob:") || previewUrl.startsWith("data:") ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={previewUrl} alt="Selected dental image" className="h-full w-full object-contain p-1" />
          ) : (
            <Image
              src={previewUrl}
              alt="Selected dental image"
              fill
              className="object-contain p-1"
              sizes="(max-width: 768px) 100vw, 340px"
            />
          )}
        </div>
      ) : (
        <button
          type="button"
          onClick={openFilePicker}
          disabled={disabled}
          className={cn(
            "flex w-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-border-subtle bg-surface-container-low text-on-surface-variant transition-colors hover:border-primary-container/40 hover:bg-surface-container disabled:opacity-60",
            previewHeight,
            previewClassName
          )}
        >
          <ImagePlus className="mb-2 h-7 w-7 text-primary-container/60" />
          <span className="text-body-sm">{emptyHint}</span>
        </button>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled || preparing || libraryLoading}
          onClick={openFilePicker}
        >
          <ImagePlus className="mr-1.5 h-4 w-4" />
          {hasFile ? "Change image" : "Select image"}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled || preparing || libraryLoading}
          onClick={() => setLibraryOpen(true)}
        >
          <BookOpen className="mr-1.5 h-4 w-4" />
          Browse library
        </Button>
        {hasFile && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={disabled || preparing || libraryLoading}
            onClick={onClear}
          >
            <X className="mr-1 h-4 w-4" />
            Clear
          </Button>
        )}
      </div>

      {prepLabel && !preparing && (
        <p className="text-body-sm text-on-surface-variant">{prepLabel}</p>
      )}

      {hasFile && onRotate && (
        <GenerationImageControls compact={compact} disabled={disabled || preparing} onRotate={() => void onRotate()} />
      )}

      <GenerationLibraryDialog
        open={libraryOpen}
        loading={libraryLoading}
        onClose={() => setLibraryOpen(false)}
        onSelect={(item) => void handleLibraryPick(item)}
      />
    </div>
  );
}
