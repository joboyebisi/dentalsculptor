# DentalSculptor generation-first implementation handover

**Updated:** 29 August 2026

## 29 August implementation increment

- Community clone now verifies that the source is published, copies the GLB to
  a new owner-scoped storage object, carries source/thumbnail assets, annotations,
  objectives and assessments, and opens the new project with a `303` redirect.
  A clone is no longer incorrectly counted as a download.
- Published project cards and detail pages expose the same four primary actions:
  **Like, Download, Clone and Share**. Direct downloads increment the published
  project's download metric and return a named GLB attachment.
- Dashboard generation now ends with the same action hierarchy as landing:
  **Download or export**, **Publish and share**, optional **Create teaching case**,
  and secondary **Open free editor**.
- The fracture editor adds a straight fracture-boundary tool beside Paint and
  Erase. Case-led editing locks the operation chosen by the case preset; only the
  free editor exposes Add/Remove/Replace switching.
- The principal fracture failure was fixed at the worker boundary: Three.js
  serializes camera matrices column-major, while NumPy previously interpreted
  them row-major. Correct transposition plus a small projection tolerance makes
  a painted fragment or narrow fracture line select the intended mesh vertices.
- GPU warm requests now refresh within the deployed scale-down window. A true
  always-warm pool remains an explicit cost-bearing deployment choice via
  `TRELLIS_RESEARCH_WARM_POOL=true`; do not enable it silently.

Focused verification for this increment:

- `npm run build` passes on Next.js 16.2.12.
- `python -m unittest tests.test_camera_projection -v` passes both positive and
  off-tooth projection cases.
- `python -m compileall -q modal_app` passes.

## Product decision

The generated tooth is the trusted primary output. After generation, the two
primary actions are **Download or export** and **Publish**. Case authoring is an
optional secondary path. Editing is reserved for teaching scenarios that cannot
be represented with the generated model plus annotations.

Provider and model names are implementation details. User-facing progress,
errors, preview labels and revision proof use the DentalSculptor name only.

## Implemented flows

### Landing → download

1. The landing image, generated model URL/key, thumbnail, material URL and format
   are carried through authentication in `PendingLandingProject`.
2. A real project is created, including a persisted `sourceImageUrl`.
3. The user is routed to `/projects/{id}/download`, not the editor.
4. The existing export wizard opens with the persisted model and source image.
5. Destination-specific validation and bundled assets remain available.

### Landing → publish

1. The same complete landing payload creates the project.
2. `/projects/{id}/publish` opens the publication confirmation directly.
3. Publication returns `/community/{projectId}` rather than the gallery root.
4. The publisher can open and copy the exact link.
5. The community detail page renders the model and learning objectives.
6. Signed-in users can toggle a like, share through the system share sheet or
   copy the URL, and make a project copy.
7. Like totals are recalculated from the unique Like records instead of relying
   on a potentially negative increment/decrement counter.

### Optional case authoring

The first screen now shows six explicit pilot choices in feasibility order:

1. Tooth identification and annotations
2. Cusp fracture / chipped enamel
3. Simple Class I cavity
4. Endodontic access opening
5. Caries appearance
6. Crown reduction

Tooth identification opens annotation mode and suppresses generated editing.
Every geometry case exposes only its declared `editPresetIds`. Selecting a preset
sets both the operation and semantic instruction. The compact panel is visible
when the mark/mask workflow is active.

## Preview and edit behaviour

- Preview responses use guarded JSON parsing and display errors inline.
- A full-screen, named progress overlay remains visible while a 3D edit is queued
  or running, with stage text and percentage.
- Cusp-fracture fallback preview removes the painted fragment against the viewer
  background and draws an irregular boundary. It no longer presents an unchanged
  or merely elongated tooth.
- Deterministic geometry-removal previews can be approved; visual-only fallback
  previews cannot.
- The original source image and approved edited image are sent separately to the
  image-input edit service.

## Simplified case-led editor

When a case has already been selected, the editor no longer presents separate
mask, workflow, teaching-case, preset and edit-action windows at the same time.
The case-led layout has three coordinated surfaces:

1. **Left panel:** persisted source image, immutable-master status, selected case
   goal and one “Mark the area to change” entry point.
2. **3D view:** tooth, purple paint overlay and the compact brush/navigation tools.
3. **Bottom action bar:** a single progressive action—Paint, Preview, then Create
   3D variant—with the selected semantic instruction shown read-only.

The unrestricted/manual editor retains advanced floating panels when no case is
selected. This keeps expert capability without forcing it into the guided flow.

Two asset-path defects were corrected at the same time:

- `/api/projects/[id]/source-image` streams the authenticated persisted source
  image, recovering its storage key instead of rendering an expired signed URL.
- the edit-job API recognizes `/api/projects/[id]/model` as the authenticated
  project model, resolves a fresh storage URL server-side and refreshes old
  signed master URLs before submitting work. This removes the erroneous “Source
  model does not belong to this project” rejection visible in the old UI.

## Geometry and appearance preservation

Two safeguards address the thin, black edit result:

1. The deterministic mesh path retains the source mesh visual/material object,
   metadata, faces and topology. Displacement is proportional to the model
   bounding-box diagonal. If the mask cannot be projected to vertices, the job
   fails with an actionable message; it never scales half of the tooth.
2. The full image-input edit result is transformed back into the trusted source
   model's exact width, height, depth, centre and export scale before GLB export.
   Provenance records whether this bounds normalization occurred.

Bounds normalization solves global slimming but does not prove that regenerated
texture outside the edited region is pixel-identical. The deployment evaluator
must compare fixed-view renders and reject revisions with unacceptable protected-
region or material changes. For the cusp-fracture pilot, the deterministic
localized mesh path remains the safer fallback when appearance preservation is
more important than generative fracture morphology.

## Teaching variant builder

The editor header now exposes **Create variant**. A compact builder keeps the
generated GLB as an immutable `master-model` project version and creates every
case from that master, rather than progressively damaging an accepted edit.

- Fracture, Class I, endodontic external access, caries excavation and crown
  reduction use a mask-local deterministic geometry operation.
- Visual caries changes vertex colour only and is explicitly labelled as
  appearance-only, not soft tissue or haptic simulation.
- Missing-cusp restoration remains on the generative reconstruction path.
- Each recipe persists preset, case, technique, severity, surface, requested
  depth and fracture angle in `EditJob.metadata`, with master lineage.
- Boolean results inherit nearest source vertex colours. Non-watertight imports
  fall back to localized, scale-aware deformation instead of returning a thin or
  globally rescaled mesh.
- Every output remains an ordinary revision: the educator reviews it, accepts or
  rejects it, then uses the existing Save, Publish, Share and Export flows.

Main additions:

- `src/lib/case-variant-recipes.ts`
- `src/components/editor/case-variant-builder-dialog.tsx`
- `dentalsculptor-ml/modal_app/workers/variant_geometry.py`

## Main implementation files

- `src/components/landing/landing-model-panel.tsx`
- `src/lib/landing-session.ts`
- `src/components/projects/post-generation-action.tsx`
- `src/components/export/export-wizard-dialog.tsx`
- `src/components/editor/share-project-dialog.tsx`
- `src/app/api/projects/[id]/publish/route.ts`
- `src/app/(app)/community/[projectId]/page.tsx`
- `src/app/api/community/[projectId]/like/route.ts`
- `src/lib/educator-case-picks.ts`
- `src/components/editor/editor-edit-presets-bar.tsx`
- `src/components/editor/editor-workspace.tsx`
- `src/lib/edit-2d-preview.ts`
- `dentalsculptor-ml/modal_app/workers/nano3d_utils.py`
- `dentalsculptor-ml/modal_app/workers/nano3d_flowedit.py`

## Verification completed locally

- `npm run build` passes, including Prisma generation, production compilation,
  TypeScript validation and static route generation.
- Focused ESLint for the new variant dialog, recipes and API/server changes
  passes with no errors.
- Python byte-compilation passes for `app.py` and `variant_geometry.py`.
- `git diff --check` passes (Git reports Windows line-ending notices only).
- The repository-wide lint command still reports pre-existing React 19 hook/ref
  rules in legacy viewer and dialog components; those are outside this change and
  are not TypeScript/build blockers.

## Deployment-agent checklist

### Commit scope for the latest case-flow correction

Commit the following application files together; they form one atomic fix for
the Vercel 403, expired source image and consistent guided-case workflow:

- `dentalsculptor-app/src/app/api/projects/[id]/edit-jobs/route.ts`
- `dentalsculptor-app/src/app/api/projects/[id]/route.ts`
- `dentalsculptor-app/src/app/api/projects/[id]/source-image/route.ts`
- `dentalsculptor-app/src/components/editor/editor-source-panel.tsx`
- `dentalsculptor-app/src/components/editor/editor-workspace.tsx`
- `dentalsculptor-app/src/components/editor/guided-case-edit-bar.tsx`
- `dentalsculptor-app/src/components/generation/generation-image-picker.tsx`
- `dentalsculptor-app/src/lib/case-variant-recipes.ts`
- `dentalsculptor-app/src/lib/guided-case-flow.ts`
- `dentalsculptor-app/src/lib/project-model-asset.server.ts`
- `docs/GENERATION_FIRST_HANDOVER.md`
- `docs/CASE_CREATION_AUDIT.md`

Do **not** include unrelated root screenshots, downloaded tooth charts,
`modal-deploy.log`, or `docs/benchmarks/smoke-runs/*` unless the maintainer
explicitly wants those research artifacts committed.

Suggested local verification before committing:

```powershell
cd dentalsculptor-app
npm run build
.\node_modules\.bin\eslint.cmd `
  src/lib/guided-case-flow.ts `
  src/lib/case-variant-recipes.ts `
  src/components/editor/guided-case-edit-bar.tsx `
  "src/app/api/projects/[id]/edit-jobs/route.ts"
cd ..
git diff --check
```

### Deployment order

1. **Commit and deploy the Next.js files above first.** No new database migration
   is required for this latest correction. Existing `ProjectVersion` and
   `EditJob.metadata` fields are reused.
2. Confirm the Vercel deployment contains the new dynamic route
   `/api/projects/[id]/source-image`.
3. Open the same project that previously failed and confirm its source image
   loads through that route.
4. Reapply or reload the cusp-fracture case. The editor must automatically bind
   `fracture-oblique`; users should not need to reopen Create Variant.
5. Paint, preview and submit. `/edit-preview` should return 200 and `/edit-jobs`
   must no longer return 403. A queued/202 or completed/200 response proves the
   request passed application ownership validation and reached the configured
   editing service.
6. If the request reaches the editing service but the job then fails, deploy the
   Modal changes described below and inspect the Modal job status. Do not treat a
   worker failure as the same bug as the resolved Vercel 403.

### Modal deployment scope

The deterministic case worker is a separate deployment concern. Ensure the
commit being deployed already includes:

- `dentalsculptor-ml/modal_app/app.py`
- `dentalsculptor-ml/modal_app/workers/variant_geometry.py`
- `dentalsculptor-ml/modal_app/workers/nano3d_utils.py`
- `dentalsculptor-ml/modal_app/workers/nano3d_flowedit.py`

Deploy from `dentalsculptor-ml` with the authenticated Modal profile and existing
secrets. Capture the emitted edit and job-status URLs, then verify Vercel has the
matching `MODAL_EDIT_URL`, `MODAL_JOB_STATUS_URL` and
`MODAL_WEBHOOK_SECRET`. Never place secret values in the repository or handover.

### Required post-deploy regression sequence

Run in this order and retain the Vercel request status plus final GLB for each:

1. cusp fracture;
2. Class I cavity;
3. external endodontic access;
4. visual caries, then caries excavation;
5. crown reduction.

Each must use the same Goal → Target → Preview → Create interaction layout. See
`docs/CASE_CREATION_AUDIT.md` for the case-specific default recipe, claims and
release gates. Tooth identification is excluded from this geometry sequence
until annotation authoring is completed.

1. Apply the existing Prisma schema before testing Like records.
2. Confirm storage credentials persist both the generation image and GLB.
3. Deploy the Next.js application and verify auth continuation for both
   `nextStep=download` and `nextStep=publish`.
4. Publish a generated project and open its exact URL in a second user account.
5. Like/unlike it, reload, share the URL, and clone it.
6. Deploy the isolated editing GPU image and confirm source-model URLs are
   reachable from the GPU container.
   The updated CPU image also requires `manifold3d>=3.1.0`; deploy the Modal app
   after this dependency is built. Deterministic variants run on CPU and do not
   require GPU capacity.
7. Run a cusp-fracture edit with a fixed camera and seed. Verify:
   - the 2D proposal has visible missing cusp structure;
   - progress remains visible until completion;
   - output bounds match the source bounds;
   - materials render in the browser;
   - protected surfaces remain stable;
   - accept/reject revision works;
   - accepted GLB passes export validation.
8. Repeat the edit gate in pilot order. Keep any failing geometry case out of the
   live demo; download and publication of the original generated model remain the
   primary production path.
9. For each deterministic preset, verify the resulting GLB is non-empty, bounds
   drift is acceptable, materials render, accept/reject works, and the accepted
   variant downloads and publishes. Treat endodontic access as an external
   opening unless a validated segmented internal-anatomy model is attached.

## Generation and deployment status (August 2026)

- Landing and `/projects/new` use **single-step `standard` quality** generation
  (no preview→finalize gate on the landing page).
- Async Modal jobs are **required on Vercel**; sync generation times out at 300s.
- Modal worker redeployed with `TRELLIS_ASYNC_S3_ENABLED=true` for async S3 jobs.
- Card previews use deterministic storage keys (`/api/projects/{id}/preview-image`);
  no `previewImageKey` database column is required.
- Cusp-fracture smoke test passes when edit jobs submit `sourceModel` inline.

## 3 September 2026 deterministic-edit correction

- `variant_geometry.py` now falls back from manifold Boolean subtraction to a
  capped surface clip for non-watertight generated meshes. It does not silently
  return the source model.
- `edit-jobs.server.ts` updates/clears the storage key whenever an edited or
  reverted URL becomes current, preventing export from resolving the stale
  master asset.
- `scripts/test_variant_geometry.py` includes a deliberately open source mesh
  and asserts that source faces are removed, cap faces are created and the GLB
  remains valid.
- Verified locally: all 18 deterministic geometry presets, the open-mesh
  fracture fallback, 9 guided case templates, 14 free-editor strategies and the
  full Next.js production build.

Post-deploy cusp-fracture gate: paint a visible cusp target, approve the 2D
proposal, wait for the 3D revision, accept it, then download both GLB and STL.
The editor mask must clear after completion, the revision must remain visibly
fractured after reload, and exported geometry must differ from the master.

## Known infrastructure notes

- Cold GPU start can still take several minutes; session warmup via
  `POST /api/ml/warm` reduces first-generation latency when it succeeds.
- Full geometry case regression (Class I, endodontic access, caries, crown) still
  requires the post-deploy sequence in `docs/CASE_CREATION_AUDIT.md`.
- Tooth identification remains annotation-only until CAM annotation authoring
  is complete.
