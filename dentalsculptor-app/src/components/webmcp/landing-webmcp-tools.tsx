"use client";

import type { PendingNextStep } from "@/lib/landing-session";
import { WebMcpTool, webMcpResult } from "@/components/webmcp/webmcp-tool";

const CONTINUE_SCHEMA = {
  type: "object" as const,
  properties: {
    nextStep: {
      type: "string",
      enum: ["download", "publish", "case-wizard", "free-editor"],
      description: "What the educator wants to do with the generated model.",
    },
  },
  required: ["nextStep"],
  additionalProperties: false,
};

export function LandingWebMcpTools({
  hasSourceImage,
  hasModel,
  busy,
  generate,
  continueWithModel,
}: {
  hasSourceImage: boolean;
  hasModel: boolean;
  busy: boolean;
  generate: () => Promise<void>;
  continueWithModel: (nextStep: PendingNextStep) => Promise<void>;
}) {
  return (
    <>
      <WebMcpTool
        name="dentalsculptor_inspect_generation"
        description="Inspect whether the educator has selected a source image and whether a generated 3D model is ready."
        readOnly
        execute={() =>
          webMcpResult(hasModel ? "A generated 3D model is ready." : "No generated 3D model is ready yet.", {
            sourceImageSelected: hasSourceImage,
            modelReady: hasModel,
            busy,
          })
        }
      />
      <WebMcpTool
        name="dentalsculptor_generate_3d"
        description="Generate a 3D dental model from the source image already selected by the educator in this browser tab."
        enabled={hasSourceImage && !hasModel && !busy}
        execute={async () => {
          if (!hasSourceImage) throw new Error("Ask the educator to select a dental image first.");
          if (busy) throw new Error("DentalSculptor is already working. Wait for the current operation.");
          await generate();
          return webMcpResult("3D generation finished. Inspect generation before choosing the next workflow.");
        }}
      />
      <WebMcpTool
        name="dentalsculptor_continue_with_model"
        description="Continue with a ready 3D model by opening download, publishing, guided teaching-case creation, or the free editor. Authentication and onboarding remain enforced by DentalSculptor."
        inputSchema={CONTINUE_SCHEMA}
        enabled={hasModel && !busy}
        execute={async ({ nextStep }) => {
          if (!hasModel) throw new Error("Generate a 3D model before continuing.");
          const allowed = ["download", "publish", "case-wizard", "free-editor"];
          if (!allowed.includes(String(nextStep))) throw new Error("Choose a supported nextStep.");
          await continueWithModel(nextStep as PendingNextStep);
          return webMcpResult(`Opened the ${String(nextStep)} workflow.`, { nextStep });
        }}
      />
    </>
  );
}
