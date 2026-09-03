"use client";

import { WebMcpTool, webMcpResult } from "@/components/webmcp/webmcp-tool";

const PRESET_SCHEMA = {
  type: "object" as const,
  properties: { presetId: { type: "string", description: "A preset ID returned by dentalsculptor_inspect_editor." } },
  required: ["presetId"],
  additionalProperties: false,
};

export function EditorWebMcpTools(props: {
  projectId: string; title: string; hasModel: boolean; selectedCase: string | null;
  activePresetId: string | null; allowedPresetIds: string[]; targetReady: boolean;
  previewReady: boolean; revisionPending: boolean; busy: boolean;
  choosePreset: (presetId: string) => void; openCaseSelector: () => void;
  openMaskTool: () => void; previewEdit: () => Promise<void>;
  createVariant: () => Promise<void>; openExport: () => void; openShare: () => void;
}) {
  const {
    projectId, title, hasModel, selectedCase, activePresetId, allowedPresetIds,
    targetReady, previewReady, revisionPending, busy, choosePreset,
    openCaseSelector, openMaskTool, previewEdit, createVariant, openExport, openShare,
  } = props;
  return <>
    <WebMcpTool name="dentalsculptor_inspect_editor"
      description="Inspect the active dental project, editing readiness, teaching case, and deterministic edit presets."
      readOnly execute={() => webMcpResult(`Inspected ${title}.`, {
        projectId, title, modelReady: hasModel, selectedCase, activePresetId,
        availablePresetIds: allowedPresetIds, targetMarked: targetReady,
        previewApproved: previewReady, revisionAwaitingEducatorReview: revisionPending, busy,
      })} />
    <WebMcpTool name="dentalsculptor_open_case_selector"
      description="Open the visual teaching-case selector for educator confirmation of the case and clinical parameters."
      enabled={hasModel && !busy} execute={() => {
        openCaseSelector();
        return webMcpResult("Teaching-case selection is open for educator confirmation.");
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
    <WebMcpTool name="dentalsculptor_open_export"
      description="Open export options for the accepted model; the educator confirms format and destination."
      enabled={hasModel && !busy && !revisionPending} execute={() => {
        openExport(); return webMcpResult("Export options are open for educator confirmation.");
      }} />
    <WebMcpTool name="dentalsculptor_open_share"
      description="Open publishing and sharing controls without publishing automatically."
      enabled={hasModel && !busy && !revisionPending} execute={() => {
        openShare(); return webMcpResult("Sharing controls are open for educator confirmation.");
      }} />
  </>;
}
