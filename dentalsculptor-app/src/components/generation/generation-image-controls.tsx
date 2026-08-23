"use client";

import { RotateCcw, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GenerationPoseNotice } from "@/components/generation/generation-pose-notice";

interface GenerationImageControlsProps {
  disabled?: boolean;
  onRotate: (direction: "cw" | "ccw") => void;
  showPoseNotice?: boolean;
}

export function GenerationImageControls({
  disabled,
  onRotate,
  showPoseNotice = true,
}: GenerationImageControlsProps) {
  return (
    <div className="space-y-3">
      {showPoseNotice && <GenerationPoseNotice />}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-body-sm text-on-surface-variant">Adjust orientation:</span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled}
          onClick={() => onRotate("ccw")}
        >
          <RotateCcw className="mr-1.5 h-4 w-4" />
          Rotate left
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled}
          onClick={() => onRotate("cw")}
        >
          <RotateCw className="mr-1.5 h-4 w-4" />
          Rotate right
        </Button>
      </div>
    </div>
  );
}
