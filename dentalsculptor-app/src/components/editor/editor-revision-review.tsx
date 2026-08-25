"use client";

import { Check, RotateCcw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EditorRevisionReviewProps {
  revisionNumber: number;
  loading?: boolean;
  onAccept: () => void;
  onReject: () => void;
}

/** Shown after a 3D edit completes — accept keeps the revision, reject restores the source model. */
export function EditorRevisionReview({
  revisionNumber,
  loading,
  onAccept,
  onReject,
}: EditorRevisionReviewProps) {
  return (
    <div className="pointer-events-auto absolute left-1/2 top-4 z-30 flex -translate-x-1/2 flex-wrap items-center justify-center gap-2 rounded-xl border border-outline-variant bg-surface-container-lowest/95 px-4 py-3 shadow-lg backdrop-blur-md">
      <Sparkles className="h-4 w-4 text-primary-container" />
      <span className="text-body-sm font-medium text-on-surface">
        Revision v{revisionNumber} ready — accept or revert?
      </span>
      <Button
        type="button"
        size="sm"
        className="bg-primary-container text-on-primary"
        disabled={loading}
        onClick={onAccept}
      >
        <Check className="mr-1.5 h-4 w-4" />
        Accept
      </Button>
      <Button type="button" size="sm" variant="outline" disabled={loading} onClick={onReject}>
        <RotateCcw className="mr-1.5 h-4 w-4" />
        Revert
      </Button>
    </div>
  );
}
