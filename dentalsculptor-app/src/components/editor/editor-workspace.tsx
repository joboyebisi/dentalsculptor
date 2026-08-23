"use client";

import { useState, useCallback, useRef } from "react";
import type { GeneratedMesh } from "@/lib/model-generator";
import { EditorHeader, type EditorTab } from "@/components/editor/editor-header";
import { EditorToolPalette, type EditorTool } from "@/components/editor/editor-tool-palette";
import { CamModelViewer, type CamViewerHandle, type RectMark, type ModelLoadStatus } from "@/components/editor/cam-model-viewer";
import { EditorAiBar } from "@/components/editor/editor-ai-bar";
import { EditorPropertiesPanel } from "@/components/editor/editor-properties-panel";
import { EditorStatusBar } from "@/components/editor/editor-status-bar";
import { EditorSourcePanel } from "@/components/editor/editor-source-panel";
import { EditorDashboardSidebar } from "@/components/editor/editor-dashboard-sidebar";
import { MaskPaintOverlay, type MaskPaintOverlayHandle, type MaskBrushMode } from "@/components/editor/mask-paint-overlay";
import { EditorMaskToolbar } from "@/components/editor/editor-mask-toolbar";
import { EditorEditWorkflowPanel } from "@/components/editor/editor-edit-workflow-panel";
import {
  EditPreviewModal,
  EditorEditActions,
  EditorMaskContextPanel,
} from "@/components/editor/edit-preview-modal";
import { ExportWizardDialog } from "@/components/export/export-wizard-dialog";
import { EditorCasePanel } from "@/components/editor/editor-case-panel";
import { CaseWizardDialog, type CaseWizardContinuePayload } from "@/components/case-wizard/case-wizard-dialog";
import type { CaseTemplate } from "@/lib/case-templates";
import { getCaseTemplate } from "@/lib/case-templates";
import type { CaseRecipe } from "@/lib/clinical-case-params";
import { parseCaseRecipeFromProject, formatInstructionsFromRecipe, buildEditPromptFromRecipe } from "@/lib/case-recipe-utils";
import { useResearchTracker } from "@/hooks/use-research-tracker";
import { generateSegmentParts, type SegmentPart } from "@/lib/editor-segmentation";
import { triggerSFX } from "@/lib/sfx-bus";
import { parseModelProcessingStage } from "@/lib/model-processing-stage";
import { detectModelFormat } from "@/lib/model-format";
import type { SerializedCameraState } from "@/lib/camera-utils";
import { prepareGenerationImage } from "@/lib/prepare-generation-image";
import {
  notifyGenerationComplete,
  prepareGenerationNotification,
} from "@/lib/generation-notifications";
import { GENERATION_COPY } from "@/lib/generation-copy";
import { pollGenerationJob } from "@/lib/generation-jobs";
import { EDITOR_SURFACE } from "@/lib/constants";
import { expandDentalPrompt } from "@/lib/dental-prompt-glossary";
import type { EditOperation } from "@/lib/edit-types";
import {
  attachmentFromRectMark,
  buildRegionMarksPayload,
  instructionWithRegionRefs,
} from "@/lib/edit-region-attachments";
import { DEFAULT_EXPORT_TARGET } from "@/lib/export-presets";
import type { ViewerInteractionMode } from "@/components/editor/cam-model-viewer";

export interface EditorProject {
  id: string;
  title: string;
  description: string | null;
  status: string;
  instructions: string | null;
  hints: string | null;
  feedback: string | null;
  dentalModel: {
    meshData: GeneratedMesh | null;
    generated3DUrl?: string | null;
    sourceImageUrl?: string | null;
    thumbnailUrl?: string | null;
    processingStage?: string | null;
  } | null;
  annotations: Array<{ id: string; text: string; position: number[]; color: string }>;
  learningObjectives: Array<{ id: string; title: string }>;
  assessments: Array<{ id: string; question: string }>;
  versions?: Array<{ label: string | null; snapshot: unknown; version: number }>;
}

interface EditorWorkspaceProps {
  project: EditorProject;
  projectId: string;
  onSave: (updates: Partial<EditorProject>) => Promise<void>;
  initialCaseWizardOpen?: boolean;
}

export function EditorWorkspace({
  project,
  projectId,
  onSave,
  initialCaseWizardOpen = false,
}: EditorWorkspaceProps) {
  const initialRecipe = parseCaseRecipeFromProject(project);
  const initialTemplate = initialRecipe?.templateId
    ? getCaseTemplate(initialRecipe.templateId) ?? null
    : null;

  const { track } = useResearchTracker();
  const viewerRef = useRef<CamViewerHandle>(null);
  const maskOverlayRef = useRef<MaskPaintOverlayHandle>(null);

  const modelMeta = parseModelProcessingStage(project.dentalModel?.processingStage);
  const initialModelUrl = project.dentalModel?.generated3DUrl ?? null;

  const [title, setTitle] = useState(project.title);
  const [meshData, setMeshData] = useState<GeneratedMesh | null>(project.dentalModel?.meshData ?? null);
  const [modelUrl, setModelUrl] = useState<string | null>(initialModelUrl);
  const [modelFormat, setModelFormat] = useState<string | null>(
    modelMeta.format ?? (initialModelUrl ? detectModelFormat(initialModelUrl, modelMeta.format, modelMeta.mtlUrl) : null)
  );
  const [mtlUrl, setMtlUrl] = useState<string | null>(modelMeta.mtlUrl ?? null);
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [activeTool, setActiveTool] = useState<EditorTool>("select");
  const [wireframe, setWireframe] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(true);
  const [partsOpen, setPartsOpen] = useState(false);
  const [caseWizardOpen, setCaseWizardOpen] = useState(initialCaseWizardOpen);
  const [applyingTemplate, setApplyingTemplate] = useState(false);
  const [selectedCase, setSelectedCase] = useState<CaseTemplate | null>(initialTemplate);
  const [caseRecipe, setCaseRecipe] = useState<CaseRecipe | null>(() => initialRecipe);
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<EditorTab>("authoring");
  const [aiPrompt, setAiPrompt] = useState(() =>
    initialRecipe && initialTemplate
      ? buildEditPromptFromRecipe(initialRecipe, initialTemplate)
      : ""
  );
  const [aiLoading, setAiLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [segmenting, setSegmenting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exportWizardOpen, setExportWizardOpen] = useState(false);
  const [casePanelOpen, setCasePanelOpen] = useState(true);
  const [learningObjectives, setLearningObjectives] = useState(project.learningObjectives);
  const [instructions, setInstructions] = useState(project.instructions);
  const [brushMode, setBrushMode] = useState<MaskBrushMode>("paint");
  const [brushSize, setBrushSize] = useState(32);
  const [editOperation, setEditOperation] = useState<EditOperation>(
    initialTemplate?.defaultOperation ?? "remove"
  );
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [editJobLoading, setEditJobLoading] = useState(false);
  const [beforePreview, setBeforePreview] = useState<string | null>(null);
  const [afterPreview, setAfterPreview] = useState<string | null>(null);
  const [referenceImage, setReferenceImage] = useState<Blob | null>(null);
  const [referenceCamera, setReferenceCamera] = useState<SerializedCameraState | null>(null);
  const [maskCoverage, setMaskCoverage] = useState(0);
  const [revisionVersion] = useState(1);
  const [sourcePreview, setSourcePreview] = useState<string | null>(
    project.dentalModel?.sourceImageUrl ?? null
  );
  const [rectMarks, setRectMarks] = useState<RectMark[]>([]);
  const [markRedoStack, setMarkRedoStack] = useState<RectMark[]>([]);
  const [maskHasStrokes, setMaskHasStrokes] = useState(false);
  const [viewerInteractionMode, setViewerInteractionMode] = useState<ViewerInteractionMode>("orbit");
  const [modelSelected, setModelSelected] = useState(false);
  const [activePartId, setActivePartId] = useState<string | null>(null);
  const [modelLoadStatus, setModelLoadStatus] = useState<ModelLoadStatus>(
    initialModelUrl ? "loading" : "none"
  );
  const [modelLoadDetail, setModelLoadDetail] = useState<string | undefined>();
  const handleModelStatusChange = useCallback((status: ModelLoadStatus, detail?: string) => {
    setModelLoadStatus(status);
    setModelLoadDetail(detail);
  }, []);
  const [segmentParts, setSegmentParts] = useState<SegmentPart[]>(
    project.dentalModel?.meshData || project.dentalModel?.generated3DUrl
      ? generateSegmentParts()
      : []
  );

  const markMode = activeTool === "mark";
  const maskMode = activeTool === "mask";
  const selectMode = activeTool === "select" && !maskMode;
  const hasModel = Boolean(meshData?.vertices?.length) || Boolean(modelUrl);
  const hasPartSelection = segmentParts.some((p) => p.visible);
  const maskVisible = hasModel && (maskMode || maskHasStrokes || maskCoverage > 0);
  const regionAttachments = rectMarks.map((m, i) => attachmentFromRectMark(m, i + 1));
  const hasSpatialEditTarget =
    regionAttachments.length > 0 || maskHasStrokes || maskCoverage > 0;
  const canApply =
    hasModel && (modelSelected || hasPartSelection || hasSpatialEditTarget);

  const handleRectMarkComplete = useCallback(
    async (partial: Omit<RectMark, "id" | "index" | "label" | "text">) => {
      const index = rectMarks.length + 1;
      const label = `Region ${index}`;
      const id = `mark-${Date.now()}-${index}`;
      const thumbnailUrl =
        (await viewerRef.current?.captureRegionThumbnail(partial)) ?? undefined;
      const mark: RectMark = {
        ...partial,
        id,
        index,
        label,
        text: label,
        thumbnailUrl,
      };
      setRectMarks((prev) => [...prev, mark]);
      setMarkRedoStack([]);
      track("ANNOTATION_CREATED", projectId, { text: label, type: "rect", index });
    },
    [rectMarks.length, projectId, track]
  );

  const handleRemoveRegionAttachment = useCallback((id: string) => {
    setRectMarks((prev) =>
      prev
        .filter((m) => m.id !== id)
        .map((m, i) => ({
          ...m,
          index: i + 1,
          label: `Region ${i + 1}`,
          text: `Region ${i + 1}`,
        }))
    );
    setMarkRedoStack([]);
    triggerSFX("toggle");
  }, []);

  const handleToolChange = (tool: EditorTool) => {
    if (tool === "edit") {
      setWireframe((w) => !w);
      return;
    }
    if (tool === "zoom-in") {
      viewerRef.current?.zoomIn();
      triggerSFX("tool-click");
      return;
    }
    if (tool === "zoom-out") {
      viewerRef.current?.zoomOut();
      triggerSFX("tool-click");
      return;
    }
    if (tool === "undo") {
      if (maskOverlayRef.current?.hasStrokes()) {
        maskOverlayRef.current.undo();
        bumpMaskCoverage();
      } else if (rectMarks.length > 0) {
        const last = rectMarks[rectMarks.length - 1]!;
        setRectMarks((prev) => prev.slice(0, -1));
        setMarkRedoStack((prev) => [...prev, last]);
      }
      triggerSFX("tool-click");
      return;
    }
    if (tool === "redo") {
      if (markRedoStack.length > 0) {
        const mark = markRedoStack[markRedoStack.length - 1]!;
        setMarkRedoStack((prev) => prev.slice(0, -1));
        setRectMarks((prev) => [...prev, mark]);
      } else {
        maskOverlayRef.current?.redo();
        bumpMaskCoverage();
      }
      triggerSFX("tool-click");
      return;
    }
    triggerSFX("tool-click");
    setActiveTool(tool);
    setViewerInteractionMode(tool === "pan" ? "pan" : "orbit");
  };

  const handleSave = async () => {
    setSaving(true);
    await onSave({ title });
    track("MODEL_EDITED", projectId);
    setSaving(false);
  };

  const handleApplyAi = async () => {
    if (!aiPrompt.trim()) return;
    if (hasSpatialEditTarget || maskMode) {
      if (!hasSpatialEditTarget && maskMode) return;
      await handlePreview2d();
      return;
    }
    if (!canApply) return;
    setAiLoading(true);
    track("AI_PROMPT_SUBMITTED", projectId, { prompt: aiPrompt });
    await new Promise((r) => setTimeout(r, 1200));
    track("AI_SUGGESTION_ACCEPTED", projectId, { prompt: aiPrompt });
    setAiLoading(false);
  };

  const handleExport = () => {
    if (!hasModel) return;
    setExportWizardOpen(true);
  };

  const handleCaseWizardContinue = async (payload: CaseWizardContinuePayload) => {
    setTemplateError(null);
    if (!payload.template) {
      setCaseWizardOpen(false);
      return;
    }

    setApplyingTemplate(true);
    try {
      const res = await fetch(`/api/projects/${projectId}/apply-template`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          templateId: payload.template.id,
          clinicalParameters: payload.clinicalParameters,
          promptRefinement: payload.promptRefinement,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error ?? "Failed to apply case template.");
      }

      setSelectedCase(payload.template);
      setCaseRecipe(data.recipe as CaseRecipe);
      setTitle(data.project?.title ?? payload.template.title);
      setInstructions(formatInstructionsFromRecipe(data.recipe as CaseRecipe, payload.template));
      setLearningObjectives(
        payload.template.learningObjectives.map((title, i) => ({
          id: `lo-${i}`,
          title,
        }))
      );
      if (data.editPrompt) setAiPrompt(data.editPrompt);
      if (payload.template.defaultOperation) setEditOperation(payload.template.defaultOperation);
      setActiveTool("mask");
      setCaseWizardOpen(false);
      track("LEARNING_OBJECTIVE_CREATED", projectId, {
        caseTemplateId: payload.template.id,
        usedTemplate: true,
      });
    } catch (err) {
      setTemplateError(err instanceof Error ? err.message : "Failed to apply template.");
    } finally {
      setApplyingTemplate(false);
    }
  };

  const handlePreview2d = async () => {
    if (!hasModel) return;
    setPreviewLoading(true);
    setPreviewOpen(true);
    try {
      const capture = await viewerRef.current?.captureView();
      if (!capture) throw new Error("Could not capture the current model view.");
      if (beforePreview?.startsWith("blob:")) URL.revokeObjectURL(beforePreview);
      if (afterPreview?.startsWith("blob:") && afterPreview !== beforePreview) {
        URL.revokeObjectURL(afterPreview);
      }
      const previewUrl = URL.createObjectURL(capture.image);
      setReferenceImage(capture.image);
      setReferenceCamera(capture.camera);
      setBeforePreview(previewUrl);
      // The image-edit worker will replace this with the inpainted reference.
      setAfterPreview(previewUrl);
      const expanded = expandDentalPrompt(aiPrompt);
      track("AI_PROMPT_SUBMITTED", projectId, {
        stage: "2d-mask-approval",
        prompt: expanded.original,
      });
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleGenerate3dEdit = async () => {
    if (!modelUrl || !aiPrompt.trim()) return;
    setEditJobLoading(true);
    const maskBlob = await maskOverlayRef.current?.toMaskBlob();
    const instruction = instructionWithRegionRefs(aiPrompt, rectMarks);
    const formData = new FormData();
    formData.append("instruction", instruction);
    formData.append("operation", editOperation);
    formData.append("sourceModelUrl", modelUrl);
    if (maskBlob) formData.append("maskImage", maskBlob, "mask.png");
    if (referenceImage) formData.append("referenceImage", referenceImage, "reference.png");
    if (referenceCamera) formData.append("camera", JSON.stringify(referenceCamera));
    if (rectMarks.length > 0) {
      formData.append("regionMarks", JSON.stringify(buildRegionMarksPayload(rectMarks)));
    }
    const selectedPartIds = segmentParts.filter((part) => part.visible).map((part) => part.id);
    if (selectedPartIds.length > 0) {
      formData.append("selectedPartIds", JSON.stringify(selectedPartIds));
    }

    try {
      const res = await fetch(`/api/projects/${projectId}/edit-jobs`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Edit failed");

      track("AI_SUGGESTION_ACCEPTED", projectId, { jobId: data.jobId });

      if (data.status === "completed" && data.modelUrl) {
        setModelUrl(data.modelUrl);
        setModelFormat(data.format ?? detectModelFormat(data.modelUrl));
        setModelLoadStatus("loading");
        maskOverlayRef.current?.clear();
        setMaskCoverage(0);
        triggerSFX("toggle");
        return;
      }

      const jobId = data.jobId as string;
      for (let attempt = 0; attempt < 90; attempt++) {
        await new Promise((r) => setTimeout(r, 2000));
        const statusRes = await fetch(`/api/edit-jobs/${encodeURIComponent(jobId)}`);
        const status = await statusRes.json();
        if (status.status === "completed" && status.modelUrl) {
          setModelUrl(status.modelUrl);
          setModelFormat(status.format ?? detectModelFormat(status.modelUrl));
          setModelLoadStatus("loading");
          maskOverlayRef.current?.clear();
          setMaskCoverage(0);
          triggerSFX("toggle");
          return;
        }
        if (status.status === "failed") {
          throw new Error(status.error ?? "Edit job failed.");
        }
      }
      throw new Error("Edit job timed out — check back later.");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Edit job failed");
    } finally {
      setEditJobLoading(false);
    }
  };

  const bumpMaskCoverage = () => {
    setMaskCoverage(maskOverlayRef.current?.getCoveragePercent() ?? 0);
  };

  const handleSourceUpload = (file: File) => {
    if (sourcePreview) URL.revokeObjectURL(sourcePreview);
    setSourceFile(file);
    setSourcePreview(URL.createObjectURL(file));
  };

  const runSegmentation = async () => {
    setSegmenting(true);
    await new Promise((r) => setTimeout(r, 1500));
    setSegmentParts(generateSegmentParts());
    setSegmenting(false);
  };

  const handleGenerateModel = async () => {
    if (!sourceFile) {
      alert("Upload a scan or image in the Source panel first.");
      return;
    }

    setGenerating(true);
    setModelUrl(null);
    setMeshData(null);
    setMtlUrl(null);
    setModelFormat(null);

    try {
      await prepareGenerationNotification();
      const prepared = await prepareGenerationImage(sourceFile);
      const formData = new FormData();
      formData.append("image", prepared);
      formData.append("projectId", projectId);
      formData.append("quality", "standard");

      const res = await fetch("/api/generate/mesh", {
        method: "POST",
        body: formData,
      });

      let data = await res.json();
      if (!res.ok) {
        throw new Error(data.error ?? "Generation failed");
      }
      if (res.status === 202 && data.jobId && data.jobToken) {
        data = {
          ...(await pollGenerationJob(data.jobId, data.jobToken)),
          source: "modal",
        };
      }

      if (data.modelUrl) {
        setModelUrl(data.modelUrl);
        setMtlUrl(data.mtlUrl ?? null);
        setModelFormat(data.format ?? detectModelFormat(data.modelUrl, data.format, data.mtlUrl));
        setModelLoadStatus("loading");
      } else if (data.meshData) {
        setMeshData(data.meshData);
      }

      setModelSelected(false);
      track("MODEL_GENERATED", projectId, {
        source: data.source ?? "unknown",
        format: data.format,
      });
      await runSegmentation();
      notifyGenerationComplete(GENERATION_COPY.notifyReadyBodyEditor);
    } catch (err) {
      console.error(err);
      alert(err instanceof Error ? err.message : "Could not generate 3D model.");
    } finally {
      setGenerating(false);
    }
  };

  const handleTogglePart = (id: string) => {
    triggerSFX("toggle");
    setSegmentParts((parts) =>
      parts.map((p) => (p.id === id ? { ...p, visible: !p.visible } : p))
    );
  };

  const handlePartActivate = (id: string) => {
    triggerSFX("select");
    setActivePartId(id);
    setModelSelected(true);
  };

  const handleMeshSelect = () => {
    triggerSFX("select");
    setModelSelected(true);
    if (!activePartId && segmentParts.length > 0) {
      setActivePartId(segmentParts.find((p) => p.visible)?.id ?? segmentParts[0]?.id ?? null);
    }
  };

  return (
    <div className="editor-chrome flex h-screen flex-col overflow-hidden">
      <EditorHeader
        projectTitle={title}
        projectStatus={project.status}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        draftCount={1}
        saving={saving}
        exporting={false}
        exportDisabled={!hasModel}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((o) => !o)}
        onSave={handleSave}
        onExport={handleExport}
        onTitleChange={setTitle}
      />

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <EditorDashboardSidebar open={sidebarOpen} />

        <EditorSourcePanel
          open={sourceOpen}
          onToggle={() => setSourceOpen((o) => !o)}
          sourcePreview={sourcePreview}
          onSourceUpload={handleSourceUpload}
          onGenerateModel={handleGenerateModel}
          generating={generating}
        />

        <section
          className="relative flex min-w-0 flex-1 flex-col overflow-hidden"
          style={{ backgroundColor: EDITOR_SURFACE }}
        >
          <div className="relative min-h-0 flex-1">
            <CamModelViewer
              ref={viewerRef}
              meshData={meshData}
              modelUrl={modelUrl}
              modelFormat={modelFormat}
              mtlUrl={mtlUrl}
              sourcePreview={sourcePreview}
              wireframe={wireframe}
              rectMarks={rectMarks}
              markMode={markMode && !maskMode}
              selectMode={selectMode}
              onMeshSelect={handleMeshSelect}
              onRectMarkComplete={(partial) => void handleRectMarkComplete(partial)}
              segmentParts={segmentParts}
              activePartId={activePartId}
              modelSelected={modelSelected}
              className="absolute inset-0"
              onModelStatusChange={handleModelStatusChange}
              interactionMode={viewerInteractionMode}
            />

            <MaskPaintOverlay
              ref={maskOverlayRef}
              interactive={maskMode && hasModel}
              visible={maskVisible}
              brushSize={brushSize}
              brushMode={brushMode}
              onStrokeEnd={bumpMaskCoverage}
              onStrokesChange={setMaskHasStrokes}
            />

            <EditorMaskContextPanel
              visible={maskVisible}
              coveragePercent={maskCoverage}
              revisionLabel={`v${revisionVersion}`}
              operation={editOperation}
            />

            <EditorEditWorkflowPanel
              selectedCase={selectedCase}
              activeTool={activeTool}
              editOperation={editOperation}
              maskCoverage={maskCoverage}
              hasInstruction={Boolean(aiPrompt.trim())}
              regionMarkCount={rectMarks.length}
            />

            <EditorEditActions
              visible={maskVisible}
              previewLoading={previewLoading}
              generateLoading={editJobLoading}
              canPreview={Boolean(aiPrompt.trim()) && hasSpatialEditTarget}
              canGenerate={Boolean(afterPreview) && !previewLoading}
              onPreview2d={handlePreview2d}
              onGenerate3d={() => void handleGenerate3dEdit()}
            />

            {maskVisible && (
              <EditorMaskToolbar
                brushMode={brushMode}
                onBrushModeChange={setBrushMode}
                brushSize={brushSize}
                onBrushSizeChange={setBrushSize}
                operation={editOperation}
                onOperationChange={setEditOperation}
                onUndo={() => maskOverlayRef.current?.undo()}
                onClear={() => {
                  maskOverlayRef.current?.clear();
                  setMaskCoverage(0);
                  setMaskHasStrokes(false);
                }}
              />
            )}

            <EditorToolPalette
              activeTool={activeTool}
              onToolChange={handleToolChange}
              className="absolute right-4 top-1/2 z-20 -translate-y-1/2"
            />
          </div>

          <EditorAiBar
            value={aiPrompt}
            onChange={setAiPrompt}
            onApply={handleApplyAi}
            loading={aiLoading || previewLoading}
            canApply={canApply}
            maskMode={maskMode}
            regionAttachments={regionAttachments}
            onRemoveAttachment={handleRemoveRegionAttachment}
            hasMask={maskHasStrokes || maskCoverage > 0}
          />
        </section>

        <EditorPropertiesPanel
          open={partsOpen}
          onToggle={() => setPartsOpen((o) => !o)}
          hasModel={hasModel}
          segmentParts={segmentParts}
          onTogglePart={handleTogglePart}
          onPartActivate={handlePartActivate}
          activePartId={activePartId}
          onSelectAll={() => {
            setSegmentParts((p) => p.map((x) => ({ ...x, visible: true })));
            triggerSFX("select");
          }}
          onDeselectAll={() => {
            setSegmentParts((p) => p.map((x) => ({ ...x, visible: false })));
            setModelSelected(false);
            setActivePartId(null);
          }}
          segmenting={segmenting}
          disabled
        />

        <EditorCasePanel
          open={casePanelOpen}
          onToggle={() => setCasePanelOpen((o) => !o)}
          caseRecipe={caseRecipe}
          selectedCase={selectedCase}
          instructions={instructions}
          learningObjectives={learningObjectives}
          onSelectPrompt={(prompt) => {
            setAiPrompt(prompt);
            setActiveTool("mask");
          }}
          onStartMaskEdit={() => {
            if (selectedCase?.defaultOperation) setEditOperation(selectedCase.defaultOperation);
            setActiveTool("mask");
          }}
        />
      </div>

      <EditorStatusBar
        modelStatus={modelLoadStatus}
        modelDetail={modelLoadDetail}
        hasSourceImage={Boolean(sourcePreview)}
      />

      <EditPreviewModal
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        beforePreview={beforePreview}
        afterPreview={afterPreview}
        loading={previewLoading}
        onRefineMask={() => setPreviewOpen(false)}
        onApprove={() => {
          setPreviewOpen(false);
          void handleGenerate3dEdit();
        }}
      />

      <ExportWizardDialog
        open={exportWizardOpen}
        onClose={() => setExportWizardOpen(false)}
        projectId={projectId}
        projectTitle={title}
        modelUrl={modelUrl}
        defaultTarget={selectedCase?.exportRecommendation ?? DEFAULT_EXPORT_TARGET}
        hasPartSelection={hasPartSelection}
        selectedPartCount={segmentParts.filter((p) => p.visible).length}
        onExportComplete={() => {
          triggerSFX("toggle");
          track("EXPORT_REQUESTED", projectId, { target: selectedCase?.exportRecommendation ?? DEFAULT_EXPORT_TARGET });
        }}
      />

      <CaseWizardDialog
        open={caseWizardOpen}
        onClose={() => setCaseWizardOpen(false)}
        applying={applyingTemplate}
        onContinue={handleCaseWizardContinue}
      />
      {templateError && (
        <div className="fixed bottom-4 left-1/2 z-[95] -translate-x-1/2 rounded-lg border border-error/30 bg-error-container px-4 py-2 text-body-sm text-on-error-container shadow-lg">
          {templateError}
        </div>
      )}
    </div>
  );
}
