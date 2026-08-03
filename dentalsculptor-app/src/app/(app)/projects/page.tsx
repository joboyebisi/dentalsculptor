import Link from "next/link";
import { Plus, Search } from "lucide-react";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import { isUiPreviewMode } from "@/lib/preview-mode";
import { PREVIEW_PROJECTS } from "@/lib/preview-data";

export default async function ProjectsPage() {
  const user = await getAuthUser();
  if (!user) return null;

  const projects = isUiPreviewMode()
    ? PREVIEW_PROJECTS
    : await prisma.project.findMany({
    where: { ownerId: user.id },
    orderBy: { updatedAt: "desc" },
    include: {
      dentalModel: true,
      communityProject: true,
      _count: { select: { annotations: true, learningObjectives: true } },
    },
  });

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
        <div className="relative flex-1 max-w-sm">
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
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link key={project.id} href={`/editor/${project.id}`}>
              <Card className="overflow-hidden transition-shadow hover:workbench-shadow">
                <div className="aspect-video bg-gradient-to-br from-surface-container to-primary-container/10" />
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <h3 className="font-semibold">{project.title}</h3>
                    <Badge variant="outline">{project.status}</Badge>
                  </div>
                  {project.description && (
                    <p className="mt-1 line-clamp-2 text-body-sm text-on-surface-variant">
                      {project.description}
                    </p>
                  )}
                  <div className="mt-3 flex items-center gap-3 text-body-sm text-on-surface-variant">
                    <span>{project._count.annotations} annotations</span>
                    <span>{project._count.learningObjectives} objectives</span>
                    <span>{formatDate(project.updatedAt)}</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
