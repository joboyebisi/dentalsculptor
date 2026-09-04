# DentalSculptor — WebMCP Challenge submission pack

## Submission links

- Live application: <https://dentalsculptor.vercel.app>
- Public source: <https://github.com/joboyebisi/dentalsculptor>
- License: MIT (`LICENSE` at the repository root)

## Short description

DentalSculptor is a browser-based 3D teaching-case studio for dental educators.
An educator selects a tooth image and works in a visible 3D workspace while an
agent uses WebMCP tools to inspect readiness, generate a model, configure a
clinical case, coordinate a localized edit, and prepare the result for sharing
or simulator export. The agent operates the same project and scene the educator
is watching rather than guessing at screen coordinates.

## Why this is a strong WebMCP use case

Dental case authoring combines long-running generation, spatial decisions,
clinical presets, reversible revisions, and several export targets. Pure UI
automation is brittle, while a fully autonomous workflow would hide clinically
important choices. WebMCP gives the agent structured state and safe actions;
the viewport gives the educator continuous visual control. Together they can
produce a reusable case without forcing the educator to understand the
underlying 3D pipeline or surrender approval of anatomical changes.

## What people and agents do together

The agent can:

- inspect the current generation or editor state;
- start generation after the educator has selected an image;
- route the result to download, publishing, a guided teaching case, or Free Editor;
- select and synchronize a case preset;
- open the correct marking control and explain what input is still required;
- request the 2D preview and create a reversible 3D variant when prerequisites are met;
- open export and sharing workflows;
- inspect, like, share, or download a published model when those actions are available.

The educator remains responsible for selecting source material, marking the
anatomical target, approving the preview/revision, publishing, and choosing the
final simulator/export configuration.

## Implementation

The React application registers 19 page-scoped tools through the Chrome Labs
`use-webmcp-tool` package. The package drives the browser's
`document.modelContext.registerTool(...)` API and unregisters tools when their
React surface unmounts. Each tool has a JSON input schema, concise clinical
description, availability derived from live page state, and an abort-aware
handler. The adapter is isolated under
`dentalsculptor-app/src/components/webmcp/`; it does not replace existing APIs,
authentication, storage, generation, editing, or UI behavior.

For protected actions, the agent first inspects authentication state. When the
educator is signed out, it can return a clickable, same-origin sign-in or
registration URL with a validated post-auth destination. The educator completes
authentication visibly in the browser and then asks the agent to re-check the
session. Passwords, OAuth credentials, cookies, and access tokens are never
returned through WebMCP.

## Under-three-minute demo outline

**0:00–0:15 — outcome first.** Show the original tooth image, finished 3D model,
one fracture teaching variant, and export panel. Say: “DentalSculptor lets an
educator and an agent turn a tooth image into an editable, simulator-ready 3D
teaching case in one browser workspace.”

**0:15–0:45 — structured inspection and generation.** In ChatGPT's in-app
browser, ask the agent to inspect the app. Select an image visibly, then ask it
to generate the model. Explain that WebMCP exposes state and actions directly,
without screen-coordinate guessing.

**0:45–1:25 — human-agent case authoring.** Ask the agent to continue with a
cusp-fracture case and choose the fracture preset. Let it open the target tool.
Draw the target on the tooth yourself and request a preview. Emphasize that the
agent coordinates the workflow while the educator owns the spatial and clinical
decision.

**1:25–1:55 — reversible result.** Approve the preview, create the 3D variant,
and compare it with the master in revision history. Show that the resulting mesh,
not merely the preview overlay, contains the edit.

**1:55–2:25 — reuse.** Open export, briefly show a simulator-ready selection,
then show the public sharing flow. Mention that browsers without WebMCP still
receive the full conventional UI.

**2:25–2:45 — close.** “WebMCP makes the agent precise and the workflow faster,
while the educator stays visibly in control of anatomy, approval, and release.”

## Release and submission checklist

- [x] Production application is deployed over HTTPS.
- [x] WebMCP tools are additive and page-scoped.
- [x] Tool discovery and a read-only tool call were verified in ChatGPT's in-app browser.
- [x] Unsupported-browser behavior, workflow contracts, and production build pass locally.
- [x] Repository is public.
- [x] MIT license is present and linked from the README.
- [ ] Merge the WebMCP branch into the public default branch.
- [ ] Verify the deployed URL in Chrome with `chrome://flags/#enable-webmcp-testing`.
- [ ] Record and publish the narrated demo (less than three minutes).
- [ ] Add the video URL and final screenshots to the Devpost entry.
- [ ] Confirm every teammate has accepted the Devpost project invitation.
- [ ] Submit the entry (not merely save it as a draft) before the deadline.

## Local verification

```powershell
cd dentalsculptor-app
npm install
npm run test:webmcp
npm run test:case-workflows
npm run build
```

The application requires the environment variables documented in
`dentalsculptor-app/.env.example`; production secrets are not stored in source.
