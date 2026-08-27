# DentalSculptor generation-first implementation handover

**Updated:** 28 August 2026

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

## Known infrastructure blocker

The configured local Modal profile previously returned `Could not connect to the
Modal server` even for a read-only app listing, before image construction began.
The implementation compiles, but a successful remote build and GPU smoke test
must be completed on the deployment system before full editing is presented as
production-ready.
