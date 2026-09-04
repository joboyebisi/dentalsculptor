# WebMCP work added to the pre-existing DentalSculptor project

DentalSculptor existed before the WebMCP Challenge as a research platform for image-to-3D dental
model generation, clinical case authoring, editing, export, community sharing, and educator
evaluation. The challenge work did not present that earlier platform as newly created. It added a
new agent-native interaction layer and the reliability work needed for agents and educators to
share the existing workspace safely.

## Before WebMCP

The application already provided:

- a Next.js dental educator interface;
- image upload and Modal-backed 3D generation;
- Three.js model viewing;
- guided case templates and a Free Editor;
- mask/region targeting, previews, and reversible edit revisions;
- project persistence, simulator export, and community publishing;
- Supabase authentication and research instrumentation.

These capabilities were operated through the conventional user interface and APIs.

## Challenge-period contribution

The WebMCP work added:

- page-scoped structured tools for global, generation, editor, share, and community surfaces;
- a typed React adapter over `document.modelContext.registerTool(...)`;
- schema-constrained inputs and MCP-shaped text/structured results;
- safe authentication links that never expose credentials or session tokens;
- invited-guest generation and download;
- structured clinical case selection and preset synchronization;
- normalized 3D target regions and gated preview/variant creation;
- visible accept/reject revision decisions;
- explicit export, publication, and patient-privacy confirmations;
- embedded-browser-safe model loading through a same-origin proxy;
- viewer-level readiness so agents cannot act on a model URL before geometry is visible;
- live WebMCP diagnostics, tests, judge documentation, and submission materials.

## Public commit evidence

The public history separates the WebMCP extension from the earlier product:

- `e1806a1` — Add page-scoped WebMCP collaboration tools
- `2cc8cb4` — Prepare WebMCP challenge release documentation
- `82b6684` — Add secure WebMCP authentication handoff
- `761cf42` — Complete WebMCP dental authoring workflow
- `cbd623e` — Fix invited guest and WebMCP image flows
- `c385201` — Fix generated model viewport framing
- `5c7aad9` — Expose publish confirmation through WebMCP
- `e8b0e3d` — Harden WebMCP embedded model loading
- `009375a` — Gate WebMCP on visible model readiness

The corresponding changes were merged into the public default branch through pull requests
[#1](https://github.com/joboyebisi/dentalsculptor/pull/1) through
[#8](https://github.com/joboyebisi/dentalsculptor/pull/8).

## Why this extension is substantive

The work is more than exposing existing endpoints. Tools are bound to live React state and
appear/disappear with the visible page and prerequisites. The implementation also introduced
agent-specific safety contracts: truthful viewer readiness, secure authentication handoff,
reversible review, privacy confirmation, and structured state inspection. Those changes make
human-agent co-authoring possible without creating a second, hidden source of truth.
