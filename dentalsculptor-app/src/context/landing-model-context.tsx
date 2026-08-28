"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import type { GeneratedMesh } from "@/lib/model-generator";
import { prepareGenerationImageDetailed } from "@/lib/prepare-generation-image";
import {
  notifyGenerationComplete,
  prepareGenerationNotification,
} from "@/lib/generation-notifications";
import {
  GENERATION_COPY,
  DEFAULT_GENERATION_QUALITY,
  GENERATION_FETCH_TIMEOUT_MS,
  GENERATION_POLL_INTERVAL_MS,
  GENERATION_POLL_MAX_ATTEMPTS,
} from "@/lib/generation-copy";
import { finalizeGenerationJob, pollGenerationJob } from "@/lib/generation-jobs";
import {
  INVITE_QUERY_PARAM,
  persistInviteCode,
  resolveInviteCode,
} from "@/lib/research-invite";
import { requestGpuWarmup } from "@/lib/gpu-warmup";
import { rotateImageFile } from "@/lib/image-rotation";

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
  generationStage: string | null;
  generationProgress: number;
  isLoading: boolean;
  isPreparingImage: boolean;
  imagePrepLabel: string | null;
  error: string | null;
  modelQuality: "preview" | "standard" | "final" | null;
  isEnhancing: boolean;
  lastGenerationSeconds: number | null;
}

interface LandingModelContextType extends LandingModelState {
  setUploadedFile: (file: File | null) => void;
  prepareAndSetUploadedFile: (file: File | null) => Promise<void>;
  generateModel: () => Promise<void>;
  enhanceModel: () => Promise<void>;
  rotateUploadedImage: (direction: "cw" | "ccw") => Promise<void>;
  clearAll: () => void;
  clearError: () => void;
  hasModel: boolean;
  canEnhance: boolean;
  isFinalModel: boolean;
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
  const [generationStage, setGenerationStage] = useState<string | null>(null);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isPreparingImage, setIsPreparingImage] = useState(false);
  const [imagePrepLabel, setImagePrepLabel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modelQuality, setModelQuality] = useState<"preview" | "standard" | "final" | null>(
    null
  );
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobToken, setJobToken] = useState<string | null>(null);
  const [lastGenerationSeconds, setLastGenerationSeconds] = useState<number | null>(null);

  useEffect(() => {
    const fromUrl = searchParams.get(INVITE_QUERY_PARAM);
    if (fromUrl) persistInviteCode(fromUrl);
    if (resolveInviteCode(fromUrl)) {
      requestGpuWarmup("invite");
    }
  }, [searchParams]);

  const clearUploadState = useCallback(() => {
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
    setGenerationStage(null);
    setGenerationProgress(0);
    setError(null);
    setModelQuality(null);
    setIsEnhancing(false);
    setJobId(null);
    setJobToken(null);
    setLastGenerationSeconds(null);
  }, [previewUrl]);

  const prepareAndSetUploadedFile = useCallback(
    async (file: File | null) => {
      clearUploadState();
      if (!file) return;

      setIsPreparingImage(true);
      setImagePrepLabel("Preparing image for generation…");
      try {
        const prepared = await prepareGenerationImageDetailed(file);
        setUploadedFileState(prepared.file);
        setPreviewUrl(URL.createObjectURL(prepared.file));
        if (prepared.warnings.includes("converted-to-jpeg")) {
          setImagePrepLabel("Optimized: resized and converted for faster generation.");
        } else if (prepared.warnings.includes("very-small-image")) {
          setImagePrepLabel("Note: this image is quite small — a higher-resolution photo may improve results.");
        } else if (prepared.warnings.length > 0) {
          setImagePrepLabel("Image prepared for single-tooth generation.");
        } else {
          setImagePrepLabel(null);
        }
        requestGpuWarmup("upload");
      } catch {
        setUploadedFileState(file);
        setPreviewUrl(URL.createObjectURL(file));
        setImagePrepLabel(null);
      } finally {
        setIsPreparingImage(false);
      }
    },
    [clearUploadState]
  );

  const setUploadedFile = useCallback(
    (file: File | null) => {
      void prepareAndSetUploadedFile(file);
    },
    [prepareAndSetUploadedFile]
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
    setGenerationStage(null);
    setGenerationProgress(0);
    setModelQuality(null);
    setJobId(null);
    setJobToken(null);

    const startedAt = Date.now();

    try {
      await prepareGenerationNotification();
      requestGpuWarmup("generate");
      const formData = new FormData();
      formData.append("image", uploadedFile);
      formData.append("quality", DEFAULT_GENERATION_QUALITY);
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
        const statusMsg =
          res.status === 504 || res.status === 502
            ? GENERATION_COPY.gatewayTimeoutError
            : res.status === 503
              ? GENERATION_COPY.serviceUnavailableError
              : res.ok
                ? "Unexpected server response. Restart the dev server and try again."
                : `Generation failed (${res.status}). Sign in may be required — refresh the page and retry.`;
        throw new Error(statusMsg);
      }

      let data = await res.json();
      if (!res.ok) {
        throw new Error(data.error ?? "Generation failed.");
      }

      let activeJobId: string | null = null;
      let activeJobToken: string | null = null;
      if (res.status === 202 && data.jobId && data.jobToken) {
        activeJobId = data.jobId;
        activeJobToken = data.jobToken;
        setJobId(activeJobId);
        setJobToken(activeJobToken);
        data = {
          ...(await pollGenerationJob(data.jobId, data.jobToken, {
            intervalMs: GENERATION_POLL_INTERVAL_MS,
            maxAttempts: GENERATION_POLL_MAX_ATTEMPTS,
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
        setModelQuality(
          data.quality === "final" || data.quality === "standard"
            ? data.quality
            : DEFAULT_GENERATION_QUALITY
        );
        setGenerationSource(
          data.source === "modal" ? "modal" : data.source === "fal" ? "fal" : "mock"
        );
        setLastGenerationSeconds(Math.max(1, Math.round((Date.now() - startedAt) / 1000)));
        notifyGenerationComplete();
      } else if (data.meshData) {
        setMeshData(data.meshData);
        setGenerationSource("mock");
        setLastGenerationSeconds(Math.max(1, Math.round((Date.now() - startedAt) / 1000)));
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

  const enhanceModel = useCallback(async () => {
    if (!jobId || !jobToken) {
      setError("Enhancement is unavailable for this session. Generate a new preview first.");
      return;
    }
    if (modelQuality !== "preview") return;

    setIsEnhancing(true);
    setError(null);
    setGenerationStage(null);
    setGenerationProgress(0);

    try {
      const data = await finalizeGenerationJob(jobId, jobToken, "standard", {
        intervalMs: GENERATION_POLL_INTERVAL_MS,
        maxAttempts: GENERATION_POLL_MAX_ATTEMPTS,
        onUpdate: (job) => {
          setGenerationStage(job.stage ?? null);
          setGenerationProgress(job.progress ?? 0);
        },
      });
      setModelUrl(data.modelUrl ?? null);
      setModelKey(data.modelKey ?? null);
      setFormat(data.format ?? "glb");
      setModelQuality("standard");
      notifyGenerationComplete();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not enhance the model. Try again."
      );
    } finally {
      setIsEnhancing(false);
    }
  }, [jobId, jobToken, modelQuality]);

  const rotateUploadedImage = useCallback(
    async (direction: "cw" | "ccw") => {
      if (!uploadedFile || isLoading || isEnhancing) return;
      const degrees = direction === "cw" ? 90 : -90;
      const rotated = await rotateImageFile(uploadedFile, degrees);
      await prepareAndSetUploadedFile(rotated);
    },
    [uploadedFile, isLoading, isEnhancing, prepareAndSetUploadedFile]
  );

  const clearAll = useCallback(() => {
    setIsPreparingImage(false);
    setImagePrepLabel(null);
    clearUploadState();
  }, [clearUploadState]);

  const clearError = useCallback(() => setError(null), []);

  const hasModel = Boolean(modelUrl || meshData);
  const canEnhance = modelQuality === "preview" && Boolean(jobId && jobToken);
  const isFinalModel = modelQuality === "standard" || modelQuality === "final";

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
        generationStage,
        generationProgress,
        isLoading,
        isPreparingImage,
        imagePrepLabel,
        error,
        modelQuality,
        isEnhancing,
        lastGenerationSeconds,
        setUploadedFile,
        prepareAndSetUploadedFile,
        generateModel,
        enhanceModel,
        rotateUploadedImage,
        clearAll,
        clearError,
        hasModel,
        canEnhance,
        isFinalModel,
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
