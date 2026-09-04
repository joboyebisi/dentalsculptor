# Under-three-minute WebMCP demo script

Target length: **2:40–2:50**. Record at 1080p with readable browser and chat text. Warm the GPU
before recording, and edit out waiting time while leaving a short view of real progress.

## 0:00–0:15 — show the outcome first

**On screen:** original tooth image, visible generated 3D model, localized teaching variant, then
the export panel.

**Narration:**

> DentalSculptor lets a dental educator and an agent turn one tooth image into an editable,
> simulator-ready 3D teaching case in the same browser workspace.

## 0:15–0:35 — explain the problem

**On screen:** return to the landing workbench in ChatGPT's in-app browser.

**Narration:**

> Dental case authoring mixes long-running AI generation, spatial 3D decisions, clinical
> parameters, and irreversible release actions. Screen automation has to guess. Full autonomy
> would hide decisions an educator needs to own.

## 0:35–1:00 — WebMCP inspection and generation

**Prompt:** “Inspect DentalSculptor and tell me what we can do together.”

**Prompt:** “List the curated dental images and select the upper molar.”

**Prompt:** “Generate the 3D model and tell me when it is visible.”

**Narration:**

> WebMCP gives the agent structured state and valid actions. It starts generation only after a
> source is selected, and it does not report the model ready merely because an API returned a URL.
> It waits for the Three.js viewer to confirm visible geometry.

Show generation progress briefly, then cut to the loaded model.

## 1:00–1:40 — human-agent case authoring

**Prompt:** “Continue to the case wizard and prepare a cusp-fracture teaching case.”

**Prompt:** “Inspect the editor, choose the compatible fracture preset, and open the target tool.”

Use the visible brush or region tool yourself.

**Narration:**

> The agent coordinates the multi-step workflow, but I mark the exact anatomy. Tool discovery is
> page-scoped, so the agent sees only actions that make sense here. Model-dependent tools remain
> unavailable until the 3D scene is loaded.

## 1:40–2:10 — reversible approval

**Prompt:** “Create the review preview.”

Approve the preview visibly.

**Prompt:** “Create the reversible 3D variant.”

Show the revision controls and accept or reject.

**Narration:**

> Clinical edits do not become hidden one-shot actions. The preview, 3D result, and revision
> decision stay visible. The educator owns approval and can reject the change.

## 2:10–2:35 — reuse and safety

**Prompt:** “Open export options.”

Briefly show the supported formats and then the share dialog.

**Narration:**

> The same structured workflow continues into reuse. Downloads require confirmation. Publishing
> additionally requires an explicit patient-privacy declaration. Credentials and infrastructure
> secrets never pass through WebMCP.

## 2:35–2:48 — close

**On screen:** `/webmcp` diagnostics showing the browser's live tool registry, then the final 3D
model.

**Narration:**

> The agent coordinates. The educator owns anatomy, approval, and release. That is the
> agent-native web experience DentalSculptor makes possible.

## Recording checklist

- Keep the final public YouTube video under 3:00 and include audio.
- Show ChatGPT's in-app browser or flagged Chrome.
- Show at least one discovered WebMCP tool and one real tool execution.
- Show visible 3D geometry, not only a success message.
- Show one human-controlled spatial or approval action.
- Avoid displaying the invite code, judge credentials, tokens, or private dashboards.
- Put the public YouTube URL in Devpost; repository inclusion is intentionally optional.
