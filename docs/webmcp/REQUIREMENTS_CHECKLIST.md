# WebMCP Challenge requirements and evidence

This file maps each submission requirement to public evidence. Manual Devpost-only fields remain
explicitly separated from repository content.

## Build requirements

- [x] **Meaningful WebMCP app:** DentalSculptor exposes a complete human-agent 3D authoring flow,
  not a chatbot layered over static content.
- [x] **Imperative WebMCP API:** the Chrome Labs React adapter calls
  `document.modelContext.registerTool(...)`; source attribution and automated verification are in
  `src/components/webmcp/webmcp-tool.tsx` and `scripts/test-webmcp.ts`.
- [x] **Structured tools:** 29 non-duplicated tools use constrained JSON Schemas, structured
  results, page-scoped availability, and read-only annotations.
- [x] **Human-agent collaboration:** the agent coordinates stateful work while the educator
  controls anatomy, approval, privacy, and release.
- [x] **Conventional fallback:** browsers without WebMCP retain the normal DentalSculptor UI.

## Submission requirements

- [x] **Working HTTPS URL:** <https://dentalsculptor.vercel.app>
- [x] **Browser diagnostics:** <https://dentalsculptor.vercel.app/webmcp>
- [x] **Public source repository:** <https://github.com/joboyebisi/dentalsculptor>
- [x] **Open-source license:** root `LICENSE`; GitHub detects MIT.
- [x] **Functional source and setup instructions:** root/app READMEs, `.env.example`, and
  `docs/webmcp/`.
- [x] **Project description:** [PROJECT_STORY.md](./PROJECT_STORY.md)
- [x] **Why WebMCP and improved UX:** documented in the project story and WebMCP overview.
- [x] **Human-agent capability:** documented and demonstrated by the page-scoped tool flow.
- [x] **Implementation explanation:** [README.md](./README.md)
- [x] **Pre-existing project delta:** [PROJECT_DELTA.md](./PROJECT_DELTA.md)
- [x] **Judge instructions:** [JUDGE_GUIDE.md](./JUDGE_GUIDE.md)
- [x] **Under-three-minute script:** [DEMO_SCRIPT.md](./DEMO_SCRIPT.md)
- [ ] **Public YouTube video under three minutes with audio:** URL supplied on Devpost only.
- [ ] **Private judge invite URL:** add to Devpost Testing Instructions; never commit it.
- [ ] **Final Devpost submission:** submit under the approved deadline extension.

## Technical verification

Run from `dentalsculptor-app/`:

```powershell
npm install
npm run test:webmcp
npm run test:viewer
npm run test:case-workflows
npx tsc --noEmit
npm run lint
npm run build
```

Manual browser acceptance:

1. open `/webmcp` in ChatGPT's in-app browser;
2. confirm WebMCP is reported available;
3. confirm `document.modelContext.getTools()` returns page tools;
4. execute `dentalsculptor_inspect_app`;
5. use the private invite path to select a curated image and generate a model;
6. wait for `modelReady: true` and visible 3D geometry;
7. enter the editor and verify tools remain gated until its viewer reports `ready`;
8. verify the preview/revision and publication confirmation boundaries.

## Repository safety

- [x] Real `.env` files and Vercel metadata are gitignored.
- [x] Production credentials are not required in public documentation.
- [x] Invite codes and judge credentials remain in Devpost's private field.
- [x] WebMCP results do not expose provider names, storage keys, cookies, or access tokens.
- [x] Publishing requires a no-identifiable-patient-information confirmation.
