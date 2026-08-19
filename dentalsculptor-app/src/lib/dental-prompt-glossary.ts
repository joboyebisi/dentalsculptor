/**
 * Expands colloquial educator prompts into anatomically precise inpaint instructions.
 * Log both strings in ModelRevision.metadata for research and future LoRA datasets.
 */

const EXPANSIONS: Record<string, string> = {
  "remove decay":
    "remove dark carious dentin in the marked region, preserve surrounding sound enamel and dentin",
  "remove caries":
    "excavate soft carious tissue within the masked area, maintain smooth cavity walls",
  "cavity prep":
    "prepare a conservative dental cavity with defined margins in the masked region",
  "class 1 prep":
    "create a Class I occlusal preparation with uniform depth and retention form in the masked area",
  "class i prep":
    "create a Class I occlusal preparation with uniform depth and retention form in the masked area",
  "endo access":
    "open the pulp chamber roof through the occlusal surface, expose canal orifices, minimal extension",
  "crown prep":
    "reduce axial and occlusal surfaces for full crown clearance, continuous chamfer margin",
  "add caries":
    "add realistic dark brown carious lesion texture in the masked region on the tooth surface",
  "fracture":
    "add an oblique cusp fracture line with missing fragment in the masked region",
};

export interface ExpandedDentalPrompt {
  original: string;
  expanded: string;
  matchedKey: string | null;
}

export function expandDentalPrompt(instruction: string): ExpandedDentalPrompt {
  const trimmed = instruction.trim();
  const lower = trimmed.toLowerCase();

  for (const [key, expansion] of Object.entries(EXPANSIONS)) {
    if (lower.includes(key)) {
      return {
        original: trimmed,
        expanded: `${trimmed}. ${expansion}`,
        matchedKey: key,
      };
    }
  }

  return {
    original: trimmed,
    expanded: trimmed,
    matchedKey: null,
  };
}

/** Anatomical terms for case wizard / AI bar autocomplete (E0 UI). */
export const DENTAL_VOCABULARY_HINTS = [
  "central occlusal fossa",
  "mesiobuccal cusp",
  "distobuccal cusp",
  "marginal ridge",
  "pulp chamber roof",
  "cementoenamel junction",
  "proximal box",
  "buccal surface",
  "lingual surface",
] as const;
