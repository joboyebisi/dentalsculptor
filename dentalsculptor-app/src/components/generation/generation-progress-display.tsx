"use client";

import { Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { GENERATION_COPY, GENERATION_STAGE_LABELS } from "@/lib/generation-copy";

interface GenerationProgressDisplayProps {
  title: string;
  detail?: string;
  stage?: string | null;
  progress: number;
  elapsedSec: number;
  compact?: boolean;
}

export function GenerationProgressDisplay({
  title,
  detail = GENERATION_COPY.inProgressDetail,
  stage,
  progress,
  elapsedSec,
  compact = false,
}: GenerationProgressDisplayProps) {
  const stageLabel = stage ? (GENERATION_STAGE_LABELS[stage] ?? stage) : null;
  const barValue = progress > 0 ? progress : Math.min(90, 10 + elapsedSec * 2);

  return (
    <div
      className={
        compact
          ? "flex flex-col gap-2"
          : "flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-on-surface-variant"
      }
    >
      {!compact && <Loader2 className="h-8 w-8 animate-spin text-primary-container" />}
      <p className={compact ? "font-medium text-text-main" : "font-medium text-text-main"}>
        {title}
      </p>
      <p className="text-body-sm">{detail}</p>
      {stageLabel && (
        <p className="text-body-sm text-primary-container">
          {stageLabel}
          {progress > 0 ? ` · ${progress}%` : ""}
        </p>
      )}
      <Progress value={barValue} className={compact ? "h-2" : "mt-2 w-full max-w-xs"} />
      {elapsedSec > 0 && (
        <p className="text-body-sm text-on-surface-variant/80">Elapsed: {elapsedSec}s</p>
      )}
      {elapsedSec >= 30 && elapsedSec < 90 && (
        <p className="max-w-xs text-body-sm text-on-surface-variant/80">
          {GENERATION_COPY.inProgressQueuedHint}
        </p>
      )}
      {elapsedSec >= 90 && (
        <p className="max-w-xs text-body-sm text-on-surface-variant/80">
          {GENERATION_COPY.inProgressSlowHint}
        </p>
      )}
    </div>
  );
}
