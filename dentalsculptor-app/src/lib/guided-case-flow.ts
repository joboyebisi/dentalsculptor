import type { CaseTemplate } from "@/lib/case-templates";

export interface GuidedCaseFlowCopy {
  mark: string;
  preview: string;
  create: string;
  targetHint: string;
}

export function guidedCaseFlowCopy(caseTemplate: CaseTemplate): GuidedCaseFlowCopy {
  switch (caseTemplate.procedure) {
    case "pathology-add":
      return { mark: "Paint, draw fracture line, or mark region", preview: "Preview fracture", create: "Create fracture variant", targetHint: "Use the Mask brush or line tool on the cusp, or draw a region rectangle over the fragment to remove." };
    case "prep-class-1":
    case "prep-class-2":
      return { mark: "Paint preparation outline", preview: "Preview cavity", create: "Create cavity variant", targetHint: "Paint the intended preparation boundary on the occlusal surface." };
    case "endo-access":
      return { mark: "Paint access outline", preview: "Preview access", create: "Create access variant", targetHint: "Mark the external access opening; internal canal anatomy is not inferred." };
    case "caries-occlusal":
    case "caries-smooth-surface":
      return { mark: "Paint lesion area", preview: "Preview lesion", create: "Create caries variant", targetHint: "Paint only the localized lesion or excavation area." };
    case "crown-prep":
      return { mark: "Paint reduction area", preview: "Preview reduction", create: "Create crown-prep variant", targetHint: "Mark the surfaces to reduce while preserving the root." };
    default:
      return { mark: "Mark target area", preview: "Preview change", create: "Create 3D variant", targetHint: "Mark the anatomical region that should change." };
  }
}
