"use client";

import { useRef, useEffect, useState } from "react";
import { Factory, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSupabaseAuth } from "@/hooks/use-supabase-auth";
import { useSearchParams } from "next/navigation";
import { useLandingModel } from "@/context/landing-model-context";
import { GenerationNotifyOption } from "@/components/generation/generation-notify-option";
import { GenerationImagePicker } from "@/components/generation/generation-image-picker";
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
        <GenerationImagePicker
          compact
          previewUrl={previewUrl}
          hasFile={Boolean(uploadedFile)}
          disabled={isLoading || isEnhancing}
          preparing={isPreparingImage}
          prepLabel={imagePrepLabel}
          onSelectFile={(file) => void prepareAndSetUploadedFile(file)}
          onClear={clearAll}
          onRotate={() => void rotateUploadedImage("cw")}
        />

        {error && <p className="text-body-sm text-error">{error}</p>}

        <GenerationNotifyOption className="py-2" disabled={isLoading || isEnhancing} />
      </CardContent>
      <CardFooter className="flex-col items-stretch gap-0 pb-4 pt-0">
        <Button className="w-full" disabled={!canGenerate} onClick={() => void generateModel()}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating model…
            </>
          ) : (
            <>
              <Factory className="mr-2 h-4 w-4" />
              Generate 3D model
            </>
          )}
        </Button>
        <ResearchInviteCallout hasInvite={hasInvite} isSignedIn={Boolean(isSignedIn)} />
      </CardFooter>
    </Card>
  );
}
