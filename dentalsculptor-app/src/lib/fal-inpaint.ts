import { fal } from "@fal-ai/client";
import { expandDentalPrompt } from "@/lib/dental-prompt-glossary";
import type { EditOperation } from "@/lib/edit-types";

/** SDXL inpainting on fal — E0 default for masked 2D preview (see MILESTONE_E0_E2 §4.3). */
export const FAL_INPAINT_MODEL = "fal-ai/inpaint";

const SDXL_INPAINT =
  "diffusers/stable-diffusion-xl-1.0-inpainting-0.1";

function buildInpaintPrompt(instruction: string, operation: EditOperation): string {
  const base =
    "clinical dental tooth photograph, realistic enamel and dentin texture, intraoral lighting";
  if (operation === "remove") {
    return `${base}, ${instruction}, excavate or remove tissue in masked area, preserve natural anatomy outside mask`;
  }
  if (operation === "add") {
    return `${base}, ${instruction}, add anatomical detail only within masked region`;
  }
  return `${base}, ${instruction}, replace masked region with anatomically correct tooth structure`;
}

function extractImageUrl(output: unknown): string | null {
  if (!output || typeof output !== "object") return null;
  const o = output as Record<string, unknown>;
  if (typeof o.image === "object" && o.image !== null) {
    const url = (o.image as { url?: string }).url;
    if (url) return url;
  }
  if (Array.isArray(o.images) && o.images.length > 0) {
    const first = o.images[0];
    if (typeof first === "object" && first !== null && "url" in first) {
      return (first as { url: string }).url;
    }
    if (typeof first === "string") return first;
  }
  if (typeof o.image_url === "string") return o.image_url;
  return null;
}

export function isFalInpaintConfigured(): boolean {
  return Boolean(process.env.FAL_KEY?.trim());
}

export async function runFalMaskedInpaint(options: {
  referenceBlob: Blob;
  maskBlob: Blob;
  instruction: string;
  operation: EditOperation;
}): Promise<{ imageUrl: string; prompt: string }> {
  const key = process.env.FAL_KEY;
  if (!key) {
    throw new Error("FAL_KEY is not configured.");
  }

  fal.config({ credentials: key });
  const expanded = expandDentalPrompt(options.instruction);
  const prompt = buildInpaintPrompt(expanded.expanded, options.operation);

  const [imageUrl, maskUrl] = await Promise.all([
    fal.storage.upload(options.referenceBlob),
    fal.storage.upload(options.maskBlob),
  ]);

  const result = await fal.subscribe(FAL_INPAINT_MODEL, {
    input: {
      model_name: SDXL_INPAINT,
      prompt,
      negative_prompt:
        "cartoon, painting, blurry, low quality, extra teeth, deformed, watermark, text",
      image_url: imageUrl,
      mask_url: maskUrl,
      num_inference_steps: 28,
      guidance_scale: 7.5,
    },
  });

  const outUrl = extractImageUrl((result as { data?: unknown }).data ?? result);
  if (!outUrl) {
    throw new Error("fal inpaint returned no image URL.");
  }

  return { imageUrl: outUrl, prompt };
}
