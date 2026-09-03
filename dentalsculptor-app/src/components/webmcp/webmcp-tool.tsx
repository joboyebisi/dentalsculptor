"use client";

import { useWebMCP } from "use-webmcp-tool";

type JsonSchema = {
  type: "object";
  properties?: Record<string, unknown>;
  required?: string[];
  additionalProperties?: boolean;
};

export type DentalSculptorWebMcpTool = {
  name: string;
  description: string;
  inputSchema?: JsonSchema;
  readOnly?: boolean;
  enabled?: boolean;
  execute: (input: Record<string, unknown>) => unknown | Promise<unknown>;
};

/** Registers one page-scoped WebMCP tool and renders no additional UI. */
export function WebMcpTool({
  name,
  description,
  inputSchema,
  readOnly = false,
  enabled = true,
  execute,
}: DentalSculptorWebMcpTool) {
  useWebMCP({
    name,
    description,
    inputSchema,
    annotations: { readOnlyHint: readOnly, untrustedContentHint: false },
    execute,
    enabled,
  });
  return null;
}

export function webMcpResult(message: string, data?: Record<string, unknown>) {
  return {
    content: [{ type: "text" as const, text: message }],
    ...(data ? { structuredContent: data } : {}),
  };
}
