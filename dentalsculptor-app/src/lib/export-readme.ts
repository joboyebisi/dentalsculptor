import type { CaseRecipe } from "@/lib/clinical-case-params";
import type { CaseTemplate } from "@/lib/case-templates";
import type { ExportTarget } from "@/lib/export-presets";
import { getExportPreset } from "@/lib/export-presets";

export function buildExportReadme(input: {
  projectTitle: string;
  target: ExportTarget;
  outputFormat: string;
  caseRecipe?: CaseRecipe | null;
  selectedCase?: CaseTemplate | null;
}): string {
  const preset = getExportPreset(input.target);
  const fdi = input.caseRecipe?.clinicalParameters?.fdiTooth;
  const lines = [
    `DentalSculptor export — ${input.projectTitle}`,
    `Generated: ${new Date().toISOString()}`,
    "",
    "Files",
    `• Primary mesh: ${input.outputFormat.toUpperCase()} (${preset.units})`,
    "",
    "Clinical context",
    input.selectedCase ? `• Case template: ${input.selectedCase.title}` : "• Case template: custom",
    fdi ? `• FDI tooth: ${fdi}` : "• FDI tooth: not specified",
    "",
    "Haptic realism (important)",
    `• Tier: ${preset.hapticRealism}`,
    preset.hapticDisclosure ?? "Custom STL/PLY imports use uniform drill resistance on most simulators.",
    "",
    "Visual caries vs soft feel",
    "Brown/dark lesion textures in DentalSculptor are VISUAL ONLY on custom import.",
    "Simodont and SimtoCARE apply their own material model after STL import — typically uniform hardness.",
    "For authentic soft caries tactile feedback, use Simodont native cariology library cases or TrueTeethLab (CBCT).",
    "",
    "Scale",
    `• Units: ${preset.units}`,
    `• Scale factor applied: ${preset.scaleFactor}`,
    "",
    "Validate import in your simulator Teacher console before classroom rollout.",
  ];
  return lines.join("\n");
}

export function downloadTextFile(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
