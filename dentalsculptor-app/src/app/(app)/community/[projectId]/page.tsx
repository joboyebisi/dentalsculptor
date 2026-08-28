import { notFound } from "next/navigation";
import { Download } from "lucide-react";
import { prisma } from "@/lib/prisma";
import { getAuthUser } from "@/lib/auth";
import { communityModelServePath } from "@/lib/project-model-path";
import { DentalViewer } from "@/components/three/dental-viewer";
import { CommunityActions } from "@/components/community/community-actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { detectModelFormat } from "@/lib/model-format";

export default async function CommunityProjectPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const [entry, user] = await Promise.all([
    prisma.communityProject.findFirst({
      where: { projectId, published: true },
      include: { project: { include: { owner: { select: { name: true, institution: true } }, dentalModel: true, learningObjectives: { orderBy: { order: "asc" } } } } },
    }),
    getAuthUser(),
  ]);
  if (!entry) notFound();
  const liked = user ? Boolean(await prisma.like.findUnique({ where: { projectId_userId: { projectId, userId: user.id } } })) : false;
  const model = entry.project.dentalModel;
  const modelUrl =
    model?.generated3DUrl || model?.generated3DKey ? communityModelServePath(projectId) : null;

  return <div className="mx-auto max-w-6xl space-y-6 p-margin-page"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="mb-2 flex gap-2">{entry.project.category && <Badge variant="outline">{entry.project.category}</Badge>}{entry.featured && <Badge variant="research">Featured</Badge>}</div><h1 className="text-display-lg">{entry.project.title}</h1><p className="mt-1 text-on-surface-variant">Published by {entry.project.owner.name ?? "Educator"}{entry.project.owner.institution ? ` · ${entry.project.owner.institution}` : ""}</p></div><CommunityActions projectId={projectId} initialLikes={entry.likes} initialLiked={liked} /></div><div className="h-[min(65vh,680px)] overflow-hidden rounded-2xl border border-outline-variant bg-surface-container-low">{modelUrl ? <DentalViewer modelUrl={modelUrl} modelFormat={detectModelFormat(modelUrl)} className="h-full" /> : <div className="flex h-full items-center justify-center text-on-surface-variant">Model unavailable</div>}</div>{entry.project.description && <p className="max-w-3xl text-body-md text-on-surface-variant">{entry.project.description}</p>}{entry.project.learningObjectives.length > 0 && <section><h2 className="text-title-lg font-semibold">Learning objectives</h2><ul className="mt-2 list-disc space-y-1 pl-5 text-on-surface-variant">{entry.project.learningObjectives.map((item) => <li key={item.id}>{item.title}</li>)}</ul></section>}<form action={`/api/community/${projectId}/clone`} method="POST"><Button variant="outline" type="submit"><Download className="mr-2 h-4 w-4" />Make a copy</Button></form></div>;
}
