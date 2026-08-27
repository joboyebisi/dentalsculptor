"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { ExportWizardDialog } from "@/components/export/export-wizard-dialog";
import { ShareProjectDialog } from "@/components/editor/share-project-dialog";
import { jsonResponseError, readJsonResponse } from "@/lib/safe-json-response";

interface ActionProject {
  id: string;
  title: string;
  dentalModel?: {
    generated3DUrl?: string | null;
    sourceImageUrl?: string | null;
  } | null;
  communityProject?: { published: boolean } | null;
}

export function PostGenerationAction({
  projectId,
  action,
}: {
  projectId: string;
  action: "download" | "publish";
}) {
  const router = useRouter();
  const [project, setProject] = useState<ActionProject | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetch(`/api/projects/${projectId}`, { cache: "no-store" })
      .then(async (response) => {
        const { data, raw } = await readJsonResponse<{ project?: ActionProject; error?: string }>(response);
        if (!data) throw new Error(jsonResponseError(response, raw, "Project returned an invalid response."));
        if (!response.ok || !data.project) throw new Error(data.error ?? "Project unavailable.");
        if (!cancelled) setProject(data.project);
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Project unavailable.");
      });
    return () => { cancelled = true; };
  }, [projectId]);

  if (error) return <div className="flex min-h-[60vh] items-center justify-center p-6 text-error">{error}</div>;
  if (!project) return <div className="flex min-h-[60vh] items-center justify-center gap-3 text-on-surface-variant"><Loader2 className="h-5 w-5 animate-spin" />Preparing your model…</div>;

  const close = () => router.push("/projects");
  if (action === "download") {
    return (
      <ExportWizardDialog
        open
        onClose={close}
        projectId={project.id}
        projectTitle={project.title}
        modelUrl={project.dentalModel?.generated3DUrl}
        sourceImageUrl={project.dentalModel?.sourceImageUrl}
      />
    );
  }
  return (
    <ShareProjectDialog
      open
      onClose={close}
      projectId={project.id}
      projectTitle={project.title}
      hasModel={Boolean(project.dentalModel?.generated3DUrl)}
      initiallyPublished={Boolean(project.communityProject?.published)}
    />
  );
}
