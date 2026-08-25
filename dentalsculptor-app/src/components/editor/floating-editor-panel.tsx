"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronUp, GripVertical, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface FloatingEditorPanelProps {
  id: string;
  title: string;
  /** Expanded panel body visible. */
  open: boolean;
  /** Collapsed to title bar only — use X to minimize, not remove. */
  minimized?: boolean;
  onMinimize: () => void;
  onRestore: () => void;
  defaultPosition?: { x: number; y: number };
  className?: string;
  bodyClassName?: string;
  children: ReactNode;
  /** When false the panel is visible but does not capture clicks (info-only). */
  interactive?: boolean;
}

function loadPosition(id: string, fallback: { x: number; y: number }) {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(`editor-panel-${id}`);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw) as { x?: number; y?: number };
    if (typeof parsed.x === "number" && typeof parsed.y === "number") {
      return { x: parsed.x, y: parsed.y };
    }
  } catch {
    /* ignore */
  }
  return fallback;
}

/** Draggable floating panel — close (X) minimizes; click minimized bar to expand. */
export function FloatingEditorPanel({
  id,
  title,
  open,
  minimized = false,
  onMinimize,
  onRestore,
  defaultPosition = { x: 16, y: 16 },
  className,
  bodyClassName,
  children,
  interactive = true,
}: FloatingEditorPanelProps) {
  const [pos, setPos] = useState(() => loadPosition(id, defaultPosition));
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(
    null
  );

  useEffect(() => {
    setPos(loadPosition(id, defaultPosition));
  }, [id, defaultPosition.x, defaultPosition.y]);

  const persistPosition = useCallback(
    (next: { x: number; y: number }) => {
      localStorage.setItem(`editor-panel-${id}`, JSON.stringify(next));
    },
    [id]
  );

  const onHeaderPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("button")) return;
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      origX: pos.x,
      origY: pos.y,
    };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const onHeaderPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragRef.current) return;
    const next = {
      x: dragRef.current.origX + (e.clientX - dragRef.current.startX),
      y: dragRef.current.origY + (e.clientY - dragRef.current.startY),
    };
    setPos(next);
  };

  const onHeaderPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragRef.current) return;
    const next = {
      x: dragRef.current.origX + (e.clientX - dragRef.current.startX),
      y: dragRef.current.origY + (e.clientY - dragRef.current.startY),
    };
    dragRef.current = null;
    e.currentTarget.releasePointerCapture(e.pointerId);
    setPos(next);
    persistPosition(next);
  };

  if (!open) return null;

  return (
    <div
      className={cn(
        "absolute z-20 max-w-[min(100%,760px)] rounded-lg border border-outline-variant bg-surface/95 shadow-md backdrop-blur-md",
        interactive ? "pointer-events-auto" : "pointer-events-none",
        minimized && "opacity-95",
        className
      )}
      style={{ left: pos.x, top: pos.y }}
    >
      <div
        className={cn(
          "flex items-center justify-between gap-2 border-outline-variant/50 px-2 py-1.5",
          !minimized && "border-b",
          interactive && "cursor-grab active:cursor-grabbing"
        )}
        onPointerDown={interactive ? onHeaderPointerDown : undefined}
        onPointerMove={interactive ? onHeaderPointerMove : undefined}
        onPointerUp={interactive ? onHeaderPointerUp : undefined}
      >
        <button
          type="button"
          onClick={minimized ? onRestore : undefined}
          className={cn(
            "flex min-w-0 flex-1 items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-on-surface-variant",
            minimized && interactive && "cursor-pointer hover:text-on-surface"
          )}
        >
          {interactive && <GripVertical className="h-3 w-3 shrink-0" aria-hidden />}
          <span className="truncate">{title}</span>
        </button>
        {interactive && (
          <button
            type="button"
            onClick={minimized ? onRestore : onMinimize}
            className="shrink-0 rounded p-1 text-on-surface-variant transition-colors hover:bg-surface-container-high"
            aria-label={minimized ? `Expand ${title}` : `Minimize ${title}`}
            title={minimized ? "Expand panel" : "Minimize panel"}
          >
            {minimized ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <X className="h-3.5 w-3.5" />
            )}
          </button>
        )}
      </div>
      {!minimized && <div className={cn("p-3", bodyClassName)}>{children}</div>}
    </div>
  );
}
