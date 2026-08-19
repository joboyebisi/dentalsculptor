"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import type { GeneratedMesh } from "@/lib/model-generator";
import { prepareGenerationImage } from "@/lib/prepare-generation-image";
import {
  notifyGenerationComplete,
  prepareGenerationNotification,
} from "@/lib/generation-notifications";
import { GENERATION_COPY, GENERATION_FETCH_TIMEOUT_MS } from "@/lib/generation-copy";
import { finalizeGenerationJob, pollGenerationJob } from "@/lib/generation-jobs";
import {
  INVITE_QUERY_PARAM,
  persistInviteCode,
  resolveInviteCode,
} from "@/lib/research-invite";

interface LandingModelState {
  uploadedFile: File | null;
  previewUrl: string | null;
  meshData: GeneratedMesh | null;
  modelUrl: string | null;
  modelKey: string | null;
  thumbnailUrl: string | null;
  mtlUrl: string | null;
  format: string | null;
  generationSource: "modal" | "fal" | "mock" | null;
  generationQuality: "preview" | "standard" | "final" | null;
  canEnhanceQuality: boolean;
  generationStage: string | null;
  generationProgress: number;
  isEnhancing: boolean;
  isLoading: boolean;
  error: string | null;
}

interface LandingModelContextType extends LandingModelState {
  setUploadedFile: (file: File | null) => void;
  generateModel: () => Promise<void>;
  enhanceModelQuality: () => Promise<void>;
  clearAll: () => void;
  clearError: () => void;
  hasPreview: boolean;
  isFinalReady: boolean;
  hasModel: boolean;
}

const LandingModelContext = createContext<LandingModelContextType | undefined>(undefined);

export function LandingModelProvider({ children }: { children: React.ReactNode }) {
  const searchParams = useSearchParams();
  const [uploadedFile, setUploadedFileState] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [meshData, setMeshData] = useState<GeneratedMesh | null>(null);
  const [modelUrl, setModelUrl] = useState<string | null>(null);
  const [modelKey, setModelKey] = useState<string | null>(null);
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);
  const [mtlUrl, setMtlUrl] = useState<string | null>(null);
  const [format, setFormat] = useState<string | null>(null);
  const [generationSource, setGenerationSource] = useState<"modal" | "fal" | "mock" | null>(null);
  const [generationQuality, setGenerationQuality] = useState<"preview" | "standard" | "final" | null>(null);
  const [canEnhanceQuality, setCanEnhanceQuality] = useState(false);
  const [generationStage, setGenerationStage] = useState<string | null>(null);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationJobId, setGenerationJobId] = useState<string | null>(null);
  const [generationJobToken, setGenerationJobToken] = useState<string | null>(null);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fromUrl = searchParams.get(INVITE_QUERY_PARAM);
    if (fromUrl) persistInviteCode(fromUrl);
  }, [searchParams]);

  const setUploadedFile = useCallback(
    (file: File | null) => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setUploadedFileState(file);
      setPreviewUrl(file ? URL.createObjectURL(file) : null);
      setMeshData(null);
      setModelUrl(null);
      setModelKey(null);
      setThumbnailUrl(null);
      setMtlUrl(null);
      setFormat(null);
      setGenerationSource(null);
      setGenerationQuality(null);
      setCanEnhanceQuality(false);
      setGenerationStage(null);
      setGenerationProgress(0);
      setGenerationJobId(null);
      setGenerationJobToken(null);
      setError(null);
    },
    [previewUrl]
  );

  const generateModel = useCallback(async () => {
    if (!uploadedFile) {
      setError("Select an image first.");
      return;
    }

    const inviteCode = resolveInviteCode(searchParams.get(INVITE_QUERY_PARAM));

    setIsLoading(true);
    setError(null);
    setMeshData(null);
    setModelUrl(null);
    setModelKey(null);
    setThumbnailUrl(null);
    setMtlUrl(null);
    setFormat(null);
    setGenerationSource(null);
    setGenerationQuality(null);
    setCanEnhanceQuality(false);
    setGenerationStage(null);
    setGenerationProgress(0);
    setGenerationJobId(null);
    setGenerationJobToken(null);

    try {
      await prepareGenerationNotification();
      const prepared = await prepareGenerationImage(uploadedFile);
      const formData = new FormData();
      formData.append("image", prepared);
      formData.append("quality", "preview");
      if (inviteCode) formData.append("accessCode", inviteCode);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), GENERATION_FETCH_TIMEOUT_MS);

      let res: Response;
      try {
        res = await fetch("/api/generate/mesh", {
          method: "POST",
          body: formData,
          signal: controller.signal,
        });
      } catch (fetchErr) {
        if (fetchErr instanceof Error && fetchErr.name === "AbortError") {
          throw new Error(GENERATION_COPY.timeoutError);
        }
        throw fetchErr;
      } finally {
        clearTimeout(timeoutId);
      }

      const contentType = res.headers.get("content-type") ?? "";
      if (!contentType.includes("application/json")) {
        throw new Error(
          res.ok
            ? "Unexpected server response. Restart the dev server and try again."
            : `Generation failed (${res.status}). Sign in may be required — refresh the page and retry.`
        );
      }

      let data = await res.json();
      if (!res.ok) {
        throw new Error(data.error ?? "Generation failed.");
      }
      if (res.status === 202 && data.jobId && data.jobToken) {
        setGenerationJobId(data.jobId);
        setGenerationJobToken(data.jobToken);
        data = {
          ...(await pollGenerationJob(data.jobId, data.jobToken, {
            onUpdate: (job) => {
              setGenerationStage(job.stage ?? null);
              setGenerationProgress(job.progress ?? 0);
            },
          })),
          source: "modal",
        };
      }

      if (data.modelUrl) {
        setModelUrl(data.modelUrl);
        setModelKey(data.modelKey ?? null);
        setThumbnailUrl(data.thumbnailUrl ?? null);
        setMtlUrl(data.mtlUrl ?? null);
        setFormat(data.format ?? "glb");
        setGenerationSource(
          data.source === "modal" ? "modal" : data.source === "fal" ? "fal" : "mock"
        );
        const quality =
          data.quality === "preview" || data.quality === "final" || data.quality === "standard"
            ? data.quality
            : "preview";
        setGenerationQuality(quality);
        setCanEnhanceQuality(Boolean(data.canFinalize));
        notifyGenerationComplete();
      } else if (data.meshData) {
        setMeshData(data.meshData);
        setGenerationSource("mock");
        notifyGenerationComplete();
      } else {
        throw new Error("No model was returned.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not process the image. Try another file.");
    } finally {
      setIsLoading(false);
    }
  }, [uploadedFile, searchParams]);

  const enhanceModelQuality = useCallback(async () => {
    if (!generationJobId || !generationJobToken) {
      setError("Enhancement is unavailable for this model.");
      return;
    }
    setIsEnhancing(true);
    setError(null);
    setGenerationStage("queued");
    setGenerationProgress(0);
    try {
      const result = await finalizeGenerationJob(
        generationJobId,
        generationJobToken,
        "standard",
        {
          onUpdate: (job) => {
            setGenerationStage(job.stage ?? null);
            setGenerationProgress(job.progress ?? 0);
          },
        }
      );
      setModelUrl(result.modelUrl ?? null);
      setModelKey(result.modelKey ?? null);
      setFormat(result.format ?? "glb");
      setGenerationQuality("standard");
      setCanEnhanceQuality(false);
      notifyGenerationComplete(GENERATION_COPY.finalModelReadyHint);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not enhance model quality.");
    } finally {
      setIsEnhancing(false);
      setGenerationStage(null);
      setGenerationProgress(0);
    }
  }, [generationJobId, generationJobToken]);

  const clearAll = useCallback(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setUploadedFileState(null);
    setPreviewUrl(null);
    setMeshData(null);
    setModelUrl(null);
    setModelKey(null);
    setThumbnailUrl(null);
    setMtlUrl(null);
    setFormat(null);
    setGenerationSource(null);
    setGenerationQuality(null);
    setCanEnhanceQuality(false);
    setGenerationStage(null);
    setGenerationProgress(0);
    setGenerationJobId(null);
    setGenerationJobToken(null);
    setError(null);
  }, [previewUrl]);

  const clearError = useCallback(() => setError(null), []);

  const hasPreview = Boolean(modelUrl || meshData);
  const isFinalReady =
    hasPreview &&
    !canEnhanceQuality &&
    !isLoading &&
    !isEnhancing &&
    (generationQuality === "standard" ||
      generationQuality === "final" ||
      generationSource === "mock" ||
      generationSource === "fal");
  const hasModel = hasPreview;

  return (
    <LandingModelContext.Provider
      value={{
        uploadedFile,
        previewUrl,
        meshData,
        modelUrl,
        modelKey,
        thumbnailUrl,
        mtlUrl,
        format,
        generationSource,
        generationQuality,
        canEnhanceQuality,
        generationStage,
        generationProgress,
        isEnhancing,
        isLoading,
        error,
        setUploadedFile,
        generateModel,
        enhanceModelQuality,
        clearAll,
        clearError,
        hasPreview,
        isFinalReady,
        hasModel,
      }}
    >
      {children}
    </LandingModelContext.Provider>
  );
}

export function useLandingModel() {
  const ctx = useContext(LandingModelContext);
  if (!ctx) throw new Error("useLandingModel must be used within LandingModelProvider");
  return ctx;
}
