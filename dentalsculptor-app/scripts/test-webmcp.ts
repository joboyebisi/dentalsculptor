import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const root = resolve(import.meta.dirname, "..");
const files = [
  "src/components/webmcp/webmcp-tool.tsx",
  "src/components/webmcp/global-webmcp-tools.tsx",
  "src/components/webmcp/landing-webmcp-tools.tsx",
  "src/components/landing/landing-model-panel.tsx",
  "src/components/webmcp/editor-webmcp-tools.tsx",
  "src/components/editor/share-project-dialog.tsx",
  "src/components/community/community-actions.tsx",
];
const source = files.map((file) => readFileSync(resolve(root, file), "utf8")).join("\n");
const names = [...source.matchAll(/name="(dentalsculptor_[a-z0-9_]+)"/g)].map((match) => match[1]);
const required = [
  "dentalsculptor_inspect_app",
  "dentalsculptor_inspect_auth",
  "dentalsculptor_get_auth_link",
  "dentalsculptor_open_auth",
  "dentalsculptor_inspect_generation",
  "dentalsculptor_import_source_image",
  "dentalsculptor_list_image_library",
  "dentalsculptor_select_library_image",
  "dentalsculptor_generate_3d",
  "dentalsculptor_continue_with_model",
  "dentalsculptor_inspect_editor",
  "dentalsculptor_apply_teaching_case",
  "dentalsculptor_choose_edit_preset",
  "dentalsculptor_open_target_tool",
  "dentalsculptor_mark_target_region",
  "dentalsculptor_preview_edit",
  "dentalsculptor_create_3d_variant",
  "dentalsculptor_resolve_revision",
  "dentalsculptor_save_project",
  "dentalsculptor_open_export",
  "dentalsculptor_export_model",
  "dentalsculptor_open_share",
  "dentalsculptor_publish_project",
  "dentalsculptor_confirm_publish",
  "dentalsculptor_inspect_published_model",
  "dentalsculptor_download_published_model",
];

assert(names.length === new Set(names).size, "WebMCP tool names must be globally unique on a page.");
for (const name of required) assert(names.includes(name), `Missing required WebMCP tool: ${name}`);
assert(source.includes("readOnlyHint"), "Read-only tools must advertise readOnlyHint.");
assert(source.includes("enabled={"), "Page tools must feature-detect prerequisites through enabled state.");
assert(source.includes("user_action_required"), "Authentication must return a user-clickable handoff rather than credentials.");
assert(source.includes("redirect_url"), "Authentication links must preserve a safe post-auth destination.");
assert(source.includes("noPatientInformationConfirmed"), "Publishing must require an explicit privacy confirmation.");
assert(source.includes("confirmation !== true"), "External release actions must require confirmation.");
assert(source.includes("invited_guest"), "WebMCP authentication inspection must distinguish invited guests.");
assert(source.includes("hasInvite && nextStep === \"download\""), "Invited guests must be able to download without project authentication.");
assert(!/TRELLIS|Nano3D|MODAL_|AWS_|SUPABASE_/i.test(source), "WebMCP surface must not expose infrastructure or secrets.");

const layout = readFileSync(resolve(root, "src/app/layout.tsx"), "utf8");
const landing = readFileSync(resolve(root, "src/components/landing/landing-model-panel.tsx"), "utf8");
const editor = readFileSync(resolve(root, "src/components/editor/editor-workspace.tsx"), "utf8");
assert(layout.includes("<GlobalWebMcpTools"), "Global WebMCP tools are not mounted.");
assert(landing.includes("<LandingWebMcpTools"), "Landing WebMCP tools are not mounted.");
assert(editor.includes("<EditorWebMcpTools"), "Editor WebMCP tools are not mounted.");

console.log(`Validated ${names.length} DentalSculptor WebMCP tools and page-scoped mounts.`);
