"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import {
  clearPendingLandingProject,
  getPendingLandingProject,
} from "@/lib/landing-session";
import {
  createProjectFromLandingPayload,
  pendingToPayload,
} from "@/lib/create-landing-project";

/**
 * Resume a landing workbench session after sign-in, consent, and onboarding.
 * Creates a project from sessionStorage and redirects to the editor.
 */
export default function AuthContinuePage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function resume() {
      const pending = getPendingLandingProject();

      if (!pending?.modelUrl || !pending.imageDataUrl) {
        router.replace("/dashboard");
        return;
      }

      try {
        const { projectId } = await createProjectFromLandingPayload(pendingToPayload(pending));
        clearPendingLandingProject();
        if (pending.nextStep === "download") {
          router.replace(`/projects/${projectId}/download`);
        } else if (pending.nextStep === "publish") {
          router.replace(`/projects/${projectId}/publish`);
        } else if (pending.nextStep === "case-wizard") {
          router.replace(`/editor/${projectId}?caseWizard=1`);
        } else {
          router.replace(`/editor/${projectId}`);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not resume your session.");
      }
    }

    resume();
  }, [router]);

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background p-6 text-center">
        <p className="text-body-md text-error">{error}</p>
        <button
          type="button"
          className="text-body-sm text-primary-container underline"
          onClick={() => router.push("/dashboard")}
        >
          Go to dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background">
      <Loader2 className="h-8 w-8 animate-spin text-primary-container" />
      <p className="text-body-md text-on-surface-variant">Preparing your editor workspace…</p>
    </div>
  );
}
