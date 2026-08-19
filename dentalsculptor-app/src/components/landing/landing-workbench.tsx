"use client";

import { Suspense } from "react";
import { LandingImageUploader } from "@/components/landing/landing-image-uploader";
import { LandingModelPanel } from "@/components/landing/landing-model-panel";
import { SingleToothScopeNote } from "@/components/landing/single-tooth-scope-note";

/** Landing workbench: upload → generate → preview → download / create case (auth later). */
export function LandingWorkbench() {
  return (
    <div className="flex flex-col items-start justify-center gap-8 lg:flex-row lg:items-start">
      <div className="w-full shrink-0 lg:w-[340px]">
        <Suspense
          fallback={
            <div className="h-[420px] w-full max-w-md animate-pulse rounded-xl border border-border-subtle bg-surface-container-low" />
          }
        >
          <LandingImageUploader />
        </Suspense>
        <SingleToothScopeNote />
      </div>
      <div className="min-w-0 flex-1">
        <LandingModelPanel />
      </div>
    </div>
  );
}
