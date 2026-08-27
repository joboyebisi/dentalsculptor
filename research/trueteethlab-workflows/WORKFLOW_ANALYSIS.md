# Workflow analysis: lessons from TrueTeethLab

**Source reviewed:** Three publicly embedded TrueTeethLab instructional videos  
**Review date:** 17 August 2026  
**Method:** Downloaded MP4s, isolated 16 kHz mono audio, 12-second visual timeline,
contact sheets, and selected key frames. On-screen narration captions and visible
application states were used to reconstruct the workflows. This is a product
workflow analysis, not a verbatim transcript.

## Executive finding

TrueTeethLab succeeds because it gives educators a narrow, recognizable route:
choose the kind of model, upload a known source, review the conversion, attach
clinical metadata, publish, and download. DentalSculptor should preserve this
clarity while adding the educator agency that TrueTeethLab largely omits:
correction of segmentation, generative pathology authoring, tooth placement,
assessment design, open export, provenance, and reversible revisions.

The best shared DentalSculptor spine is:

```text
Choose case -> Add source -> Build anatomy -> Review/correct -> Design task
-> Validate -> Publish/export
```

## Workflow A: Model from snapshot

### Observed sequence

1. Prepare or modify a model in Simodont and create a snapshot/report.
2. Open the Simodont model library and select the source model.
3. Upload the snapshot and associated model/report files.
4. Preview the isolated model.
5. Enter a model name and description.
6. Choose permanent/deciduous dentition and a tooth number.
7. Mark supported procedure categories.
8. Convert/publish the model.
9. Download the resulting model; the UI discloses a credit cost before download.

### What the workflow tells us

- Educators value reusing an existing trusted model library, not always starting
  from patient data.
- A source model and a saved procedural state can be treated as a new reusable
  case template.
- Naming, dentition, tooth identity and supported procedures are part of model
  creation—not administrative fields added later.
- Preview-before-publish and explicit conversion cost are important trust steps.

### DentalSculptor version

Call this **Create from an existing model**:

1. Select a model revision from **My library**, **Institution library**, or a
   licensed teaching template.
2. Choose **Use current state** or **Start from original anatomy**.
3. Optionally add/edit pathology, preparation geometry or target regions.
4. Confirm tooth/arch labels through the odontogram.
5. Define the learner starting state and permitted actions.
6. Add outcome, procedure, difficulty and assessment tolerances.
7. Run case preflight and publish to a course or export target.

Unlike a literal screenshot workflow, DentalSculptor should save the complete
versioned scene state: source revision, transforms, masks, labels, pathology,
camera, learner task and assessment rubric.

## Workflow B: Single tooth from CT/CBCT

### Observed sequence

1. Choose the single-tooth workflow.
2. Acknowledge privacy/consent guidance before uploading patient data.
3. Select and upload a DICOM series.
4. Wait for conversion.
5. Inspect synchronized orthogonal slices and a 3D preview.
6. Adjust model presentation/orientation and centring.
7. Enter the model name and description.
8. Choose permanent/deciduous dentition and FDI tooth number.
9. Mark supported procedures such as cariology, crown, dental anatomy,
   endodontic access, sound tooth and implantology.
10. Convert/publish and download the simulator model locally.

### What the workflow tells us

- The expected source is a DICOM study, not a generic image upload.
- Consent is part of the workflow itself.
- Educators need both slice evidence and a 3D preview before accepting anatomy.
- Centring and orientation affect downstream haptic use and deserve an explicit
  review step.
- A model is not complete until its clinical identity and intended procedures
  are declared.
- The tool is transient: narration states that uploaded scans and results are
  not retained. DentalSculptor may retain data only under an explicit project
  retention policy and should offer an ephemeral mode.

### DentalSculptor version

Call this **Single-tooth clinical case**:

1. Select teaching intent first: anatomy, caries, crown or endodontic access.
2. Add a DICOM/NIfTI tooth scan, an IOS/mesh, a photograph-based illustrative
   source, or a template. Clearly label each evidence level.
3. De-identify, crop and quality-check locally where possible.
4. Show axial/coronal/sagittal slices plus the reconstructed model.
5. Automatically segment enamel, dentin and pulp where supported; expose a
   correction/approval step rather than treating prediction as truth.
6. Confirm FDI number, dentition, orientation, scale and origin.
7. Author pathology/procedure using clinical controls plus optional generative
   editing.
8. Define learner instructions, protected tissues and scoring tolerances.
9. Validate mesh, tissues, scale and case behavior.
10. Publish a versioned web/VR case and/or export STL/PLY/vendor package.

## Workflow C: Partial/full jaw CBCT

### Observed sequence

1. Choose the full/partial-jaw CBCT workflow.
2. Upload a DICOM series and wait for conversion.
3. Inspect orthogonal volume views and the reconstructed arch.
4. Review automatic segmentation of all teeth.
5. Select teeth and assign tooth numbers through an odontogram-like control.
6. Choose up to three drillable teeth; additional teeth are exported as
   non-drillable context.
7. Add case metadata and supported procedures.
8. Publish/convert the model.
9. Review segmentation through linked 2D and 3D previews.
10. Download the resulting model.

The video describes a maximum volume of eight consecutive teeth for that
release. This is a product constraint, not a clinical standard; DentalSculptor
should expose current compute/quality limits honestly but avoid encoding an
arbitrary fixed maximum into the case model.

### What the workflow tells us

- Jaw cases distinguish **active/drillable anatomy** from contextual anatomy.
- Tooth selection and numbering are explicit educator decisions even after
  automatic segmentation.
- A segmentation preview remains necessary after conversion.
- Partial-jaw workflows are valuable on their own and should not be treated as
  failed full-jaw uploads.

### DentalSculptor version

Call this **Arch or multi-tooth case**:

1. Choose partial arch, full arch, or tooth-in-jaw placement.
2. Upload CBCT, IOS mesh, or a labelled teaching template.
3. Crop/orient and inspect the source in volume or surface views.
4. Segment teeth, gingiva/bone and other supported anatomy.
5. Review an odontogram with predicted FDI labels; correct split, merge, missing
   and duplicated structures.
6. Assign each part a role:
   - **Target** — learner may cut/manipulate it;
   - **Protected** — contact/removal is penalized;
   - **Context** — visible/haptic context but not assessed;
   - **Hidden reference** — scoring geometry unavailable to learner.
7. Place/replace teeth if required, with contact heatmaps and antagonist checks.
8. Add pathology and define the learner task.
9. Preview the exact learner experience and assessment overlay.
10. Publish/export with per-part semantics and a compatibility report.

## Recommended case-creation UI

### Entry screen: start with teaching intent

Use large case cards:

- Anatomy exploration
- Caries
- Crown preparation
- Endodontic access
- Bridge preparation
- Implant case
- Custom case

After selection, ask for anatomy scope:

- Single tooth
- Tooth in jaw
- Partial arch
- Full arch

Only then ask for a source. This reverses the TrueTeethLab order but preserves
its narrow workflow: educational intent configures required tissues, validation,
assessment and compatible sources before the educator uploads anything.

### Persistent case rail

```text
1 Case goal
2 Source
3 Anatomy
4 Pathology/task
5 Assessment
6 Validate
7 Publish
```

Each step has `not started`, `needs review`, `complete`, or `warning`. The main
canvas changes between upload, volume review, 3D editing and learner preview,
while the rail preserves orientation and progress.

### Anatomy review workspace

- Left: steps, odontogram and anatomy tree.
- Centre: 3D model or synchronized volume slices.
- Right: selected structure identity, confidence, tissue, role and correction
  tools.
- Bottom: previous/current prediction comparison and revision controls.

The primary action is **Confirm anatomy**, not **Convert**. This makes the
educator's authority visible and creates high-quality correction data.

### Case design workspace

- Structured pathology/procedure controls first.
- Optional prompt and mask editing second.
- Learner-task panel: instructions, tools, time and starting view.
- Assessment panel: target, protected regions, tolerances and critical errors.
- One-click **Preview as learner**.

### Publish/export workspace

Separate three destinations:

- Publish to DentalSculptor course/library.
- Export standard geometry: STL, PLY, OBJ, GLB.
- Export simulator-specific package where tested.

Show processing time/credit estimate before a paid GPU action, and show which
labels/materials will be lost before format conversion.

## Product requirements derived from the videos

### Must-have

- Modality-specific workflows rather than one universal upload.
- DICOM series/folder upload with conversion progress.
- Privacy consent and de-identification review before upload.
- Linked slice and 3D previews.
- Explicit orientation, scale and origin confirmation.
- Automatic segmentation with human review.
- FDI/deciduous numbering through an odontogram.
- Target/protected/context anatomy roles.
- Name, description, procedure and teaching metadata before publish.
- Preview-before-publish and downloadable output.
- Clear processing/cost estimate and data-retention policy.

### DentalSculptor differentiators

- Create cases from photographs, IOS meshes, CT/CBCT, existing models and
  labelled teaching templates with honest evidence labels.
- Paint/text-guided local 3D editing constrained by confirmed anatomy.
- Generated-tooth placement into a jaw with collision/contact feedback.
- Educator correction of segmentation and labels.
- Pathology recipes rather than prompt-only authoring.
- Assessment zones and learner-state design.
- Open interchange plus vendor-specific adapters.
- Immutable revisions, provenance and reusable institutional libraries.

## Suggested first four case templates

### 1. Dental anatomy — single tooth

Required anatomy: enamel/dentin/pulp when available. Educator confirms tooth,
orientation and labels, chooses visible layers and annotations, then publishes
an exploration case.

### 2. Caries — single tooth

Educator selects tooth/surface, lesion site, depth and pulp proximity. The app
generates or edits the lesion under a tissue-aware mask. Assessment measures
caries removal, healthy-tissue preservation and pulp exposure.

### 3. Crown preparation — tooth in jaw

Educator selects or places the target tooth in a partial arch, marks neighbours
as protected and defines reduction/taper/margin tolerances. Learner preview
includes contextual teeth while scoring the target preparation.

### 4. Endodontic access — single tooth

Educator confirms pulp/canal anatomy, chooses the desired access target and
protected floor/walls, then defines critical errors and completion criteria.

## Evidence and limitations

- The visual/audio review reflects the publicly embedded versions available on
  the review date; TrueTeethLab may change its workflows later.
- Some workflow facts were visible in narrated on-screen captions rather than
  independently verified product documentation.
- Simulator packages and drillable/non-drillable tissue behavior are proprietary;
  DentalSculptor must validate actual vendor interfaces before claiming direct
  compatibility.
- Downloaded media is retained locally for internal analysis and excluded from
  source control.

