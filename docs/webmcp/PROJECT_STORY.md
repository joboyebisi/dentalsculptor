# DentalSculptor — WebMCP Challenge project story

## Inspiration

Dental educators often need custom 3D examples: a fractured cusp for one seminar, an occlusal
lesion for another, or a preparation that matches a particular learning objective. Creating those
assets usually means learning specialist modelling software, waiting for technical support, or
settling for a generic model that does not fit the lesson.

DentalSculptor began as doctoral research into educator agency and human–AI co-creation in dental
education. The central question was not simply, “Can AI generate a tooth?” It was, “Can an
educator remain the author while AI handles the technical complexity?”

WebMCP made a new answer possible. Instead of asking an agent to guess its way through buttons,
loading states, and a spatial 3D editor, DentalSculptor gives the agent a precise vocabulary for
the real workflow. The agent can coordinate; the educator can keep ownership of anatomy,
pedagogy, approval, and release.

## What it does

DentalSculptor turns a dental image into an editable 3D teaching case in one visible browser
workspace.

An educator and an agent can work together to:

1. inspect the current app, authentication, generation, and viewer state;
2. choose a curated tooth image or attach an educator-provided image;
3. start 3D generation and wait until the model is actually visible;
4. continue into a guided clinical case or the Free Editor;
5. synchronize the correct edit preset and mark the intended anatomy;
6. generate a 2D review preview and a reversible 3D variant;
7. accept or reject the revision;
8. export for supported teaching/simulation targets or publish with explicit privacy approval.

The result is not an agent-only back channel. Every tool acts on the same project, React state,
3D scene, revision history, and approval controls the educator sees.

## Why WebMCP is essential

Without WebMCP, an agent has to infer whether generation finished, whether a model is visible,
which clinical preset is compatible, whether a mask exists, or whether the educator approved the
result. Coordinate-based browser automation is especially fragile in a resizable 3D viewport.

With WebMCP:

- tool schemas replace screen-coordinate guessing;
- live readiness state prevents premature actions;
- page-scoped discovery reveals only actions relevant to the current workspace;
- structured results tell the agent what happened and what remains;
- human approval boundaries are encoded into the workflow rather than left to prompting.

This improves speed and reliability without making the clinical workflow less accountable.

## The human–agent partnership

The agent is good at orchestration: inspecting state, explaining prerequisites, selecting a
compatible workflow, keeping a multi-stage process on track, and preparing reuse.

The educator is responsible for judgment: selecting source material, defining clinical intent,
marking the exact anatomy, approving previews, accepting revisions, confirming privacy, and
authorizing publication or download.

That division is the project’s core contribution. WebMCP does not remove the person from the
creative loop; it gives them a more capable collaborator.

## How we built it

The production application uses Next.js 16, React 19, TypeScript, Three.js, React Three Fiber,
Supabase Auth/PostgreSQL/Storage, Prisma, Modal GPU services, and Vercel.

The WebMCP adapter is isolated in `dentalsculptor-app/src/components/webmcp/`. Google Chrome
Labs' lifecycle hook registers tools through `document.modelContext.registerTool(...)` and
unregisters them when their React surface disappears.

The tools are organized by page:

- global app/authentication/navigation tools;
- image-to-3D generation tools;
- clinical case and editor tools;
- confirmed publishing tools in the visible share dialog;
- public community inspection and reuse tools.

Every mutating tool has a constrained JSON Schema. Read-only tools advertise `readOnlyHint`.
Model-dependent tools wait for the viewer—not merely a model URL—to report that geometry is
visible. Publishing requires both explicit release approval and confirmation that the model
contains no identifiable patient information.

## Challenges we faced

### Making 3D readiness truthful

A generation API can return a URL before an embedded browser has downloaded, parsed, framed, and
rendered the model. We added viewer-level readiness, bounded same-origin asset loading, actionable
proxy errors, and a load watchdog. WebMCP reports `modelReady` only after the viewer confirms the
model is visible.

### Keeping tools synchronized with a changing interface

The landing page, editor, share dialog, and community page expose different capabilities.
Page-scoped React registration lets the available tool set follow the visible UI and unregister
cleanly during navigation.

### Preserving educator authority

The fastest implementation would have let the agent mark anatomy, approve an edit, and publish
in one opaque step. We deliberately separated those moments. The agent can prepare the next
action, but spatial targeting, revision decisions, privacy confirmation, and release remain
visible and reversible.

### Working with an emerging standard

WebMCP is still evolving. We kept the browser adapter isolated, documented the imperative API,
added a live diagnostics page, and retained a complete non-WebMCP interface as a fallback.

## Accomplishments

- 29 non-duplicated, page-scoped WebMCP tools spanning a real 3D authoring workflow.
- A model-readiness contract based on rendered geometry rather than optimistic API completion.
- Structured clinical case authoring with reversible human approval.
- Secure authentication handoff without exposing credentials, cookies, or tokens.
- Explicit confirmation gates for export, publishing, and patient privacy.
- A public diagnostic route that reads the browser’s real tool registry.

## What we learned

The most valuable agent tools are not one-to-one copies of buttons. They expose the state
transitions and safety boundaries that make a complex application understandable. We also learned
that “human in the loop” is strongest when the loop is visible in the product architecture:
the educator and agent should share one workspace and one source of truth.

## What is next

We plan to evaluate how educators divide work with agents across different levels of experience,
add richer model-semantic targeting, and contribute practical feedback from spatial authoring to
the emerging WebMCP standard.

## Built with

WebMCP, OpenAI ChatGPT in-app browser, Google Chrome, TypeScript, React, Next.js, Three.js,
React Three Fiber, Tailwind CSS, Prisma, PostgreSQL, Supabase, Modal, Python, TRELLIS, AWS S3,
Vercel, PostHog, WebXR, GLB, and OBJ.

## Try it out

- Live app: <https://dentalsculptor.vercel.app>
- WebMCP diagnostics: <https://dentalsculptor.vercel.app/webmcp>
- Public code: <https://github.com/joboyebisi/dentalsculptor>
- MIT license: <https://github.com/joboyebisi/dentalsculptor/blob/main/LICENSE>

The required public YouTube URL is supplied directly on Devpost.
