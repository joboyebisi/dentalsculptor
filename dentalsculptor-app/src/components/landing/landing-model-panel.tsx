"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { Download, Loader2, BookOpen, Pencil, Sparkles, CheckCircle2 } from "lucide-react";
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
import { cn } from "@/lib/utils";

export function LandingModelPanel() {
  const router = useRouter();
  const { isSignedIn } = useAuth();
  const {
    meshData,
    modelUrl,
    modelKey,
    thumbnailUrl,
    mtlUrl,
    format,
    isLoading,
    uploadedFile,
    hasPreview,
    isFinalReady,
    error,
    canEnhanceQuality,
    generationStage,
    generationProgress,
    isEnhancing,
    enhanceModelQuality,
  } = useLandingModel();
  const [busy, setBusy] = useState<PendingNextStep | "download" | null>(null);
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
    if (!isFinalReady || !uploadedFile || !modelUrl) return;

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

  const enhanceReady = canEnhanceQuality && hasPreview && !isEnhancing && !isLoading;
  const enhanceDisabled = !enhanceReady || isEnhancing || isLoading || isFinalReady;

  return (
    <div className="flex w-full flex-col">
      <div className="relative h-[420px] overflow-hidden rounded-xl border border-border-subtle bg-surface-container-low md:h-[500px]">
        {hasPreview ? (
          <>
            <DentalViewer
              meshData={meshData}
              modelUrl={modelUrl}
              modelFormat={format}
              mtlUrl={mtlUrl}
              className="h-full"
            />
            {hasPreview && !isFinalReady && !isEnhancing && (
              <div className="absolute left-3 top-3 rounded-full border border-amber-200/80 bg-amber-50/95 px-3 py-1 text-body-sm font-medium text-amber-900 shadow-sm">
                Preview — inspect shape before building final model
              </div>
            )}
          </>
        ) : isLoading || isEnhancing ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-on-surface-variant">
            <Loader2 className="h-8 w-8 animate-spin text-primary-container" />
            <p className="font-medium text-text-main">
              {isEnhancing
                ? GENERATION_COPY.buildingFinalModelLabel
                : GENERATION_COPY.inProgressTitle}
            </p>
            <p className="text-body-sm">
              {isEnhancing
                ? GENERATION_COPY.buildFinalModelHint
                : GENERATION_COPY.inProgressDetail}
            </p>
            {generationStage && (
              <p className="text-body-sm text-primary-container">
                {GENERATION_STAGE_LABELS[generationStage] ?? generationStage}
                {generationProgress > 0 ? ` · ${generationProgress}%` : ""}
              </p>
            )}
            {elapsedSec > 0 && (
              <p className="text-body-sm text-on-surface-variant/80">Elapsed: {elapsedSec}s</p>
            )}
            {elapsedSec >= 30 && elapsedSec < 90 && !isEnhancing && (
              <p className="max-w-xs text-center text-body-sm text-on-surface-variant/80">
                {GENERATION_COPY.inProgressQueuedHint}
              </p>
            )}
            {elapsedSec >= 90 && !isEnhancing && (
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
              {uploadedFile ? "Ready to generate" : "Your 3D preview appears here"}
            </p>
            <p className="mt-2 max-w-sm text-body-sm">
              {uploadedFile
                ? "Click Generate 3D model for a fast preview, then build the final model below."
                : "Upload an image using the panel on the left."}
            </p>
          </div>
        )}
      </div>

      {/* Step 2 — always visible once user has uploaded; primary action below viewer */}
      <div className="mt-4 space-y-2">
        <Button
          size="lg"
          className={cn(
            "h-12 w-full text-base font-semibold transition-all",
            enhanceReady &&
              "bg-primary-container text-on-primary shadow-md ring-2 ring-primary-container/30 ring-offset-2 hover:bg-primary-container/90",
            !enhanceReady && !isFinalReady && "bg-muted text-muted-foreground hover:bg-muted"
          )}
          onClick={() => void enhanceModelQuality()}
          disabled={enhanceDisabled}
        >
          {isEnhancing ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              {GENERATION_COPY.buildingFinalModelLabel}
            </>
          ) : isFinalReady ? (
            <>
              <CheckCircle2 className="mr-2 h-5 w-5" />
              Final model ready
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-5 w-5" />
              {GENERATION_COPY.buildFinalModelLabel}
            </>
          )}
        </Button>
        <p className="text-center text-body-sm text-on-surface-variant">
          {isFinalReady
            ? GENERATION_COPY.finalModelReadyHint
            : enhanceReady
              ? GENERATION_COPY.previewReadyHint
              : hasPreview
                ? GENERATION_COPY.buildFinalModelHint
                : "Generate a preview first — this button unlocks when the preview is ready."}
        </p>
      </div>

      {isFinalReady && (
        <div className="mt-4 space-y-3 border-t border-border-subtle pt-4">
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
