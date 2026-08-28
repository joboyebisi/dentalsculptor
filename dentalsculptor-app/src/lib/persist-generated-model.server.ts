import { prisma } from "@/lib/prisma";
import { mirrorRemoteAssetToStorage } from "@/lib/mirror-remote-asset";
import { extractStorageKeyFromUrl } from "@/lib/storage";
import { serializeModelProcessingStage } from "@/lib/model-processing-stage";
import { isSupabaseStorageConfigured } from "@/lib/supabase-server";
import type { Prisma } from "@/generated/prisma/client";

export interface PersistGeneratedModelInput {
  projectId: string;
  userId: string;
  modelUrl?: string | null;
  modelKey?: string | null;
  meshData?: Prisma.InputJsonValue | null;
  format?: string | null;
  mtlUrl?: string | null;
  thumbnailUrl?: string | null;
}

/**
 * Attach a generated 3D model to an existing project (mirrors remote URLs when configured).
 */
export async function persistGeneratedModelToProject(
  input: PersistGeneratedModelInput
): Promise<{ generated3DUrl: string | null; generated3DKey: string | null }> {
  const owns = await prisma.project.count({
    where: { id: input.projectId, ownerId: input.userId },
  });
  if (!owns) {
    throw new Error("Project not found.");
  }

  let generated3DUrl = input.modelUrl ?? null;
  let generated3DKey = input.modelKey ?? null;
  let mtlUrl = input.mtlUrl ?? null;

  if (!generated3DKey && generated3DUrl && isSupabaseStorageConfigured()) {
    try {
      const ext = input.format === "obj" ? "model.obj" : "model.glb";
      generated3DUrl = await mirrorRemoteAssetToStorage(
        generated3DUrl,
        input.userId,
        ext,
        input.format
      );
      if (mtlUrl) {
        mtlUrl = await mirrorRemoteAssetToStorage(mtlUrl, input.userId, "model.mtl", "obj");
      }
    } catch (error) {
      console.error("[persist-generated-model] mirror failed, keeping remote URL:", error);
    }
  }

  if (!generated3DKey && generated3DUrl) {
    generated3DKey = extractStorageKeyFromUrl(generated3DUrl);
  }

  await prisma.dentalModel.updateMany({
    where: { projectId: input.projectId },
    data: {
      generated3DUrl: generated3DUrl ?? undefined,
      generated3DKey: generated3DKey ?? undefined,
      thumbnailUrl: input.thumbnailUrl ?? undefined,
      meshData: input.meshData ?? undefined,
      processingStage: serializeModelProcessingStage({
        mtlUrl,
        format: input.format,
      }),
    },
  });

  if (input.thumbnailUrl) {
    await prisma.project.updateMany({
      where: { id: input.projectId },
      data: { thumbnailUrl: input.thumbnailUrl, status: "READY" },
    });
  } else {
    await prisma.project.updateMany({
      where: { id: input.projectId },
      data: { status: "READY" },
    });
  }

  return { generated3DUrl, generated3DKey };
}
