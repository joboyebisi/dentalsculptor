"use client";

import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from "react";
import { cn } from "@/lib/utils";

export type MaskBrushMode = "paint" | "erase";

export interface MaskPaintOverlayHandle {
  clear: () => void;
  undo: () => void;
  redo: () => void;
  toMaskBlob: () => Promise<Blob | null>;
  getCoveragePercent: () => number;
  hasStrokes: () => boolean;
}

interface MaskPaintOverlayProps {
  /** Allow painting — typically when mask tool is active */
  interactive: boolean;
  /** Show the overlay canvas (true when interactive or strokes exist) */
  visible: boolean;
  brushSize: number;
  brushMode: MaskBrushMode;
  onStrokeEnd?: () => void;
  onStrokesChange?: (hasStrokes: boolean) => void;
}

export const MaskPaintOverlay = forwardRef<MaskPaintOverlayHandle, MaskPaintOverlayProps>(
  function MaskPaintOverlay(
    { interactive, visible, brushSize, brushMode, onStrokeEnd, onStrokesChange },
    ref
  ) {
    const containerRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const drawingRef = useRef(false);
    const historyRef = useRef<ImageData[]>([]);
    const redoRef = useRef<ImageData[]>([]);

    const syncCanvasSize = useCallback(() => {
      const container = containerRef.current;
      const canvas = canvasRef.current;
      if (!container || !canvas) return;
      const { width, height } = container.getBoundingClientRect();
      if (width < 1 || height < 1) return;
      if (canvas.width !== Math.floor(width) || canvas.height !== Math.floor(height)) {
        const prev = canvas.width > 0 ? getCtx()?.getImageData(0, 0, canvas.width, canvas.height) : null;
        canvas.width = Math.floor(width);
        canvas.height = Math.floor(height);
        if (prev) getCtx()?.putImageData(prev, 0, 0);
      }
    }, []);

    useEffect(() => {
      if (!visible) return;
      syncCanvasSize();
      const ro = new ResizeObserver(syncCanvasSize);
      if (containerRef.current) ro.observe(containerRef.current);
      return () => ro.disconnect();
    }, [visible, syncCanvasSize]);

    const getCtx = () => {
      const canvas = canvasRef.current;
      if (!canvas) return null;
      return canvas.getContext("2d");
    };

    const notifyStrokes = useCallback(() => {
      const canvas = canvasRef.current;
      const context = getCtx();
      if (!canvas || !context) {
        onStrokesChange?.(false);
        return;
      }
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
      let has = false;
      for (let i = 3; i < pixels.length; i += 4) {
        if (pixels[i] > 0) {
          has = true;
          break;
        }
      }
      onStrokesChange?.(has);
    }, [onStrokesChange]);

    const pushHistory = () => {
      const canvas = canvasRef.current;
      const ctx = getCtx();
      if (!canvas || !ctx) return;
      historyRef.current.push(ctx.getImageData(0, 0, canvas.width, canvas.height));
      if (historyRef.current.length > 30) historyRef.current.shift();
      redoRef.current = [];
    };

    const drawDot = (x: number, y: number) => {
      const ctx = getCtx();
      if (!ctx) return;
      ctx.globalCompositeOperation = brushMode === "erase" ? "destination-out" : "source-over";
      ctx.fillStyle = "rgba(124, 58, 237, 0.55)";
      ctx.beginPath();
      ctx.arc(x, y, brushSize / 2, 0, Math.PI * 2);
      ctx.fill();
    };

    const pointerPos = (e: React.PointerEvent) => {
      const canvas = canvasRef.current;
      if (!canvas) return { x: 0, y: 0 };
      const rect = canvas.getBoundingClientRect();
      return {
        x: ((e.clientX - rect.left) / rect.width) * canvas.width,
        y: ((e.clientY - rect.top) / rect.height) * canvas.height,
      };
    };

    useImperativeHandle(ref, () => ({
      clear: () => {
        const canvas = canvasRef.current;
        const ctx = getCtx();
        if (!canvas || !ctx) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        historyRef.current = [];
        redoRef.current = [];
        notifyStrokes();
      },
      undo: () => {
        const prev = historyRef.current.pop();
        const canvas = canvasRef.current;
        const ctx = getCtx();
        if (!canvas || !ctx) return;
        const current = ctx.getImageData(0, 0, canvas.width, canvas.height);
        redoRef.current.push(current);
        if (prev) {
          ctx.putImageData(prev, 0, 0);
        } else {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
        notifyStrokes();
      },
      redo: () => {
        const next = redoRef.current.pop();
        const canvas = canvasRef.current;
        const ctx = getCtx();
        if (!canvas || !ctx || !next) return;
        const current = ctx.getImageData(0, 0, canvas.width, canvas.height);
        historyRef.current.push(current);
        ctx.putImageData(next, 0, 0);
        notifyStrokes();
      },
      toMaskBlob: () =>
        new Promise((resolve) => {
          const source = canvasRef.current;
          const sourceContext = getCtx();
          if (!source || !sourceContext) {
            resolve(null);
            return;
          }
          const output = document.createElement("canvas");
          output.width = source.width;
          output.height = source.height;
          const outputContext = output.getContext("2d");
          if (!outputContext) {
            resolve(null);
            return;
          }
          const sourcePixels = sourceContext.getImageData(0, 0, source.width, source.height);
          const maskPixels = outputContext.createImageData(source.width, source.height);
          for (let i = 0; i < sourcePixels.data.length; i += 4) {
            const editable = sourcePixels.data[i + 3] > 0 ? 255 : 0;
            maskPixels.data[i] = editable;
            maskPixels.data[i + 1] = editable;
            maskPixels.data[i + 2] = editable;
            maskPixels.data[i + 3] = 255;
          }
          outputContext.putImageData(maskPixels, 0, 0);
          output.toBlob(resolve, "image/png");
        }),
      getCoveragePercent: () => {
        const canvas = canvasRef.current;
        const context = getCtx();
        if (!canvas || !context || canvas.width * canvas.height === 0) return 0;
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
        let editablePixels = 0;
        for (let i = 3; i < pixels.length; i += 4) {
          if (pixels[i] > 0) editablePixels += 1;
        }
        return (editablePixels / (canvas.width * canvas.height)) * 100;
      },
      hasStrokes: () => {
        const canvas = canvasRef.current;
        const context = getCtx();
        if (!canvas || !context) return false;
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
        for (let i = 3; i < pixels.length; i += 4) {
          if (pixels[i] > 0) return true;
        }
        return false;
      },
    }));

    if (!visible) return null;

    return (
      <div ref={containerRef} className="absolute inset-0 z-10 touch-none pointer-events-none">
        <canvas
          ref={canvasRef}
          className={cn(
            "h-full w-full",
            interactive ? "pointer-events-auto cursor-crosshair" : "pointer-events-none cursor-default"
          )}
          onPointerDown={(e) => {
            if (!interactive) return;
            if (e.button !== 0 || e.altKey) {
              const root = containerRef.current;
              if (root) root.style.pointerEvents = "none";
              const restore = () => {
                if (root) root.style.pointerEvents = "";
              };
              window.addEventListener("pointerup", restore, { once: true });
              return;
            }
            e.currentTarget.setPointerCapture(e.pointerId);
            drawingRef.current = true;
            pushHistory();
            const { x, y } = pointerPos(e);
            drawDot(x, y);
          }}
          onPointerMove={(e) => {
            if (!interactive || !drawingRef.current) return;
            const { x, y } = pointerPos(e);
            drawDot(x, y);
          }}
          onPointerUp={(e) => {
            if (!interactive) return;
            drawingRef.current = false;
            e.currentTarget.releasePointerCapture(e.pointerId);
            onStrokeEnd?.();
            notifyStrokes();
          }}
          onPointerLeave={() => {
            drawingRef.current = false;
          }}
        />
        {interactive && (
          <div
            className="pointer-events-none absolute inset-0 border border-white/10"
            style={{
              backgroundImage:
                "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)",
              backgroundSize: "20px 20px",
            }}
          />
        )}
      </div>
    );
  }
);
