import { NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { extractStorageKeyFromUrl } from "@/lib/storage";
import { streamStorageObjectByKey } from "@/lib/project-model-asset.server";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const { id } = await params;
  const project = await prisma.project.findFirst({
    where: { id, ownerId: user.id },
    select: { dentalModel: { select: { sourceImageUrl: true } } },
  });
  const sourceUrl = project?.dentalModel?.sourceImageUrl;
  if (!sourceUrl) return NextResponse.json({ error: "Source image not found" }, { status: 404 });
  if (sourceUrl.startsWith("/")) return NextResponse.redirect(new URL(sourceUrl, _request.url));
  const key = extractStorageKeyFromUrl(sourceUrl);
  if (key) {
    const asset = await streamStorageObjectByKey(key);
    if (asset) return new NextResponse(asset.body, { headers: { "Content-Type": asset.contentType, "Cache-Control": asset.cacheControl } });
  }
  const upstream = await fetch(sourceUrl, { cache: "no-store", signal: AbortSignal.timeout(30_000) });
  if (!upstream.ok) return NextResponse.json({ error: "Source image unavailable" }, { status: 502 });
  return new NextResponse(await upstream.arrayBuffer(), { headers: { "Content-Type": upstream.headers.get("content-type") ?? "image/jpeg", "Cache-Control": "private, max-age=300" } });
}
