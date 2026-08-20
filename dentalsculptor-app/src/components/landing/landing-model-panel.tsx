"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSupabaseAuth } from "@/hooks/use-supabase-auth";
import { Download, Loader2, BookOpen, Pencil } from "lucide-react";
import { DentalViewer } from "@/components/three/dental-viewer";
import { Button } from "@/components/ui/button";
import { useLandingModel } from "@/context/landing-model-context";
import {
  fileToDataUrl,
  savePendingLandingProject,
  type PendingNextStep,
} from "@/lib/landing-session";
import { createProjectFromLandingPayload } from "@/lib/create-landing-project";
import { GENERATION_COPY, GENERATION_STAGE_LABELS } from "@/lib/generation-copy";
import { projectFileName } from "@/lib/editor-segmentation";

export function LandingModelPanel() {
  const router = useRouter();
  const { isSignedIn } = useSupabaseAuth();
  const {
    meshData,
    modelUrl,
    modelKey,
    thumbnailUrl,
    mtlUrl,
    format,
    isLoading,
    uploadedFile,
    hasModel,
    error,
    generationStage,
    generationProgress,
  } = useLandingModel();
  const [busy, setBusy] = useState<PendingNextStep | "download" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);

  useEffect(() => {
    if (!isLoading) {
      setElapsedSec(0);
      return;
    }
    const start = Date.now();
    const id = setInterval(() => setElapsedSec(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, [isLoading]);

  async function handleDownload() {
    if (!modelUrl) return;
    setBusy("download");
    setActionError(null);
    try {
      const res = await fetch(`/api/models/proxy?url=${encodeURIComponent(modelUrl)}`);
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const ext = format === "obj" ? "obj" : "glb";
      const name = uploadedFile
        ? `${projectFileName(uploadedFile.name.replace(/\.[^.]+$/, ""))}.${ext}`
        : `dental-model.${ext}`;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = name;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      setActionError("Could not download the model. Try again after it finishes loading.");
    } finally {
      setBusy(null);
    }
  }

  async function resumeAfterAuth(nextStep: PendingNextStep) {
    if (!hasModel || !uploadedFile || !modelUrl) return;

    setBusy(nextStep);
    setActionError(null);

    try {
      const payload = {
        imageFile: uploadedFile,
        modelUrl,
        modelKey: modelKey ?? undefined,
        thumbnailUrl: thumbnailUrl ?? undefined,
        mtlUrl: mtlUrl ?? undefined,
        format: format ?? undefined,
        sourceFileName: uploadedFile.name,
      };

      if (!isSignedIn) {
        const imageDataUrl = await fileToDataUrl(uploadedFile);
        savePendingLandingProject({ ...payload, imageDataUrl, nextStep });
        router.push(`/sign-up?redirect_url=${encodeURIComponent("/auth/continue")}`);
        return;
      }

      const profileRes = await fetch("/api/user/profile");
      if (!profileRes.ok) {
        const imageDataUrl = await fileToDataUrl(uploadedFile);
        savePendingLandingProject({ ...payload, imageDataUrl, nextStep });
        router.push(`/sign-in?redirect_url=${encodeURIComponent("/auth/continue")}`);
        return;
      }

      const { user } = await profileRes.json();

      if (!user.consentAccepted || !user.onboardingCompleted) {
        const imageDataUrl = await fileToDataUrl(uploadedFile);
        savePendingLandingProject({ ...payload, imageDataUrl, nextStep });
        router.push(user.consentAccepted ? "/onboarding" : "/consent");
        return;
      }

      const { projectId } = await createProjectFromLandingPayload(payload);
      if (nextStep === "case-wizard") {
        router.push(`/editor/${projectId}?caseWizard=1`);
      } else {
        router.push(`/editor/${projectId}`);
      }
    } catch {
      setActionError("Could not continue. Try again.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex w-full flex-col">
      <div className="relative h-[420px] overflow-hidden rounded-xl border border-border-subtle bg-surface-container-low md:h-[500px]">
        {hasModel ? (
          <DentalViewer
            meshData={meshData}
            modelUrl={modelUrl}
            modelFormat={format}
            mtlUrl={mtlUrl}
            className="h-full"
          />
        ) : isLoading ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-on-surface-variant">
            <Loader2 className="h-8 w-8 animate-spin text-primary-container" />
            <p className="font-medium text-text-main">{GENERATION_COPY.inProgressTitle}</p>
            <p className="text-body-sm">{GENERATION_COPY.inProgressDetail}</p>
            {generationStage && (
              <p className="text-body-sm text-primary-container">
                {GENERATION_STAGE_LABELS[generationStage] ?? generationStage}
                {generationProgress > 0 ? ` · ${generationProgress}%` : ""}
              </p>
            )}
            {elapsedSec > 0 && (
              <p className="text-body-sm text-on-surface-variant/80">Elapsed: {elapsedSec}s</p>
            )}
            {elapsedSec >= 30 && elapsedSec < 90 && (
              <p className="max-w-xs text-center text-body-sm text-on-surface-variant/80">
                {GENERATION_COPY.inProgressQueuedHint}
              </p>
            )}
            {elapsedSec >= 90 && (
              <p className="max-w-xs text-center text-body-sm text-on-surface-variant/80">
                {GENERATION_COPY.inProgressSlowHint}
              </p>
            )}
          </div>
        ) : error ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
            <p className="font-medium text-error">Generation failed</p>
            <p className="max-w-sm text-body-sm text-on-surface-variant">{error}</p>
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center px-6 text-center text-on-surface-variant">
            <p className="text-body-md text-text-main">
              {uploadedFile ? "Ready to generate" : "Your 3D model appears here"}
            </p>
            <p className="mt-2 max-w-sm text-body-sm">
              {uploadedFile
                ? "Click Generate 3D model to reconstruct the tooth from your photo."
                : "Upload an image using the panel on the left."}
            </p>
          </div>
        )}
      </div>

      {hasModel && (
        <div className="mt-4 space-y-3 border-t border-border-subtle pt-4">
          <p className="text-center text-body-sm text-on-surface-variant">
            {GENERATION_COPY.modelReadyHint}
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button variant="outline" onClick={handleDownload} disabled={!modelUrl || busy !== null}>
              {busy === "download" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              Download model
            </Button>
            <Button
              className="bg-primary-container text-on-primary"
              onClick={() => resumeAfterAuth("case-wizard")}
              disabled={!modelUrl || busy !== null}
            >
              {busy === "case-wizard" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <BookOpen className="mr-2 h-4 w-4" />
              )}
              Create teaching case
            </Button>
            <Button
              variant="secondary"
              onClick={() => resumeAfterAuth("editor")}
              disabled={!modelUrl || busy !== null}
            >
              {busy === "editor" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Pencil className="mr-2 h-4 w-4" />
              )}
              Open in editor
            </Button>
          </div>
          <p className="text-center text-body-sm text-on-surface-variant">
            Creating a case or opening the editor will ask you to sign in if needed — then you can
            pick a case template, edit, place on a jaw, and export.
          </p>
          {actionError && (
            <p className="text-center text-body-sm text-error">{actionError}</p>
          )}
        </div>
      )}
    </div>
  );
}
