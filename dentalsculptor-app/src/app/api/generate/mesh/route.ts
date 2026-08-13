import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { isUiPreviewMode } from "@/lib/preview-mode";
import { generateMeshFromImage, isFalConfigured } from "@/lib/fal-mesh-generator";
import { generateDentalMeshFromImage } from "@/lib/model-generator";
import { trackResearchEvent } from "@/lib/research-events";

export const maxDuration = 120;

export async function POST(req: NextRequest) {
  // Auth optional — landing workbench and editor both call this route.
  // FAL_KEY stays server-side; anonymous users can try generation before sign-up.
  const user = await getAuthUser();

  const formData = await req.formData();
  const image = formData.get("image") as File | null;
  const projectId = (formData.get("projectId") as string) || undefined;

  if (!image?.size) {
    return NextResponse.json({ error: "Image file is required." }, { status: 400 });
  }

  if (!isFalConfigured()) {
    const meshData = generateDentalMeshFromImage(800, 600);
    return NextResponse.json({
      source: "mock",
      meshData,
      message: "FAL_KEY not set — returning procedural mock mesh. Add FAL_KEY for Hunyuan 3D.",
    });
  }

  try {
    const t0 = Date.now();
    const result = await generateMeshFromImage(image);

    console.info(`[generate/mesh] completed in ${Date.now() - t0}ms format=${result.format}`);

    if (user && projectId && !isUiPreviewMode()) {
      await trackResearchEvent({
        userId: user.id,
        projectId,
        eventType: "MODEL_GENERATED",
        metadata: {
          provider: "fal",
          model: "hunyuan-3d-v3.1-rapid",
          format: result.format,
          requestId: result.requestId,
        },
      });
    }

    return NextResponse.json({
      source: "fal",
      modelUrl: result.modelUrl,
      thumbnailUrl: result.thumbnailUrl,
      textureUrl: result.textureUrl,
      mtlUrl: result.mtlUrl,
      format: result.format,
      requestId: result.requestId,
    });
  } catch (error) {
    console.error("[generate/mesh]", error);
    const message = error instanceof Error ? error.message : "Mesh generation failed.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
