# WebMCP judge guide

## Access

- Production app: <https://dentalsculptor.vercel.app>
- Live diagnostics: <https://dentalsculptor.vercel.app/webmcp>
- Source: <https://github.com/joboyebisi/dentalsculptor>

Use ChatGPT's in-app browser, which supports WebMCP, or Chrome 149+ with
`chrome://flags/#enable-webmcp-testing` enabled and the browser restarted.

## Private Devpost testing instructions

Paste the following into Devpost's private Testing Instructions field, replacing the placeholder
with the configured invite code. Do not publish or commit the code.

```text
Open https://dentalsculptor.vercel.app/?invite=PRIVATE_CODE in ChatGPT's in-app browser.
The invite permits source-image selection, 3D generation, and direct generated-model download
without an account. Saved projects, clinical editing, and publishing require the supplied judge
account or visible registration.

Start with: “Inspect DentalSculptor and tell me what we can do together.”
Then ask: “List the curated dental images.”
Choose an ID and ask the agent to select it, generate the 3D model, and inspect generation until
modelReady is true. The first GPU request after an idle period may take 2–5 minutes; progress is
shown in the page. Once the model is visible, ask the agent to continue to a teaching case or
download it.

For the full editor workflow, use the judge credentials supplied in this private field. Enter
credentials only in DentalSculptor's visible authentication page, never in chat.
```

## Recommended walkthrough

1. Ask: **“Inspect DentalSculptor and explain the collaborative workflow.”**
2. Ask: **“List the curated dental images.”**
3. Ask the agent to select one returned library ID.
4. Ask: **“Generate the 3D model and tell me when it is visible.”**
5. Wait until `dentalsculptor_inspect_generation` reports `modelReady: true`.
6. Ask the agent to continue to `case-wizard` or `editor`.
7. In the editor, ask the agent to inspect the project and available cases/presets.
8. Let the agent synchronize a preset and open the target tool.
9. Mark the clinical target visibly, then request the preview.
10. Approve the preview, create the reversible variant, and accept or reject it.
11. Open export or sharing. Confirm downloads/public release only when you intend to.

## Expected safety boundaries

- The agent never receives passwords, cookies, OAuth tokens, storage credentials, or provider
  secrets.
- A generated URL is not reported as ready until the 3D viewer confirms visible geometry.
- Model-dependent editor tools stay unavailable while the viewer is loading or has failed.
- Publishing requires explicit release approval and a no-patient-information confirmation.
- Export requires explicit download confirmation.
- A 3D revision remains reversible until the educator accepts it.

## Diagnostics

Open `/webmcp` to see whether the current browser exposes `document.modelContext` and to inspect
the tools registered on that page through `document.modelContext.getTools()`.

If WebMCP is unavailable:

1. confirm the page is HTTPS;
2. use ChatGPT's in-app browser, or enable Chrome's WebMCP testing flag;
3. restart Chrome after changing the flag;
4. refresh `/webmcp`.

The conventional interface continues to work in browsers without WebMCP.

## Cold-start note

DentalSculptor's research deployment scales GPU workers to zero while idle. The first 3D
generation may take 2–5 minutes to start and load model weights. Later requests are typically
faster. This is compute startup, not a stalled WebMCP tool; generation progress remains visible.
