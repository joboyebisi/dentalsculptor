import Link from "next/link";
import {
  Plus,
  Upload,
  Box,
  UserPlus,
  Share2,
  FolderOpen,
  TrendingUp,
  Activity,
} from "lucide-react";
import { getAuthUser } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { getResearchMetrics } from "@/lib/research-events";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import { isUiPreviewMode } from "@/lib/preview-mode";
import { PREVIEW_PROJECTS, PREVIEW_METRICS, PREVIEW_EVENTS, PREVIEW_COMMUNITY } from "@/lib/preview-data";

export default async function DashboardPage() {
  const user = await getAuthUser();
  if (!user) return null;

  let projects;
  let metrics;
  let recentEvents;
  let communityProjects;

  if (isUiPreviewMode()) {
    projects = PREVIEW_PROJECTS;
    metrics = PREVIEW_METRICS;
    recentEvents = PREVIEW_EVENTS;
    communityProjects = PREVIEW_COMMUNITY;
  } else {
    [projects, metrics, recentEvents, communityProjects] = await Promise.all([
    prisma.project.findMany({
      where: { ownerId: user.id },
      orderBy: { updatedAt: "desc" },
      take: 5,
      include: { dentalModel: true, communityProject: true },
    }),
    getResearchMetrics(user.id),
    prisma.researchEvent.findMany({
      where: { userId: user.id },
      orderBy: { timestamp: "desc" },
      take: 8,
      include: { project: { select: { title: true } } },
    }),
    prisma.communityProject.findMany({
      where: { published: true },
      orderBy: { downloads: "desc" },
      take: 3,
      include: {
        project: {
          include: { owner: { select: { name: true, institution: true } } },
        },
      },
    }),
  ]);
  }

  const quickActions = [
    { href: "/projects/new", label: "New Project", icon: Plus },
    { href: "/projects/new", label: "Upload Image", icon: Upload },
    { href: "/projects/new", label: "Generate 3D", icon: Box },
    { href: "/students", label: "Invite Students", icon: UserPlus },
    { href: "/community", label: "Publish Project", icon: Share2 },
  ];

  return (
    <div className="p-margin-page">
      <div className="mb-8">
        <h1 className="text-display-lg text-text-main">
          Welcome back{user.name ? `, ${user.name.split(" ")[0]}` : ""}
        </h1>
        <p className="mt-1 text-body-md text-on-surface-variant">
          {user.role.charAt(0) + user.role.slice(1).toLowerCase()} · {user.institution ?? "No institution set"}
        </p>
      </div>

      {/* Quick Actions */}
      <div className="mb-8 flex flex-wrap gap-2">
        {quickActions.map((action) => (
          <Link key={action.label} href={action.href}>
            <Button variant="outline" size="sm">
              <action.icon className="mr-2 h-4 w-4" />
              {action.label}
            </Button>
          </Link>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Projects */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <FolderOpen className="h-5 w-5" />
                Recent Projects
              </CardTitle>
              <Link href="/projects">
                <Button variant="ghost" size="sm">View All</Button>
              </Link>
            </CardHeader>
            <CardContent>
              {projects.length === 0 ? (
                <div className="py-8 text-center">
                  <p className="text-on-surface-variant">No projects yet</p>
                  <Link href="/projects/new">
                    <Button className="mt-4" size="sm">Create Your First Project</Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {projects.map((project) => (
                    <Link
                      key={project.id}
                      href={`/editor/${project.id}`}
                      className="flex items-center justify-between rounded-lg border border-border-subtle p-3 transition-colors hover:bg-surface-container-low"
                    >
                      <div>
                        <p className="font-medium">{project.title}</p>
                        <p className="text-body-sm text-on-surface-variant">
                          Updated {formatDate(project.updatedAt)}
                        </p>
                      </div>
                      <Badge variant="outline">{project.status}</Badge>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Research Insights Widget */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-research-indigo" />
                Research Insights
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {[
                  { label: "Ownership", value: metrics.ownershipScore },
                  { label: "Agency", value: metrics.agencyScore },
                  { label: "Personalisation", value: metrics.personalisationScore },
                  { label: "Confidence", value: metrics.confidenceScore },
                ].map((m) => (
                  <div key={m.label} className="text-center">
                    <p className="text-2xl font-bold text-research-indigo">{m.value}</p>
                    <p className="text-body-sm text-on-surface-variant">{m.label}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar Widgets */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="h-4 w-4" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {recentEvents.length === 0 ? (
                  <p className="text-body-sm text-on-surface-variant">No activity yet</p>
                ) : (
                  recentEvents.map((event) => (
                    <div key={event.id} className="text-body-sm">
                      <p className="font-medium">{event.eventType.replace(/_/g, " ")}</p>
                      <p className="text-on-surface-variant">
                        {event.project?.title ?? "Platform"} · {formatDate(event.timestamp)}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Community Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {communityProjects.length === 0 ? (
                  <p className="text-body-sm text-on-surface-variant">No community activity yet</p>
                ) : (
                  communityProjects.map((cp) => (
                    <div key={cp.id} className="text-body-sm">
                      <p className="font-medium">{cp.project.title}</p>
                      <p className="text-on-surface-variant">
                        {cp.project.owner.name ?? "Educator"} · {cp.downloads} downloads
                      </p>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
