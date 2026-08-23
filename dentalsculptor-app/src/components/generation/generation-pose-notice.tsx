import { Compass } from "lucide-react";
import { GENERATION_COPY } from "@/lib/generation-copy";

/** Explains that camera pose in the photo drives the 3D orientation. */
export function GenerationPoseNotice({ className }: { className?: string }) {
  return (
    <div
      role="note"
      className={`rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2.5 ${className ?? ""}`}
    >
      <div className="flex gap-2.5">
        <Compass className="mt-0.5 h-4 w-4 shrink-0 text-primary-container" aria-hidden />
        <p className="text-body-sm leading-snug text-on-surface-variant">
          {GENERATION_COPY.poseNotice}
        </p>
      </div>
    </div>
  );
}
