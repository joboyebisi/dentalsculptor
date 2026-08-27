# DentalSculptor real-time evaluation handoff

**Updated:** 27 August 2026  
**Purpose:** Single source of truth for the generation → edit → export pilot path.

## Product claim we can test now

DentalSculptor lets an educator choose or upload a single-tooth image, generate a
3D teaching asset with TRELLIS.2, define a case-aware edit using a painted region
and semantic preset, review a 2D proposal, create an auditable revision, and
export or publish the result.

Do not yet claim clinically accurate anatomy, production-verified Nano3D edits,
or multi-tissue haptics. The real FlowEdit path is implemented but still needs a
successful Modal GPU build and case benchmark before it is a product claim.

## Architecture decision: keep image and mesh edit paths

Nano3D documents two relevant paths:

- `inference.py`: edit an existing GLB. Upstream warns that render-projection
  encoding can reduce consistency.
- `inference2.py`: original image → TRELLIS reconstruction → edit. Upstream says
  this avoids the render-projection step and produces more consistent pairs.

Therefore every DentalSculptor revision must retain the original generation
image, seed, generated GLB, camera, mask, operation, prompt, 2D edited reference,
provider/checkpoint and result GLB. The UI should eventually offer the image path
as the default and label direct-GLB editing experimental.

## Changes in this implementation pass

1. `/api/generate/mesh` now persists the exact submitted generation image to the
   project's `DentalModel.sourceImageUrl`. Library images consequently remain
   visible after reopening the editor and are available to future Nano3D
   image-input inference.
2. `CamModelViewer` performs camera fitting after two animation frames and repeats
   it after layout settles. This addresses generated meshes initially appearing
   outside or too far from the view.
3. The cusp-fracture case now uses `remove`, with prompts that explicitly remove
   tooth structure and request an irregular enamel edge. A missing cusp is not an
   `add` edit.
4. The header's redundant placeholder Preview button was removed. Share now opens
   a working publication dialog, checks that a model exists, publishes through a
   server-owned route, records `PROJECT_PUBLISHED`, and exposes the community link.
5. Export destinations are grouped into Dental simulation, VR headsets, and
   Presentations & teaching. PowerPoint/Microsoft 365 uses GLB, the format Microsoft
   recommends for portable Office 3D content.
6. The six pilot cases are explicitly ordered in the case picker. Each geometry
   case exposes only its case-specific presets; tooth identification switches to
   annotation mode and never asks the user to paint or approve a generated edit.
7. The 2D review now distinguishes a real AI proposal from the illustrative local
   fallback. The fallback explains its limitation and cannot be approved for 3D.
8. Nano3D image-input FlowEdit is implemented in a separate pinned Modal image at
   `JAMESYJL/Nano3D@7d20eb6`. The frontend sends separate pre-edit and AI-edited
   captures, the job reports named progress stages, the GLB is stored through the
   existing S3 job path, and provenance is saved with the revision.
9. Both FlowEdit inputs are letterboxed to a common square without changing aspect
   ratio. The prior direct resize could make an unchanged tooth appear elongated.

## Why the present 2D preview can look stretched or unchanged

There are three providers in priority order: Modal SDXL, fal inpaint, then a local
pixel preview. The local path is not generative; it only alters pixels in the mask
and must not be used as evidence that the requested anatomy can be generated.
Generic SDXL also has weak knowledge of dental morphology. A good-looking 2D
fracture is necessary for Nano3D Case 3, but does not prove that the 3D edit will
preserve the rest of the tooth.

Before user evaluation, the preview UI should display a hard provider state:

- **AI preview ready** — Modal/fal returned a dimension-checked image.
- **Illustrative local preview** — useful for testing flow only; 3D AI approval is
  disabled or explicitly marked experimental.
- **Unavailable** — no silent fallback during a clinical-quality study.

## Pilot case order

| Order | Case | Why it is feasible | Required gate |
|---|---|---|---|
| 1 | Tooth identification and annotation | No generative edit is required | Correct tooth class and stable viewer |
| 2 | Cusp fracture / chipped enamel | Localized removal is visually obvious | 2D fracture visible; protected surface stable |
| 3 | Simple Class I cavity | Localized removal on occlusal surface | Depth/diameter bounds and watertight output |
| 4 | Endodontic access opening | Another localized removal task | Opening location and pulp-direction rubric |
| 5 | Occlusal caries appearance | Texture/appearance can be previewed | Must disclose that STL has uniform hardness |
| 6 | Crown reduction | Broad controlled surface removal | Uniform clearance cannot yet be guaranteed |

Defer soft-tissue pathology, pulp/enamel/dentine editing and clinically meaningful
soft caries haptics until multilayer meshes or voxel labels exist. A surface GLB or
STL cannot encode tissue-specific drilling resistance.

## Evaluation gates

### Generation

- 20 de-identified or synthetic single-tooth images, balanced across tooth types.
- Fixed seeds across preview/standard/final.
- Record success, time-to-first-preview, mesh load failure, unwanted defects,
  silhouette agreement and educator anatomy rating.
- Viewer must frame every successful model without manual wheel zoom.

### Editing

- Start with image-input Nano3D, not only direct-GLB Case 3.
- For every edit store before/after renders from at least four fixed views.
- Measure protected-region displacement, changed-region coverage, watertightness,
  triangle count and educator accept/reject reason.
- A case enters a live demo only after at least 8/10 blinded edits are accepted by
  the dental reviewer and no protected-region failure is severe.

### Export

- Simodont: validate STL and PLY in Courseware. The official teacher manual states
  both are importable; STL has uniform colour/hardness and no internal anatomy.
- Meta Quest: GLB scale, orientation and triangle budget test.
- PowerPoint: desktop insertion test with GLB. PowerPoint for the web should not be
  presented as supporting direct 3D insertion.

## DTU FDI 16 dataset decision

The cited DTU dataset is useful as a dental-shape source and evaluation reference,
but meshes alone are not sufficient for conditional image-to-3D fine-tuning. The
TRELLIS.2 training stack expects preprocessed O-Voxels/shape latents plus rendered
conditioning views and metadata. Before training:

1. Verify licence, subject consent/de-identification and permitted derivative use.
2. Inspect sample count, mesh topology, units, orientation and whether scans include
   surrounding gingiva or only the target tooth.
3. Normalize each mesh; create standardized multi-view renders with alpha masks.
4. Split by subject/source before augmentation to prevent leakage.
5. Establish zero-shot TRELLIS.2 and deterministic geometric baselines.
6. Fine-tune only after the baseline shows the dataset covers the intended case.

Given the 4B model and limited dental dataset size, start with a small controlled
shape-flow fine-tuning experiment; do not promise full-model training or improved
pathology generation from a single-tooth mesh collection.

## Next engineering sequence

1. Restore Modal API connectivity and deploy the new isolated Nano3D image.
2. Smoke-test one fixed-seed cusp fracture end to end and verify a valid GLB,
   visible localized removal, stable protected surface and persisted provenance.
3. Run the same gate for Class I, endodontic access, caries appearance and crown
   reduction; keep any failing case out of the live pilot rather than silently
   substituting a pixel preview.
4. Add the edit metrics above and a 20-case benchmark command.
5. Validate STL/PLY/GLB in actual destination applications.
6. Only then run educator usability sessions and publish interactive demo cases.

## Verification status

- TypeScript: `npx tsc --noEmit` passes after the six-case/Nano3D changes.
- Python: `python -m compileall modal_app` passes.
- Focused new files type-check.
- Repository ESLint still fails on existing React 19 hook/immutability rules in
  several older files. These are pre-existing and should be cleared before CI is
  treated as a release gate.
- Modal CLI profile `dentalsculptor` is present, but both deployment and a read-only
  `modal app list` failed on 27 August 2026 with `Could not connect to the Modal
  server` before an image build began. This is an account/network connectivity
  blocker, not evidence that the Nano3D container has built successfully.
- Live Modal, S3, Supabase and vendor import tests therefore remain unverified.
