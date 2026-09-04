"use client";

import type { PendingNextStep } from "@/lib/landing-session";
import type { GenerationOutcome } from "@/context/landing-model-context";
import type { DentalViewerLoadState } from "@/components/three/dental-viewer";
import { WebMcpTool, webMcpResult } from "@/components/webmcp/webmcp-tool";

const CONTINUE_SCHEMA = {
  type: "object" as const,
  properties: {
    nextStep: {
      type: "string",
      enum: ["download", "publish", "case-wizard", "editor"],
      description: "What the educator wants to do with the generated model.",
    },
  },
  required: ["nextStep"],
  additionalProperties: false,
};

const IMAGE_SCHEMA = {
  type: "object" as const,
  properties: {
    imageUrl: {
      type: "string",
      description: "An HTTPS or data:image URL for a PNG or JPEG containing one tooth.",
    },
    fileName: {
      type: "string",
      description: "A short PNG or JPG filename used inside DentalSculptor.",
    },
  },
  required: ["imageUrl", "fileName"],
  additionalProperties: false,
};

const LIBRARY_SCHEMA = {
  type: "object" as const,
  properties: { libraryId: { type: "string", description: "An image ID returned by dentalsculptor_list_image_library." } },
  required: ["libraryId"], additionalProperties: false,
};

export function LandingWebMcpTools({
  hasSourceImage,
  hasModel,
  viewerState,
  busy,
  importImage,
  listLibrary,
  selectLibraryImage,
  generate,
  continueWithModel,
}: {
  hasSourceImage: boolean;
  hasModel: boolean;
  viewerState: DentalViewerLoadState | "idle";
  busy: boolean;
  importImage: (imageUrl: string, fileName: string) => Promise<void>;
  listLibrary: () => Promise<unknown[]>;
  selectLibraryImage: (libraryId: string) => Promise<{ id: string; title: string }>;
  generate: () => Promise<GenerationOutcome>;
  continueWithModel: (nextStep: PendingNextStep) => Promise<void>;
}) {
  return (
    <>
      <WebMcpTool
        name="dentalsculptor_inspect_generation"
        description="Inspect whether the educator has selected a source image and whether a generated 3D model is ready."
        readOnly
        execute={() =>
          webMcpResult(
            viewerState === "ready"
              ? "A generated 3D model is loaded and visible."
              : hasModel
                ? `A model was generated, but the viewer is ${viewerState}.`
                : "No generated 3D model is ready yet.",
            {
            sourceImageSelected: hasSourceImage,
            modelGenerated: hasModel,
            modelReady: hasModel && viewerState === "ready",
            viewerState,
            busy,
            }
          )
        }
      />
      <WebMcpTool
        name="dentalsculptor_list_image_library"
        description="List DentalSculptor's curated single-tooth teaching images that can be selected for generation."
        readOnly enabled={!busy}
        execute={async () => {
          const items = await listLibrary();
          return webMcpResult(`Found ${items.length} curated dental images.`, { items });
        }}
      />
      <WebMcpTool
        name="dentalsculptor_select_library_image"
        description="Select a curated DentalSculptor image by its library ID and attach it visibly as the generation source."
        inputSchema={LIBRARY_SCHEMA} enabled={!busy}
        execute={async ({ libraryId }) => {
          const item = await selectLibraryImage(String(libraryId ?? ""));
          return webMcpResult(`Selected library image: ${item.title}.`, item);
        }}
      />
      <WebMcpTool
        name="dentalsculptor_import_source_image"
        description="Attach a single-tooth PNG or JPEG from an HTTPS or data:image URL to the visible generation workspace. Remote servers must permit browser access."
        inputSchema={IMAGE_SCHEMA}
        enabled={!busy}
        execute={async ({ imageUrl, fileName }) => {
          await importImage(String(imageUrl ?? ""), String(fileName ?? ""));
          return webMcpResult("The source image is attached and visible. Inspect generation readiness before generating.", { fileName });
        }}
      />
      <WebMcpTool
        name="dentalsculptor_generate_3d"
        description="Generate a 3D dental model from the source image already selected by the educator in this browser tab."
        enabled={hasSourceImage && !hasModel && !busy}
        execute={async () => {
          if (!hasSourceImage) throw new Error("Ask the educator to select a dental image first.");
          if (busy) throw new Error("DentalSculptor is already working. Wait for the current operation.");
          const outcome = await generate();
          if (!outcome.ok) throw new Error(outcome.error);
          return webMcpResult(
            "3D generation finished and the model is loading in the visible DentalSculptor viewer.",
            { modelGenerated: true, modelReady: false, viewerState: "loading", format: outcome.format, source: outcome.source }
          );
        }}
      />
      <WebMcpTool
        name="dentalsculptor_continue_with_model"
        description="Continue with a ready 3D model. An active educator invite permits direct model download without sign-in; saved projects, publishing, guided cases, and Free Editor require authentication and onboarding."
        inputSchema={CONTINUE_SCHEMA}
        enabled={hasModel && viewerState === "ready" && !busy}
        execute={async ({ nextStep }) => {
          if (!hasModel) throw new Error("Generate a 3D model before continuing.");
          if (viewerState !== "ready") {
            throw new Error(`Wait for the generated model to become visible; viewer state is ${viewerState}.`);
          }
          const allowed: PendingNextStep[] = ["download", "publish", "case-wizard", "editor"];
          const requested = String(nextStep);
          if (!allowed.some((step) => step === requested)) throw new Error("Choose a supported nextStep.");
          await continueWithModel(requested as PendingNextStep);
          return webMcpResult(`Opened the ${requested} workflow.`, { nextStep: requested });
        }}
      />
    </>
  );
}
