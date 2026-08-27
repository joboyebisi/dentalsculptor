import type { EditOperation } from "@/lib/edit-types";
import type { ToothType } from "@/lib/tooth-taxonomy";

export type EditPresetCategory = "pathology" | "restorative" | "morphology" | "surface";

/** Geometry changes shape; texture changes appearance only (haptics unchanged on import). */
export type EditPresetMode = "geometry" | "texture" | "both";

export interface EditPreset {
  id: string;
  label: string;
  operation: EditOperation;
  prompt: string;
  category: EditPresetCategory;
  description?: string;
  /** Empty = all tooth types. */
  compatibleToothTypes?: ToothType[];
  preferredSurfaces?: string[];
  linkedTemplateIds?: string[];
  editMode: EditPresetMode;
  /** Shown when preset affects caries appearance — links to haptic tier disclosure. */
  hapticNote?: string;
}

/** Quick dental edit presets — gated by tooth type from case FDI when available. */
export const EDIT_PRESETS: EditPreset[] = [
  {
    id: "remove-caries",
    label: "Remove caries",
    operation: "remove",
    category: "pathology",
    editMode: "both",
    prompt: "Remove dark carious dentin in the masked region, preserve surrounding sound enamel",
    hapticNote:
      "Visual cavity only — Simodont STL import drills with uniform hardness. Soft caries feel requires native Simodont cariology or TrueTeethLab.",
  },
  {
    id: "add-caries",
    label: "Add caries",
    operation: "add",
    category: "pathology",
    editMode: "texture",
    prompt: "Add realistic brown carious lesion texture in the masked occlusal region",
    hapticNote:
      "Adds visual lesion texture only. Target simulator applies its own haptic material after import.",
  },
  {
    id: "cusp-fracture",
    label: "Cusp fracture",
    operation: "remove",
    category: "pathology",
    editMode: "geometry",
    compatibleToothTypes: ["premolar", "molar"],
    linkedTemplateIds: ["pathology-fracture-cusp"],
    prompt: "Remove the masked cusp fragment and create an irregular oblique enamel fracture edge",
  },
  {
    id: "class1-prep",
    label: "Class I prep",
    operation: "remove",
    category: "restorative",
    editMode: "geometry",
    compatibleToothTypes: ["premolar", "molar"],
    preferredSurfaces: ["occlusal"],
    linkedTemplateIds: ["prep-class-1-amalgam", "caries-occlusal-excavation"],
    prompt: "Class I occlusal cavity preparation with uniform depth and defined margins",
  },
  {
    id: "endo-access",
    label: "Endo access",
    operation: "remove",
    category: "restorative",
    editMode: "geometry",
    compatibleToothTypes: ["premolar", "molar"],
    preferredSurfaces: ["occlusal"],
    linkedTemplateIds: ["endo-access-intro", "endo-access-molar"],
    prompt: "Open pulp chamber roof through occlusal surface, expose canal orifices",
  },
  {
    id: "crown-prep",
    label: "Crown prep",
    operation: "remove",
    category: "restorative",
    editMode: "geometry",
    prompt: "Reduce axial and occlusal surfaces for full crown clearance with chamfer margin",
  },
  {
    id: "add-cusp",
    label: "Add cusp",
    operation: "add",
    category: "morphology",
    editMode: "geometry",
    compatibleToothTypes: ["premolar", "molar"],
    prompt: "Build up a sharper buccal cusp form in the masked region",
  },
  {
    id: "remove-cusp",
    label: "Remove cusp",
    operation: "remove",
    category: "morphology",
    editMode: "geometry",
    compatibleToothTypes: ["premolar", "molar"],
    prompt: "Reduce and flatten the cusp height in the masked region",
  },
  {
    id: "replace-cusp",
    label: "Replace cusp",
    operation: "replace",
    category: "morphology",
    editMode: "geometry",
    compatibleToothTypes: ["premolar", "molar"],
    prompt: "Replace the masked cusp with anatomically correct enamel form",
  },
  {
    id: "incisor-edge",
    label: "Incisal edge",
    operation: "replace",
    category: "morphology",
    editMode: "geometry",
    compatibleToothTypes: ["incisor"],
    preferredSurfaces: ["incisal"],
    prompt: "Restore incisal edge form and translucency in the masked region",
  },
  {
    id: "smooth-surface",
    label: "Smooth surface",
    operation: "replace",
    category: "surface",
    editMode: "both",
    prompt: "Smooth rough enamel surface and blend with adjacent tooth structure",
  },
  {
    id: "stain-discoloration",
    label: "Add stain",
    operation: "add",
    category: "surface",
    editMode: "texture",
    prompt: "Add yellow-brown extrinsic stain on enamel in the masked area",
  },
  {
    id: "whiten-enamel",
    label: "Whiten enamel",
    operation: "replace",
    category: "surface",
    editMode: "texture",
    prompt: "Lighten enamel shade in masked region while keeping natural texture",
  },
];

export function getEditPresetsByCategory(category: EditPresetCategory): EditPreset[] {
  return EDIT_PRESETS.filter((p) => p.category === category);
}

export function getEditPreset(id: string): EditPreset | undefined {
  return EDIT_PRESETS.find((p) => p.id === id);
}
