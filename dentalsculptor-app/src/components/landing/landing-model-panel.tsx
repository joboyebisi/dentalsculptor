"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { Loader2 } from "lucide-react";
import { DentalViewer } from "@/components/three/dental-viewer";
import { Button } from "@/components/ui/button";
import { useLandingModel } from "@/context/landing-model-context";
import {
  fileToDataUrl,
  savePendingLandingProject,
} from "@/lib/landing-session";
import { createProjectFromLandingPayload } from "@/lib/create-landing-project";
import { GENERATION_COPY } from "@/lib/generation-copy";

export function LandingModelPanel() {
  const router = useRouter();
  const { isSignedIn } = useAuth();
  const {
    meshData,
    modelUrl,
    thumbnailUrl,
    mtlUrl,
    format,
    isLoading,
    uploadedFile,
    hasModel,
  } = useLandingModel();
  const [opening, setOpening] = useState(false);
  const [openError, setOpenError] = useState<string | null>(null);
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

  async function handleOpenEditor() {
    if (!hasModel || !uploadedFile || !modelUrl) return;

    setOpening(true);
    setOpenError(null);

    try {
      const payload = {
        imageFile: uploadedFile,
        modelUrl,
        thumbnailUrl: thumbnailUrl ?? undefined,
        mtlUrl: mtlUrl ?? undefined,
        format: format ?? undefined,
        sourceFileName: uploadedFile.name,
      };

      if (!isSignedIn) {
        const imageDataUrl = await fileToDataUrl(uploadedFile);
        savePendingLandingProject({ ...payload, imageDataUrl });
        router.push(`/sign-up?redirect_url=${encodeURIComponent("/auth/continue")}`);
        return;
      }

      const profileRes = await fetch("/api/user/profile");
      if (!profileRes.ok) {
        const imageDataUrl = await fileToDataUrl(uploadedFile);
        savePendingLandingProject({ ...payload, imageDataUrl });
        router.push(`/sign-in?redirect_url=${encodeURIComponent("/auth/continue")}`);
        return;
      }

      const { user } = await profileRes.json();

      if (!user.consentAccepted || !user.onboardingCompleted) {
        const imageDataUrl = await fileToDataUrl(uploadedFile);
        savePendingLandingProject({ ...payload, imageDataUrl });
        router.push(user.consentAccepted ? "/onboarding" : "/consent");
        return;
      }

      const { projectId } = await createProjectFromLandingPayload(payload);
      router.push(`/editor/${projectId}`);
    } catch {
      setOpenError("Could not prepare your project. Try again.");
    } finally {
      setOpening(false);
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
            {elapsedSec > 0 && (
              <p className="text-body-sm text-on-surface-variant/80">Elapsed: {elapsedSec}s</p>
            )}
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center px-6 text-center text-on-surface-variant">
            <p className="text-body-md text-text-main">
              {uploadedFile ? "Ready to generate" : "Your 3D model appears here"}
            </p>
            <p className="mt-2 max-w-sm text-body-sm">
              {uploadedFile
                ? "Click Generate 3D model to preview the reconstruction."
                : "Upload an image using the panel on the left."}
            </p>
          </div>
        )}
      </div>

      {hasModel && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
          <Button onClick={handleOpenEditor} disabled={opening || !modelUrl}>
            {opening ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Opening…
              </>
            ) : (
              "Open in editor"
            )}
          </Button>
          <p className="text-body-sm text-on-surface-variant">
            Your image and 3D model carry over into the editor.
          </p>
          {openError && <p className="w-full text-center text-body-sm text-error">{openError}</p>}
        </div>
      )}
    </div>
  );
}
