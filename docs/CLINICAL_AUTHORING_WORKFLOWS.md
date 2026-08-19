# Clinical authoring workflows, UX, and model routing

**Status:** Product recommendation for Phases D–F  
**Updated:** 17 August 2026

## TrueTeethLab-derived workflows (captured)

Local research from Simodont TrueTeethLab demos (videos/frames in
`research/trueteethlab-workflows/` — **gitignored**, not shipped with the app)
maps to **three DentalSculptor authoring paths**. Each path saves a **complete
versioned scene** (meshes, transforms, labels, masks, assessment zones,
revisions) — not a screenshot.

### Anatomy part roles (assessment-aware)

Generalises TrueTeethLab’s **drillable vs non-drillable** jaw workflow:

| Role | Learner can modify | Scoring use |
|------|-------------------|-------------|
| **Target** | Yes — primary task region | Volume removed / prep shape vs tolerance |
| **Protected** | No — violation scored | Pulp, gingiva, neighbour contacts |
| **Context** | Visible only | Arch neighbours, orientation references |
| **Hidden scoring reference** | Invisible to learner | Ideal prep outline, tolerance mesh |

Stored per part in `anatomyParts[] { role, fdi, tissue, confirmed }`.
Implementation types: `clinical-case-params.ts`.

---

### Workflow A — Create from an existing model

*TrueTeethLab: **Model from snapshot***

| Step | Educator action | System |
|------|-----------------|--------|
| 1 | Choose model from personal / institutional / teaching library | List projects + licensed templates |
| 2 | Start from original anatomy **or** current modified revision | Load `ModelRevision` chain |
| 3 | Add pathology, prep geometry or target regions | Mask + structured params + optional Nano3D |
| 4 | Confirm tooth / arch labels (odontogram) | FDI assignment |
| 5 | Define learner starting state | Viewpoint, visible refs, instruments |
| 6 | Add learning outcome, procedure, assessment criteria | `CaseRecipe` persisted |
| 7 | Preview as learner | Read-only learner mode |
| 8 | Publish or export | Versioned case archive or simulator STL |

**DentalSculptor delta vs TTL:** save full scene graph + revision history, not
only a Simodont export file.

**E0–E2 entry:** landing generate → editor → case wizard → edit from revision v1.

---

### Workflow B — Single-tooth clinical case

*TrueTeethLab: **Single tooth** (µCT / photo / IOS)*

| Step | Educator action | System |
|------|-----------------|--------|
| 1 | Choose anatomy / caries / crown / endo teaching intent | Primary case template |
| 2 | Upload DICOM/NIfTI, IOS, photo, or pick template | Modality router |
| 3 | Review consent, de-ID, source quality | Gate before processing |
| 4 | Inspect synchronized slices + reconstructed 3D | Tri-planar + viewer (E3 for DICOM) |
| 5 | Segment enamel, dentin, pulp where supported | Parts panel (coming soon) |
| 6 | Correct and confirm anatomy | Human confirmation required |
| 7 | Confirm FDI, scale, orientation, origin | Placement metadata |
| 8 | Add pathology / procedure | Structured params → masks |
| 9 | Define learner instructions, protected tissues, tolerances | Assessment roles |
| 10 | Validate, publish, export | Export centre + preflight |

**E0–E2 entry:** PNG/JPG upload → TRELLIS/fal generate → template wizard with
structured caries/anatomy/endo fields → edit.

---

### Workflow C — Arch or multi-tooth case

*TrueTeethLab: **Partial jaw CBCT** (up to 8 teeth, ≤3 drillable)*

| Step | Educator action | System |
|------|-----------------|--------|
| 1 | Choose partial arch, full arch, or tooth-in-jaw | Template + workflow C |
| 2 | Upload CBCT, IOS, or teaching template | Volume or surface route |
| 3 | Crop and orient anatomy | Crop box + occlusal plane |
| 4 | Segment teeth and supporting structures | IOS/CBCT segmentation workers |
| 5 | Review labels via odontogram | Linked 3D + slice hover |
| 6 | Assign role per structure: Target / Protected / Context / Hidden | Role picker |
| 7 | Place or replace teeth where required | Placement Studio (E2) |
| 8 | Add pathology and learner task | Case recipe |
| 9 | Preview segmentation + learner experience | Learner preview mode |
| 10 | Publish/export with semantic parts intact | Multi-part GLB + manifest |

**E2+ scope** for full CBCT; **E2** starts with template jaw + single placed tooth.

---

### First four recommended case templates (E0–E2)

Structured clinical parameters — **not prompts alone** — defined in
`case-templates.ts` + `clinical-case-params.ts`:

| Template | Workflow | Structured params (examples) |
|----------|----------|------------------------------|
| **Dental anatomy — single tooth** | B | FDI, tooth type, structures to label |
| **Caries — single tooth** | B | FDI, surface, site, depth, tissue involvement, pulp proximity |
| **Crown preparation — tooth in jaw** | C | FDI, arch, margin type, occlusal reduction mm, protected tissues |
| **Endodontic access — single tooth** | B | FDI, access type, canals expected, pulp chamber status |

Text prompts remain **optional refinement** after structured fields are confirmed.

---

## Product decision

DentalSculptor should become a case authoring system with four guided starting
points, not a generic image-to-3D generator:

1. **Single tooth** — create or import one tooth, add anatomy/pathology, and
   export it alone or place it in an arch.
2. **Tooth in jaw** — start from an arch scan or template, choose an FDI tooth
   position, place/replace a tooth, validate contacts, and merge or export parts.
3. **Partial or full arch** — import IOS geometry, segment and label teeth,
   author multi-tooth cases, and preserve separate semantic parts.
4. **CT/CBCT anatomy** — import DICOM/NIfTI, inspect slices, segment anatomical
   structures, create true-scale surfaces, then author and export a case.

Panoramic/periapical X-rays and ordinary photographs are reference evidence,
not metrically reliable 3D geometry. They can guide an educational reconstruction
or pathology annotation, but the UI must never imply that a true patient-specific
3D surface was recovered from one projection.

## The case-authoring shell

Use one consistent five-step shell for every pathway:

```text
1 Source  ->  2 Anatomy  ->  3 Case  ->  4 Validate  ->  5 Publish
```

- **Source:** upload, identify modality, de-identify, orient, crop, and check
  quality/scale.
- **Anatomy:** reconstruct or extract surfaces; segment and label structures;
  let the educator correct labels.
- **Case:** place teeth, sculpt or generatively edit, add pathology, and specify
  learner task and assessment criteria.
- **Validate:** inspect contacts, protected anatomy, mesh health, scale, and the
  learner starting state.
- **Publish:** export files or package a versioned learning case.

The current 3D editor remains the workspace inside steps 2–4. A persistent case
rail shows progress, warnings, autosaved revisions, and the next clinical action.
Advanced controls are progressively disclosed; the default experience uses
plain dental actions such as **Choose tooth**, **Position**, **Check contacts**,
and **Create cavity**, rather than mesh terminology.

## 1. Placing a generated tooth into a lower jaw

### Recommended experience

1. User selects **Place in jaw** from the single-tooth result.
2. They upload/select a lower-arch IOS mesh or choose a de-identified teaching
   template.
3. The arch is oriented and segmented. The user chooses the destination using
   an interactive FDI odontogram, e.g. `46`.
4. DentalSculptor proposes an initial transform from the tooth centroid, arch
   curve, occlusal plane, neighbours, and—when replacing—a template tooth.
5. A focused placement workspace provides:
   - translate/rotate handles aligned to mesiodistal, buccolingual and occlusal
     dental axes;
   - uniform scale only by default, with a prominent scale warning;
   - occlusal, buccal, lingual and proximal preset views;
   - transparent neighbours and a clipping plane;
   - live clearance/contact heatmap and minimum-distance readout;
   - snap strength: off, gentle, or fit to socket;
   - undo/redo and **Reset suggested position**.
6. The user confirms placement and chooses either **Keep as separate parts** or
   **Create printable merged model**.

The open-source Meshmixer workflow demonstrates the essential mental model:
tooth library -> separate object/layer -> transform -> inspect -> combine -> STL.
DentalSculptor should preserve that simplicity while adding automatic dental
orientation, labelling, collision checking, and reversible merging.

### Geometry pipeline

- Normalize units without destroying physical scale; retain a complete transform
  chain from source to export.
- Estimate the jaw's occlusal plane and arch curve from labelled crown points.
- Obtain an initial tooth pose from an FDI template or the missing-tooth gap.
- Refine with constrained ICP against socket/neighbour surfaces, never unconstrained
  global ICP.
- Compute signed/unsigned surface distances and collision regions using a BVH.
- Optionally evaluate an opposing arch/bite scan; do not claim occlusal accuracy
  without one.
- Keep jaw, placed tooth, antagonist and pathology as separate scene entities.
- For printable union, repair meshes, perform a robust Boolean/voxel union,
  remove internal shells, check watertightness and preserve a pre-merge revision.

`DMM` is useful as a research prior for tooth/gum templates, correspondence and
tooth replacement, but not as the primary segmentation service. The newer
template-based semantic alignment previewer is relevant to suggested tooth
poses, but must not replace educator confirmation.

## 2. Download and interoperability

### Export centre

Replace a single download button with an **Export centre** containing presets:

| Preset | Output | Purpose |
|---|---|---|
| Web/VR preview | GLB | Materials, labels in metadata, compact viewing |
| Haptic/simulator | STL and optional PLY | Widely accepted surface formats |
| 3D printing | Binary STL | Watertight, true-scale merged surface |
| Further CAD | OBJ + MTL/textures, PLY | Editable interchange |
| Medical volume | NIfTI label map and/or DICOM SEG when valid | Volumetric research workflow |
| Case archive | ZIP manifest + assets | Reproducible DentalSculptor case |

Simodont documentation supports STL or PLY imports for reusable courseware, but
some simulator workflows use vendor-specific packages. Therefore, DentalSculptor
must distinguish **geometry export** from **simulator-ready package** and only
offer the latter after validating a specific vendor's schema/licence.

### Mandatory preflight

Every export reports:

- coordinate units and physical bounding-box dimensions;
- triangle count and simplification choice;
- watertightness, non-manifold edges, inverted normals, self-intersections,
  disconnected shells, minimum wall thickness where relevant;
- whether the pathology and tooth are merged or separate;
- which semantic labels/materials will be lost by the chosen format;
- source modality, revision, segmentation/model version, and an educational-use
  disclaimer in a sidecar manifest.

STL stores only surface geometry, so labels, colours, materials, units and case
metadata need a manifest or separate files. Never silently flatten a labelled
case into an unlabeled STL.

## 3. Segmentation and automatic labelling

There is no single best model for all DentalSculptor inputs. Route by modality:

| Input | First production candidate | Output/use |
|---|---|---|
| IOS upper/lower surface mesh | DentalModelSeg baseline; benchmark a modern Teeth3DS/3DTeethSeg2 model | Per-crown instances, gingiva, FDI/Universal labels |
| CT/CBCT volume | DentalSegmentator for reliable coarse anatomy | Maxilla/skull, mandible, upper/lower teeth, mandibular canal |
| CBCT needing individual tooth IDs | ToothSeg/ToothFairy2-derived pipeline | Tooth instances and numbering; benchmark on local cases |
| µCT single tooth | ToothAnalyserMicroCT workflow | Enamel/dentin/pulp/pathology-oriented research segmentation |
| Generated generic GLB/photo-derived mesh | Geometry/part segmentation plus educator confirmation | Do not assign clinical labels with false confidence |

`DentalModelSeg` is a practical IOS baseline with per-tooth FDI/Universal labels
and per-label output, but it is Linux/CUDA-only, expects VTK, and notes reduced
performance with wisdom teeth. `DentalSegmentator` is more mature for diverse
CT/CBCT and was trained on 470 scans and evaluated on 256 scans from seven
institutions, but its five classes are too coarse for per-tooth editing.
`ToothSeg` and ToothFairy2 are better research candidates for individual tooth
instances and numbering in CBCT. ToothFairy2 exposes 42 annotated classes and
also shows that correct FDI numbering is harder than tooth delineation.

### Segmentation review UI

- Display an odontogram beside the 3D scene and synchronized slice views for
  volumes.
- Colour by anatomical class; hover links label, mesh and slices.
- Show confidence as a subtle badge, not a misleading precise percentage.
- Flag duplicates, impossible FDI order, missing teeth, fused components and
  uncertain boundaries.
- Support rename/relabel, split, merge, erase, paint and restore prediction.
- Require **Confirm anatomy** before labels become edit constraints.
- Store prediction and human correction separately for audit/training.

### Downstream value

Confirmed labels enable selection by tooth number, protected-region masks for
Nano3D/custom editing, automatic placement anchors, pathology targeting,
visibility/isolation, per-part export, assessment zones, and analytics such as
material removed inside/outside the intended preparation.

## 4. Multi-modal source intake

### Upload experience

The upload screen accepts files/folders, inspects them locally when possible,
and proposes a detected source type:

| Source | Accepted examples | Route |
|---|---|---|
| Photo | JPG, PNG, HEIC | Background/orientation -> generative 3D, explicitly approximate |
| IOS/surface | STL, OBJ, PLY, VTK, GLB | Validate units -> orient -> surface segmentation |
| CBCT/CT | DICOM series/ZIP, NIfTI | De-identify -> volume viewer -> crop -> segmentation -> surfaces |
| X-ray | DICOM/JPG/PNG panoramic or periapical | Reference/annotation; optional research reconstruction with uncertainty |
| Existing case | DentalSculptor ZIP | Validate manifest -> restore revisions and labels |

For DICOM, show series selection, modality, voxel spacing, slice count, physical
extent, orientation, metal-artifact warning and de-identification status before
upload. Use a tri-planar viewer (axial/coronal/sagittal), window/level, crop box,
measurements, segmentation overlays and linked 3D rendering. VoxelLab is a useful
local-first UX reference, but its code is a viewer rather than the dental
segmentation backend.

Large or identifiable volumes should be de-identified and cropped locally where
possible. Upload by signed multipart transfer, process asynchronously, encrypt
at rest, expire raw data according to consent, and clearly label the product as
research/educational software rather than a diagnostic device.

## 5. Whole jaw and oral-cavity workflows

Do not send full oral-cavity photographs or radiographs to TRELLIS/Hunyuan and
expect anatomically faithful jaws. General image-to-3D models lack dental
identity, metric scale, hidden roots/internal tissues, FDI ordering, and reliable
multi-object separation. The reported hollow-shell failure is an expected model
and evidence mismatch, not merely a prompt problem.

Use these routes instead:

- **IOS arch:** the scan is already 3D; clean, orient, segment and label it.
- **CBCT:** segment true-scale volume and extract surfaces.
- **Panoramic X-ray:** keep as 2D teaching reference. Oral-3D is a 2021 GAN
  research reconstruction requiring CBCT-derived training fields and a prior
  arch shape; it is not a production path to patient-specific geometry.
- **Photograph:** use only for illustrative reconstruction with a conspicuous
  approximation label, or pair it with an IOS/CBCT source.
- **No patient scan:** start from a licensed, anatomically labelled teaching
  template library and let the educator customize it.

Whole-jaw authoring should be a later, dedicated workspace with odontogram,
upper/lower arch visibility, bite registration, multi-tooth selections, semantic
labels and global orientation—not an enlarged version of single-tooth generation.

## 6. Clinical case creation

### Start from teaching intent

The primary dashboard action should be **Create learning case**, followed by:

- Dental anatomy exploration
- Caries identification or preparation
- Crown preparation
- Endodontic access cavity
- Bridge preparation
- Implant planning simulation
- Custom case

This matches simulator practice more closely than asking educators to begin with
file formats or AI prompts. TrueTeethLab identifies single-tooth models as useful
for anatomy, caries, crown and endodontic access cases, with partial/full jaws
supporting caries, crown, bridge, endodontic and implant cases.

### Case recipe

Each template preconfigures a short recipe:

1. **Learning outcome:** what the learner should demonstrate.
2. **Anatomy:** tooth/arch, dentition, FDI location and source.
3. **Tissues:** enamel, dentin, pulp, caries/lesion and optional bone/gingiva.
4. **Pathology/procedure:** choose preset or paint/describe a region; preview and
   approve the generated geometry.
5. **Learner start state:** viewpoint, visible references, instruments and time.
6. **Assessment:** target preparation, protected regions, tolerance bands,
   critical errors and feedback.
7. **Delivery:** web/VR case and/or simulator geometry export.

For caries, provide clinical controls—surface, site, extent/depth and proximity
to pulp—then translate them into geometry/material masks. Text prompts remain an
optional refinement, not the sole authoring control.

### Case data model

```text
Case
  sourceStudies[]
  modelRevisions[]
  anatomyParts[] { id, label, fdi?, tissue?, confidence, confirmed }
  placements[] { objectId, transform, targetFdi, contactMetrics }
  pathologies[] { type, regionMask, severity, tissueIds, parameters }
  learnerTask { outcome, instructions, startState, allowedTools }
  assessment { targetRegions, protectedRegions, tolerances, criticalErrors }
  exports[] { format, preset, validation, createdAt }
  provenance { models, checkpoints, prompts, seeds, humanApprovals }
```

## Architecture and Modal strategy

Use a modality router and separate versioned workers:

```text
Next.js case API
  -> source inspection/de-identification
  -> job orchestrator
       -> TRELLIS/Nano3D generation-edit worker (Modal GPU)
       -> IOS segmentation worker (Modal GPU)
       -> CBCT segmentation worker (Modal GPU)
       -> mesh placement/repair/export worker (CPU or GPU as profiled)
  -> object storage + immutable revision/provenance database
```

With the available Modal credits, prioritize TRELLIS/Nano3D and segmentation
benchmarks there. Keep the current FAL Hunyuan route as a low-credit fallback
until TRELLIS passes a dental benchmark; provider selection should be server-side
and invisible to the educator.

## Delivery sequence

1. **Foundation:** case types, source classifier, unit/provenance model and
   immutable revisions.
2. **Export centre:** real STL/PLY/OBJ/GLB export with mesh and scale preflight.
3. **Single tooth -> lower jaw:** template/arch import, FDI target, transform,
   contact heatmap and reversible union.
4. **IOS anatomy:** DentalModelSeg baseline, odontogram review, corrected labels,
   per-tooth scene registry.
5. **CBCT anatomy:** DICOM/NIfTI intake, tri-planar viewer, DentalSegmentator,
   then ToothSeg benchmark for instances/FDI.
6. **Case templates:** anatomy, caries, crown and endodontic access first.
7. **Localised generative editing:** masked 2D approval plus Nano3D/custom worker,
   constrained by confirmed anatomy.
8. **Whole-jaw workspace:** bite/antagonist support and multi-tooth cases.
9. **Custom models:** train from confirmed labels, accepted edits, placements and
   case outcomes without coupling the UX to any one research model.

## Safety and validation gates

- Use a separate claim for **illustrative**, **true-scale extracted**, and
  **patient-derived** models.
- Never infer physical scale from an ordinary photograph or raster X-ray.
- Require human confirmation of anatomical labels and generative changes.
- Keep original data and every accepted revision recoverable.
- Validate on missing teeth, restorations, metal artifacts, partial arches,
  wisdom teeth and mixed dentition—not only clean complete arches.
- Treat simulator compatibility as tested per vendor/version; STL acceptance
  alone does not prove haptic material or assessment compatibility.

