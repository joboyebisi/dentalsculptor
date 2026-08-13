import { fal } from "@fal-ai/client";
import { getFalGenerationOptions } from "@/lib/fal-generation-options";

/** Hunyuan 3D Rapid — image to 3D (GLB/OBJ). */
export const HUNYUAN_3D_MODEL = "fal-ai/hunyuan-3d/v3.1/rapid/image-to-3d";

export interface FalMeshResult {
  modelUrl: string;
  thumbnailUrl?: string;
  textureUrl?: string;
  mtlUrl?: string;
  format: "glb" | "obj";
  requestId?: string;
}

interface FalFileRef {
  url: string;
  content_type?: string;
  file_name?: string;
}

interface FalHunyuanOutput {
  model_glb?: FalFileRef;
  material_mtl?: FalFileRef;
  thumbnail?: FalFileRef;
  texture?: FalFileRef;
  model_urls?: {
    glb?: FalFileRef;
    obj?: FalFileRef;
    mtl?: FalFileRef;
    texture?: FalFileRef;
  };
}

function isGlbRef(ref?: FalFileRef): boolean {
  if (!ref?.url) return false;
  const name = (ref.file_name ?? ref.url).toLowerCase();
  const type = (ref.content_type ?? "").toLowerCase();
  return name.endsWith(".glb") || type.includes("glb") || type.includes("gltf");
}

function isObjRef(ref?: FalFileRef): boolean {
  if (!ref?.url) return false;
  const name = (ref.file_name ?? ref.url).toLowerCase();
  const type = (ref.content_type ?? "").toLowerCase();
  return name.endsWith(".obj") || type.includes("obj");
}

function pickMtlUrl(data: FalHunyuanOutput): string | undefined {
  return data.model_urls?.mtl?.url ?? data.material_mtl?.url;
}

/**
 * fal often puts OBJ in `model_glb` when PBR is enabled — inspect extension/content-type,
 * not the field name.
 */
function pickModelUrl(
  data: FalHunyuanOutput
): { url: string; format: "glb" | "obj"; mtlUrl?: string } | null {
  const mtlUrl = pickMtlUrl(data);

  const glbCandidates = [data.model_urls?.glb, data.model_glb].filter(Boolean) as FalFileRef[];
  const glb = glbCandidates.find(isGlbRef);
  if (glb) return { url: glb.url, format: "glb" };

  const objCandidates = [data.model_urls?.obj, data.model_glb, data.model_urls?.glb].filter(
    Boolean
  ) as FalFileRef[];
  const obj = objCandidates.find(isObjRef);
  if (obj) return { url: obj.url, format: "obj", mtlUrl };

  const fallback = data.model_urls?.obj?.url ?? data.model_glb?.url;
  if (fallback) {
    return {
      url: fallback,
      format: isGlbRef({ url: fallback }) ? "glb" : "obj",
      mtlUrl,
    };
  }

  return null;
}

export function isFalConfigured(): boolean {
  return Boolean(process.env.FAL_KEY);
}

/**
 * Generate a 3D mesh from an image using fal.ai Hunyuan 3D.
 * Must only run on the server — requires FAL_KEY.
 *
 * @param options.inputImageUrl — skip fal.storage upload when image is already hosted (e.g. Supabase public URL)
 */
export async function generateMeshFromImage(
  file: File,
  options?: { inputImageUrl?: string }
): Promise<FalMeshResult> {
  if (!process.env.FAL_KEY) {
    throw new Error("FAL_KEY is not configured. Add it to .env or Vercel environment variables.");
  }

  fal.config({ credentials: process.env.FAL_KEY });
  const falOptions = getFalGenerationOptions();
  const t0 = Date.now();

  const imageUrl = options?.inputImageUrl ?? (await fal.storage.upload(file));
  const uploadMs = Date.now() - t0;

  const t1 = Date.now();
  const result = await fal.subscribe(HUNYUAN_3D_MODEL, {
    input: {
      input_image_url: imageUrl,
      enable_geometry: falOptions.enable_geometry,
      enable_pbr: falOptions.enable_pbr,
    },
    logs: true,
    onQueueUpdate: (update) => {
      if (update.status === "IN_PROGRESS") {
        update.logs?.map((log) => log.message).forEach((msg) => console.log("[fal]", msg));
      }
    },
  });
  const inferenceMs = Date.now() - t1;

  console.info(
    `[fal] mesh generation complete mode=${falOptions.mode} upload=${uploadMs}ms inference=${inferenceMs}ms total=${Date.now() - t0}ms`
  );

  const data = (result as { data?: FalHunyuanOutput }).data;
  if (!data) {
    throw new Error("fal.ai returned an empty response.");
  }

  const picked = pickModelUrl(data);
  if (!picked) {
    throw new Error("fal.ai response did not include a model URL.");
  }

  return {
    modelUrl: picked.url,
    thumbnailUrl: data.thumbnail?.url ?? data.model_urls?.texture?.url,
    textureUrl: data.texture?.url ?? data.model_urls?.texture?.url,
    mtlUrl: picked.mtlUrl,
    format: picked.format,
    requestId: (result as { requestId?: string }).requestId,
  };
}
