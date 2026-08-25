import type { EditOperation } from "@/lib/edit-types";

export type EditWorkflowStep =
  | "paint"
  | "instruction"
  | "preview"
  | "submit";

export function resolveEditWorkflowStep(input: {
  hasMask: boolean;
  hasInstruction: boolean;
  hasPreview: boolean;
}): EditWorkflowStep {
  if (!input.hasMask) return "paint";
  if (!input.hasInstruction) return "instruction";
  if (!input.hasPreview) return "preview";
  return "submit";
}

export function editWorkflowStepCopy(step: EditWorkflowStep): {
  title: string;
  detail: string;
  cta: string;
} {
  switch (step) {
    case "paint":
      return {
        title: "Step 1 · Mark the tooth",
        detail: "Paint the region you want to change (purple overlay).",
        cta: "Use the Mask tool, then brush on the model.",
      };
    case "instruction":
      return {
        title: "Step 2 · Describe the edit",
        detail: "Pick a suggested edit or type what should happen in the region.",
        cta: "Click a suggestion in the Case panel, or type below.",
      };
    case "preview":
      return {
        title: "Step 3 · Preview",
        detail: "Check the 2D preview on your current 3D view before committing.",
        cta: 'Click "Preview 2D" (top right).',
      };
    case "submit":
      return {
        title: "Step 4 · Run 3D edit",
        detail: "Approve the preview, then apply the change to the mesh.",
        cta: 'Click Send ↑ in the instruction bar, or "Generate 3D".',
      };
  }
}

export function operationLabel(op: EditOperation): string {
  return op.charAt(0).toUpperCase() + op.slice(1);
}
