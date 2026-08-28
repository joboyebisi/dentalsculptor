import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { generateAssetKey, uploadAsset } from "@/lib/storage";

/** Upload a 2.5D viewport capture of the generated 3D model for project cards. */
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;
  const owns = await prisma.project.count({ where: { id, ownerId: user.id } });
  if (!owns) return NextResponse.json({ error: "Project not found." }, { status: 404 });

  const formData = await req.formData();
  const previewImage = formData.get("previewImage") as File | null;
  if (!previewImage?.size) {
    return NextResponse.json({ error: "Preview image is required." }, { status: 400 });
  }

  const buffer = Buffer.from(await previewImage.arrayBuffer());
  const key = generateAssetKey(user.id, `projects/${id}/preview-${Date.now()}.png`);
  const previewUrl = await uploadAsset(key, buffer, previewImage.type || "image/png");

  await prisma.$transaction([
    prisma.dentalModel.updateMany({
      where: { projectId: id },
      data: { thumbnailUrl: previewUrl },
    }),
    prisma.project.update({
      where: { id },
      data: { thumbnailUrl: previewUrl },
    }),
  ]);

  return NextResponse.json({ previewUrl, thumbnailUrl: previewUrl });
}
