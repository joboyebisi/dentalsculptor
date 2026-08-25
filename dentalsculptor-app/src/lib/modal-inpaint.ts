import type { EditOperation } from "@/lib/edit-types";

export function isModalInpaintConfigured(): boolean {
  return Boolean(process.env.MODAL_INPAINT_URL?.trim());
}

/** Self-hosted SDXL inpaint on Modal — no per-image fal token cost. */
export async function runModalMaskedInpaint(options: {
  referenceBlob: Blob;
  maskBlob: Blob;
  instruction: string;
  operation: EditOperation;
}): Promise<{ previewBase64: string; contentType: string; prompt?: string }> {
  const url = process.env.MODAL_INPAINT_URL;
  if (!url) throw new Error("MODAL_INPAINT_URL is not configured.");

  const form = new FormData();
  form.append("instruction", options.instruction);
  form.append("operation", options.operation);
  form.append("referenceImage", options.referenceBlob, "reference.png");
  form.append("maskImage", options.maskBlob, "mask.png");

  const res = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.MODAL_WEBHOOK_SECRET ?? ""}` },
    body: form,
  });
  const data = (await res.json()) as {
    previewBase64?: string;
    contentType?: string;
    prompt?: string;
    error?: string;
  };
  if (!res.ok || !data.previewBase64) {
    throw new Error(data.error ?? "Modal inpaint failed.");
  }
  return {
    previewBase64: data.previewBase64,
    contentType: data.contentType ?? "image/png",
    prompt: data.prompt,
  };
}
