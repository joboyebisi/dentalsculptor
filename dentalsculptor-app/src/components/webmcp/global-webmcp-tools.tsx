"use client";

import { usePathname, useRouter } from "next/navigation";
import { useSearchParams } from "next/navigation";
import { WebMcpTool, webMcpResult } from "@/components/webmcp/webmcp-tool";
import { useSupabaseAuth } from "@/hooks/use-supabase-auth";
import { INVITE_QUERY_PARAM, resolveInviteCode } from "@/lib/research-invite";

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

const AUTH_LINK_SCHEMA = {
  type: "object" as const,
  properties: {
    mode: {
      type: "string",
      enum: ["sign_in", "register"],
      description: "Whether the educator wants to sign in or create an account.",
    },
    destination: {
      type: "string",
      enum: ["current", "dashboard", "new_project", "community"],
      description: "The safe DentalSculptor page to return to after authentication.",
    },
  },
  required: ["mode", "destination"],
  additionalProperties: false,
};

const AUTH_DESTINATIONS = {
  dashboard: "/dashboard",
  new_project: "/projects/new",
  community: "/community",
} as const;

function currentSafePath(pathname: string) {
  if (!pathname.startsWith("/") || pathname.startsWith("//")) return "/dashboard";
  if (pathname === "/sign-in" || pathname === "/sign-up") return "/dashboard";
  return pathname;
}

function buildAuthUrl(mode: unknown, destination: unknown, pathname: string) {
  const selectedDestination = destination as keyof typeof AUTH_DESTINATIONS | "current";
  const returnPath = selectedDestination === "current"
    ? currentSafePath(pathname)
    : AUTH_DESTINATIONS[selectedDestination];
  if (!returnPath) throw new Error("Choose current, dashboard, new_project, or community.");
  const authPath = mode === "register" ? "/sign-up" : mode === "sign_in" ? "/sign-in" : null;
  if (!authPath) throw new Error("Choose sign_in or register.");
  const url = new URL(authPath, window.location.origin);
  url.searchParams.set("redirect_url", returnPath);
  return { authenticationUrl: url.toString(), returnPath, authPath };
}

export function GlobalWebMcpTools() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { isSignedIn, loading: authLoading } = useSupabaseAuth();
  const hasInvite = Boolean(resolveInviteCode(searchParams.get(INVITE_QUERY_PARAM)));

  return (
    <>
      <WebMcpTool
        name="dentalsculptor_inspect_app"
        description="Inspect the current DentalSculptor page and learn the supported human-and-agent workflow before choosing an action."
        readOnly
        execute={() =>
          webMcpResult("DentalSculptor is ready for collaborative dental 3D authoring.", {
            currentPath: pathname,
            authentication: authLoading ? "checking" : isSignedIn ? "signed_in" : hasInvite ? "invited_guest" : "signed_out",
            inviteCapabilities: hasInvite && !isSignedIn ? ["import image", "generate 3D", "download generated model"] : [],
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
        name="dentalsculptor_inspect_auth"
        description="Check whether the educator is signed in to DentalSculptor. This never returns credentials, cookies, access tokens, or personal profile data."
        readOnly
        execute={() =>
          webMcpResult(
            authLoading
              ? "DentalSculptor is still checking the browser session. Try again shortly."
              : isSignedIn
                ? "The educator is signed in to DentalSculptor."
                : hasInvite
                  ? "An educator invite is active. The guest can import an image, generate 3D, and download it without signing in. Sign-in is optional unless they want saved projects, editing, or publishing."
                : "The educator is not signed in. Request a secure authentication link before using a protected workspace.",
            { status: authLoading ? "checking" : isSignedIn ? "signed_in" : hasInvite ? "invited_guest" : "signed_out", inviteAllowsGenerationAndDownload: hasInvite }
          )
        }
      />
      <WebMcpTool
        name="dentalsculptor_get_auth_link"
        description="Create a secure DentalSculptor sign-in or registration link for the educator to click in chat. Authentication happens visibly in the browser; credentials and tokens never pass through the agent."
        inputSchema={AUTH_LINK_SCHEMA}
        readOnly
        enabled={!authLoading && !isSignedIn}
        execute={({ mode, destination }) => {
          const { authenticationUrl, returnPath } = buildAuthUrl(mode, destination, pathname);
          return webMcpResult(
            `Open this DentalSculptor ${mode === "register" ? "registration" : "sign-in"} link in the browser: ${authenticationUrl}\n\nAfter authentication, return to this chat and ask me to check your DentalSculptor sign-in status.`,
            {
              authenticationUrl,
              mode,
              returnPath,
              status: "user_action_required",
              securityNote: "Enter credentials only on the DentalSculptor or configured identity-provider page.",
            }
          );
        }}
      />
      <WebMcpTool
        name="dentalsculptor_open_auth"
        description="Open DentalSculptor's visible sign-in or registration page in the current browser tab. Use when the chat client does not make a returned URL clickable."
        inputSchema={AUTH_LINK_SCHEMA}
        execute={({ mode, destination }) => {
          const { authenticationUrl, returnPath } = buildAuthUrl(mode, destination, pathname);
          window.location.assign(authenticationUrl);
          return webMcpResult("Opened DentalSculptor authentication in the browser. The educator must complete it visibly; use email sign-in if an OAuth provider blocks embedded browsers.", { authenticationUrl, returnPath, status: "user_action_required" });
        }}
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
