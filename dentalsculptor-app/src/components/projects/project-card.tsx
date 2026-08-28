"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, MoreVertical, Trash2, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { ProjectPreviewImage } from "@/components/projects/project-preview-image";

export type ProjectListItem = {
  id: string;
  title: string;
  description: string | null;
  status: string;
  updatedAt: string;
  annotationCount: number;
  objectiveCount: number;
  previewImageUrl: string | null;
};

function DeleteProjectDialog({
  project,
  open,
  onClose,
  onDeleted,
}: {
  project: ProjectListItem;
  open: boolean;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [confirmed, setConfirmed] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setConfirmed(false);
      setDeleting(false);
      setError(null);
    }
  }, [open, project.id]);

  async function handleDelete() {
    if (!confirmed || deleting) return;
    setDeleting(true);
    setError(null);
    try {
      const res = await fetch(`/api/projects/${project.id}`, { method: "DELETE" });
      const data = (await res.json().catch(() => null)) as { error?: string } | null;
      if (!res.ok) throw new Error(data?.error ?? "Could not delete project");
      onDeleted();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete project");
    } finally {
      setDeleting(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        className="w-full max-w-md rounded-xl border border-border-subtle bg-panel-bg p-6 shadow-lg"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-project-title"
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="delete-project-title" className="text-headline-md font-semibold">
            Delete project?
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-on-surface-variant hover:bg-surface-container-low"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="mt-2 text-body-sm text-on-surface-variant">
          <span className="font-medium text-on-surface">{project.title}</span> and its 3D model,
          annotations, and learning content will be permanently removed.
        </p>
        <label
          htmlFor="delete-confirm"
          className="mt-4 flex cursor-pointer items-start gap-3 rounded-lg border border-border-subtle p-3"
        >
          <Checkbox
            id="delete-confirm"
            checked={confirmed}
            onCheckedChange={(v) => setConfirmed(v === true)}
            className="mt-0.5"
          />
          <span className="text-body-sm leading-relaxed">
            I understand this action cannot be undone
          </span>
        </label>
        {error && <p className="mt-3 text-body-sm text-destructive">{error}</p>}
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={deleting}>
            Cancel
          </Button>
          <Button variant="destructive" disabled={!confirmed || deleting} onClick={handleDelete}>
            {deleting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Deleting…
              </>
            ) : (
              <>
                <Trash2 className="mr-2 h-4 w-4" />
                Delete project
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

function ProjectCardMenu({ onDelete }: { onDelete: () => void }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  return (
    <div ref={menuRef} className="relative shrink-0">
      <button
        type="button"
        aria-label="Project options"
        aria-expanded={open}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className="rounded-lg p-1.5 text-on-surface-variant hover:bg-surface-container-low"
      >
        <MoreVertical className="h-4 w-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-full z-20 mt-1 min-w-[10rem] rounded-lg border border-border-subtle bg-panel-bg py-1 shadow-lg">
          <button
            type="button"
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-body-sm text-destructive hover:bg-destructive/10"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setOpen(false);
              onDelete();
            }}
          >
            <Trash2 className="h-4 w-4" />
            Delete project
          </button>
        </div>
      )}
    </div>
  );
}

export function ProjectCard({
  project,
  onDeleted,
}: {
  project: ProjectListItem;
  onDeleted: () => void;
}) {
  const router = useRouter();
  const [deleteOpen, setDeleteOpen] = useState(false);

  function openEditor() {
    router.push(`/editor/${project.id}`);
  }

  return (
    <>
      <Card
        className="flex h-full cursor-pointer flex-col overflow-hidden transition-shadow hover:workbench-shadow"
        onClick={openEditor}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openEditor();
          }
        }}
        role="button"
        tabIndex={0}
      >
        <ProjectPreviewImage src={project.previewImageUrl} alt={`${project.title} 3D preview`} />
        <CardContent className="flex flex-1 flex-col p-4">
          <div className="flex items-start gap-2">
            <h3 className="line-clamp-2 min-h-[2.75rem] flex-1 font-semibold leading-snug">
              {project.title}
            </h3>
            <Badge variant="outline" className="shrink-0">
              {project.status}
            </Badge>
            <div onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
              <ProjectCardMenu onDelete={() => setDeleteOpen(true)} />
            </div>
          </div>
          <p
            className={cn(
              "mt-1 line-clamp-2 min-h-[2.5rem] text-body-sm text-on-surface-variant",
              !project.description && "invisible"
            )}
          >
            {project.description || "No description"}
          </p>
          <div className="mt-auto flex items-center gap-3 pt-3 text-body-sm text-on-surface-variant">
            <span>{project.annotationCount} annotations</span>
            <span>{project.objectiveCount} objectives</span>
            <span>{formatDate(project.updatedAt)}</span>
          </div>
        </CardContent>
      </Card>
      <DeleteProjectDialog
        project={project}
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onDeleted={onDeleted}
      />
    </>
  );
}

export function ProjectsGrid({ projects }: { projects: ProjectListItem[] }) {
  const router = useRouter();
  const onDeleted = useCallback(() => router.refresh(), [router]);

  return (
    <div className="grid auto-rows-fr gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} onDeleted={onDeleted} />
      ))}
    </div>
  );
}
