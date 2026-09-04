"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useSupabaseAuth } from "@/hooks/use-supabase-auth";
import { Download, Loader2, BookOpen, Share2, SlidersHorizontal } from "lucide-react";
import { DentalViewer, type DentalViewerHandle } from "@/components/three/dental-viewer";
import { Button } from "@/components/ui/button";
import { useLandingModel } from "@/context/landing-model-context";
import {
  fileToDataUrl,
  savePendingLandingProject,
  type PendingNextStep,
} from "@/lib/landing-session";
import { createProjectFromLandingPayload } from "@/lib/create-landing-project";
import { captureAndUploadCardPreview } from "@/lib/upload-project-preview-image";
import { GENERATION_COPY } from "@/lib/generation-copy";
import { GenerationProgressDisplay } from "@/components/generation/generation-progress-display";
import { LandingWebMcpTools } from "@/components/webmcp/landing-webmcp-tools";

export function LandingModelPanel() {
  const router = useRouter();
  const { isSignedIn } = useSupabaseAuth();
  const {
    meshData,
    modelUrl,
    modelKey,
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
    canEnhance,
    isFinalModel,
    lastGenerationSeconds,
    prepareAndSetUploadedFile,
    generateModel,
  } = useLandingModel();
  const [busy, setBusy] = useState<PendingNextStep | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const viewerRef = useRef<DentalViewerHandle>(null);

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
      const capturePreview = () => viewerRef.current?.capturePreview() ?? Promise.resolve(null);
      const payload = {
        imageFile: uploadedFile,
        modelUrl,
        modelKey: modelKey ?? undefined,
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

      const { projectId } = await createProjectFromLandingPayload({
        ...payload,
        previewImage: (await capturePreview()) ?? undefined,
      });
      void captureAndUploadCardPreview(projectId, capturePreview, { delayMs: 400, retries: 4 });
      if (nextStep === "download") router.push(`/projects/${projectId}/download`);
      else if (nextStep === "publish") router.push(`/projects/${projectId}/publish`);
      else if (nextStep === "case-wizard") router.push(`/editor/${projectId}?caseWizard=1`);
      else router.push(`/editor/${projectId}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not continue. Try again.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex w-full flex-col">
      <LandingWebMcpTools
        hasSourceImage={Boolean(uploadedFile)}
        hasModel={hasModel}
        busy={Boolean(isLoading || isEnhancing || busy)}
        importImage={async (imageUrl, requestedName) => {
          const parsed = new URL(imageUrl, window.location.origin);
          if (parsed.protocol !== "https:" && parsed.protocol !== "data:") {
            throw new Error("Use an HTTPS or data:image URL.");
          }
          const response = await fetch(parsed.toString(), { cache: "no-store" });
          if (!response.ok) throw new Error(`Could not retrieve the image (${response.status}).`);
          const blob = await response.blob();
          const type = blob.type.toLowerCase();
          if (!type.includes("image/png") && !type.includes("image/jpeg")) {
            throw new Error("DentalSculptor accepts PNG or JPEG source images only.");
          }
          if (blob.size > 15 * 1024 * 1024) throw new Error("The source image must be 15 MB or smaller.");
          const fallbackExtension = type.includes("png") ? ".png" : ".jpg";
          const safeBase = requestedName.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 80) || `dental-source${fallbackExtension}`;
          const fileName = /\.(png|jpe?g)$/i.test(safeBase) ? safeBase : `${safeBase}${fallbackExtension}`;
          await prepareAndSetUploadedFile(new File([blob], fileName, { type }));
        }}
        generate={generateModel}
        continueWithModel={resumeAfterAuth}
      />
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
            ref={viewerRef}
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
          {(isFinalModel || (hasModel && !canEnhance && !isLoading)) && (
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
                <Button
                  variant="ghost"
                  onClick={() => resumeAfterAuth("editor")}
                  disabled={!modelUrl || busy !== null}
                >
                  {busy === "editor" ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <SlidersHorizontal className="mr-2 h-4 w-4" />
                  )}
                  Free editor
                </Button>
              </div>
              <p className="text-center text-body-sm text-on-surface-variant">
                Download opens destination-specific export without entering the editor. Publishing
                creates a shareable community project. Teaching cases guide the workflow; Free editor keeps a compact mark → instruction → preview flow.
              </p>
            </>
          )}

          {actionError && (
            <p className="text-center text-body-sm text-error">{actionError}</p>
          )}
        </div>
      )}
    </div>
  );
}
