"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Upload, ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { DentalViewer } from "@/components/three/dental-viewer";
import { autoProjectTitle } from "@/lib/auto-project-title";
import { prepareGenerationImageDetailed } from "@/lib/prepare-generation-image";
import { GENERATION_COPY } from "@/lib/generation-copy";
import { GenerationNotifyOption } from "@/components/generation/generation-notify-option";
import {
  notifyGenerationComplete,
  prepareGenerationNotification,
} from "@/lib/generation-notifications";
import { pollGenerationJob } from "@/lib/generation-jobs";
import { requestGpuWarmup } from "@/lib/gpu-warmup";
import type { GeneratedMesh } from "@/lib/model-generator";

export default function NewProjectPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState(1);
  const [description, setDescription] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stageLabel, setStageLabel] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [meshData, setMeshData] = useState<GeneratedMesh | null>(null);
  const [modelUrl, setModelUrl] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);

  useEffect(() => {
    requestGpuWarmup("upload");
  }, []);

  useEffect(() => {
    if (!processing) {
      setElapsedSec(0);
      return;
    }
    const start = Date.now();
    const id = setInterval(() => setElapsedSec(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, [processing]);

  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const applyImageFile = useCallback((file: File) => {
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    setError(null);
  }, []);

  const handleFileDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith("image/")) {
        applyImageFile(file);
      }
    },
    [applyImageFile]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) applyImageFile(file);
    },
    [applyImageFile]
  );

  async function startProcessing() {
    if (!imageFile) return;
    setStep(2);
    setProcessing(true);
    setProgress(5);
    setError(null);
    setStageLabel("Preparing image…");

    try {
      await prepareGenerationNotification();
      const prepared = await prepareGenerationImageDetailed(imageFile);
      setStageLabel("Creating project…");

      const formData = new FormData();
      formData.append("title", autoProjectTitle(imageFile.name));
      formData.append("description", description);
      formData.append("image", prepared.file);

      const res = await fetch("/api/projects", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Could not create project");

      setProjectId(data.project.id);

      if (data.asyncGeneration) {
        setStageLabel(GENERATION_COPY.inProgressTitle);
        const genForm = new FormData();
        genForm.append("image", prepared.file);
        genForm.append("projectId", data.project.id);
        genForm.append("quality", "preview");

        const genRes = await fetch("/api/generate/mesh", { method: "POST", body: genForm });
        const genData = await genRes.json();
        if (!genRes.ok) throw new Error(genData.error ?? "Generation failed");

        if (genRes.status === 202 && genData.jobId && genData.jobToken) {
          const polled = await pollGenerationJob(genData.jobId, genData.jobToken, {
            onUpdate: (job) => {
              setStageLabel(job.stage ?? GENERATION_COPY.inProgressTitle);
              setProgress(Math.max(10, job.progress ?? 0));
            },
          });
          setModelUrl(polled.modelUrl ?? null);
        } else {
          setModelUrl(genData.modelUrl ?? null);
          setMeshData(genData.meshData ?? null);
        }
      } else {
        setMeshData(data.meshData ?? data.project?.dentalModel?.meshData ?? null);
        setModelUrl(data.project?.dentalModel?.generated3DUrl ?? null);
      }

      setProgress(100);
      notifyGenerationComplete();
      setStep(3);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Generation failed.");
      setStep(1);
    } finally {
      setProcessing(false);
      setStageLabel(null);
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
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileSelect}
            />
            <Card
              className="mt-6 cursor-pointer border-dashed"
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              onClick={openFilePicker}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  openFilePicker();
                }
              }}
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
                      PNG, JPG, JPEG supported — or click anywhere to browse
                    </p>
                  </>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    openFilePicker();
                  }}
                >
                  Browse Files
                </Button>
              </CardContent>
            </Card>
            {error && (
              <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-body-sm text-destructive">
                {error}
              </p>
            )}
            <Button className="mt-8" disabled={!imageFile || processing} onClick={startProcessing}>
              Generate 3D Model
            </Button>
            <GenerationNotifyOption className="mt-4" />
          </div>
        )}

        {step === 2 && (
          <div className="text-center">
            <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-primary-container" />
            <h1 className="text-display-lg">{stageLabel ?? GENERATION_COPY.inProgressTitle}</h1>
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
