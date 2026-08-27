"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSupabaseAuth } from "@/hooks/use-supabase-auth";
import { Download, Loader2, BookOpen, Sparkles, Share2 } from "lucide-react";
import { DentalViewer } from "@/components/three/dental-viewer";
import { Button } from "@/components/ui/button";
import { useLandingModel } from "@/context/landing-model-context";
import {
  fileToDataUrl,
  savePendingLandingProject,
  type PendingNextStep,
} from "@/lib/landing-session";
import { createProjectFromLandingPayload } from "@/lib/create-landing-project";
import { GENERATION_COPY } from "@/lib/generation-copy";
import { GenerationProgressDisplay } from "@/components/generation/generation-progress-display";

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
    modelQuality,
    isEnhancing,
    enhanceModel,
    canEnhance,
    isFinalModel,
    lastGenerationSeconds,
  } = useLandingModel();
  const [busy, setBusy] = useState<PendingNextStep | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);

  useEffect(() => {
    if (!isLoading && !isEnhancing) {
      setElapsedSec(0);
      return;
    }
    const start = Date.now();
    const id = setInterval(() => setElapsedSec(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, [isLoading, isEnhancing]);

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
      if (nextStep === "download") router.push(`/projects/${projectId}/download`);
      else if (nextStep === "publish") router.push(`/projects/${projectId}/publish`);
      else if (nextStep === "case-wizard") router.push(`/editor/${projectId}?caseWizard=1`);
      else router.push(`/editor/${projectId}`);
    } catch {
      setActionError("Could not continue. Try again.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex w-full flex-col">
      <div
        className="relative h-[420px] overflow-hidden rounded-xl border border-border-subtle bg-surface-container-low sm:h-[480px] lg:h-[calc(100dvh-14rem)] lg:min-h-[520px]"
      >
        {hasModel && modelQuality === "preview" && !isEnhancing && (
          <span className="absolute left-3 top-3 z-10 rounded-full bg-warning/90 px-2.5 py-1 text-xs font-medium text-white">
            Preview
          </span>
        )}
        {hasModel ? (
          <DentalViewer
            meshData={meshData}
            modelUrl={modelUrl}
            modelFormat={format}
            mtlUrl={mtlUrl}
            className="h-full"
          />
        ) : isLoading || isEnhancing ? (
          <GenerationProgressDisplay
            title={
              isEnhancing ? GENERATION_COPY.enhancingQualityLabel : GENERATION_COPY.inProgressTitle
            }
            detail={
              isEnhancing
                ? "Extracting full-resolution mesh from the preview — no second inference run."
                : GENERATION_COPY.inProgressDetail
            }
            stage={generationStage}
            progress={generationProgress}
            elapsedSec={elapsedSec}
          />
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
          {lastGenerationSeconds != null && (
            <p className="text-center text-body-sm text-on-surface-variant">
              {GENERATION_COPY.completedIn(lastGenerationSeconds)}
            </p>
          )}
          {canEnhance && (
            <Button
              className="w-full bg-primary-container text-on-primary ring-2 ring-primary-container/30"
              onClick={() => void enhanceModel()}
              disabled={isEnhancing || isLoading || busy !== null}
            >
              {isEnhancing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="mr-2 h-4 w-4" />
              )}
              {isEnhancing
                ? GENERATION_COPY.enhancingQualityLabel
                : "Build final 3D model"}
            </Button>
          )}

          {isFinalModel && (
            <>
              <p className="text-center text-body-sm text-on-surface-variant">
                {GENERATION_COPY.modelReadyHint}
              </p>
              <div className="flex flex-wrap items-center justify-center gap-3">
                <Button
                  className="bg-primary-container text-on-primary"
                  onClick={() => resumeAfterAuth("download")}
                  disabled={!modelUrl || busy !== null}
                >
                  {busy === "download" ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="mr-2 h-4 w-4" />
                  )}
                  Download or export
                </Button>
                <Button
                  variant="outline"
                  onClick={() => resumeAfterAuth("publish")}
                  disabled={!modelUrl || busy !== null}
                >
                  {busy === "publish" ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Share2 className="mr-2 h-4 w-4" />
                  )}
                  Publish
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => resumeAfterAuth("case-wizard")}
                  disabled={!modelUrl || busy !== null}
                >
                  {busy === "case-wizard" ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <BookOpen className="mr-2 h-4 w-4" />
                  )}
                  Optional: create a teaching case
                </Button>
              </div>
              <p className="text-center text-body-sm text-on-surface-variant">
                Download opens destination-specific export without entering the editor. Publishing
                creates a shareable community project. Editing is optional.
              </p>
            </>
          )}

          {canEnhance && !isEnhancing && (
            <p className="text-center text-body-sm text-on-surface-variant">
              Preview loaded — build the final model for download, teaching cases, or editing.
            </p>
          )}

          {actionError && (
            <p className="text-center text-body-sm text-error">{actionError}</p>
          )}
        </div>
      )}
    </div>
  );
}
