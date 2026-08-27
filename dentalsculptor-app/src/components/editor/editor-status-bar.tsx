"use client";

import { Mouse, Cpu, Box, Sparkles, TriangleAlert } from "lucide-react";
import type { ModelLoadStatus } from "@/components/editor/cam-model-viewer";

const MODEL_STATUS_LABEL: Record<ModelLoadStatus, string> = {
  none: "No 3D model — upload and generate from Source",
  loading: "Loading 3D model…",
  ready: "3D model ready",
  error: "3D model failed to load",
};

interface EditorStatusBarProps {
  modelStatus?: ModelLoadStatus;
  modelDetail?: string;
  hasSourceImage?: boolean;
  editStatus?: string | null;
  error?: string | null;
}

export function EditorStatusBar({
  modelStatus = "none",
  modelDetail,
  hasSourceImage,
  editStatus,
  error,
}: EditorStatusBarProps) {
  const now = new Date().toISOString().replace("T", " ").slice(0, 19);

  return (
    <footer className="flex h-8 shrink-0 items-center justify-between bg-primary-container px-4 text-[10px] text-on-primary">
      <div className="flex min-w-0 items-center gap-6">
        <span className="flex min-w-0 items-center gap-2">
          <Box className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">
            {MODEL_STATUS_LABEL[modelStatus]}
            {modelDetail ? ` — ${modelDetail}` : ""}
          </span>
        </span>
        {editStatus && (
          <span className="flex min-w-0 max-w-[min(420px,50vw)] items-center gap-2 text-amber-100">
            <Sparkles className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{editStatus}</span>
          </span>
        )}
        {error && (
          <span className="flex min-w-0 max-w-[min(560px,55vw)] items-center gap-2 text-red-200" role="alert">
            <TriangleAlert className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate" title={error}>{error}</span>
          </span>
        )}
        <span className="hidden items-center gap-2 sm:flex">
          <Mouse className="h-3.5 w-3.5" />
          Left: Select · Middle: Orbit · Space: Navigate while masking
        </span>
        <span className="hidden items-center gap-2 md:flex">
          <Cpu className="h-3.5 w-3.5" />
          {hasSourceImage ? "Source image attached" : "No source image"}
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-4">
        <span className="text-label-mono">{now} UTC</span>
      </div>
    </footer>
  );
}
