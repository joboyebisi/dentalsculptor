"use client";

import { useState } from "react";
import { Check, Copy, Share2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { jsonResponseError, readJsonResponse } from "@/lib/safe-json-response";

interface ShareProjectDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  projectTitle: string;
  hasModel: boolean;
  initiallyPublished?: boolean;
}

export function ShareProjectDialog({ open, onClose, projectId, projectTitle, hasModel, initiallyPublished = false }: ShareProjectDialogProps) {
  const [publishing, setPublishing] = useState(false);
  const [published, setPublished] = useState(initiallyPublished);
  const [copied, setCopied] = useState(false);
  const [communityUrl, setCommunityUrl] = useState<string | null>(initiallyPublished ? `/community/${projectId}` : null);
  const [error, setError] = useState<string | null>(null);
  if (!open) return null;

  async function publish() {
    setPublishing(true);
    setError(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/publish`, { method: "POST" });
      const { data, raw } = await readJsonResponse<{ error?: string; communityUrl?: string }>(res);
      if (!data) throw new Error(jsonResponseError(res, raw, "Publishing returned an invalid response."));
      if (!res.ok) throw new Error(data.error ?? "Could not publish project.");
      setCommunityUrl(data.communityUrl ?? `/community/${projectId}`);
      setPublished(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not publish project.");
    } finally {
      setPublishing(false);
    }
  }

  async function copyLink() {
    await navigator.clipboard.writeText(`${window.location.origin}${communityUrl ?? `/community/${projectId}`}`);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-on-surface/65 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg overflow-hidden rounded-xl border border-outline-variant bg-surface shadow-2xl">
        <div className="flex items-center justify-between border-b border-outline-variant px-5 py-4">
          <div><h2 className="text-title-lg font-semibold text-on-surface">Share project</h2><p className="mt-0.5 text-body-sm text-on-surface-variant">{projectTitle}</p></div>
          <button type="button" onClick={onClose} className="rounded-full p-2 hover:bg-surface-container-high" aria-label="Close"><X className="h-5 w-5" /></button>
        </div>
        <div className="space-y-4 p-5">
          <div className="rounded-xl border border-primary-container/25 bg-primary-container/5 p-4">
            <div className="flex gap-3"><Share2 className="mt-0.5 h-5 w-5 shrink-0 text-primary-container" /><div><p className="font-semibold text-on-surface">Publish to the community gallery</p><p className="mt-1 text-body-sm leading-relaxed text-on-surface-variant">Other educators can discover and clone this teaching project. Confirm that its image, model and case details contain no identifiable patient information.</p></div></div>
          </div>
          {published && <div className="space-y-2 rounded-lg border border-secondary/30 bg-secondary/10 px-3 py-2 text-body-sm text-on-surface"><div className="flex items-center gap-2"><Check className="h-4 w-4 text-secondary" /> Published to the community gallery.</div><a className="block break-all font-mono text-xs text-primary-container underline" href={communityUrl ?? `/community/${projectId}`}>View published project</a></div>}
          {error && <p className="text-body-sm text-error">{error}</p>}
        </div>
        <div className="flex justify-end gap-2 border-t border-outline-variant px-5 py-4">
          {published && <Button type="button" variant="outline" onClick={() => void copyLink()}>{copied ? <Check className="mr-2 h-4 w-4" /> : <Copy className="mr-2 h-4 w-4" />}{copied ? "Copied" : "Copy gallery link"}</Button>}
          <Button type="button" className="bg-primary-container text-on-primary" disabled={!hasModel || publishing || published} onClick={() => void publish()}>{publishing ? "Publishing…" : published ? "Published" : "Publish"}</Button>
        </div>
      </div>
    </div>
  );
}
