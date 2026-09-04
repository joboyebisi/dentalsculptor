# DentalSculptor WebMCP implementation

## Design contract

WebMCP is an additive, client-side adapter over the existing application. It
does not replace DentalSculptor's UI, APIs, authentication, storage, generation
workers, editing workers or deployment model. When `document.modelContext` is
absent, registration is a no-op and the application behaves exactly as before.

Tools are registered only while their matching page is mounted. `AbortSignal`
cleanup is handled by Chrome Labs' `use-webmcp-tool` package. Page state controls
the `enabled` flag, so an agent cannot discover Create Variant before a marked
target and approved preview exist.

The hook is a React lifecycle adapter for the browser API illustrated by the
WebMCP specification:

```javascript
document.modelContext.registerTool({
  name: "dentalsculptor_inspect_app",
  description: "Inspect the current DentalSculptor workspace and available next steps.",
  inputSchema: { type: "object", properties: {}, additionalProperties: false },
  execute: async () => ({ content: [{ type: "text", text: "..." }] }),
});
```

The production implementation uses typed React wrappers rather than registering
this sample directly, preventing duplicate registrations across route changes.

## Human-agent boundary

Agents can inspect state, navigate, start generation from an image the educator
already selected, synchronize an edit preset, open the visible marking tool,
request previews/variants, and open export/share controls. The educator retains
visible control of local anatomy marking, clinical parameters, preview approval,
revision acceptance/rejection, publishing and final export configuration.

No model-provider names, infrastructure configuration, credentials, storage
keys or secrets are returned through WebMCP.

## Tool surfaces

- Global: inspect app/authentication, return a clickable sign-in or registration
  handoff, and open a workspace.
- Landing generation: inspect readiness, generate 3D, continue to download,
  publish, teaching-case creation or Free Editor.
- Editor: inspect state, open case selection, choose a synchronized preset, open
  the target tool, preview an edit, create a reversible variant, and open
  export/share controls.
- Published project: inspect public state, retrieve its share link, toggle a
  like, and download the validated model asset.

## Verification

```powershell
cd dentalsculptor-app
npm run test:webmcp
npm run test:case-workflows
npm run build
```

Browser verification:

1. Deploy to HTTPS.
2. Open the site in ChatGPT's in-app browser; or use a compatible Chromium build
   with `chrome://flags/#enable-webmcp-testing` enabled.
3. On the landing page, verify the agent sees global and generation tools.
4. When signed out, invoke `dentalsculptor_get_auth_link`, click the returned
   URL, authenticate visibly, and invoke `dentalsculptor_inspect_auth` after the
   browser returns to DentalSculptor. Credentials and session tokens must never
   appear in the tool result or chat.
5. Select an image manually and invoke `dentalsculptor_generate_3d`.
6. Continue to a teaching case or Free Editor.
7. Verify editor tools appear/disappear as target, preview and revision state
   changes.
8. Confirm ordinary Chrome with WebMCP unavailable retains the existing UI and
   workflows with no console or rendering failure.

WebMCP remains an early-preview API. Keep the wrapper isolated under
`src/components/webmcp/` and update only that adapter if the specification
changes.

## Repository and hosting decision

Keep the WebMCP adapter in the same repository and deployment as DentalSculptor.
The tools need the production page's live React state, authenticated project,
3D viewport, and revision history. The challenge accepts Vercel-hosted apps, and
ChatGPT's in-app browser can open the same HTTPS deployment. ChatGPT Sites is an
alternative host, not an additional runtime that a Vercel submission must use.
A separate public mirror is appropriate only if the main repository cannot be
public; it must not become a forked second implementation.
