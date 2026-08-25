"use client";

import { useRef, useEffect, useState } from "react";
import Image from "next/image";
import { useSupabaseAuth } from "@/hooks/use-supabase-auth";
import { useSearchParams } from "next/navigation";
import { X, ImagePlus, Factory, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useLandingModel } from "@/context/landing-model-context";
import { GenerationNotifyOption } from "@/components/generation/generation-notify-option";
import { GenerationImageControls } from "@/components/generation/generation-image-controls";
import { ResearchInviteCallout } from "@/components/landing/research-invite-callout";
import { LANDING_WORKBENCH_HEIGHT } from "@/components/landing/landing-workbench-heights";
import { INVITE_QUERY_PARAM, normalizeInviteCode, resolveInviteCode } from "@/lib/research-invite";

export function LandingImageUploader() {
  const { isSignedIn } = useSupabaseAuth();
  const searchParams = useSearchParams();
  const {
    previewUrl,
    uploadedFile,
    isLoading,
    isPreparingImage,
    imagePrepLabel,
    error,
    prepareAndSetUploadedFile,
    generateModel,
    rotateUploadedImage,
    clearAll,
    isEnhancing,
  } = useLandingModel();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const inviteFromUrl = normalizeInviteCode(searchParams.get(INVITE_QUERY_PARAM));
  const [hasInvite, setHasInvite] = useState(Boolean(inviteFromUrl));

  useEffect(() => {
    setHasInvite(Boolean(resolveInviteCode(searchParams.get(INVITE_QUERY_PARAM))));
  }, [searchParams]);

  const canGenerate =
    Boolean(uploadedFile) &&
    !isLoading &&
    !isPreparingImage &&
    !isEnhancing &&
    (Boolean(isSignedIn) || hasInvite);

  return (
    <Card
      className="flex w-full max-w-md flex-col border-border-subtle lg:max-h-[var(--workbench-h)]"
      style={{ ["--workbench-h" as string]: LANDING_WORKBENCH_HEIGHT }}
    >
      <CardHeader className="space-y-1 pb-3 pt-4">
        <CardTitle className="text-headline-sm">Upload dental image</CardTitle>
        <CardDescription className="text-body-sm">
          One tooth, PNG or JPG — we turn it into an editable 3D model.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col space-y-3">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0] ?? null;
            void prepareAndSetUploadedFile(file);
          }}
        />

        {isPreparingImage ? (
          <div className="flex h-[140px] w-full flex-col items-center justify-center rounded-lg border border-border-subtle bg-surface-container-low text-on-surface-variant lg:h-[150px]">
            <Loader2 className="mb-2 h-7 w-7 animate-spin text-primary-container" />
            <span className="text-body-sm">{imagePrepLabel ?? "Preparing image…"}</span>
          </div>
        ) : previewUrl ? (
          <div className="relative h-[140px] overflow-hidden rounded-lg border border-border-subtle bg-surface-container-low lg:h-[150px]">
            <Image
              src={previewUrl}
              alt="Selected dental image"
              fill
              className="object-contain p-1"
              sizes="(max-width: 768px) 100vw, 340px"
            />
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex h-[140px] w-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-border-subtle bg-surface-container-low text-on-surface-variant transition-colors hover:border-primary-container/40 hover:bg-surface-container lg:h-[150px]"
          >
            <ImagePlus className="mb-2 h-7 w-7 text-primary-container/60" />
            <span className="text-body-sm">PNG or JPG · single tooth</span>
          </button>
        )}

        <div className="flex items-center justify-between gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
            {uploadedFile ? "Change image" : "Select image"}
          </Button>
          {uploadedFile && (
            <Button type="button" variant="ghost" size="sm" onClick={clearAll}>
              <X className="mr-1 h-4 w-4" />
              Clear
            </Button>
          )}
        </div>

        {imagePrepLabel && !isPreparingImage && (
          <p className="text-body-sm text-on-surface-variant">{imagePrepLabel}</p>
        )}

        {error && <p className="text-body-sm text-error">{error}</p>}

        {uploadedFile && (
          <GenerationImageControls
            compact
            disabled={isLoading || isPreparingImage || isEnhancing}
            onRotate={() => void rotateUploadedImage("cw")}
          />
        )}

        <GenerationNotifyOption className="py-2" disabled={isLoading || isEnhancing} />
      </CardContent>
      <CardFooter className="flex-col items-stretch gap-0 pb-4 pt-0">
        <Button className="w-full" disabled={!canGenerate} onClick={() => void generateModel()}>
          <Factory className="mr-2 h-4 w-4" />
          {isLoading ? "Generating model…" : "Generate 3D model"}
        </Button>
        <ResearchInviteCallout hasInvite={hasInvite} isSignedIn={Boolean(isSignedIn)} />
      </CardFooter>
    </Card>
  );
}
