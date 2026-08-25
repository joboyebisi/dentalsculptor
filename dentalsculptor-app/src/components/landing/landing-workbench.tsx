"use client";

import { Suspense } from "react";
import { LandingImageUploader } from "@/components/landing/landing-image-uploader";
import { LandingModelPanel } from "@/components/landing/landing-model-panel";
import { SingleToothScopeNote } from "@/components/landing/single-tooth-scope-note";
import { LANDING_WORKBENCH_HEIGHT } from "@/components/landing/landing-workbench-heights";

/** Landing workbench: upload → generate → preview → download / create case (auth later). */
export function LandingWorkbench() {
  return (
    <div className="flex flex-col items-start gap-6 lg:grid lg:grid-cols-[minmax(280px,340px)_1fr] lg:items-stretch lg:gap-6">
      <div className="flex w-full shrink-0 flex-col lg:w-auto lg:min-h-0">
        <Suspense
          fallback={
            <div
              className="h-[420px] w-full max-w-md animate-pulse rounded-xl border border-border-subtle bg-surface-container-low lg:h-[var(--workbench-h)]"
              style={{ ["--workbench-h" as string]: LANDING_WORKBENCH_HEIGHT }}
            />
          }
        >
          <LandingImageUploader />
        </Suspense>
        <SingleToothScopeNote className="mt-3 lg:hidden" />
      </div>
      <div className="min-h-0 min-w-0 flex-1">
        <LandingModelPanel />
      </div>
    </div>
  );
}
