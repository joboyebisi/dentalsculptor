"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Upload, ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { DentalViewer } from "@/components/three/dental-viewer";
import { autoProjectTitle } from "@/lib/auto-project-title";
import { prepareGenerationImage } from "@/lib/prepare-generation-image";
import { GENERATION_COPY } from "@/lib/generation-copy";
import { GenerationNotifyOption } from "@/components/generation/generation-notify-option";
import {
  notifyGenerationComplete,
  prepareGenerationNotification,
} from "@/lib/generation-notifications";
import type { GeneratedMesh } from "@/lib/model-generator";

export default function NewProjectPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [description, setDescription] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [meshData, setMeshData] = useState<GeneratedMesh | null>(null);
  const [modelUrl, setModelUrl] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);

  useEffect(() => {
    if (!processing) {
      setElapsedSec(0);
      return;
    }
    const start = Date.now();
    const id = setInterval(() => setElapsedSec(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, [processing]);

  useEffect(() => {
    if (!processing) return;
    const id = setInterval(() => {
      setProgress((p) => (p >= 90 ? p : p + 2));
    }, 2000);
    return () => clearInterval(id);
  }, [processing]);

  const handleFileDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  }, []);

  async function startProcessing() {
    if (!imageFile) return;
    setStep(2);
    setProcessing(true);
    setProgress(5);

    try {
      await prepareGenerationNotification();
      const prepared = await prepareGenerationImage(imageFile);
      const formData = new FormData();
      formData.append("title", autoProjectTitle(imageFile.name));
      formData.append("description", description);
      formData.append("image", prepared);

      const res = await fetch("/api/projects", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      setProjectId(data.project.id);
      setMeshData(data.meshData ?? data.project?.dentalModel?.meshData ?? null);
      setModelUrl(data.project?.dentalModel?.generated3DUrl ?? null);
      setProgress(100);
      notifyGenerationComplete();
      setStep(3);
    } catch (err) {
      console.error(err);
    } finally {
      setProcessing(false);
    }
  }

  return (
    <div className="p-margin-page">
      <div className="mx-auto max-w-2xl">
        <Button variant="ghost" size="sm" className="mb-6" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>

        <div className="mb-8 flex gap-2">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full ${s <= step ? "bg-primary-container" : "bg-surface-container"}`}
            />
          ))}
        </div>

        {step === 1 && (
          <div>
            <h1 className="text-display-lg">New Project</h1>
            <p className="mt-1 text-body-md text-on-surface-variant">
              Upload a dental image — your project will be named automatically. You can rename it
              in the editor header.
            </p>
            <div className="mt-4">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the learning experience..."
                className="mt-1.5"
              />
            </div>
            <Card
              className="mt-6 cursor-pointer border-dashed"
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
            >
              <CardContent className="flex flex-col items-center py-12">
                {imagePreview ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={imagePreview} alt="Preview" className="max-h-48 rounded-lg" />
                ) : (
                  <>
                    <Upload className="mb-4 h-10 w-10 text-on-surface-variant" />
                    <p className="font-medium">Drop your dental image here</p>
                    <p className="mt-1 text-body-sm text-on-surface-variant">
                      PNG, JPG, JPEG supported
                    </p>
                  </>
                )}
                <label className="mt-4">
                  <input type="file" accept="image/*" className="hidden" onChange={handleFileSelect} />
                  <Button variant="outline" size="sm" asChild>
                    <span>Browse Files</span>
                  </Button>
                </label>
              </CardContent>
            </Card>
            <Button className="mt-8" disabled={!imageFile} onClick={startProcessing}>
              Generate 3D Model
            </Button>
            <GenerationNotifyOption className="mt-4" />
          </div>
        )}

        {step === 2 && (
          <div className="text-center">
            <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-primary-container" />
            <h1 className="text-display-lg">{GENERATION_COPY.inProgressTitle}</h1>
            <p className="mt-2 text-body-md text-on-surface-variant">
              {GENERATION_COPY.inProgressDetail}
            </p>
            {elapsedSec > 0 && (
              <p className="mt-1 text-body-sm text-on-surface-variant/80">
                Elapsed: {elapsedSec}s
              </p>
            )}
            <Progress value={progress} className="mt-6" />
          </div>
        )}

        {step === 3 && (
          <div>
            <h1 className="text-display-lg">3D Preview Ready</h1>
            <p className="mt-1 text-body-md text-on-surface-variant">
              Your model has been generated. Open the editor to annotate and author content.
            </p>
            <div className="mt-6 h-80 overflow-hidden rounded-xl border border-border-subtle">
              <DentalViewer meshData={meshData} modelUrl={modelUrl} className="h-full" />
            </div>
            <div className="mt-8 flex gap-3">
              <Button
                className="flex-1"
                onClick={() => router.push(`/editor/${projectId}`)}
              >
                Open Editor
              </Button>
              <Button variant="outline" onClick={() => router.push("/projects")}>
                View All Projects
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
