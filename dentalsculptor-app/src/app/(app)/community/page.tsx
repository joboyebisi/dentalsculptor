import Link from "next/link";
import { Heart, Download, Copy, Star } from "lucide-react";
import { prisma } from "@/lib/prisma";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { COMMUNITY_CATEGORIES } from "@/lib/constants";
import { isUiPreviewMode } from "@/lib/preview-mode";
import { PREVIEW_COMMUNITY } from "@/lib/preview-data";

export default async function CommunityPage() {
  const communityProjects = isUiPreviewMode()
    ? PREVIEW_COMMUNITY
    : await prisma.communityProject.findMany({
    where: { published: true },
    orderBy: { downloads: "desc" },
    include: {
      project: {
        include: {
          owner: { select: { name: true, institution: true } },
          learningObjectives: { take: 2 },
          _count: { select: { annotations: true } },
        },
      },
    },
  });

  return (
    <div className="p-margin-page">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-display-lg">Community Hub</h1>
          <p className="mt-1 text-body-md text-on-surface-variant">
            Discover, clone, and remix dental learning experiences
          </p>
        </div>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {COMMUNITY_CATEGORIES.map((cat) => (
          <Badge key={cat} variant="outline" className="cursor-pointer hover:bg-surface-container">
            {cat}
          </Badge>
        ))}
      </div>

      {communityProjects.length === 0 ? (
        <Card className="py-16 text-center">
          <CardContent>
            <p className="text-on-surface-variant">No community projects yet. Be the first to publish!</p>
            <Link href="/projects/new">
              <Button className="mt-4">Create & Publish</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {communityProjects.map((cp) => (
            <Card key={cp.id} className="overflow-hidden">
              <div className="aspect-video bg-gradient-to-br from-surface-container to-primary-container/10" />
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <Link href={`/community/${cp.project.id}`} className="font-semibold hover:text-primary-container hover:underline">{cp.project.title}</Link>
                  {cp.featured && <Badge variant="research">Featured</Badge>}
                </div>
                <p className="mt-1 text-body-sm text-on-surface-variant">
                  {cp.project.owner.name} · {cp.project.owner.institution}
                </p>
                {cp.project.category && (
                  <Badge variant="outline" className="mt-2">{cp.project.category}</Badge>
                )}
                <div className="mt-3 flex flex-wrap gap-1">
                  {cp.project.learningObjectives.map((obj) => (
                    <Badge key={obj.id} variant="outline" className="text-xs">{obj.title}</Badge>
                  ))}
                </div>
                <div className="mt-4 flex items-center justify-between">
                  <div className="flex items-center gap-3 text-body-sm text-on-surface-variant">
                    <span className="flex items-center gap-1"><Heart className="h-3.5 w-3.5" />{cp.likes}</span>
                    <span className="flex items-center gap-1"><Download className="h-3.5 w-3.5" />{cp.downloads}</span>
                    <span className="flex items-center gap-1"><Star className="h-3.5 w-3.5" />{cp.rating.toFixed(1)}</span>
                  </div>
                  <form action={`/api/community/${cp.project.id}/clone`} method="POST">
                    <Button size="sm" variant="outline" type="submit">
                      <Copy className="mr-1 h-3 w-3" />Clone
                    </Button>
                  </form>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
