"use client";

import { RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GenerationPoseNotice } from "@/components/generation/generation-pose-notice";

interface GenerationImageControlsProps {
  disabled?: boolean;
  onRotate: () => void;
  showPoseNotice?: boolean;
  compact?: boolean;
}

export function GenerationImageControls({
  disabled,
  onRotate,
  showPoseNotice = true,
  compact = false,
}: GenerationImageControlsProps) {
  return (
    <div className={compact ? "space-y-2" : "space-y-3"}>
      {showPoseNotice && <GenerationPoseNotice className={compact ? "py-2" : undefined} />}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled}
          onClick={onRotate}
        >
          <RotateCw className="mr-1.5 h-4 w-4" />
          Rotate
        </Button>
        {!compact && (
          <span className="text-body-sm text-on-surface-variant">
            Tap again until the tooth looks upright.
          </span>
        )}
      </div>
    </div>
  );
}
