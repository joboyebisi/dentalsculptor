"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import type { GeneratedMesh } from "@/lib/model-generator";
import { prepareGenerationImage } from "@/lib/prepare-generation-image";
import {
  notifyGenerationComplete,
  prepareGenerationNotification,
} from "@/lib/generation-notifications";

interface LandingModelState {
  uploadedFile: File | null;
  previewUrl: string | null;
  meshData: GeneratedMesh | null;
  modelUrl: string | null;
  thumbnailUrl: string | null;
  mtlUrl: string | null;
  format: string | null;
  generationSource: "fal" | "mock" | null;
  isLoading: boolean;
  error: string | null;
}

interface LandingModelContextType extends LandingModelState {
  setUploadedFile: (file: File | null) => void;
  generateModel: () => Promise<void>;
  clearAll: () => void;
  clearError: () => void;
  hasModel: boolean;
}

const LandingModelContext = createContext<LandingModelContextType | undefined>(undefined);

export function LandingModelProvider({ children }: { children: React.ReactNode }) {
  const [uploadedFile, setUploadedFileState] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [meshData, setMeshData] = useState<GeneratedMesh | null>(null);
  const [modelUrl, setModelUrl] = useState<string | null>(null);
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);
  const [mtlUrl, setMtlUrl] = useState<string | null>(null);
  const [format, setFormat] = useState<string | null>(null);
  const [generationSource, setGenerationSource] = useState<"fal" | "mock" | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setUploadedFile = useCallback(
    (file: File | null) => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setUploadedFileState(file);
      setPreviewUrl(file ? URL.createObjectURL(file) : null);
      setMeshData(null);
      setModelUrl(null);
      setThumbnailUrl(null);
      setMtlUrl(null);
      setFormat(null);
      setGenerationSource(null);
      setError(null);
    },
    [previewUrl]
  );

  const generateModel = useCallback(async () => {
    if (!uploadedFile) {
      setError("Select an image first.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setMeshData(null);
    setModelUrl(null);
    setThumbnailUrl(null);
    setMtlUrl(null);
    setFormat(null);
    setGenerationSource(null);

    try {
      await prepareGenerationNotification();
      const prepared = await prepareGenerationImage(uploadedFile);
      const formData = new FormData();
      formData.append("image", prepared);

      const res = await fetch("/api/generate/mesh", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error ?? "Generation failed.");
      }

      if (data.modelUrl) {
        setModelUrl(data.modelUrl);
        setThumbnailUrl(data.thumbnailUrl ?? null);
        setMtlUrl(data.mtlUrl ?? null);
        setFormat(data.format ?? "glb");
        setGenerationSource(data.source === "fal" ? "fal" : "mock");
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
  }, [uploadedFile]);

  const clearAll = useCallback(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setUploadedFileState(null);
    setPreviewUrl(null);
    setMeshData(null);
    setModelUrl(null);
    setThumbnailUrl(null);
    setMtlUrl(null);
    setFormat(null);
    setGenerationSource(null);
    setError(null);
  }, [previewUrl]);

  const clearError = useCallback(() => setError(null), []);

  const hasModel = Boolean(modelUrl || meshData);

  return (
    <LandingModelContext.Provider
      value={{
        uploadedFile,
        previewUrl,
        meshData,
        modelUrl,
        thumbnailUrl,
        mtlUrl,
        format,
        generationSource,
        isLoading,
        error,
        setUploadedFile,
        generateModel,
        clearAll,
        clearError,
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
