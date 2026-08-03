"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";
import { DentalViewer } from "@/components/three/dental-viewer";
import { Button } from "@/components/ui/button";
import { useLandingModel } from "@/context/landing-model-context";

export function LandingModelPanel() {
  const { meshData, isLoading, uploadedFile } = useLandingModel();

  return (
    <div className="flex w-full flex-col">
      <div className="relative h-[420px] overflow-hidden rounded-xl border border-border-subtle bg-surface-container-low md:h-[500px]">
        {meshData ? (
          <DentalViewer meshData={meshData} className="h-full" />
        ) : isLoading ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-on-surface-variant">
            <Loader2 className="h-8 w-8 animate-spin text-primary-container" />
            <p className="font-medium text-text-main">Generating 3D model</p>
            <p className="text-body-sm">Analysing image and building geometry…</p>
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

      {meshData && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
          <Link href="/editor/preview-project-1">
            <Button>Open in editor</Button>
          </Link>
          <p className="text-body-sm text-on-surface-variant">
            Annotate, add learning objectives, and prepare for teaching.
          </p>
        </div>
      )}
    </div>
  );
}
