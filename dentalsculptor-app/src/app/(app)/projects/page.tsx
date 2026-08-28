import Link from "next/link";
import { Plus, Search } from "lucide-react";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { isUiPreviewMode } from "@/lib/preview-mode";
import { PREVIEW_PROJECTS } from "@/lib/preview-data";
import { ProjectsGrid, type ProjectListItem } from "@/components/projects/project-card";
import { getProjectPreviewImageUrl } from "@/lib/project-preview-image";

function toListItem(project: {
  id: string;
  title: string;
  description: string | null;
  status: string;
  updatedAt: Date;
  thumbnailUrl?: string | null;
  dentalModel?: {
    sourceImageUrl?: string | null;
    thumbnailUrl?: string | null;
    previewImageKey?: string | null;
    generated3DUrl?: string | null;
    generated3DKey?: string | null;
    meshData?: unknown;
  } | null;
  _count: { annotations: number; learningObjectives: number };
}): ProjectListItem {
  return {
    id: project.id,
    title: project.title,
    description: project.description,
    status: project.status,
    updatedAt: project.updatedAt.toISOString(),
    annotationCount: project._count.annotations,
    objectiveCount: project._count.learningObjectives,
    previewImageUrl: getProjectPreviewImageUrl(project),
  };
}

export default async function ProjectsPage() {
  const user = await getAuthUser();
  if (!user) return null;

  const projects: ProjectListItem[] = isUiPreviewMode()
    ? PREVIEW_PROJECTS.map((project) => toListItem(project))
    : (
        await prisma.project.findMany({
          where: { ownerId: user.id },
          orderBy: { updatedAt: "desc" },
          include: {
            dentalModel: {
              select: {
                sourceImageUrl: true,
                thumbnailUrl: true,
                previewImageKey: true,
                generated3DUrl: true,
                generated3DKey: true,
                meshData: true,
              },
            },
            _count: { select: { annotations: true, learningObjectives: true } },
          },
        })
      ).map((project) => toListItem(project));

  return (
    <div className="p-margin-page">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-display-lg">Projects</h1>
          <p className="mt-1 text-body-md text-on-surface-variant">
            Manage your dental learning experiences
          </p>
        </div>
        <Link href="/projects/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Project
          </Button>
        </Link>
      </div>

      <div className="mb-6 flex gap-3">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant" />
          <Input placeholder="Search projects..." className="pl-9" />
        </div>
      </div>

      {projects.length === 0 ? (
        <Card className="py-16 text-center">
          <CardContent>
            <p className="text-on-surface-variant">No projects yet. Create your first one.</p>
            <Link href="/projects/new">
              <Button className="mt-4">Create Project</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <ProjectsGrid projects={projects} />
      )}
    </div>
  );
}
