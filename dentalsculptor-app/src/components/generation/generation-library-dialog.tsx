"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { GenerationLibraryItem } from "@/lib/generation-library";

interface GenerationLibraryDialogProps {
  open: boolean;
  loading?: boolean;
  onClose: () => void;
  onSelect: (item: GenerationLibraryItem) => void;
}

export function GenerationLibraryDialog({
  open,
  loading,
  onClose,
  onSelect,
}: GenerationLibraryDialogProps) {
  const [items, setItems] = useState<GenerationLibraryItem[]>([]);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setFetching(true);
    setError(null);
    fetch("/api/generation/library", { cache: "no-store" })
      .then(async (res) => {
        const data = (await res.json()) as { items?: GenerationLibraryItem[]; error?: string };
        if (!res.ok) throw new Error(data.error ?? "Could not load library.");
        if (!cancelled) setItems(data.items ?? []);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load library.");
      })
      .finally(() => {
        if (!cancelled) setFetching(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-on-surface/50 p-4 backdrop-blur-sm">
      <div
        className="flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-outline-variant bg-background shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="generation-library-title"
      >
        <div className="flex items-start justify-between gap-3 border-b border-outline-variant px-5 py-4">
          <div>
            <h2 id="generation-library-title" className="text-headline-sm font-semibold text-on-surface">
              Image library
            </h2>
            <p className="mt-1 text-body-sm text-on-surface-variant">
              Choose a curated teaching image — same workflow as uploading from your device.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-on-surface-variant hover:bg-surface-container-high"
            aria-label="Close library"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {fetching ? (
            <div className="flex items-center justify-center py-16 text-on-surface-variant">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Loading library…
            </div>
          ) : error ? (
            <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-body-sm text-destructive">
              {error}
            </p>
          ) : items.length === 0 ? (
            <p className="text-body-sm text-on-surface-variant">
              No library images yet. Add PNG/JPG files to{" "}
              <code className="rounded bg-surface-container-low px-1">public/generation-library/</code> and list them in{" "}
              <code className="rounded bg-surface-container-low px-1">manifest.json</code>.
            </p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  disabled={loading}
                  onClick={() => onSelect(item)}
                  className="group overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest text-left transition-all hover:border-primary-container/40 hover:shadow-md disabled:opacity-60"
                >
                  <div className="relative aspect-[4/5] bg-surface-container-low">
                    <Image
                      src={item.path}
                      alt={item.title}
                      fill
                      className="object-contain p-2"
                      sizes="240px"
                    />
                  </div>
                  <div className="space-y-2 p-3">
                    <p className="font-medium text-on-surface">{item.title}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {item.toothType && (
                        <Badge variant="outline" className="text-[10px] capitalize">
                          {item.toothType}
                        </Badge>
                      )}
                      {item.fdiHint && (
                        <Badge variant="outline" className="text-[10px]">
                          FDI {item.fdiHint}
                        </Badge>
                      )}
                    </div>
                    {item.credit && (
                      <p className="text-[10px] text-on-surface-variant">{item.credit}</p>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end border-t border-outline-variant px-5 py-3">
          <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
