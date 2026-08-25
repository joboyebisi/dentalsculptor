import type { EditOperation } from "@/lib/edit-types";

export type EditPresetCategory = "pathology" | "restorative" | "morphology" | "surface";

export interface EditPreset {
  id: string;
  label: string;
  operation: EditOperation;
  prompt: string;
  category: EditPresetCategory;
  description?: string;
}

/** Quick dental edit presets — Meshmixer-style modifiers for the mask workflow. */
export const EDIT_PRESETS: EditPreset[] = [
  {
    id: "remove-caries",
    label: "Remove caries",
    operation: "remove",
    category: "pathology",
    prompt: "Remove dark carious dentin in the masked region, preserve surrounding sound enamel",
  },
  {
    id: "add-caries",
    label: "Add caries",
    operation: "add",
    category: "pathology",
    prompt: "Add realistic brown carious lesion texture in the masked occlusal region",
  },
  {
    id: "cusp-fracture",
    label: "Cusp fracture",
    operation: "add",
    category: "pathology",
    prompt: "Add an oblique cusp fracture with missing fragment in the masked region",
  },
  {
    id: "class1-prep",
    label: "Class I prep",
    operation: "remove",
    category: "restorative",
    prompt: "Class I occlusal cavity preparation with uniform depth and defined margins",
  },
  {
    id: "endo-access",
    label: "Endo access",
    operation: "remove",
    category: "restorative",
    prompt: "Open pulp chamber roof through occlusal surface, expose canal orifices",
  },
  {
    id: "crown-prep",
    label: "Crown prep",
    operation: "remove",
    category: "restorative",
    prompt: "Reduce axial and occlusal surfaces for full crown clearance with chamfer margin",
  },
  {
    id: "add-cusp",
    label: "Add cusp",
    operation: "add",
    category: "morphology",
    prompt: "Build up a sharper buccal cusp form in the masked region",
  },
  {
    id: "remove-cusp",
    label: "Remove cusp",
    operation: "remove",
    category: "morphology",
    prompt: "Reduce and flatten the cusp height in the masked region",
  },
  {
    id: "replace-cusp",
    label: "Replace cusp",
    operation: "replace",
    category: "morphology",
    prompt: "Replace the masked cusp with anatomically correct enamel form",
  },
  {
    id: "smooth-surface",
    label: "Smooth surface",
    operation: "replace",
    category: "surface",
    prompt: "Smooth rough enamel surface and blend with adjacent tooth structure",
  },
  {
    id: "stain-discoloration",
    label: "Add stain",
    operation: "add",
    category: "surface",
    prompt: "Add yellow-brown extrinsic stain on enamel in the masked area",
  },
  {
    id: "whiten-enamel",
    label: "Whiten enamel",
    operation: "replace",
    category: "surface",
    prompt: "Lighten enamel shade in masked region while keeping natural texture",
  },
];

export function getEditPresetsByCategory(category: EditPresetCategory): EditPreset[] {
  return EDIT_PRESETS.filter((p) => p.category === category);
}
