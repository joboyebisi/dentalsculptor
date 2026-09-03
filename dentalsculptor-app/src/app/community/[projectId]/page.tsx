import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { prisma } from "@/lib/prisma";
import { getAuthUser } from "@/lib/auth";
import { communityModelServePath } from "@/lib/project-model-path";
import { DentalViewer } from "@/components/three/dental-viewer";
import { CommunityActions } from "@/components/community/community-actions";
import { Badge } from "@/components/ui/badge";
import { detectModelFormat } from "@/lib/model-format";

export async function generateMetadata({ params }: { params: Promise<{ projectId: string }> }): Promise<Metadata> {
  const { projectId } = await params;
  const entry = await prisma.communityProject.findFirst({
    where: { projectId, published: true },
    select: { project: { select: { title: true, description: true } } },
  });
  if (!entry) return { title: "Published dental teaching model" };
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "https://dentalsculptor.vercel.app";
  const url = `${appUrl}/community/${projectId}`;
  const image = `${appUrl}/api/community/${projectId}/preview-image`;
  const description = entry.project.description ?? "Explore this interactive 3D dental teaching model.";
  return {
    title: `${entry.project.title} | DentalSculptor`,
    description,
    alternates: { canonical: url },
    openGraph: { title: entry.project.title, description, url, type: "website", images: [{ url: image, alt: `${entry.project.title} 3D preview` }] },
    twitter: { card: "summary_large_image", title: entry.project.title, description, images: [image] },
  };
}

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
  const modelUrl = model?.generated3DUrl || model?.generated3DKey ? communityModelServePath(projectId) : null;

  return (
    <main className="min-h-screen bg-surface">
      <header className="border-b border-outline-variant bg-surface px-5 py-3">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link href="/" className="font-semibold text-primary-container">DentalSculptor</Link>
          <Link href={user ? "/community" : "/sign-in"} className="text-body-sm text-on-surface-variant hover:text-primary-container">{user ? "Community gallery" : "Sign in to clone or like"}</Link>
        </div>
      </header>
      <div className="mx-auto max-w-6xl space-y-6 p-margin-page">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 flex gap-2">{entry.project.category && <Badge variant="outline">{entry.project.category}</Badge>}{entry.featured && <Badge variant="research">Featured</Badge>}</div>
            <h1 className="text-display-lg">{entry.project.title}</h1>
            <p className="mt-1 text-on-surface-variant">Published by {entry.project.owner.name ?? "Educator"}{entry.project.owner.institution ? ` · ${entry.project.owner.institution}` : ""}</p>
          </div>
          <CommunityActions projectId={projectId} projectTitle={entry.project.title} initialLikes={entry.likes} initialLiked={liked} signedIn={Boolean(user)} />
        </div>
        <div className="h-[min(65vh,680px)] overflow-hidden rounded-2xl border border-outline-variant bg-surface-container-low">{modelUrl ? <DentalViewer modelUrl={modelUrl} modelFormat={detectModelFormat(modelUrl)} className="h-full" /> : <div className="flex h-full items-center justify-center text-on-surface-variant">Model unavailable</div>}</div>
        {entry.project.description && <p className="max-w-3xl text-body-md text-on-surface-variant">{entry.project.description}</p>}
        {entry.project.learningObjectives.length > 0 && <section><h2 className="text-title-lg font-semibold">Learning objectives</h2><ul className="mt-2 list-disc space-y-1 pl-5 text-on-surface-variant">{entry.project.learningObjectives.map((item) => <li key={item.id}>{item.title}</li>)}</ul></section>}
      </div>
    </main>
  );
}
