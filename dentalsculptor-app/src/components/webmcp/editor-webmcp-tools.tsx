"use client";

import { WebMcpTool, webMcpResult } from "@/components/webmcp/webmcp-tool";

const PRESET_SCHEMA = {
  type: "object" as const,
  properties: { presetId: { type: "string", description: "A preset ID returned by dentalsculptor_inspect_editor." } },
  required: ["presetId"],
  additionalProperties: false,
};

const CASE_SCHEMA = {
  type: "object" as const,
  properties: {
    templateId: { type: "string", description: "A case template ID returned by dentalsculptor_inspect_editor." },
    clinicalParameters: { type: "object", description: "Clinical parameters required by the selected case, such as fdiTooth, surface, site, or depth." },
    promptRefinement: { type: "string", description: "Optional educator-authored refinement." },
  },
  required: ["templateId", "clinicalParameters"],
  additionalProperties: false,
};

const TARGET_SCHEMA = {
  type: "object" as const,
  properties: {
    x: { type: "number", minimum: 0, maximum: 1, description: "Left edge as a fraction of viewport width." },
    y: { type: "number", minimum: 0, maximum: 1, description: "Top edge as a fraction of viewport height." },
    width: { type: "number", exclusiveMinimum: 0, maximum: 1, description: "Target width as a fraction of viewport width." },
    height: { type: "number", exclusiveMinimum: 0, maximum: 1, description: "Target height as a fraction of viewport height." },
  },
  required: ["x", "y", "width", "height"],
  additionalProperties: false,
};

const REVISION_SCHEMA = {
  type: "object" as const,
  properties: { decision: { type: "string", enum: ["accept", "reject"], description: "The educator's explicit revision decision." } },
  required: ["decision"], additionalProperties: false,
};

const EXPORT_SCHEMA = {
  type: "object" as const,
  properties: {
    target: { type: "string", enum: ["simodont", "simtocare", "virteasy", "meta-quest", "powerpoint", "teaching-bundle"] },
    outputFormat: { type: "string", enum: ["stl", "obj", "glb", "ply"] },
    confirmation: { type: "boolean", description: "True only after the educator explicitly asks to download the export." },
  },
  required: ["target", "outputFormat", "confirmation"], additionalProperties: false,
};

const PUBLISH_SCHEMA = {
  type: "object" as const,
  properties: {
    confirmation: { type: "boolean", description: "True only after the educator explicitly approves public publishing." },
    noPatientInformationConfirmed: { type: "boolean", description: "True only after the educator confirms the project contains no identifiable patient information." },
  },
  required: ["confirmation", "noPatientInformationConfirmed"], additionalProperties: false,
};

export function EditorWebMcpTools(props: {
  projectId: string; title: string; hasModel: boolean; selectedCase: string | null;
  activePresetId: string | null; allowedPresetIds: string[]; availableCases: unknown[]; targetReady: boolean;
  previewReady: boolean; revisionPending: boolean; busy: boolean;
  choosePreset: (presetId: string) => void; openCaseSelector: () => void;
  openMaskTool: () => void; previewEdit: () => Promise<void>;
  createVariant: () => Promise<void>; openExport: () => void; openShare: () => void;
  applyCase: (templateId: string, clinicalParameters: Record<string, unknown>, promptRefinement?: string) => Promise<void>;
  markTarget: (region: { x: number; y: number; width: number; height: number }) => Promise<void>;
  saveProject: () => Promise<void>; resolveRevision: (decision: "accept" | "reject") => Promise<void>;
  exportModel: (target: string, outputFormat: string) => Promise<{ fileName: string }>;
  publishProject: () => Promise<{ communityUrl: string }>;
}) {
  const {
    projectId, title, hasModel, selectedCase, activePresetId, allowedPresetIds,
    targetReady, previewReady, revisionPending, busy, choosePreset,
    availableCases, openCaseSelector, openMaskTool, previewEdit, createVariant, openExport, openShare,
    applyCase, markTarget, saveProject, resolveRevision, exportModel, publishProject,
  } = props;
  return <>
    <WebMcpTool name="dentalsculptor_inspect_editor"
      description="Inspect the active dental project, editing readiness, teaching case, and deterministic edit presets."
      readOnly execute={() => webMcpResult(`Inspected ${title}.`, {
        projectId, title, modelReady: hasModel, selectedCase, activePresetId,
        availablePresetIds: allowedPresetIds, availableCases, targetMarked: targetReady,
        previewApproved: previewReady, revisionAwaitingEducatorReview: revisionPending, busy,
      })} />
    <WebMcpTool name="dentalsculptor_open_case_selector"
      description="Open the visual teaching-case selector for educator confirmation of the case and clinical parameters."
      enabled={hasModel && !busy} execute={() => {
        openCaseSelector();
        return webMcpResult("Teaching-case selection is open for educator confirmation.");
      }} />
    <WebMcpTool name="dentalsculptor_apply_teaching_case"
      description="Apply a teaching-case template and its structured clinical parameters to the active project. Use IDs and required fields returned by inspect_editor."
      inputSchema={CASE_SCHEMA} enabled={hasModel && !busy && !revisionPending}
      execute={async ({ templateId, clinicalParameters, promptRefinement }) => {
        await applyCase(String(templateId), (clinicalParameters ?? {}) as Record<string, unknown>, promptRefinement ? String(promptRefinement) : undefined);
        return webMcpResult(`Applied teaching case ${String(templateId)}.`, { templateId });
      }} />
    <WebMcpTool name="dentalsculptor_choose_edit_preset"
      description="Choose an available dental edit preset, synchronize its operation and semantic instruction, and open the marking tool."
      inputSchema={PRESET_SCHEMA} enabled={hasModel && !busy && !revisionPending}
      execute={({ presetId }) => {
        const id = String(presetId ?? "");
        if (!allowedPresetIds.includes(id)) throw new Error(`Choose one of: ${allowedPresetIds.join(", ")}.`);
        choosePreset(id); openMaskTool();
        return webMcpResult(`Selected ${id}. The educator can now mark the exact tooth region.`, { presetId: id });
      }} />
    <WebMcpTool name="dentalsculptor_open_target_tool"
      description="Open the visible mask tool so the educator can mark the exact anatomy to change."
      enabled={hasModel && !busy && !revisionPending} execute={() => {
        openMaskTool();
        return webMcpResult("The marking tool is active. Ask the educator to mark the intended anatomy.");
      }} />
    <WebMcpTool name="dentalsculptor_mark_target_region"
      description="Create a resolution-independent rectangular target on the current 3D viewport, equivalent to marking with the visible brush. Coordinates are normalized from 0 to 1 and must identify anatomy the educator has requested."
      inputSchema={TARGET_SCHEMA} enabled={hasModel && Boolean(activePresetId) && !busy && !revisionPending}
      execute={async ({ x, y, width, height }) => {
        const region = { x: Number(x), y: Number(y), width: Number(width), height: Number(height) };
        if (Object.values(region).some((value) => !Number.isFinite(value)) || region.x < 0 || region.y < 0 || region.width <= 0 || region.height <= 0 || region.x + region.width > 1 || region.y + region.height > 1) {
          throw new Error("Target coordinates must form a rectangle fully inside the normalized 0–1 viewport.");
        }
        await markTarget(region);
        return webMcpResult("The target region is marked on the visible 3D viewport. Inspect the editor before previewing.", region);
      }} />
    <WebMcpTool name="dentalsculptor_preview_edit"
      description="Create the 2D review preview for the selected preset and educator-marked target."
      enabled={hasModel && targetReady && Boolean(activePresetId) && !busy && !revisionPending}
      execute={async () => {
        if (!targetReady) throw new Error("The educator must mark a target first.");
        await previewEdit();
        return webMcpResult("The edit preview is open for educator review and approval.");
      }} />
    <WebMcpTool name="dentalsculptor_create_3d_variant"
      description="Create a reversible 3D teaching variant from an educator-approved preview; visible acceptance is still required."
      enabled={hasModel && previewReady && !busy && !revisionPending} execute={async () => {
        if (!previewReady) throw new Error("The educator must approve the 2D preview first.");
        await createVariant();
        return webMcpResult("The 3D variant is ready for visible educator acceptance or rejection.");
      }} />
    <WebMcpTool name="dentalsculptor_resolve_revision"
      description="Accept or reject the pending reversible 3D revision after the educator has reviewed it."
      inputSchema={REVISION_SCHEMA} enabled={revisionPending && !busy}
      execute={async ({ decision }) => {
        if (decision !== "accept" && decision !== "reject") throw new Error("Choose accept or reject.");
        await resolveRevision(decision);
        return webMcpResult(`The pending 3D revision was ${decision === "accept" ? "accepted" : "rejected"}.`, { decision });
      }} />
    <WebMcpTool name="dentalsculptor_save_project"
      description="Save the current DentalSculptor project title and accepted authoring state."
      enabled={!busy && !revisionPending} execute={async () => {
        await saveProject(); return webMcpResult("The DentalSculptor project is saved.");
      }} />
    <WebMcpTool name="dentalsculptor_open_export"
      description="Open export options for the accepted model; the educator confirms format and destination."
      enabled={hasModel && !busy && !revisionPending} execute={() => {
        openExport(); return webMcpResult("Export options are open for educator confirmation.");
      }} />
    <WebMcpTool name="dentalsculptor_export_model"
      description="Validate, convert, and download the active model for a supported simulator or presentation target. Requires explicit educator confirmation."
      inputSchema={EXPORT_SCHEMA} enabled={hasModel && !busy && !revisionPending}
      execute={async ({ target, outputFormat, confirmation }) => {
        if (confirmation !== true) throw new Error("Ask the educator to confirm the download first.");
        const result = await exportModel(String(target), String(outputFormat));
        return webMcpResult(`Exported and downloaded ${result.fileName}.`, { ...result, target, outputFormat });
      }} />
    <WebMcpTool name="dentalsculptor_open_share"
      description="Open publishing and sharing controls without publishing automatically."
      enabled={hasModel && !busy && !revisionPending} execute={() => {
        openShare(); return webMcpResult("Sharing controls are open for educator confirmation.");
      }} />
    <WebMcpTool name="dentalsculptor_publish_project"
      description="Publish the active model to the DentalSculptor community and return its shareable link. Requires explicit public-release and patient-privacy confirmation."
      inputSchema={PUBLISH_SCHEMA} enabled={hasModel && !busy && !revisionPending}
      execute={async ({ confirmation, noPatientInformationConfirmed }) => {
        if (confirmation !== true || noPatientInformationConfirmed !== true) throw new Error("Publishing requires explicit educator approval and confirmation that no identifiable patient information is present.");
        const result = await publishProject();
        return webMcpResult(`Published successfully. Shareable project: ${result.communityUrl}`, result);
      }} />
  </>;
}
