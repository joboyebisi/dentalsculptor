"use client";

import { useRef } from "react";
import Image from "next/image";
import { X, ImagePlus, Factory } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useLandingModel } from "@/context/landing-model-context";
import {
  GenerationNotifyOption,
} from "@/components/generation/generation-notify-option";

export function LandingImageUploader() {
  const { previewUrl, uploadedFile, isLoading, error, setUploadedFile, generateModel, clearAll } =
    useLandingModel();
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <Card className="w-full max-w-md border-border-subtle">
      <CardHeader>
        <CardTitle className="text-headline-md">Upload dental image</CardTitle>
        <CardDescription>
          Select a clinical photograph, scan, or teaching image to generate a 3D model.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg,image/webp"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0] ?? null;
            setUploadedFile(file);
          }}
        />

        {previewUrl ? (
          <div className="relative aspect-[4/3] overflow-hidden rounded-lg border border-border-subtle bg-surface-container-low">
            <Image src={previewUrl} alt="Selected dental image" fill className="object-cover" />
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex aspect-[4/3] w-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-border-subtle bg-surface-container-low text-on-surface-variant transition-colors hover:border-primary-container/40 hover:bg-surface-container"
          >
            <ImagePlus className="mb-2 h-8 w-8 text-primary-container/60" />
            <span className="text-body-sm">No image selected</span>
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

        {error && <p className="text-body-sm text-error">{error}</p>}

        <GenerationNotifyOption disabled={isLoading} />
      </CardContent>
      <CardFooter>
        <Button
          className="w-full"
          disabled={!uploadedFile || isLoading}
          onClick={generateModel}
        >
          <Factory className="mr-2 h-4 w-4" />
          {isLoading ? "Generating model…" : "Generate 3D model"}
        </Button>
      </CardFooter>
    </Card>
  );
}
