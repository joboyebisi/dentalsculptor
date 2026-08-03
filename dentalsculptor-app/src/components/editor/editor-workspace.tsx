"use client";

import { useState, useCallback, useRef } from "react";
import { generateDentalMeshFromImage } from "@/lib/model-generator";
import type { GeneratedMesh } from "@/lib/model-generator";
import { EditorHeader, type EditorTab } from "@/components/editor/editor-header";
import { EditorToolPalette, type EditorTool } from "@/components/editor/editor-tool-palette";
import { CamModelViewer, type CamViewerHandle, type RectMark } from "@/components/editor/cam-model-viewer";
import { EditorAiBar } from "@/components/editor/editor-ai-bar";
import { EditorPropertiesPanel } from "@/components/editor/editor-properties-panel";
import { EditorStatusBar } from "@/components/editor/editor-status-bar";
import { EditorSourcePanel } from "@/components/editor/editor-source-panel";
import { EditorDashboardSidebar } from "@/components/editor/editor-dashboard-sidebar";
import { useResearchTracker } from "@/hooks/use-research-tracker";
import { generateSegmentParts, type SegmentPart } from "@/lib/editor-segmentation";

export interface EditorProject {
  id: string;
  title: string;
  description: string | null;
  status: string;
  instructions: string | null;
  hints: string | null;
  feedback: string | null;
  dentalModel: { meshData: GeneratedMesh | null } | null;
  annotations: Array<{ id: string; text: string; position: number[]; color: string }>;
  learningObjectives: Array<{ id: string; title: string }>;
  assessments: Array<{ id: string; question: string }>;
}

interface EditorWorkspaceProps {
  project: EditorProject;
  projectId: string;
  onSave: (updates: Partial<EditorProject>) => Promise<void>;
}

export function EditorWorkspace({ project, projectId, onSave }: EditorWorkspaceProps) {
  const { track } = useResearchTracker();
  const viewerRef = useRef<CamViewerHandle>(null);

  const [title, setTitle] = useState(project.title);
  const [meshData, setMeshData] = useState<GeneratedMesh | null>(project.dentalModel?.meshData ?? null);
  const [activeTool, setActiveTool] = useState<EditorTool>("select");
  const [wireframe, setWireframe] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(true);
  const [partsOpen, setPartsOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<EditorTab>("authoring");
  const [aiPrompt, setAiPrompt] = useState(
    "Deepen the distal groove by 0.5mm and smoothen the buccal cusp transitions for better occlusion."
  );
  const [aiLoading, setAiLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [segmenting, setSegmenting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [sourcePreview, setSourcePreview] = useState<string | null>(null);
  const [rectMarks, setRectMarks] = useState<RectMark[]>([]);
  const [modelSelected, setModelSelected] = useState(false);
  const [segmentParts, setSegmentParts] = useState<SegmentPart[]>(
    project.dentalModel?.meshData ? generateSegmentParts() : []
  );

  const markMode = activeTool === "mark";
  const selectMode = activeTool === "select";
  const hasModel = Boolean(meshData?.vertices?.length);
  const hasPartSelection = segmentParts.some((p) => p.visible);
  const canApply = hasModel && (modelSelected || hasPartSelection);

  const handleRectMarkComplete = useCallback(
    (partial: Omit<RectMark, "id" | "text">) => {
      const text = prompt("Label this region:");
      if (!text) return;
      setRectMarks((prev) => [...prev, { ...partial, id: `mark-${Date.now()}`, text }]);
      track("ANNOTATION_CREATED", projectId, { text, type: "rect" });
    },
    [projectId, track]
  );

  const handleToolChange = (tool: EditorTool) => {
    if (tool === "edit") setWireframe((w) => !w);
    setActiveTool(tool);
  };

  const handleSave = async () => {
    setSaving(true);
    await onSave({ title });
    track("MODEL_EDITED", projectId);
    setSaving(false);
  };

  const handleApplyAi = async () => {
    if (!aiPrompt.trim() || !canApply) return;
    setAiLoading(true);
    track("AI_PROMPT_SUBMITTED", projectId, { prompt: aiPrompt });
    await new Promise((r) => setTimeout(r, 1200));
    track("AI_SUGGESTION_ACCEPTED", projectId, { prompt: aiPrompt });
    setAiLoading(false);
  };

  const handleExport = async () => {
    if (!hasModel) return;
    setExporting(true);
    setPartsOpen(true);
    const allSelected = segmentParts.map((p) => ({ ...p, visible: true }));
    setSegmentParts(allSelected);
    track("MODEL_EDITED", projectId, {
      action: "export",
      parts: allSelected.map((p) => p.id),
    });
    await new Promise((r) => setTimeout(r, 800));
    setExporting(false);
  };

  const handleSourceUpload = (file: File) => {
    if (sourcePreview) URL.revokeObjectURL(sourcePreview);
    setSourcePreview(URL.createObjectURL(file));
  };

  const runSegmentation = async () => {
    setSegmenting(true);
    await new Promise((r) => setTimeout(r, 1500));
    setSegmentParts(generateSegmentParts());
    setSegmenting(false);
  };

  const handleGenerateModel = async () => {
    setGenerating(true);
    await new Promise((r) => setTimeout(r, 2000));
    setMeshData(generateDentalMeshFromImage(800, 600));
    setModelSelected(false);
    track("MODEL_GENERATED", projectId);
    setGenerating(false);
    await runSegmentation();
  };

  const handleTogglePart = (id: string) => {
    setSegmentParts((parts) =>
      parts.map((p) => (p.id === id ? { ...p, visible: !p.visible } : p))
    );
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-surface">
      <EditorHeader
        projectTitle={title}
        projectStatus={project.status}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        draftCount={1}
        saving={saving}
        exporting={exporting}
        exportDisabled={!hasModel}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((o) => !o)}
        onSave={handleSave}
        onExport={handleExport}
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

        <section className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
          <div className="relative min-h-0 flex-1">
            <CamModelViewer
              ref={viewerRef}
              meshData={meshData}
              sourcePreview={sourcePreview}
              wireframe={wireframe}
              rectMarks={rectMarks}
              markMode={markMode}
              selectMode={selectMode}
              onMeshSelect={() => setModelSelected(true)}
              onRectMarkComplete={handleRectMarkComplete}
              className="absolute inset-0"
            />

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
            loading={aiLoading}
            canApply={canApply}
          />
        </section>

        <EditorPropertiesPanel
          open={partsOpen}
          onToggle={() => setPartsOpen((o) => !o)}
          hasModel={hasModel}
          segmentParts={segmentParts}
          onTogglePart={handleTogglePart}
          onSelectAll={() => setSegmentParts((p) => p.map((x) => ({ ...x, visible: true })))}
          onDeselectAll={() => {
            setSegmentParts((p) => p.map((x) => ({ ...x, visible: false })));
            setModelSelected(false);
          }}
          segmenting={segmenting}
        />
      </div>

      <EditorStatusBar />
    </div>
  );
}
