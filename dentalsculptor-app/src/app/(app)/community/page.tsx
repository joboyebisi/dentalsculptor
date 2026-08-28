import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { COMMUNITY_CATEGORIES } from "@/lib/constants";
import { isUiPreviewMode } from "@/lib/preview-mode";
import { PREVIEW_COMMUNITY } from "@/lib/preview-data";
import { getCommunityPreviewImageUrl } from "@/lib/project-preview-image";
import {
  CommunityProjectCard,
  type CommunityProjectCardItem,
} from "@/components/community/community-project-card";

function toCommunityCardItem(cp: {
  id: string;
  likes: number;
  downloads: number;
  featured: boolean;
  rating: number;
  project: {
    id: string;
    title: string;
    category: string | null;
    thumbnailUrl?: string | null;
    dentalModel?: {
      sourceImageUrl?: string | null;
      thumbnailUrl?: string | null;
      generated3DUrl?: string | null;
      generated3DKey?: string | null;
      meshData?: unknown;
    } | null;
    owner: { name: string | null; institution: string | null };
    learningObjectives: { id: string; title: string }[];
  };
}): CommunityProjectCardItem {
  return {
    id: cp.id,
    likes: cp.likes,
    downloads: cp.downloads,
    featured: cp.featured,
    rating: cp.rating,
    project: {
      id: cp.project.id,
      title: cp.project.title,
      category: cp.project.category,
      previewImageUrl: getCommunityPreviewImageUrl(cp.project),
      owner: cp.project.owner,
      learningObjectives: cp.project.learningObjectives,
    },
  };
}

export default async function CommunityPage() {
  const communityProjects: CommunityProjectCardItem[] = isUiPreviewMode()
    ? PREVIEW_COMMUNITY.map((cp) => toCommunityCardItem(cp))
    : (
        await prisma.communityProject.findMany({
          where: { published: true },
          orderBy: { downloads: "desc" },
          include: {
            project: {
              include: {
                dentalModel: {
                  select: {
                    sourceImageUrl: true,
                    thumbnailUrl: true,
                    generated3DUrl: true,
                    generated3DKey: true,
                    meshData: true,
                  },
                },
                owner: { select: { name: true, institution: true } },
                learningObjectives: { take: 2 },
                _count: { select: { annotations: true } },
              },
            },
          },
        })
      ).map((cp) => toCommunityCardItem(cp));

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
            <CommunityProjectCard key={cp.id} entry={cp} />
          ))}
        </div>
      )}
    </div>
  );
}
