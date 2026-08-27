import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ projectId: string }> }
) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Sign in to like this project." }, { status: 401 });
  const { projectId } = await params;
  const community = await prisma.communityProject.findFirst({
    where: { projectId, published: true },
    select: { id: true },
  });
  if (!community) return NextResponse.json({ error: "Published project not found." }, { status: 404 });

  const existing = await prisma.like.findUnique({
    where: { projectId_userId: { projectId, userId: user.id } },
    select: { id: true },
  });
  const liked = !existing;
  const likes = await prisma.$transaction(async (tx) => {
    if (existing) await tx.like.delete({ where: { id: existing.id } });
    else await tx.like.create({ data: { projectId, userId: user.id } });
    const exactCount = await tx.like.count({ where: { projectId } });
    await tx.communityProject.update({ where: { projectId }, data: { likes: exactCount } });
    return exactCount;
  });
  return NextResponse.json({ liked, likes });
}
