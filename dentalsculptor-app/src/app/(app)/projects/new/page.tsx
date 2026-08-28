"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { DentalViewer, type DentalViewerHandle } from "@/components/three/dental-viewer";
import { autoProjectTitle } from "@/lib/auto-project-title";
import { prepareGenerationImageDetailed } from "@/lib/prepare-generation-image";
import { rotateImageFile } from "@/lib/image-rotation";
import { GENERATION_COPY } from "@/lib/generation-copy";
import { GenerationNotifyOption } from "@/components/generation/generation-notify-option";
import { GenerationImagePicker } from "@/components/generation/generation-image-picker";
import { GenerationProgressDisplay } from "@/components/generation/generation-progress-display";
import {
  notifyGenerationComplete,
  prepareGenerationNotification,
} from "@/lib/generation-notifications";
import { pollGenerationJob } from "@/lib/generation-jobs";
import { captureAndUploadCardPreview } from "@/lib/upload-project-preview-image";
import { requestGpuWarmup } from "@/lib/gpu-warmup";
import type { GeneratedMesh } from "@/lib/model-generator";

export default function NewProjectPage() {
  const router = useRouter();
  const previewUrlRef = useRef<string | null>(null);
  const viewerRef = useRef<DentalViewerHandle>(null);
  const previewUploadedRef = useRef(false);
  const [step, setStep] = useState(1);
  const [description, setDescription] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stageLabel, setStageLabel] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [lastGenerationSeconds, setLastGenerationSeconds] = useState<number | null>(null);
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

  useEffect(() => {
    if (step !== 3 || !projectId || previewUploadedRef.current) return;
    if (!modelUrl && !meshData) return;
    previewUploadedRef.current = true;
    void captureAndUploadCardPreview(
      projectId,
      () => viewerRef.current?.capturePreview() ?? Promise.resolve(null),
      { delayMs: 500, retries: 5 }
    );
  }, [step, projectId, modelUrl, meshData]);

  const revokePreview = useCallback((url: string | null) => {
    if (url?.startsWith("blob:")) URL.revokeObjectURL(url);
  }, []);

  const applyImageFile = useCallback(
    (file: File) => {
      revokePreview(previewUrlRef.current);
      const nextUrl = URL.createObjectURL(file);
      previewUrlRef.current = nextUrl;
      setImageFile(file);
      setImagePreview(nextUrl);
      setError(null);
    },
    [revokePreview]
  );

  const clearImage = useCallback(() => {
    revokePreview(previewUrlRef.current);
    previewUrlRef.current = null;
    setImageFile(null);
    setImagePreview(null);
    setError(null);
  }, [revokePreview]);

  const rotateImage = useCallback(
    async (direction: "cw" | "ccw") => {
      if (!imageFile || processing) return;
      const degrees = direction === "cw" ? 90 : -90;
      const rotated = await rotateImageFile(imageFile, degrees);
      applyImageFile(rotated);
    },
    [imageFile, processing, applyImageFile]
  );

  async function startProcessing() {
    if (!imageFile) return;
    setStep(2);
    setProcessing(true);
    setProgress(5);
    setError(null);
    setStageLabel("preprocessing");
    setLastGenerationSeconds(null);
    const startedAt = Date.now();

    try {
      await prepareGenerationNotification();
      const prepared = await prepareGenerationImageDetailed(imageFile);
      setStageLabel("starting");

      const formData = new FormData();
      formData.append("title", autoProjectTitle(imageFile.name));
      formData.append("description", description);
      formData.append("image", prepared.file);

      const res = await fetch("/api/projects", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Could not create project");

      setProjectId(data.project.id);

      if (data.asyncGeneration) {
        setStageLabel("queued");
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
              setStageLabel(job.stage ?? "generating_shape");
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
      setLastGenerationSeconds(Math.max(1, Math.round((Date.now() - startedAt) / 1000)));
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
              Select or upload a dental image — same workflow as the landing page. Your project is
              named automatically; rename it in the editor header.
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

            <Card className="mt-6 border-dashed">
              <CardContent className="py-6">
                <GenerationImagePicker
                  previewUrl={imagePreview}
                  hasFile={Boolean(imageFile)}
                  disabled={processing}
                  onSelectFile={applyImageFile}
                  onClear={clearImage}
                  onRotate={() => void rotateImage("cw")}
                  emptyHint="Drop or select a single-tooth image"
                />
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
          <div className="py-8">
            <GenerationProgressDisplay
              title={GENERATION_COPY.inProgressTitle}
              stage={stageLabel}
              progress={progress}
              elapsedSec={elapsedSec}
            />
          </div>
        )}

        {step === 3 && (
          <div>
            <h1 className="text-display-lg">3D Preview Ready</h1>
            <p className="mt-1 text-body-md text-on-surface-variant">
              Your model has been generated and saved to this project. Open the editor to annotate
              and author content.
            </p>
            {lastGenerationSeconds != null && (
              <p className="mt-2 text-body-sm text-on-surface-variant">
                {GENERATION_COPY.completedIn(lastGenerationSeconds)}
              </p>
            )}
            <div className="mt-6 h-80 overflow-hidden rounded-xl border border-border-subtle">
              <DentalViewer ref={viewerRef} meshData={meshData} modelUrl={modelUrl} className="h-full" />
            </div>
            <div className="mt-8 flex gap-3">
              <Button className="flex-1" onClick={() => router.push(`/editor/${projectId}`)}>
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
