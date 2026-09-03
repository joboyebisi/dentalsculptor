import { CASE_TEMPLATES } from "../src/lib/case-templates";
import {
  defaultVariantPresetForCase,
  recipeFromVariantPreset,
  validateCaseVariantRecipe,
  variantPresetForEditPreset,
} from "../src/lib/case-variant-recipes";
import { EDIT_PRESETS, getEditPreset } from "../src/lib/edit-presets";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

for (const template of CASE_TEMPLATES) {
  const required = template.clinicalParameterFields.filter((field) => field.required);
  assert(
    required.every((field) => field.type === "fdi-tooth"),
    `${template.id}: only FDI may be required; found ${required.map((field) => field.id).join(", ")}`
  );

  if (template.requiresGeometryEdit === false) continue;

  const defaultVariant = defaultVariantPresetForCase(template);
  assert(defaultVariant, `${template.id}: editable case has no default 3D variant`);
  assert(template.editPresetIds?.length, `${template.id}: editable case has no edit preset`);

  const defaultEditPreset = getEditPreset(template.editPresetIds[0]!);
  assert(defaultEditPreset, `${template.id}: unknown edit preset ${template.editPresetIds[0]}`);
  assert(
    defaultEditPreset.operation === defaultVariant.operation,
    `${template.id}: preset operation ${defaultEditPreset.operation} conflicts with variant ${defaultVariant.operation}`
  );

  const mappedVariant = variantPresetForEditPreset(defaultEditPreset.id);
  assert(mappedVariant, `${template.id}: edit preset ${defaultEditPreset.id} has no variant mapping`);
  assert(
    mappedVariant.id === defaultVariant.id ||
      (template.id === "endo-access-molar" && mappedVariant.caseId === defaultVariant.caseId),
    `${template.id}: edit preset maps to ${mappedVariant.id}, default is ${defaultVariant.id}`
  );
}

for (const editPreset of EDIT_PRESETS) {
  const variant = variantPresetForEditPreset(editPreset.id);
  assert(variant, `Free-editor preset ${editPreset.id} has no hardened 3D strategy`);
  assert(
    variant.operation === editPreset.operation,
    `Free-editor preset ${editPreset.id} conflicts with ${variant.id}`
  );
  const recipe = recipeFromVariantPreset(variant);
  const valid = validateCaseVariantRecipe(recipe, editPreset.operation);
  assert(!("error" in valid), `Recipe ${variant.id} failed its own contract`);
  const contradictory = validateCaseVariantRecipe(recipe, editPreset.operation === "add" ? "remove" : "add");
  assert("error" in contradictory, `Recipe ${variant.id} accepted a contradictory operation`);
}

console.log(
  `Validated ${CASE_TEMPLATES.length} case templates and ${EDIT_PRESETS.length} free-editor strategies.`
);
