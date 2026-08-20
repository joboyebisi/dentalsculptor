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
import { ResearchInviteCallout } from "@/components/landing/research-invite-callout";
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
    clearAll,
  } = useLandingModel();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const inviteFromUrl = normalizeInviteCode(searchParams.get(INVITE_QUERY_PARAM));
  const [hasInvite, setHasInvite] = useState(Boolean(inviteFromUrl));

  useEffect(() => {
    setHasInvite(Boolean(resolveInviteCode(searchParams.get(INVITE_QUERY_PARAM))));
  }, [searchParams]);

  const canGenerate =
    Boolean(uploadedFile) && !isLoading && !isPreparingImage && (Boolean(isSignedIn) || hasInvite);

  return (
    <Card className="w-full max-w-md border-border-subtle">
      <CardHeader>
        <CardTitle className="text-headline-md">Upload dental image</CardTitle>
        <CardDescription>
          Start with a clinical photograph of one tooth — we will turn it into an editable 3D model.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
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
          <div className="flex aspect-[4/3] w-full flex-col items-center justify-center rounded-lg border border-border-subtle bg-surface-container-low text-on-surface-variant">
            <Loader2 className="mb-2 h-8 w-8 animate-spin text-primary-container" />
            <span className="text-body-sm">{imagePrepLabel ?? "Preparing image…"}</span>
          </div>
        ) : previewUrl ? (
          <div className="relative aspect-[4/3] overflow-hidden rounded-lg border border-border-subtle bg-surface-container-low">
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
            className="flex aspect-[4/3] w-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-border-subtle bg-surface-container-low text-on-surface-variant transition-colors hover:border-primary-container/40 hover:bg-surface-container"
          >
            <ImagePlus className="mb-2 h-8 w-8 text-primary-container/60" />
            <span className="text-body-sm">PNG or JPG · single tooth</span>
          </button>
        )}

        <div className="flex items-center justify-between gap-2">
          <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
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

        <GenerationNotifyOption disabled={isLoading} />
      </CardContent>
      <CardFooter className="flex-col items-stretch gap-0">
        <Button
          className="w-full"
          disabled={!canGenerate}
          onClick={() => void generateModel()}
        >
          <Factory className="mr-2 h-4 w-4" />
          {isLoading ? "Generating model…" : "Generate 3D model"}
        </Button>
        <ResearchInviteCallout hasInvite={hasInvite} isSignedIn={Boolean(isSignedIn)} />
      </CardFooter>
    </Card>
  );
}
