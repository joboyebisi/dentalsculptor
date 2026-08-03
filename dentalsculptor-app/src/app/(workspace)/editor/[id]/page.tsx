"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { EditorWorkspace, type EditorProject } from "@/components/editor/editor-workspace";
import { PREVIEW_EDITOR_PROJECT } from "@/lib/preview-data";

const isPreview = process.env.NEXT_PUBLIC_UI_PREVIEW_MODE === "true";

export default function EditorPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [project, setProject] = useState<EditorProject | null>(null);
  const [loading, setLoading] = useState(true);

  const loadProject = useCallback(async () => {
    if (isPreview && projectId.startsWith("preview-")) {
      setProject(PREVIEW_EDITOR_PROJECT as EditorProject);
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(`/api/projects/${projectId}`);
      const data = await res.json();
      setProject(data.project);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  async function handleSave(updates: Partial<EditorProject>) {
    if (isPreview && projectId.startsWith("preview-")) {
      setProject((p) => (p ? { ...p, ...updates } : p));
      return;
    }
    await fetch(`/api/projects/${projectId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface">
        <p className="text-on-surface-variant">Loading authoring workspace…</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface">
        <p className="text-on-surface-variant">Project not found.</p>
      </div>
    );
  }

  return (
    <EditorWorkspace
      project={project}
      projectId={projectId}
      onSave={handleSave}
    />
  );
}
