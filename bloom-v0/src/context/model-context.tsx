'use client'; // Context needs to be client-side

import React, { createContext, useState, useContext, ReactNode } from 'react';

// 1. Define the state interface
interface ModelState {
  uploadedFiles: File[];
  generatedModelUrl: string | null;
  isLoading: boolean;
  error: string | null;
}

// Define the context type including state and actions
interface ModelContextType extends ModelState {
  setUploadedFiles: (files: File[]) => void;
  // Placeholder function for generation logic
  generateModel: (files: File[]) => Promise<void>; 
  clearError: () => void;
  // Add other actions as needed
}

// 2. Create the context with a default value
const ModelContext = createContext<ModelContextType | undefined>(undefined);

// 3. Create the Provider component
interface ModelProviderProps {
  children: ReactNode;
}

export const ModelProvider: React.FC<ModelProviderProps> = ({ children }) => {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [generatedModelUrl, setGeneratedModelUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = () => setError(null);

  // Updated function to call the API route
  const generateModel = async (files: File[]) => {
    if (!files || files.length === 0) {
      setError("No files provided for generation.");
      return;
    }
    setIsLoading(true);
    setError(null);
    setGeneratedModelUrl(null);
    console.log("Context: Starting generation call...");

    // Create FormData to send files
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file); // Use the key expected by the API route
    });

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        // Handle API errors (e.g., 4xx, 5xx)
        throw new Error(result.error || `API Error: ${response.statusText}`);
      }

      // Success
      if (result.modelUrl) {
        setGeneratedModelUrl(result.modelUrl);
        console.log("Context: Generation successful, URL:", result.modelUrl);
      } else {
        // Handle unexpected success response format
        throw new Error("API response missing modelUrl.");
      }

    } catch (err) {
      console.error("Context: Generation failed:", err);
      setError(err instanceof Error ? err.message : "An unknown error occurred during generation.");
      // Optionally, show a toast notification here as well
      // toast.error("Generation failed: " + (err instanceof Error ? err.message : "Unknown error"));
    } finally {
      setIsLoading(false);
    }
  };

  const value = {
    uploadedFiles,
    generatedModelUrl,
    isLoading,
    error,
    setUploadedFiles,
    generateModel,
    clearError,
  };

  return <ModelContext.Provider value={value}>{children}</ModelContext.Provider>;
};

// 4. Create a custom hook for easy context consumption
export const useModelContext = () => {
  const context = useContext(ModelContext);
  if (context === undefined) {
    throw new Error('useModelContext must be used within a ModelProvider');
  }
  return context;
}; 