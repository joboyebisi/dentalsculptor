import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { trackResearchEvent } from "@/lib/research-events";
import { generateDentalMeshFromImage } from "@/lib/model-generator";
import { generateAssetKey, uploadToS3 } from "@/lib/s3";

export async function POST(req: NextRequest) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const formData = await req.formData();
  const title = formData.get("title") as string;
  const description = (formData.get("description") as string) || "";
  const image = formData.get("image") as File;

  if (!title || !image) {
    return NextResponse.json({ error: "Title and image required" }, { status: 400 });
  }

  const buffer = Buffer.from(await image.arrayBuffer());
  const key = generateAssetKey(user.id, image.name);
  const imageUrl = await uploadToS3(key, buffer, image.type);

  const meshData = generateDentalMeshFromImage(800, 600);

  const project = await prisma.project.create({
    data: {
      ownerId: user.id,
      title,
      description,
      status: "READY",
      dentalModel: {
        create: {
          sourceImageUrl: imageUrl,
          meshData: meshData as object,
          processingStage: "complete",
        },
      },
    },
    include: { dentalModel: true },
  });

  await trackResearchEvent({
    userId: user.id,
    projectId: project.id,
    eventType: "PROJECT_CREATED",
    metadata: { title },
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
  });

  return NextResponse.json({ project, meshData });
}
