import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import {
  saveProjectCardPreview,
  streamProjectCardPreview,
} from "@/lib/project-card-preview.server";

export const maxDuration = 30;

/** Stream the 3D viewport card preview PNG for a project. */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;
  const owns = await prisma.project.count({ where: { id, ownerId: user.id } });
  if (!owns) return NextResponse.json({ error: "Project not found." }, { status: 404 });

  const asset = await streamProjectCardPreview(id);
  if (!asset) {
    return NextResponse.json({ error: "Preview not found." }, { status: 404 });
  }

  return new NextResponse(asset.body, {
    status: 200,
    headers: {
      "Content-Type": asset.contentType,
      "Cache-Control": "private, max-age=300",
    },
  });
}

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
  const key = await saveProjectCardPreview(id, buffer, previewImage.type || "image/png");

  return NextResponse.json({ previewImageKey: key });
}
