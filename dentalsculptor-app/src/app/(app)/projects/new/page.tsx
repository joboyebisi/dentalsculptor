"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Upload, ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { DentalViewer } from "@/components/three/dental-viewer";
import { PROCESSING_STAGES } from "@/lib/constants";
import type { GeneratedMesh } from "@/lib/model-generator";

export default function NewProjectPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState(0);
  const [progress, setProgress] = useState(0);
  const [meshData, setMeshData] = useState<GeneratedMesh | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);

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
    if (!imageFile || !title) return;
    setStep(3);
    setProcessing(true);

    const formData = new FormData();
    formData.append("title", title);
    formData.append("description", description);
    formData.append("image", imageFile);

    for (let i = 0; i < PROCESSING_STAGES.length; i++) {
      setProcessingStage(i);
      setProgress(((i + 1) / PROCESSING_STAGES.length) * 80);
      await new Promise((r) => setTimeout(r, 1200));
    }

    try {
      const res = await fetch("/api/projects", { method: "POST", body: formData });
      const data = await res.json();
      setProjectId(data.project.id);
      setMeshData(data.meshData);
      setProgress(100);
      await new Promise((r) => setTimeout(r, 500));
      setStep(4);
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
          {[1, 2, 3, 4].map((s) => (
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
              Step 1 — Project details
            </p>
            <div className="mt-6 space-y-4">
              <div>
                <Label htmlFor="title">Project Title</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Molar Caries Simulation"
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="description">Project Description</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe the learning experience..."
                  className="mt-1.5"
                />
              </div>
            </div>
            <Button className="mt-8" disabled={!title} onClick={() => setStep(2)}>
              Continue
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        )}

        {step === 2 && (
          <div>
            <h1 className="text-display-lg">Upload Image</h1>
            <p className="mt-1 text-body-md text-on-surface-variant">
              Step 2 — Upload a dental image (PNG, JPG, JPEG)
            </p>
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
            <div className="mt-8 flex gap-3">
              <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
              <Button disabled={!imageFile} onClick={startProcessing}>
                Generate 3D Model
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="text-center">
            <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-primary-container" />
            <h1 className="text-display-lg">Generating 3D Model</h1>
            <p className="mt-2 text-body-md text-on-surface-variant animate-pulse-slow">
              {PROCESSING_STAGES[processingStage]}
            </p>
            <Progress value={progress} className="mt-6" />
          </div>
        )}

        {step === 4 && (
          <div>
            <h1 className="text-display-lg">3D Preview Ready</h1>
            <p className="mt-1 text-body-md text-on-surface-variant">
              Your model has been generated. Open the editor to annotate and author content.
            </p>
            <div className="mt-6 h-80 overflow-hidden rounded-xl border border-border-subtle">
              <DentalViewer meshData={meshData} className="h-full" />
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
