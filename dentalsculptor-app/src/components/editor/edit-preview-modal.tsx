"use client";

import { ArrowRight, Check, Eye, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FloatingEditorPanel } from "@/components/editor/floating-editor-panel";
import type { EditOperation } from "@/lib/edit-types";
import type { EditWorkflowStep } from "@/lib/edit-workflow-steps";
import { editWorkflowStepCopy } from "@/lib/edit-workflow-steps";

interface EditPreviewModalProps {
  open: boolean;
  onClose: () => void;
  beforeLabel?: string;
  afterLabel?: string;
  beforePreview?: string | null;
  afterPreview?: string | null;
  loading?: boolean;
  onRefineMask: () => void;
  onApprove: () => void;
}

export function EditPreviewModal({
  open,
  onClose,
  beforeLabel = "Original view",
  afterLabel = "AI preview",
  beforePreview,
  afterPreview,
  loading,
  onRefineMask,
  onApprove,
}: EditPreviewModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-on-surface/70 p-4 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-outline-variant bg-surface shadow-2xl">
        <div className="flex items-center justify-between border-b border-outline-variant bg-surface-container-lowest px-4 py-3">
          <div>
            <h2 className="text-title-lg font-semibold text-on-surface">Review 2D edit</h2>
            <p className="mt-0.5 text-body-sm text-on-surface-variant">
              Preview captures your current <strong>3D model view</strong> (not the original photo). The
              AI preview shows the masked change before running the full 3D edit.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container-high"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex flex-1 flex-col gap-4 overflow-y-auto bg-surface-container p-6 md:flex-row">
          <div className="flex flex-1 flex-col gap-2">
            <h3 className="text-center font-mono text-xs uppercase tracking-wider text-on-surface-variant">
              {beforeLabel}
            </h3>
            <div className="relative min-h-[280px] flex-1 overflow-hidden rounded-lg border border-outline-variant bg-[#8b95a5]">
              {beforePreview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={beforePreview} alt="Before edit" className="h-full w-full object-contain" />
              ) : (
                <div className="flex h-full items-center justify-center text-body-sm text-on-surface-variant">
                  Capture view to preview
                </div>
              )}
              <span className="absolute bottom-3 left-3 rounded bg-surface/90 px-2 py-0.5 font-mono text-[10px] text-on-surface">
                Pre-op
              </span>
            </div>
          </div>

          <div className="flex items-center justify-center">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-container-high shadow-sm">
              <ArrowRight className="h-4 w-4 text-on-surface-variant" />
            </div>
          </div>

          <div className="flex flex-1 flex-col gap-2">
            <h3 className="flex items-center justify-center gap-1 text-center font-mono text-xs font-bold uppercase tracking-wider text-primary-container">
              <Sparkles className="h-3 w-3" />
              {afterLabel}
            </h3>
            <div className="relative min-h-[280px] flex-1 overflow-hidden rounded-lg border-2 border-tertiary-container/40 bg-[#8b95a5]">
              {loading ? (
                <div className="flex h-full items-center justify-center text-body-sm text-on-surface-variant">
                  Generating 2D preview…
                </div>
              ) : afterPreview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={afterPreview} alt="After edit" className="h-full w-full object-contain" />
              ) : (
                <div className="flex h-full items-center justify-center text-body-sm text-on-surface-variant">
                  Approve mask and instruction to preview
                </div>
              )}
              <span className="absolute bottom-3 left-3 flex items-center gap-1 rounded bg-tertiary-container px-2 py-0.5 font-mono text-[10px] text-on-tertiary">
                <Check className="h-3 w-3" />
                Preview
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap justify-end gap-2 border-t border-outline-variant bg-surface-container-lowest px-4 py-3">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" variant="outline" onClick={onRefineMask}>
            Refine mask
          </Button>
          <Button
            type="button"
            className="bg-primary-container text-on-primary"
            disabled={!afterPreview || loading}
            onClick={onApprove}
          >
            <Check className="mr-2 h-4 w-4" />
            Approve &amp; run 3D edit
          </Button>
        </div>
      </div>
    </div>
  );
}

interface EditorEditActionsProps {
  visible: boolean;
  open: boolean;
  onClose: () => void;
  previewLoading?: boolean;
  generateLoading?: boolean;
  canPreview: boolean;
  canGenerate: boolean;
  onPreview2d: () => void;
  onGenerate3d: () => void;
}

export function EditorEditActions({
  visible,
  open,
  onClose,
  previewLoading,
  generateLoading,
  canPreview,
  canGenerate,
  onPreview2d,
  onGenerate3d,
}: EditorEditActionsProps) {
  if (!visible) return null;

  return (
    <FloatingEditorPanel
      id="edit-actions"
      title="Edit actions"
      open={open}
      onClose={onClose}
      defaultPosition={{ x: 720, y: 16 }}
      bodyClassName="flex w-44 flex-col gap-2 p-2"
    >
      <Button
        type="button"
        size="sm"
        className="w-full bg-primary-container text-on-primary shadow-md"
        disabled={!canPreview || previewLoading}
        onClick={onPreview2d}
      >
        <Eye className="mr-2 h-4 w-4" />
        {previewLoading ? "Previewing…" : "Preview 2D"}
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="w-full border-outline-variant bg-surface-container-highest text-primary-container shadow-sm"
        disabled={!canGenerate || generateLoading}
        onClick={onGenerate3d}
      >
        {generateLoading ? "Submitting…" : "Generate 3D"}
        <Sparkles className="ml-2 h-4 w-4" />
      </Button>
    </FloatingEditorPanel>
  );
}

interface EditorMaskContextPanelProps {
  visible: boolean;
  open: boolean;
  onClose: () => void;
  coveragePercent: number;
  revisionLabel?: string;
  operation?: EditOperation;
  workflowStep?: EditWorkflowStep;
}

export function EditorMaskContextPanel({
  visible,
  open,
  onClose,
  coveragePercent,
  revisionLabel = "v1",
  operation = "remove",
  workflowStep = "paint",
}: EditorMaskContextPanelProps) {
  if (!visible) return null;

  const stepCopy = editWorkflowStepCopy(workflowStep);

  return (
    <FloatingEditorPanel
      id="mask-context"
      title={`Mask edit · ${revisionLabel}`}
      open={open}
      onClose={onClose}
      defaultPosition={{ x: 16, y: 16 }}
      bodyClassName="w-56 space-y-0 p-3"
    >
      <div
        className="mb-3 rounded-lg border border-primary-container/25 bg-primary-container/8 px-2.5 py-2"
        role="status"
      >
        <p className="text-[11px] font-semibold text-primary-container">{stepCopy.title}</p>
        <p className="mt-0.5 text-[10px] leading-snug text-on-surface-variant">{stepCopy.cta}</p>
      </div>
      <div className="mb-2 flex items-center justify-between text-body-sm text-on-surface">
        <span>Coverage</span>
        <span className="font-semibold uppercase text-tertiary">{operation}</span>
      </div>
      <div className="mb-3 h-1.5 w-full rounded-full bg-surface-container-high">
        <div
          className="h-1.5 rounded-full bg-tertiary transition-all"
          style={{ width: `${Math.min(100, coveragePercent)}%` }}
        />
      </div>
      <p className="text-xs text-on-surface-variant">
        Paint the region to {operation}, then preview the 2D change before running the 3D edit.
        Hold <kbd className="rounded bg-surface-container-high px-1">Space</kbd> or use middle-mouse to
        rotate the model.
      </p>
    </FloatingEditorPanel>
  );
}
