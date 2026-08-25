import { Info } from "lucide-react";

/** Beta scope notice — placed below the upload card on landing. */
export function SingleToothScopeNote({ className }: { className?: string }) {
  return (
    <div
      role="note"
      className={`rounded-lg border border-outline-variant bg-surface-container-low px-4 py-3 ${className ?? ""}`}
    >
      <div className="flex gap-3">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary-container" aria-hidden />
        <div className="space-y-1 text-body-sm text-on-surface-variant">
          <p className="font-medium text-on-surface">Single tooth only (beta)</p>
          <p>
            Upload one clear photo of a <strong className="font-medium text-on-surface">single tooth</strong>.
            Accepted formats: <strong className="font-medium text-on-surface">PNG or JPG</strong> only for now.
          </p>
          <p>
            Whole-jaw and oral-cavity workflows are coming later. For best results use a plain background
            and frame the tooth so it fills most of the image.
          </p>
        </div>
      </div>
    </div>
  );
}
