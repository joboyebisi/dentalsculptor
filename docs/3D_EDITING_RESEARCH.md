# Localised generative 3D editing — research and delivery plan

**Status:** Recommended Phase D/E bridge  
**Updated:** 17 August 2026

## Decision

Prototype localised editing with Nano3D v1 on Modal, but keep it behind a
provider-neutral job API. The first UX should let an educator choose a model
view, paint a 2D region, select `add`, `remove`, or `replace`, and enter an
instruction. The mask is a hard user-intent constraint; the backend may dilate
and project it, but must not silently edit unrelated anatomy.

Nano3D is a useful research prototype rather than the final production editor.
Its direct GLB-to-edit route renders and re-encodes the mesh and the authors
warn that this is less consistent than their image-to-3D-to-edit route. Dental
models also demand much stricter geometric fidelity than the general objects in
the published examples.

## What Nano3D actually does

Nano3D v1 is a training-free extension of Microsoft TRELLIS (not TRELLIS.2).
For an existing mesh it:

1. renders many views and voxelises/encodes the original asset;
2. renders a front reference view;
3. edits that view with Qwen-Image, or accepts a separately edited image;
4. applies FlowEdit in TRELLIS's sparse-structure and structured-latent stages;
5. merges source and edited voxel/latent regions to preserve unchanged areas;
6. decodes and exports a new GLB.

The repository currently accepts text or a pre-edited image. It does not expose
a user-painted mask in its public inference contract. For DentalSculptor, the
mask must be added to the image-editing step and retained as provenance. It can
also seed Nano3D's source/target difference region, reducing accidental edits.

## Proposed educator workflow

1. Freeze a named revision of the current GLB.
2. Let the user rotate to the best view and capture the exact camera matrix.
3. Paint the editable area on the rendered image. Offer brush, erase, undo,
   clear, and optional selection of a Phase E anatomical part.
4. Enter an instruction and choose `add`, `remove`, or `replace`.
5. Show the masked 2D edit for approval before spending on 3D inference.
6. Submit an asynchronous 3D edit job.
7. Show before/after models with accept, reject, and retry controls.
8. On accept, create a new immutable model revision; never overwrite source.

For dental work, require a warning and explicit approval when the computed edit
extends beyond the painted region or selected anatomical part.

## API contract

```text
POST /api/projects/{projectId}/edit-jobs
multipart/form-data:
  sourceModelUrl: string
  sourceRevisionId: string
  referenceImage: PNG
  maskImage: PNG (white=editable, black=protected)
  camera: { projection, view, model, width, height }
  instruction: string
  operation: "add" | "remove" | "replace"
  selectedPartIds?: string[]
  provider?: "nano3d" | "custom"

-> { jobId, status: "queued" }

GET /api/edit-jobs/{jobId}
-> {
  status, progress, stage,
  preview2dUrl?, resultModelUrl?,
  diffPreviewUrl?, warnings?, metrics?
}
```

Store the source revision, prompt, mask, camera, seed, model/checkpoint version,
result, timings, and acceptance decision for reproducibility and later custom
model training. Do not store identifiable clinical imagery without the existing
consent/de-identification controls.

## Modal deployment shape

Use two GPU functions rather than loading every model into one container:

- **Image edit worker:** source render + mask + instruction -> approved edited
  reference. Qwen-Image in Nano3D's documented local configuration requires at
  least 60 GB VRAM, so start on `A100-80GB` or `H100`. An external masked image
  editor can initially avoid this worker.
- **Nano3D worker:** source GLB + source/edited reference + operation -> result
  GLB. Start on `L40S` (48 GB) and move to `A100-80GB` if profiling shows memory
  pressure or compiled kernels are incompatible.

Build the CUDA extensions into a Modal image, download model weights during the
image build or into a versioned Modal Volume, and load pipelines once in a
`modal.Cls` container. Expose asynchronous job submission rather than holding a
Next.js request open. Use bounded concurrency (initially one request/container),
GPU fallbacks, scaledown windows for warm reuse, and signed object-storage URLs
for inputs/outputs.

Do not deploy the repository's Gradio app as the product API. Extract its
pipeline calls into typed worker methods and pin the Nano3D commit, CUDA, Torch,
and extension versions. The dependency set includes Blender Python, Open3D,
Kaolin, spconv, flash-attention, and custom voxel/raster extensions, so a build
spike is required before estimating latency or credit consumption.

## Alternatives considered

| Approach | Strength | Limitation for DentalSculptor | Decision |
|---|---|---|---|
| Nano3D v1 + TRELLIS | Released code; GLB input; add/remove/replace; latent preservation | Direct mesh route can lose fidelity; no native painted-mask API; heavy stack | Prototype now |
| Steer3D | Fast feed-forward text-steerable editing; direction aligns with future custom model | Newer research model; user mask is not its central interface; integration maturity must be tested | Benchmark next |
| SHAP-EDITOR | Very fast latent editing | Shape-E-era representation and semantic rather than precision dental edits | Research baseline only |
| GaussCtrl / EditSplat / VcEdit | Good multi-view scene/3DGS editing and localisation techniques | Expect trained multi-view Gaussian scenes, not a single generated GLB | Borrow masking ideas; do not adopt pipeline |
| SuperSplat | Excellent browser manual editing of Gaussian splats | Manual 3DGS editor, not instruction-guided GLB geometry editing | Optional future advanced tool |
| Blender-style mesh tools | Deterministic and auditable | Higher learning curve; not generative | Keep as fallback for crop/smooth/sculpt |
| Hunyuan3D-Buffalo / Nano3D v2 | Native unified generation, understanding, and editing is strategically closest | Announced very recently; verify public code/weights and licence before depending on it | Watch/benchmark, do not block prototype |

## Validation gate

Before integration, test at least 20 de-identified dental cases across additions,
removals, and replacements. Record:

- edit success and prompt adherence;
- protected-region vertex displacement and surface-distance error;
- watertightness, self-intersections, floating components, and normal quality;
- preservation of scale, orientation, occlusion, and neighbouring teeth;
- latency, GPU, cold-start, and per-edit cost;
- blinded educator accept/reject rating.

The prototype passes only if unedited anatomy is measurably preserved and every
result is reversible. A visually plausible result is not sufficient for clinical
or assessment use.

## Build sequence

1. **E0 research spike:** reproduce Nano3D on Modal with supplied example assets.
2. **E0.1 dental benchmark:** run existing DentalSculptor/FAL outputs and measure
   direct-GLB degradation before making UI changes.
3. **E0.2 masked 2D approval:** implement render/camera capture, paint mask, text,
   operation selector, and preview approval.
4. **E0.3 asynchronous edit jobs:** add provider-neutral API, storage, progress,
   retry, audit data, and immutable revisions.
5. **E0.4 mask-to-3D constraints:** back-project masks from one or more views and
   intersect them with Phase E tooth/structure labels.
6. **E0.5 provider bake-off:** compare Nano3D, Steer3D, and any released
   Hunyuan3D-Buffalo/Nano3D-v2 implementation on the same cases.
7. **Custom model:** train a feed-forward editor from accepted/rejected revision
   pairs and the saved masks, instructions, anatomical labels, and provenance.

