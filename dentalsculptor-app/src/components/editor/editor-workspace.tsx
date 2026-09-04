"use client";

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
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
import { EditorRevisionReview } from "@/components/editor/editor-revision-review";
import { EditorEditPresetsBar, EditPresetHapticNotice } from "@/components/editor/editor-edit-presets-bar";
import { resolveEditPresetContext } from "@/lib/edit-preset-context";
import { EDIT_PRESETS, resolveActiveEditPreset } from "@/lib/edit-presets";
import { readJsonResponse, jsonResponseError } from "@/lib/safe-json-response";
import { resolveEditWorkflowStep } from "@/lib/edit-workflow-steps";
import { formatEditProofDetail, logEditClient, editErrorMessage, type EditProofMetrics } from "@/lib/edit-log";
import {
  EditPreviewModal,
  EditorEditActions,
  EditorMaskContextPanel,
} from "@/components/editor/edit-preview-modal";
import { ExportWizardDialog } from "@/components/export/export-wizard-dialog";
import { EditorCaseContextPanel } from "@/components/editor/editor-case-context-panel";
import { CaseWizardDialog, type CaseWizardContinuePayload } from "@/components/case-wizard/case-wizard-dialog";
import type { CaseTemplate } from "@/lib/case-templates";
import { CASE_TEMPLATES, getCaseTemplate } from "@/lib/case-templates";
import type { ClinicalParameterValues } from "@/lib/case-recipe-utils";
import type { CaseRecipe } from "@/lib/clinical-case-params";
import { parseCaseRecipeFromProject, buildEditPromptFromRecipe } from "@/lib/case-recipe-utils";
import { useResearchTracker } from "@/hooks/use-research-tracker";
import { generateSegmentParts, type SegmentPart } from "@/lib/editor-segmentation";
import { triggerSFX } from "@/lib/sfx-bus";
import { parseModelProcessingStage } from "@/lib/model-processing-stage";
import { detectModelFormat } from "@/lib/model-format";
import type { SerializedCameraState } from "@/lib/camera-utils";
import { prepareGenerationImage } from "@/lib/prepare-generation-image";
import { rotateImageFile } from "@/lib/image-rotation";
import {
  notifyGenerationComplete,
  prepareGenerationNotification,
} from "@/lib/generation-notifications";
import { GENERATION_COPY } from "@/lib/generation-copy";
import { pollGenerationJob, type GenerationJobResult } from "@/lib/generation-jobs";
import { captureAndUploadCardPreview } from "@/lib/upload-project-preview-image";
import { projectModelServePath } from "@/lib/project-model-path";
import { EDITOR_SURFACE } from "@/lib/constants";
import { expandDentalPrompt } from "@/lib/dental-prompt-glossary";
import { applyMasked2dPreview, compositePreviewThroughMask } from "@/lib/edit-2d-preview";
import type { EditOperation } from "@/lib/edit-types";
import {
  attachmentFromRectMark,
  buildRegionMarksPayload,
  instructionWithRegionRefs,
} from "@/lib/edit-region-attachments";
import { DEFAULT_EXPORT_TARGET } from "@/lib/export-presets";
import type { ViewerInteractionMode } from "@/components/editor/cam-model-viewer";
import { ShareProjectDialog } from "@/components/editor/share-project-dialog";
import { CaseVariantBuilderDialog } from "@/components/editor/case-variant-builder-dialog";
import { GuidedCaseEditBar } from "@/components/editor/guided-case-edit-bar";
import { defaultVariantPresetForCase, getCaseVariantPreset, recipeFromVariantPreset, variantPresetForEditPreset, type CaseVariantPreset, type CaseVariantRecipe } from "@/lib/case-variant-recipes";
import { guidedCaseFlowCopy } from "@/lib/guided-case-flow";
import { rasterizeRectMarksToMask } from "@/lib/mask-from-regions";
import { EditorWebMcpTools } from "@/components/webmcp/editor-webmcp-tools";

async function resolveEditMaskBlob(
  maskOverlay: MaskPaintOverlayHandle | null | undefined,
  rectMarks: RectMark[],
  width: number,
  height: number
): Promise<Blob | null> {
  const painted = await maskOverlay?.toMaskBlob();
  if (painted) return painted;
  if (rectMarks.length > 0) {
    return rasterizeRectMarksToMask(width, height, rectMarks);
  }
  return null;
}

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
    modelServeUrl?: string | null;
    sourceImageUrl?: string | null;
    sourceImageServeUrl?: string | null;
    thumbnailUrl?: string | null;
    processingStage?: string | null;
  } | null;
  annotations: Array<{ id: string; text: string; position: number[]; color: string }>;
  learningObjectives: Array<{ id: string; title: string }>;
  assessments: Array<{ id: string; question: string }>;
  versions?: Array<{ label: string | null; snapshot: unknown; version: number }>;
  communityProject?: { published: boolean } | null;
}

type GenerationMeshResponse = Partial<GenerationJobResult> & {
  jobToken?: string;
  mtlUrl?: string;
  meshData?: GeneratedMesh;
  source?: string;
};

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
  const initialVariantPreset = initialTemplate ? defaultVariantPresetForCase(initialTemplate) : null;
  const initialEditPresetId = initialTemplate?.editPresetIds?.[0] ?? null;

  const { track } = useResearchTracker();
  const viewerRef = useRef<CamViewerHandle>(null);
  const maskOverlayRef = useRef<MaskPaintOverlayHandle>(null);

  const modelMeta = parseModelProcessingStage(project.dentalModel?.processingStage);
  const initialModelUrl =
    project.dentalModel?.modelServeUrl ?? project.dentalModel?.generated3DUrl ?? null;
  const masterSnapshot = project.versions?.find((version) => version.label === "master-model")?.snapshot as
    | { modelUrl?: string }
    | undefined;
  const masterModelUrl = masterSnapshot?.modelUrl ?? initialModelUrl;

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
    initialVariantPreset?.instruction ?? (initialRecipe && initialTemplate
      ? buildEditPromptFromRecipe(initialRecipe, initialTemplate)
      : "")
  );
  const [generating, setGenerating] = useState(false);
  const [segmenting, setSegmenting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exportWizardOpen, setExportWizardOpen] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [variantBuilderOpen, setVariantBuilderOpen] = useState(false);
  const [activeVariantRecipe, setActiveVariantRecipe] = useState<CaseVariantRecipe | null>(() =>
    initialVariantPreset ? recipeFromVariantPreset(initialVariantPreset) : null
  );
  const [brushMode, setBrushMode] = useState<MaskBrushMode>("paint");
  const [brushSize, setBrushSize] = useState(12);
  const [editOperation, setEditOperation] = useState<EditOperation>(
    initialVariantPreset?.operation ?? initialTemplate?.defaultOperation ?? "remove"
  );
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewProgress, setPreviewProgress] = useState(0);
  const [previewStage, setPreviewStage] = useState<string | null>(null);
  const [previewProvider, setPreviewProvider] = useState<string | null>(null);
  const [previewIsAi, setPreviewIsAi] = useState(false);
  const [previewNotice, setPreviewNotice] = useState<string | null>(null);
  const [targetRevision, setTargetRevision] = useState(0);
  const [approvedTargetRevision, setApprovedTargetRevision] = useState<number | null>(null);
  const [editJobLoading, setEditJobLoading] = useState(false);
  const [editStatus, setEditStatus] = useState<string | null>(null);
  const [editProgress, setEditProgress] = useState(0);
  const [uiError, setUiError] = useState<string | null>(null);
  const [revisionProofDetail, setRevisionProofDetail] = useState<string | null>(null);
  const [pendingRevision, setPendingRevision] = useState<{
    jobId: string;
    sourceModelUrl: string;
    revisionNumber: number;
  } | null>(null);
  const [revisionActionLoading, setRevisionActionLoading] = useState(false);
  const [beforePreview, setBeforePreview] = useState<string | null>(null);
  const [afterPreview, setAfterPreview] = useState<string | null>(null);
  const [editedReferenceBlob, setEditedReferenceBlob] = useState<Blob | null>(null);
  const [activePresetId, setActivePresetId] = useState<string | null>(
    initialEditPresetId ?? initialVariantPreset?.id ?? null
  );
  const [selectedSuggestedPrompt, setSelectedSuggestedPrompt] = useState<string | null>(initialVariantPreset?.instruction ?? null);
  const [referenceImage, setReferenceImage] = useState<Blob | null>(null);
  const [referenceCamera, setReferenceCamera] = useState<SerializedCameraState | null>(null);
  const [maskCoverage, setMaskCoverage] = useState(0);
  const [revisionVersion] = useState(1);
  const [sourcePreview, setSourcePreview] = useState<string | null>(
    project.dentalModel?.sourceImageServeUrl ?? project.dentalModel?.sourceImageUrl ?? null
  );
  const [rectMarks, setRectMarks] = useState<RectMark[]>([]);
  const [markRedoStack, setMarkRedoStack] = useState<RectMark[]>([]);
  const [maskHasStrokes, setMaskHasStrokes] = useState(false);
  const [viewerInteractionMode, setViewerInteractionMode] = useState<ViewerInteractionMode>("orbit");
  const [navigateHeld, setNavigateHeld] = useState(false);
  const [maskNotice, setMaskNotice] = useState<string | null>(null);
  const navigateHeldRef = useRef(false);
  const maskModeRef = useRef(false);
  const [floatingPanels, setFloatingPanels] = useState({
    maskContext: { minimized: false },
    workflow: { minimized: false },
    editActions: { minimized: false },
    maskToolbar: { minimized: false },
    presets: { minimized: false },
    caseContext: { minimized: false },
  });
  type FloatingPanelKey = keyof typeof floatingPanels;
  const minimizeFloatingPanel = useCallback(
    (key: FloatingPanelKey) =>
      setFloatingPanels((prev) => ({ ...prev, [key]: { minimized: true } })),
    []
  );
  const restoreFloatingPanel = useCallback(
    (key: FloatingPanelKey) =>
      setFloatingPanels((prev) => ({ ...prev, [key]: { minimized: false } })),
    []
  );
  const openMaskEditPanels = useCallback(() => {
    setFloatingPanels((prev) => ({
      ...prev,
      maskContext: { minimized: false },
      presets: { minimized: false },
      maskToolbar: { minimized: false },
      editActions: { minimized: false },
    }));
  }, []);
  const [modelSelected, setModelSelected] = useState(false);
  const [activePartId, setActivePartId] = useState<string | null>(null);
  const [modelLoadStatus, setModelLoadStatus] = useState<ModelLoadStatus>(
    initialModelUrl ? "loading" : "none"
  );
  const [modelLoadDetail, setModelLoadDetail] = useState<string | undefined>();
  const [viewerReloadGeneration, setViewerReloadGeneration] = useState(0);
  const handleModelStatusChange = useCallback((status: ModelLoadStatus, detail?: string) => {
    setModelLoadStatus(status);
    setModelLoadDetail(detail);
  }, []);
  const previewUploadedForModelRef = useRef<string | null>(null);

  useEffect(() => {
    if (modelLoadStatus !== "ready" || !modelUrl) return;
    if (previewUploadedForModelRef.current === modelUrl) return;
    previewUploadedForModelRef.current = modelUrl;

    void captureAndUploadCardPreview(
      projectId,
      async () => {
        const capture = await viewerRef.current?.captureView();
        return capture?.image ?? null;
      },
      { delayMs: 400, retries: 4 }
    );
  }, [modelLoadStatus, modelUrl, projectId]);
  const [segmentParts, setSegmentParts] = useState<SegmentPart[]>(
    project.dentalModel?.meshData || project.dentalModel?.generated3DUrl
      ? generateSegmentParts()
      : []
  );

  const markMode = activeTool === "mark";
  const maskMode = activeTool === "mask";
  maskModeRef.current = maskMode;
  const selectMode = activeTool === "select" && !maskMode;
  const hasModel = Boolean(meshData?.vertices?.length) || Boolean(modelUrl);
  const hasPartSelection = segmentParts.some((p) => p.visible);
  /** Keep mask strokes when switching tools so preview/3D edit can read the canvas. */
  const maskOverlayVisible = hasModel && (maskMode || maskHasStrokes || maskCoverage > 0);
  const maskVisible = hasModel && (maskMode || maskHasStrokes || maskCoverage > 0);
  const regionAttachments = rectMarks.map((m, i) => attachmentFromRectMark(m, i + 1));
  const hasPaintedMask = maskHasStrokes || maskCoverage > 0;
  const variantRequiresMask = activeVariantRecipe
    ? getCaseVariantPreset(activeVariantRecipe.presetId)?.requiresMask ?? true
    : true;
  const hasMaskForWorkflow = hasPaintedMask || rectMarks.length > 0;
  const canApply = hasModel && hasMaskForWorkflow && Boolean(aiPrompt.trim());

  const editPresetContext = useMemo(
    () => resolveEditPresetContext(caseRecipe, selectedCase, null),
    [caseRecipe, selectedCase]
  );
  const activeEditPreset = useMemo(
    () =>
      resolveActiveEditPreset({
        selectedCaseEditPresetIds: selectedCase?.editPresetIds,
        activePresetId,
        activeOperation: editOperation,
      }),
    [selectedCase, activePresetId, editOperation]
  );
  const geometryVariantPreview =
    activeVariantRecipe?.technique === "boolean" || activeEditPreset?.editMode === "geometry";
  const previewApprovedFor3d =
    Boolean(afterPreview) &&
    approvedTargetRevision === targetRevision &&
    (previewIsAi || geometryVariantPreview);
  const caseAllowsEdit = selectedCase?.requiresGeometryEdit !== false;
  const showEditPresets = caseAllowsEdit && (Boolean(selectedCase) || maskVisible);
  const editWorkflowStep = resolveEditWorkflowStep({
    hasMask: hasMaskForWorkflow,
    hasInstruction: Boolean(aiPrompt.trim()),
    hasPreview: previewApprovedFor3d,
  });
  const guidedFlow = selectedCase ? guidedCaseFlowCopy(selectedCase) : null;

  const invalidateApprovedPreview = useCallback(() => {
    setAfterPreview((current) => {
      if (current?.startsWith("blob:")) URL.revokeObjectURL(current);
      return null;
    });
    setEditedReferenceBlob(null);
    setPreviewIsAi(false);
    setApprovedTargetRevision(null);
  }, []);

  const markTargetChanged = useCallback(() => {
    setTargetRevision((revision) => revision + 1);
    invalidateApprovedPreview();
  }, [invalidateApprovedPreview]);

  const clearMaskPaint = useCallback((notice?: string) => {
    maskOverlayRef.current?.clear();
    setMaskCoverage(0);
    setMaskHasStrokes(false);
    markTargetChanged();
    if (notice) setMaskNotice(notice);
  }, [markTargetChanged]);

  const handleViewChange = useCallback(() => {
    if (!maskModeRef.current || navigateHeldRef.current) return;
    if (maskOverlayRef.current?.hasStrokes()) {
      clearMaskPaint(
        "View changed — mask cleared. Hold Space to rotate without clearing, then repaint."
      );
    }
  }, [clearMaskPaint]);

  useEffect(() => {
    navigateHeldRef.current = navigateHeld;
  }, [navigateHeld]);

  useEffect(() => {
    if (!maskNotice) return;
    const id = window.setTimeout(() => setMaskNotice(null), 5000);
    return () => window.clearTimeout(id);
  }, [maskNotice]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/ml/edit-health");
        const data = (await res.json()) as {
          ready?: boolean;
          jobStatusUrlHost?: string | null;
          configured?: Record<string, boolean>;
        };
        if (cancelled) return;
        logEditClient({
          phase: "start",
          detail: `edit-health ready=${Boolean(data.ready)} host=${data.jobStatusUrlHost ?? "none"}`,
        });
        if (!data.ready) {
          console.warn("[edit] DentalSculptor editing service is not fully ready — open /api/ml/edit-health while signed in");
        }
      } catch {
        // non-fatal — editor still works
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code !== "Space" || e.repeat) return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      e.preventDefault();
      setNavigateHeld(true);
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space") setNavigateHeld(false);
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, []);

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
      markTargetChanged();
      track("ANNOTATION_CREATED", projectId, { text: label, type: "rect", index });
    },
    [rectMarks.length, projectId, track, markTargetChanged]
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
    markTargetChanged();
    triggerSFX("toggle");
  }, [markTargetChanged]);

  const handleToolChange = (tool: EditorTool) => {
    if (tool === "edit") {
      setWireframe((w) => !w);
      return;
    }
    if (tool === "zoom-in") {
      if (maskMode && (maskHasStrokes || maskCoverage > 0)) {
        clearMaskPaint("Zoom changes the view — mask cleared. Repaint on the tooth.");
      }
      viewerRef.current?.zoomIn();
      triggerSFX("tool-click");
      return;
    }
    if (tool === "zoom-out") {
      if (maskMode && (maskHasStrokes || maskCoverage > 0)) {
        clearMaskPaint("Zoom changes the view — mask cleared. Repaint on the tooth.");
      }
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
        markTargetChanged();
      }
      triggerSFX("tool-click");
      return;
    }
    if (tool === "redo") {
      if (markRedoStack.length > 0) {
        const mark = markRedoStack[markRedoStack.length - 1]!;
        setMarkRedoStack((prev) => prev.slice(0, -1));
        setRectMarks((prev) => [...prev, mark]);
        markTargetChanged();
      } else {
        maskOverlayRef.current?.redo();
        bumpMaskCoverage();
      }
      triggerSFX("tool-click");
      return;
    }
    triggerSFX("tool-click");
    const NAVIGATION_TOOLS: EditorTool[] = ["pan", "select", "zoom-in", "zoom-out"];
    if (
      tool !== "mask" &&
      tool !== "mark" &&
      NAVIGATION_TOOLS.includes(tool) &&
      (maskHasStrokes || maskCoverage > 0)
    ) {
      clearMaskPaint(
        tool === "pan"
          ? "Pan moves the model — mask cleared. Switch back to Mask and repaint on the tooth."
          : "Mask cleared — it was tied to the previous view. Repaint after moving the model."
      );
    }
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
    if (!aiPrompt.trim() || !hasMaskForWorkflow) return;
    await handlePreview2d();
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
      const defaultVariant = defaultVariantPresetForCase(payload.template);
      if (defaultVariant) {
        setActiveVariantRecipe(recipeFromVariantPreset(defaultVariant));
        const editPresetId = payload.template.editPresetIds?.[0] ?? null;
        setActivePresetId(editPresetId ?? defaultVariant.id);
        setSelectedSuggestedPrompt(defaultVariant.instruction);
        setAiPrompt(defaultVariant.instruction);
        setEditOperation(defaultVariant.operation);
      } else {
        setActiveVariantRecipe(null);
        const editPresetId = payload.template.editPresetIds?.[0] ?? null;
        if (editPresetId) setActivePresetId(editPresetId);
      }
      setCaseRecipe(data.recipe as CaseRecipe);
      const nextTitle = data.project?.title ?? payload.template.title;
      setTitle(nextTitle);
      await onSave({ title: nextTitle });
      if (!defaultVariant && data.editPrompt) setAiPrompt(data.editPrompt);
      if (!defaultVariant && payload.template.defaultOperation) setEditOperation(payload.template.defaultOperation);
      setActiveTool(payload.template.requiresGeometryEdit !== false ? "mask" : "select");
      setFloatingPanels({
        maskContext: { minimized: false },
        workflow: { minimized: true },
        editActions: { minimized: false },
        maskToolbar: { minimized: false },
        presets: { minimized: false },
        caseContext: { minimized: true },
      });
      setCaseWizardOpen(false);
      // A full viewer remount prevents stale WebGL/camera state after the
      // full-screen case wizard closes. This is intentionally independent of
      // the unchanged master model URL.
      setViewerReloadGeneration((generation) => generation + 1);
      openMaskEditPanels();
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
    setEditedReferenceBlob(null);
    setPreviewProgress(8);
    setPreviewStage("Capturing 3D view…");
    setPreviewProvider(null);
    setPreviewIsAi(false);
    setApprovedTargetRevision(null);
    setPreviewNotice(null);
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
      setPreviewProgress(25);
      setPreviewStage("Reading mask…");

      const maskWidth = capture.camera.width ?? 512;
      const maskHeight = capture.camera.height ?? 512;
      const maskBlob = await resolveEditMaskBlob(
        maskOverlayRef.current,
        rectMarks,
        maskWidth,
        maskHeight
      );
      if (!maskBlob && variantRequiresMask) {
        throw new Error(
          "Paint the target region with the Mask brush (or draw a fracture line) before previewing."
        );
      }
      const instruction = instructionWithRegionRefs(aiPrompt, rectMarks);
      let previewBlob: Blob | null = null;
      let providerLabel: string | null = null;

      // Teaching variants use deterministic, mask-local previews. Generative
      // inpainting can alter the camera, tooth silhouette, or unrelated anatomy,
      // which is unsuitable as evidence for a precise clinical edit.
      const usesDeterministicVariant =
        Boolean(activeVariantRecipe) && activeVariantRecipe?.technique !== "generative";
      if (maskBlob && !usesDeterministicVariant) {
        setPreviewProgress(45);
        setPreviewStage("DentalSculptor is creating the proposed change…");
        const previewForm = new FormData();
        previewForm.append("instruction", instruction);
        previewForm.append("operation", editOperation);
        previewForm.append("referenceImage", capture.image, "reference.png");
        previewForm.append("maskImage", maskBlob, "mask.png");

        const previewRes = await fetch(`/api/projects/${projectId}/edit-preview`, {
          method: "POST",
          body: previewForm,
        });
        const { data: previewData, raw: previewRaw } = await readJsonResponse<{
          previewBase64?: string;
          contentType?: string;
          provider?: string;
          reason?: string;
          error?: string;
        }>(previewRes);
        if (!previewData) {
          throw new Error(jsonResponseError(previewRes, previewRaw, "Preview service returned an invalid response."));
        }
        if (!previewRes.ok) throw new Error(previewData.error ?? "Could not create the preview.");

        if (previewRes.ok && previewData.previewBase64) {
          const bytes = Uint8Array.from(atob(previewData.previewBase64 as string), (c) =>
            c.charCodeAt(0)
          );
          const generatedPreview = new Blob([bytes], {
            type: (previewData.contentType as string) ?? "image/png",
          });
          previewBlob = await compositePreviewThroughMask(
            capture.image,
            generatedPreview,
            maskBlob
          );
          providerLabel = previewData.provider ?? "DentalSculptor";
          setPreviewIsAi(true);
          setPreviewNotice("DentalSculptor preview completed. Confirm that the change is confined to the painted region before running the 3D edit.");
        }
      }

      if (!previewBlob) {
        setPreviewProgress(72);
        setPreviewStage("Building local clinical preview…");
        previewBlob = await applyMasked2dPreview(
          capture.image,
          maskBlob ?? null,
          editOperation,
          instruction
        );
        const verifiedCasePreview = usesDeterministicVariant;
        const deterministicGeometryPreview =
          editOperation === "remove" && activeEditPreset?.editMode === "geometry";
        const verifiedPreview = verifiedCasePreview || deterministicGeometryPreview;
        providerLabel = verifiedPreview
          ? "DentalSculptor region preview"
          : "Illustrative preview";
        setPreviewIsAi(verifiedPreview);
        setPreviewNotice(
          verifiedPreview
            ? "Region preview completed without changing the camera or surrounding anatomy. Review the marked boundary before continuing."
            : "Illustrative preview only — the editing service did not produce a verified proposal. A 3D edit cannot be approved from this preview."
        );
      }

      setPreviewProvider(providerLabel);
      setPreviewProgress(100);
      setPreviewStage(null);
      setEditedReferenceBlob(previewBlob);
      if (afterPreview?.startsWith("blob:") && afterPreview !== beforePreview) {
        URL.revokeObjectURL(afterPreview);
      }
      setAfterPreview(URL.createObjectURL(previewBlob));
      setApprovedTargetRevision(targetRevision);
      const expanded = expandDentalPrompt(instruction);
      track("AI_PROMPT_SUBMITTED", projectId, {
        stage: "2d-mask-approval",
        prompt: expanded.original,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not create the preview.";
      setPreviewIsAi(false);
      setPreviewStage(null);
      setPreviewNotice(message);
      setUiError(message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handlePresetSelect = (preset: {
    id: string;
    operation: EditOperation;
    prompt: string;
  }) => {
    invalidateApprovedPreview();
    setActivePresetId(preset.id);
    setSelectedSuggestedPrompt(preset.prompt);
    setEditOperation(preset.operation);
    setAiPrompt(preset.prompt);
    const variantPreset = variantPresetForEditPreset(preset.id);
    setActiveVariantRecipe(variantPreset ? recipeFromVariantPreset(variantPreset) : null);
    if (activeTool !== "mask" && activeTool !== "mark") {
      setActiveTool("mask");
    }
    triggerSFX("toggle");
  };

  const handleSelectSuggestedPrompt = (prompt: string) => {
    invalidateApprovedPreview();
    setSelectedSuggestedPrompt(prompt);
    setAiPrompt(prompt);
    const matchingPreset = EDIT_PRESETS.find((p) => p.prompt === prompt);
    if (matchingPreset) {
      setActivePresetId(matchingPreset.id);
      setEditOperation(matchingPreset.operation);
      const variantPreset = variantPresetForEditPreset(matchingPreset.id);
      setActiveVariantRecipe(variantPreset ? recipeFromVariantPreset(variantPreset) : null);
    } else if (selectedCase?.defaultOperation) {
      setEditOperation(selectedCase.defaultOperation);
      setActiveVariantRecipe(null);
    } else {
      setActiveVariantRecipe(null);
    }
    if (activeTool !== "mask" && activeTool !== "mark") {
      setActiveTool("mask");
    }
    triggerSFX("toggle");
  };

  const handleGenerate3dEdit = async () => {
    if (!modelUrl || !aiPrompt.trim()) return;
    if (!previewApprovedFor3d) {
      setUiError("Review and approve the 2D preview before creating the 3D variant.");
      return;
    }
    const sourceBeforeEdit = activeVariantRecipe && masterModelUrl ? masterModelUrl : modelUrl;
    setEditJobLoading(true);
    setEditProgress(5);
    setEditStatus("Submitting DentalSculptor edit…");
    logEditClient({ phase: "start", projectId, operation: editOperation, detail: "generate3d" });
    const maskWidth = referenceCamera?.width ?? 512;
    const maskHeight = referenceCamera?.height ?? 512;
    const maskBlob = await resolveEditMaskBlob(
      maskOverlayRef.current,
      rectMarks,
      maskWidth,
      maskHeight
    );
    if (variantRequiresMask && !maskBlob) {
      setEditJobLoading(false);
      setUiError("Paint the target region with the Mask brush before creating the variant.");
      return;
    }
    const instruction = instructionWithRegionRefs(aiPrompt, rectMarks);
    const formData = new FormData();
    formData.append("instruction", instruction);
    formData.append("operation", editOperation);
    formData.append("sourceModelUrl", sourceBeforeEdit);
    if (activeVariantRecipe) formData.append("variantRecipe", JSON.stringify(activeVariantRecipe));
    if (maskBlob) formData.append("maskImage", maskBlob, "mask.png");
    if (referenceImage) {
      formData.append("sourceImage", referenceImage, "source-view.png");
    }
    if (editedReferenceBlob) {
      formData.append("editedImage", editedReferenceBlob, "edited-view.png");
    }
    const refFor3d = editedReferenceBlob ?? referenceImage;
    if (refFor3d) {
      formData.append("referenceImage", refFor3d, "reference.png");
      if (editedReferenceBlob) formData.append("referenceEdited", "true");
    }
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
      const { data, raw } = await readJsonResponse<{
        error?: string;
        jobId?: string;
        status?: string;
        modelUrl?: string;
        format?: string;
        revisionNumber?: number;
        message?: string;
        maskedVertexRatio?: number;
        stage?: string;
        regionMarkCount?: number;
        metrics?: EditProofMetrics;
      }>(res);
      if (!data) {
        throw new Error(jsonResponseError(res, raw, "Edit service returned an empty response."));
      }
      if (!res.ok) throw new Error(data.error ?? "Edit failed");
      if (data.message && data.status === "queued" && !data.modelUrl) {
        throw new Error(data.message);
      }

      track("AI_SUGGESTION_ACCEPTED", projectId, { jobId: data.jobId });
      logEditClient({
        phase: data.status === "completed" ? "complete" : "submit",
        projectId,
        jobId: data.jobId,
        stage: data.stage ?? data.status,
        maskedVertexRatio: data.maskedVertexRatio,
      });

      const applyCompletedEdit = (
        resultUrl: string,
        fmt: string | undefined,
        jobId: string,
        revisionNumber?: number,
        proof?: {
          maskedVertexRatio?: number;
          stage?: string;
          regionMarkCount?: number;
          metrics?: EditProofMetrics;
        }
      ) => {
        setModelUrl(resultUrl);
        setModelFormat(fmt ?? detectModelFormat(resultUrl));
        setModelLoadStatus("loading");
        maskOverlayRef.current?.clear();
        setMaskCoverage(0);
        setMaskHasStrokes(false);
        setRevisionProofDetail(formatEditProofDetail(proof ?? {}));
        setPendingRevision({
          jobId,
          sourceModelUrl: sourceBeforeEdit,
          revisionNumber: revisionNumber ?? 1,
        });
        setPreviewOpen(false);
        setActiveTool("select");
        setEditStatus(null);
        setEditProgress(100);
        logEditClient({
          phase: "complete",
          projectId,
          jobId,
          maskedVertexRatio: proof?.maskedVertexRatio,
          stage: proof?.stage,
        });
        triggerSFX("toggle");
      };

      if (data.status === "completed" && data.modelUrl) {
        applyCompletedEdit(
          data.modelUrl,
          data.format,
          data.jobId as string,
          data.revisionNumber as number | undefined,
          {
            maskedVertexRatio: data.maskedVertexRatio,
            stage: data.stage,
            regionMarkCount: data.regionMarkCount,
            metrics: data.metrics,
          }
        );
        return;
      }

      const jobId = data.jobId as string;
      setEditStatus(`DentalSculptor edit queued (${jobId.slice(0, 8)}…)`);
      setEditProgress(10);
      for (let attempt = 0; attempt < 90; attempt++) {
        await new Promise((r) => setTimeout(r, 2000));
        const statusRes = await fetch(
          `/api/edit-jobs/${encodeURIComponent(jobId)}?projectId=${encodeURIComponent(projectId)}`
        );
        const { data: status, raw: statusRaw } = await readJsonResponse<{
          status?: string;
          modelUrl?: string;
          format?: string;
          revisionNumber?: number;
          preview2dUrl?: string;
          error?: string;
          progress?: number;
          stage?: string;
          message?: string;
          maskedVertexRatio?: number;
          regionMarkCount?: number;
          metrics?: EditProofMetrics;
        }>(statusRes);
        if (!status) {
          throw new Error(jsonResponseError(statusRes, statusRaw, "Edit status unavailable."));
        }

        const progressLabel =
          typeof status.progress === "number" ? ` (${status.progress}%)` : "";
        setEditStatus(
          status.message ??
            `DentalSculptor ${status.stage ?? status.status ?? "running"}${progressLabel}`
        );
        if (typeof status.progress === "number") setEditProgress(status.progress);
        logEditClient({
          phase: "poll",
          projectId,
          jobId,
          progress: status.progress,
          stage: status.stage ?? status.status,
          maskedVertexRatio: status.maskedVertexRatio,
        });

        if (status.preview2dUrl && typeof status.preview2dUrl === "string") {
          if (afterPreview?.startsWith("blob:")) URL.revokeObjectURL(afterPreview);
          setAfterPreview(status.preview2dUrl);
        }
        if (status.status === "completed" && status.modelUrl) {
          applyCompletedEdit(
            status.modelUrl,
            status.format,
            jobId,
            status.revisionNumber as number | undefined,
            {
              maskedVertexRatio: status.maskedVertexRatio,
              stage: status.stage,
              regionMarkCount: status.regionMarkCount,
              metrics: status.metrics,
            }
          );
          return;
        }
        if (status.status === "failed") {
          throw new Error(status.error ?? "Edit job failed.");
        }
      }
      throw new Error("Edit job timed out — check back later.");
    } catch (err) {
      const message = editErrorMessage(err);
      logEditClient({ phase: "failed", projectId, error: message });
      setEditStatus(null);
      setUiError(message);
    } finally {
      setEditJobLoading(false);
      window.setTimeout(() => setEditProgress(0), 500);
    }
  };

  const handleAcceptRevision = async () => {
    if (!pendingRevision) return;
    setRevisionActionLoading(true);
    try {
      const res = await fetch(`/api/edit-jobs/${pendingRevision.jobId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "accept" }),
      });
      const { data, raw } = await readJsonResponse<{ error?: string }>(res);
      if (!data) throw new Error(jsonResponseError(res, raw, "Could not accept revision."));
      if (!res.ok) throw new Error(data.error ?? "Could not accept revision.");
      logEditClient({ phase: "accept", projectId, jobId: pendingRevision.jobId });
      setPendingRevision(null);
      setRevisionProofDetail(null);
      setActiveVariantRecipe(null);
      track("AI_SUGGESTION_ACCEPTED", projectId, { editJobId: pendingRevision.jobId });
    } catch (err) {
      setUiError(err instanceof Error ? err.message : "Could not accept revision.");
    } finally {
      setRevisionActionLoading(false);
    }
  };

  const handleRejectRevision = async () => {
    if (!pendingRevision) return;
    setRevisionActionLoading(true);
    try {
      const res = await fetch(`/api/edit-jobs/${pendingRevision.jobId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "reject" }),
      });
      const { data, raw } = await readJsonResponse<{ error?: string }>(res);
      if (!data) throw new Error(jsonResponseError(res, raw, "Could not revert revision."));
      if (!res.ok) throw new Error(data.error ?? "Could not revert revision.");
      setModelUrl(pendingRevision.sourceModelUrl);
      setModelFormat(detectModelFormat(pendingRevision.sourceModelUrl));
      setModelLoadStatus("loading");
      logEditClient({ phase: "reject", projectId, jobId: pendingRevision.jobId });
      setPendingRevision(null);
      setRevisionProofDetail(null);
      setActiveVariantRecipe(null);
      track("AI_SUGGESTION_REJECTED", projectId, { editJobId: pendingRevision.jobId });
    } catch (err) {
      setUiError(err instanceof Error ? err.message : "Could not revert revision.");
    } finally {
      setRevisionActionLoading(false);
    }
  };

  const bumpMaskCoverage = () => {
    setMaskCoverage(maskOverlayRef.current?.getCoveragePercent() ?? 0);
    markTargetChanged();
  };

  const handleSourceUpload = (file: File) => {
    if (sourcePreview?.startsWith("blob:")) URL.revokeObjectURL(sourcePreview);
    setSourceFile(file);
    setSourcePreview(URL.createObjectURL(file));
  };

  const handleSourceClear = () => {
    if (sourcePreview?.startsWith("blob:")) URL.revokeObjectURL(sourcePreview);
    setSourceFile(null);
    setSourcePreview(null);
  };

  const handleSourceRotate = async () => {
    const file =
      sourceFile ??
      (await resolveSourceImageFile(sourcePreview ?? project.dentalModel?.sourceImageUrl ?? null));
    if (!file || generating) return;
    const rotated = await rotateImageFile(file, 90);
    handleSourceUpload(rotated);
  };

  async function resolveSourceImageFile(url: string | null): Promise<File | null> {
    if (sourceFile) return sourceFile;
    if (!url) return null;
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) return null;
      const blob = await res.blob();
      return new File([blob], "source-image.jpg", { type: blob.type || "image/jpeg" });
    } catch {
      return null;
    }
  }

  const runSegmentation = async () => {
    setSegmenting(true);
    await new Promise((r) => setTimeout(r, 1500));
    setSegmentParts(generateSegmentParts());
    setSegmenting(false);
  };

  const handleGenerateModel = async () => {
    const imageFile = await resolveSourceImageFile(
      sourcePreview ?? project.dentalModel?.sourceImageUrl ?? null
    );
    if (!imageFile) {
      setUiError("Select or upload a scan or image in the Source panel first.");
      return;
    }

    setUiError(null);
    setGenerating(true);
    setModelUrl(null);
    setMeshData(null);
    setMtlUrl(null);
    setModelFormat(null);

    try {
      await prepareGenerationNotification();
      const prepared = await prepareGenerationImage(imageFile);
      const formData = new FormData();
      formData.append("image", prepared);
      formData.append("projectId", projectId);
      formData.append("quality", "standard");

      const res = await fetch("/api/generate/mesh", {
        method: "POST",
        body: formData,
      });

      const parsed = await readJsonResponse<GenerationMeshResponse>(res);
      if (!parsed.data) {
        throw new Error(jsonResponseError(res, parsed.raw, "Generation service returned an invalid response."));
      }
      let data = parsed.data;
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
        setModelUrl(projectModelServePath(projectId));
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
      setUiError(err instanceof Error ? err.message : "Could not generate 3D model.");
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

  const handleWebMcpExport = async (target: string, outputFormat: string) => {
    const allowedTargets = ["simodont", "simtocare", "virteasy", "meta-quest", "powerpoint", "teaching-bundle"];
    const allowedFormats = ["stl", "obj", "glb", "ply"];
    if (!allowedTargets.includes(target) || !allowedFormats.includes(outputFormat)) {
      throw new Error("Choose a supported export target and format.");
    }
    const res = await fetch(`/api/projects/${projectId}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target, outputFormat, scope: "full", modelUrl: modelUrl ?? undefined }),
    });
    if (!res.ok) {
      const { data, raw } = await readJsonResponse<{ error?: string }>(res);
      throw new Error(data?.error ?? jsonResponseError(res, raw, "Export failed."));
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") ?? "";
    const match = disposition.match(/filename="([^"]+)"/);
    const fileName = match?.[1] ?? `${title.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 64)}-${target}.${outputFormat}`;
    const downloadUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = downloadUrl;
    anchor.download = fileName;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
    track("EXPORT_REQUESTED", projectId, { target, outputFormat, source: "webmcp" });
    return { fileName };
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
      <EditorWebMcpTools
        projectId={projectId}
        title={title}
        hasModel={hasModel}
        modelViewerReady={modelLoadStatus === "ready"}
        modelLoadStatus={modelLoadStatus}
        selectedCase={selectedCase?.title ?? null}
        activePresetId={activePresetId}
        allowedPresetIds={EDIT_PRESETS.map((preset) => preset.id)}
        availableCases={CASE_TEMPLATES.map((template) => ({
          id: template.id,
          title: template.title,
          requiresGeometryEdit: template.requiresGeometryEdit !== false,
          presetIds: template.editPresetIds ?? [],
          requiredClinicalParameters: template.clinicalParameterFields.filter((field) => field.required).map((field) => field.id),
        }))}
        targetReady={hasMaskForWorkflow}
        previewReady={previewApprovedFor3d}
        revisionPending={Boolean(pendingRevision)}
        busy={previewLoading || editJobLoading || revisionActionLoading || applyingTemplate}
        choosePreset={(presetId) => {
          const preset = EDIT_PRESETS.find((candidate) => candidate.id === presetId);
          if (preset) handlePresetSelect(preset);
        }}
        openCaseSelector={() => setCaseWizardOpen(true)}
        openMaskTool={() => { setActiveTool("mask"); openMaskEditPanels(); }}
        previewEdit={handlePreview2d}
        createVariant={handleGenerate3dEdit}
        openExport={() => setExportWizardOpen(true)}
        openShare={() => setShareDialogOpen(true)}
        applyCase={async (templateId, clinicalParameters, promptRefinement) => {
          const template = getCaseTemplate(templateId);
          if (!template) throw new Error("Choose a case template returned by inspect_editor.");
          await handleCaseWizardContinue({
            template,
            clinicalParameters: clinicalParameters as ClinicalParameterValues,
            promptRefinement,
          });
        }}
        markTarget={async (region) => {
          setActiveTool("mark");
          await handleRectMarkComplete({ ...region, color: "#0F3D91" });
        }}
        saveProject={handleSave}
        resolveRevision={async (decision) => {
          if (decision === "accept") await handleAcceptRevision();
          else await handleRejectRevision();
        }}
        exportModel={handleWebMcpExport}
      />
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
        onCreateVariant={() => setVariantBuilderOpen(true)}
        onShare={() => setShareDialogOpen(true)}
        onExport={handleExport}
        onTitleChange={setTitle}
      />

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <EditorDashboardSidebar open={sidebarOpen} />

        <EditorSourcePanel
          open={sourceOpen}
          onToggle={() => setSourceOpen((o) => !o)}
          sourcePreview={sourcePreview}
          hasSourceFile={Boolean(sourceFile || sourcePreview || project.dentalModel?.sourceImageUrl)}
          onSelectImage={handleSourceUpload}
          onClearImage={handleSourceClear}
          onRotateImage={handleSourceRotate}
          onGenerateModel={handleGenerateModel}
          generating={generating}
          hasModel={hasModel}
          caseTitle={selectedCase?.title ?? null}
          caseInstruction={guidedFlow?.targetHint ?? selectedCase?.shortDescription ?? null}
          onStartEdit={() => { setActiveTool("mask"); openMaskEditPanels(); }}
        />

        <section
          className="relative flex min-w-0 flex-1 flex-col overflow-hidden"
          style={{ backgroundColor: EDITOR_SURFACE }}
        >
          <div className="relative min-h-0 flex-1">
            <CamModelViewer
              key={`${modelUrl ?? "procedural"}:${viewerReloadGeneration}`}
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
              onViewChange={handleViewChange}
            />

            <MaskPaintOverlay
              ref={maskOverlayRef}
              interactive={maskMode && hasModel && !navigateHeld}
              visible={maskOverlayVisible}
              brushSize={brushSize}
              brushMode={brushMode}
              onStrokeEnd={bumpMaskCoverage}
              onStrokesChange={setMaskHasStrokes}
            />

            {maskNotice && (
              <div className="pointer-events-none absolute bottom-4 left-1/2 z-30 max-w-md -translate-x-1/2 rounded-lg border border-amber-300/60 bg-amber-50/95 px-4 py-2 text-center text-[11px] leading-snug text-amber-950 shadow-md backdrop-blur-sm">
                {maskNotice}
              </div>
            )}

            {editJobLoading && (
              <div className="absolute inset-0 z-40 flex items-center justify-center bg-on-surface/35 p-6 backdrop-blur-[2px]" role="status" aria-live="polite">
                <div className="w-full max-w-md rounded-2xl border border-outline-variant bg-surface/95 p-6 text-center shadow-2xl">
                  <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary-container/25 border-t-primary-container" />
                  <h3 className="text-title-lg font-semibold text-on-surface">DentalSculptor is applying your edit</h3>
                  <p className="mt-2 text-body-sm text-on-surface-variant">{editStatus ?? "Preparing the edited model…"}</p>
                  <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-surface-container-high">
                    <div className="h-full rounded-full bg-primary-container transition-all duration-500" style={{ width: `${Math.max(6, Math.min(100, editProgress))}%` }} />
                  </div>
                  <p className="mt-2 font-mono text-xs text-on-surface-variant">{Math.round(editProgress)}%</p>
                  <p className="mt-3 text-xs text-on-surface-variant">Keep this page open. Your original model remains unchanged until you accept the revision.</p>
                </div>
              </div>
            )}

            <EditorMaskContextPanel
              visible={false}
              minimized={floatingPanels.maskContext.minimized}
              onMinimize={() => minimizeFloatingPanel("maskContext")}
              onRestore={() => restoreFloatingPanel("maskContext")}
              coveragePercent={maskCoverage}
              revisionLabel={`v${revisionVersion}`}
              operation={editOperation}
              workflowStep={editWorkflowStep}
            />

            <EditorEditWorkflowPanel
              visible={false}
              minimized={floatingPanels.workflow.minimized}
              onMinimize={() => minimizeFloatingPanel("workflow")}
              onRestore={() => restoreFloatingPanel("workflow")}
              selectedCase={selectedCase}
              activeTool={activeTool}
              editOperation={editOperation}
              maskCoverage={maskCoverage}
              hasInstruction={Boolean(aiPrompt.trim())}
              regionMarkCount={rectMarks.length}
            />

            <EditorCaseContextPanel
              visible={false}
              minimized={floatingPanels.caseContext.minimized}
              onMinimize={() => minimizeFloatingPanel("caseContext")}
              onRestore={() => restoreFloatingPanel("caseContext")}
              selectedCase={selectedCase}
              caseRecipe={caseRecipe}
            />

            {pendingRevision && (
              <EditorRevisionReview
                revisionNumber={pendingRevision.revisionNumber}
                loading={revisionActionLoading}
                proofDetail={revisionProofDetail}
                onAccept={() => void handleAcceptRevision()}
                onReject={() => void handleRejectRevision()}
              />
            )}

            <EditorEditPresetsBar
              visible={showEditPresets && !selectedCase}
              minimized={floatingPanels.presets.minimized}
              onMinimize={() => minimizeFloatingPanel("presets")}
              onRestore={() => restoreFloatingPanel("presets")}
              context={editPresetContext}
              selectedCase={selectedCase}
              activePresetId={activePresetId}
              selectedSuggestedPrompt={selectedSuggestedPrompt ?? (aiPrompt.trim() || null)}
              activeOperation={editOperation}
              maskCoverage={maskCoverage}
              onSelect={handlePresetSelect}
              onSelectSuggestedPrompt={handleSelectSuggestedPrompt}
            />

            <EditorEditActions
              visible={false}
              minimized={floatingPanels.editActions.minimized}
              onMinimize={() => minimizeFloatingPanel("editActions")}
              onRestore={() => restoreFloatingPanel("editActions")}
              previewLoading={previewLoading}
              generateLoading={editJobLoading}
              canPreview={Boolean(aiPrompt.trim()) && hasMaskForWorkflow}
              canGenerate={previewApprovedFor3d && !previewLoading}
              onPreview2d={handlePreview2d}
              onGenerate3d={() => void handleGenerate3dEdit()}
            />

            {maskVisible && (
              <EditorMaskToolbar
                visible
                minimized={floatingPanels.maskToolbar.minimized}
                onMinimize={() => minimizeFloatingPanel("maskToolbar")}
                onRestore={() => restoreFloatingPanel("maskToolbar")}
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
                  markTargetChanged();
                }}
                allowFractureLine={selectedCase?.procedure === "pathology-add"}
                lockOperation={Boolean(selectedCase)}
              />
            )}

            <EditorToolPalette
              activeTool={activeTool}
              onToolChange={handleToolChange}
              className="absolute right-4 top-1/2 z-20 -translate-y-1/2"
            />
          </div>

          <EditPresetHapticNotice preset={activeEditPreset} className="mx-3 mb-1" />

          {selectedCase ? (
            <GuidedCaseEditBar
              caseTitle={selectedCase.title}
              instruction={aiPrompt || selectedCase.shortDescription}
              step={editWorkflowStep}
              previewLoading={previewLoading}
              editLoading={editJobLoading}
              onPaint={() => { setActiveTool("mask"); openMaskEditPanels(); }}
              onPreview={handlePreview2d}
              onCreate={() => void handleGenerate3dEdit()}
              canCreate={previewApprovedFor3d}
              markLabel={guidedFlow?.mark ?? "Mark target area"}
              previewLabel={guidedFlow?.preview ?? "Preview change"}
              createLabel={guidedFlow?.create ?? "Create 3D variant"}
            />
          ) : <EditorAiBar
            value={aiPrompt}
            onChange={(v) => {
              setAiPrompt(v);
              if (v.trim() !== selectedSuggestedPrompt) {
                invalidateApprovedPreview();
                setSelectedSuggestedPrompt(null);
                setActivePresetId(null);
                setActiveVariantRecipe(null);
              }
            }}
            onApply={handleApplyAi}
            loading={previewLoading || editJobLoading}
            canApply={canApply}
            maskMode={maskMode}
            regionAttachments={regionAttachments}
            onRemoveAttachment={handleRemoveRegionAttachment}
            hasMask={hasPaintedMask}
            workflowStep={editWorkflowStep}
          />}
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

      </div>

      <EditorStatusBar
        modelStatus={modelLoadStatus}
        modelDetail={modelLoadDetail}
        hasSourceImage={Boolean(sourcePreview)}
        editStatus={editStatus}
        error={uiError}
      />

      <EditPreviewModal
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        beforePreview={beforePreview}
        afterPreview={afterPreview}
        loading={previewLoading}
        progress={previewProgress}
        stageLabel={previewStage}
        previewProvider={previewProvider}
        previewIsAi={previewIsAi}
        previewNotice={previewNotice}
        onRefineMask={() => {
          setPreviewOpen(false);
          invalidateApprovedPreview();
        }}
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
        selectedCase={selectedCase}
        caseRecipe={caseRecipe}
        sourceImageUrl={sourcePreview}
        hasPartSelection={hasPartSelection}
        selectedPartCount={segmentParts.filter((p) => p.visible).length}
        onExportComplete={() => {
          triggerSFX("toggle");
          track("EXPORT_REQUESTED", projectId, { target: selectedCase?.exportRecommendation ?? DEFAULT_EXPORT_TARGET });
        }}
      />
      <ShareProjectDialog
        open={shareDialogOpen}
        onClose={() => setShareDialogOpen(false)}
        projectId={projectId}
        projectTitle={title}
        hasModel={hasModel}
        initiallyPublished={Boolean(project.communityProject?.published)}
      />
      <CaseVariantBuilderDialog
        open={variantBuilderOpen}
        onClose={() => setVariantBuilderOpen(false)}
        onPrepare={(preset: CaseVariantPreset, recipe: CaseVariantRecipe) => {
          setActiveVariantRecipe({
            ...recipe,
            schemaVersion: 1,
            operation: preset.operation,
          });
          setActivePresetId(selectedCase?.editPresetIds?.[0] ?? preset.id);
          setSelectedSuggestedPrompt(preset.instruction);
          setEditOperation(preset.operation);
          setAiPrompt(preset.instruction);
          setActiveTool(preset.requiresMask ? "mask" : "mark");
          openMaskEditPanels();
          setEditStatus(`${preset.label} configured — mark the target region.`);
          setVariantBuilderOpen(false);
          triggerSFX("toggle");
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
