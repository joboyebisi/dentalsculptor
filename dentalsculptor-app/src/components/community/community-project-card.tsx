import Link from "next/link";
import { Heart, Download, Copy, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProjectPreviewImage } from "@/components/projects/project-preview-image";

export type CommunityProjectCardItem = {
  id: string;
  likes: number;
  downloads: number;
  featured: boolean;
  rating: number;
  project: {
    id: string;
    title: string;
    category: string | null;
    previewImageUrl: string | null;
    owner: { name: string | null; institution: string | null };
    learningObjectives: { id: string; title: string }[];
  };
};

export function CommunityProjectCard({ entry }: { entry: CommunityProjectCardItem }) {
  return (
    <Card className="overflow-hidden">
      <Link href={`/community/${entry.project.id}`} className="block">
        <ProjectPreviewImage
          src={entry.project.previewImageUrl}
          alt={`${entry.project.title} 3D preview`}
        />
      </Link>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <Link
            href={`/community/${entry.project.id}`}
            className="font-semibold hover:text-primary-container hover:underline"
          >
            {entry.project.title}
          </Link>
          {entry.featured && <Badge variant="research">Featured</Badge>}
        </div>
        <p className="mt-1 text-body-sm text-on-surface-variant">
          {entry.project.owner.name} · {entry.project.owner.institution}
        </p>
        {entry.project.category && (
          <Badge variant="outline" className="mt-2">
            {entry.project.category}
          </Badge>
        )}
        <div className="mt-3 flex flex-wrap gap-1">
          {entry.project.learningObjectives.map((obj) => (
            <Badge key={obj.id} variant="outline" className="text-xs">
              {obj.title}
            </Badge>
          ))}
        </div>
        <div className="mt-4 flex items-center justify-between">
          <div className="flex items-center gap-3 text-body-sm text-on-surface-variant">
            <span className="flex items-center gap-1">
              <Heart className="h-3.5 w-3.5" />
              {entry.likes}
            </span>
            <span className="flex items-center gap-1">
              <Download className="h-3.5 w-3.5" />
              {entry.downloads}
            </span>
            <span className="flex items-center gap-1">
              <Star className="h-3.5 w-3.5" />
              {entry.rating.toFixed(1)}
            </span>
          </div>
          <form action={`/api/community/${entry.project.id}/clone`} method="POST">
            <Button size="sm" variant="outline" type="submit">
              <Copy className="mr-1 h-3 w-3" />
              Clone
            </Button>
          </form>
        </div>
      </CardContent>
    </Card>
  );
}
