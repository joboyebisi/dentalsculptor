import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { isJawPlacement } from "@/lib/jaw-placement";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const project = await prisma.project.findFirst({ where: { id, ownerId: user.id }, select: { id: true } });
  if (!project) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const version = await prisma.projectVersion.findFirst({
    where: { projectId: id, label: "jaw-placement" },
    orderBy: { version: "desc" },
  });
  return NextResponse.json({ placement: version?.snapshot ?? null });
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const placement = await req.json();
  if (!isJawPlacement(placement)) {
    return NextResponse.json({ error: "Invalid jaw placement." }, { status: 422 });
  }
  const project = await prisma.project.findFirst({ where: { id, ownerId: user.id }, select: { id: true } });
  if (!project) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const latest = await prisma.projectVersion.findFirst({
    where: { projectId: id },
    orderBy: { version: "desc" },
    select: { version: true },
  });
  const saved = { ...placement, savedAt: new Date().toISOString() };
  await prisma.projectVersion.create({
    data: { projectId: id, version: (latest?.version ?? 0) + 1, label: "jaw-placement", snapshot: saved },
  });
  return NextResponse.json({ placement: saved });
}
