import { NextRequest, NextResponse } from "next/server";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { trackResearchEvent } from "@/lib/research-events";
import { extractStorageKeyFromUrl, generateAssetKey, uploadAsset } from "@/lib/storage";
import { streamProjectModelAsset, streamStorageObjectByKey } from "@/lib/project-model-asset.server";

async function readBody(body: ReadableStream | ArrayBuffer): Promise<Buffer> {
  if (body instanceof ArrayBuffer) return Buffer.from(body);
  return Buffer.from(await new Response(body).arrayBuffer());
}

async function cloneAuxiliaryAsset(
  userId: string,
  url: string | null,
  fallbackName: string
): Promise<string | null> {
  if (!url || url.startsWith("blob:") || url.startsWith("local://")) return null;
  const storageKey = extractStorageKeyFromUrl(url);
  const stored = storageKey ? await streamStorageObjectByKey(storageKey) : null;
  if (stored) {
    const key = generateAssetKey(userId, fallbackName);
    return uploadAsset(key, await readBody(stored.body), stored.contentType);
  }
  const response = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(30_000) });
  if (!response.ok) return null;
  const key = generateAssetKey(userId, fallbackName);
  return uploadAsset(
    key,
    Buffer.from(await response.arrayBuffer()),
    response.headers.get("content-type") ?? "application/octet-stream"
  );
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ projectId: string }> }
) {
  const { projectId } = await params;
  const user = await getAuthUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const source = await prisma.project.findUnique({
    where: { id: projectId },
    include: {
      dentalModel: true,
      annotations: true,
      learningObjectives: true,
      assessments: true,
      communityProject: true,
    },
  });

  if (!source) return NextResponse.json({ error: "Not found" }, { status: 404 });

  if (!source.communityProject?.published) {
    return NextResponse.json({ error: "Published project not found." }, { status: 404 });
  }

  let clonedModel: {
    generated3DUrl?: string;
    generated3DKey?: string;
    thumbnailUrl?: string | null;
    sourceImageUrl?: string | null;
    sourceFileUrl?: string | null;
  } | null = null;
  if (source.dentalModel) {
    const asset = await streamProjectModelAsset(source.dentalModel);
    if (!asset) {
      return NextResponse.json({ error: "Published 3D asset is unavailable." }, { status: 502 });
    }
    const key = generateAssetKey(user.id, `${source.title || "community-model"}.glb`);
    const generated3DUrl = await uploadAsset(key, await readBody(asset.body), asset.contentType);
    clonedModel = {
      generated3DUrl,
      generated3DKey: key,
      thumbnailUrl: await cloneAuxiliaryAsset(user.id, source.dentalModel.thumbnailUrl, "community-thumbnail.png"),
      sourceImageUrl: await cloneAuxiliaryAsset(user.id, source.dentalModel.sourceImageUrl, "community-source-image.png"),
      sourceFileUrl: await cloneAuxiliaryAsset(user.id, source.dentalModel.sourceFileUrl, "community-source-file.bin"),
    };
  }

  const cloned = await prisma.project.create({
    data: {
      ownerId: user.id,
      title: `${source.title} (Clone)`,
      description: source.description,
      status: "READY",
      instructions: source.instructions,
      hints: source.hints,
      feedback: source.feedback,
      category: source.category,
      dentalModel: source.dentalModel
        ? {
            create: {
              meshData: source.dentalModel.meshData ?? undefined,
              sourceImageUrl: clonedModel?.sourceImageUrl,
              sourceFileUrl: clonedModel?.sourceFileUrl,
              generated3DUrl: clonedModel?.generated3DUrl,
              generated3DKey: clonedModel?.generated3DKey,
              thumbnailUrl: clonedModel?.thumbnailUrl,
              processingStage: "complete",
            },
          }
        : undefined,
      annotations: {
        create: source.annotations.map((a) => ({
          creatorId: user.id,
          text: a.text,
          position: a.position as object,
          type: a.type,
          color: a.color,
        })),
      },
      learningObjectives: {
        create: source.learningObjectives.map((o) => ({
          title: o.title,
          description: o.description,
          order: o.order,
        })),
      },
      assessments: {
        create: source.assessments.map((a) => ({
          question: a.question,
          answer: a.answer,
          type: a.type,
          order: a.order,
        })),
      },
    },
  });

  await trackResearchEvent({
    userId: user.id,
    projectId: cloned.id,
    eventType: "PROJECT_CLONED",
    metadata: { sourceProjectId: projectId },
  });

  return NextResponse.redirect(new URL(`/editor/${cloned.id}`, req.url), 303);
}
