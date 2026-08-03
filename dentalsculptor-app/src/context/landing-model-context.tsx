"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { generateDentalMeshFromImage } from "@/lib/model-generator";
import type { GeneratedMesh } from "@/lib/model-generator";

interface LandingModelState {
  uploadedFile: File | null;
  previewUrl: string | null;
  meshData: GeneratedMesh | null;
  isLoading: boolean;
  error: string | null;
}

interface LandingModelContextType extends LandingModelState {
  setUploadedFile: (file: File | null) => void;
  generateModel: () => Promise<void>;
  clearAll: () => void;
  clearError: () => void;
}

const LandingModelContext = createContext<LandingModelContextType | undefined>(undefined);

export function LandingModelProvider({ children }: { children: React.ReactNode }) {
  const [uploadedFile, setUploadedFileState] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [meshData, setMeshData] = useState<GeneratedMesh | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setUploadedFile = useCallback(
    (file: File | null) => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setUploadedFileState(file);
      setPreviewUrl(file ? URL.createObjectURL(file) : null);
      setMeshData(null);
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

    try {
      const dimensions = await loadImageDimensions(uploadedFile);
      await new Promise((r) => setTimeout(r, 2000));
      setMeshData(generateDentalMeshFromImage(dimensions.width, dimensions.height));
    } catch {
      setError("Could not process the image. Try another file.");
    } finally {
      setIsLoading(false);
    }
  }, [uploadedFile]);

  const clearAll = useCallback(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setUploadedFileState(null);
    setPreviewUrl(null);
    setMeshData(null);
    setError(null);
  }, [previewUrl]);

  const clearError = useCallback(() => setError(null), []);

  return (
    <LandingModelContext.Provider
      value={{
        uploadedFile,
        previewUrl,
        meshData,
        isLoading,
        error,
        setUploadedFile,
        generateModel,
        clearAll,
        clearError,
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

function loadImageDimensions(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve({ width: img.naturalWidth || 800, height: img.naturalHeight || 600 });
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Invalid image"));
    };
    img.src = url;
  });
}
