"use client";

import { usePathname, useRouter } from "next/navigation";
import { WebMcpTool, webMcpResult } from "@/components/webmcp/webmcp-tool";

const NAVIGATION_SCHEMA = {
  type: "object" as const,
  properties: {
    destination: {
      type: "string",
      enum: ["home", "dashboard", "new_project", "community"],
      description: "The DentalSculptor workspace to open.",
    },
  },
  required: ["destination"],
  additionalProperties: false,
};

const DESTINATIONS = {
  home: "/",
  dashboard: "/dashboard",
  new_project: "/projects/new",
  community: "/community",
} as const;

export function GlobalWebMcpTools() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <>
      <WebMcpTool
        name="dentalsculptor_inspect_app"
        description="Inspect the current DentalSculptor page and learn the supported human-and-agent workflow before choosing an action."
        readOnly
        execute={() =>
          webMcpResult("DentalSculptor is ready for collaborative dental 3D authoring.", {
            currentPath: pathname,
            workflows: [
              "generate a 3D tooth from an educator-selected image",
              "create a guided teaching case",
              "make a mask-local edit in the free editor",
              "review and accept a reversible 3D variant",
              "publish, share, or export a model",
            ],
            note: "Page-specific tools appear only when the relevant workspace and prerequisites are available.",
          })
        }
      />
      <WebMcpTool
        name="dentalsculptor_open_workspace"
        description="Open a DentalSculptor workspace. Use this for navigation; it does not create, edit, publish, or delete data."
        inputSchema={NAVIGATION_SCHEMA}
        execute={({ destination }) => {
          const path = DESTINATIONS[destination as keyof typeof DESTINATIONS];
          if (!path) throw new Error("Choose home, dashboard, new_project, or community.");
          router.push(path);
          return webMcpResult(`Opened ${destination}.`, { path });
        }}
      />
    </>
  );
}
