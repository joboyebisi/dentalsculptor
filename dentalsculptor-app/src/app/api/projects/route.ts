import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { trackResearchEvent } from "@/lib/research-events";
import { generateDentalMeshFromImage } from "@/lib/model-generator";
import { generateMeshFromImage, isFalConfigured } from "@/lib/fal-mesh-generator";
import { autoProjectTitle } from "@/lib/auto-project-title";
import { serializeModelProcessingStage } from "@/lib/model-processing-stage";
import { generateAssetKey, uploadAsset } from "@/lib/storage";
import { mirrorRemoteAssetToStorage } from "@/lib/mirror-remote-asset";
import { isSupabaseStorageConfigured } from "@/lib/supabase-server";

export async function POST(req: NextRequest) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const t0 = Date.now();
  const formData = await req.formData();
  const titleInput = (formData.get("title") as string) || "";
  const description = (formData.get("description") as string) || "";
  const image = formData.get("image") as File;
  const existingModelUrl = (formData.get("modelUrl") as string) || null;
  const existingThumbnailUrl = (formData.get("thumbnailUrl") as string) || null;
  const existingMtlUrl = (formData.get("mtlUrl") as string) || null;
  const existingFormat = (formData.get("format") as string) || null;

  if (!image?.size) {
    return NextResponse.json({ error: "Image file is required." }, { status: 400 });
  }

  const title = titleInput.trim() || autoProjectTitle(image.name);
  const buffer = Buffer.from(await image.arrayBuffer());
  const key = generateAssetKey(user.id, image.name);

  let generated3DUrl = existingModelUrl;
  let thumbnailUrl = existingThumbnailUrl;
  let mtlUrl = existingMtlUrl;
  let format = existingFormat;
  let meshData: object | null = null;
  let imageUrl: string;

  async function mirrorGeneratedAssets() {
    if (!generated3DUrl || !isSupabaseStorageConfigured()) return;
    try {
      const ext = format === "obj" ? "model.obj" : "model.glb";
      generated3DUrl = await mirrorRemoteAssetToStorage(
        generated3DUrl,
        user!.id,
        ext,
        format
      );
      if (mtlUrl) {
        mtlUrl = await mirrorRemoteAssetToStorage(mtlUrl, user!.id, "model.mtl", "obj");
      }
    } catch (mirrorError) {
      console.error("[projects] model mirror failed, keeping remote URL:", mirrorError);
    }
  }

  if (!generated3DUrl && isFalConfigured()) {
    // Run Supabase upload and fal generation in parallel (avoids sequential double wait).
    const [uploadedImageUrl, falResult] = await Promise.all([
      uploadAsset(key, buffer, image.type),
      generateMeshFromImage(image).catch((error) => {
        console.error("[projects] fal generation failed:", error);
        return null;
      }),
    ]);

    imageUrl = uploadedImageUrl;

    if (falResult) {
      generated3DUrl = falResult.modelUrl;
      thumbnailUrl = falResult.thumbnailUrl ?? thumbnailUrl;
      mtlUrl = falResult.mtlUrl ?? mtlUrl;
      format = falResult.format;
      await mirrorGeneratedAssets();
    } else {
      meshData = generateDentalMeshFromImage(800, 600) as object;
    }
  } else {
    imageUrl = await uploadAsset(key, buffer, image.type);
    if (!generated3DUrl) {
      meshData = generateDentalMeshFromImage(800, 600) as object;
    } else {
      await mirrorGeneratedAssets();
    }
  }

  console.info(`[projects] create project pipeline ${Date.now() - t0}ms`);

  const project = await prisma.project.create({
    data: {
      ownerId: user.id,
      title,
      description,
      status: "READY",
      dentalModel: {
        create: {
          sourceImageUrl: imageUrl,
          generated3DUrl,
          thumbnailUrl,
          meshData: meshData ?? undefined,
          processingStage: serializeModelProcessingStage({ mtlUrl, format }),
        },
      },
    },
    include: { dentalModel: true },
  });

  await trackResearchEvent({
    userId: user.id,
    projectId: project.id,
    eventType: "PROJECT_CREATED",
    metadata: { title, fromLanding: Boolean(existingModelUrl) },
  });
  await trackResearchEvent({
    userId: user.id,
    projectId: project.id,
    eventType: "IMAGE_UPLOADED",
    metadata: { filename: image.name },
  });
  await trackResearchEvent({
    userId: user.id,
    projectId: project.id,
    eventType: "MODEL_GENERATED",
    metadata: {
      source: existingModelUrl ? "landing-session" : isFalConfigured() ? "fal" : "mock",
      format,
    },
  });

  return NextResponse.json({ project, meshData });
}
