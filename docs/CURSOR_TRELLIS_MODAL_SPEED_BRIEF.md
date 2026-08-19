# Cursor brief: make TRELLIS.2 on Modal fast

## Objective

Optimize the existing direct TRELLIS.2 integration for interactive DentalSculptor generation. Do not deploy ComfyUI in production. The referenced video uses a ComfyUI TRELLIS2 workflow, but its useful ideas are the pipeline stages and optimized CUDA dependencies; our service should continue calling `Trellis2ImageTo3DPipeline` directly.

Existing implementation:

- `dentalsculptor-ml/modal_app/app.py`
- `dentalsculptor-ml/modal_app/images/trellis_gpu.py`
- `dentalsculptor-ml/modal_app/workers/trellis_generator.py`
- `dentalsculptor-ml/modal_app/trellis_config.py`

Do not replace these with a generic Modal or ComfyUI template. Preserve webhook authentication and the existing Next.js provider contract.

## Product latency contract

Treat generation as four separately measured intervals:

1. Modal queue/cold-start time
2. model-load/warm-up time
3. TRELLIS generation time
4. GLB extraction, serialization, upload and download time

Targets must be validated by benchmarks, not assumed:

| Mode | Intended UX | Resolution | Initial target on H100 |
|---|---|---:|---:|
| Preview | fast first result for inspection | 512 | p50 <= 12 s warm |
| Standard | default tooth-authoring result | 1024 cascade | p50 <= 30 s warm |
| Final | high-detail export requested explicitly | 1024, larger mesh/texture | p50 <= 45 s warm |

The official TRELLIS.2 reference reports approximately 3 seconds for 512 cubed and 17 seconds for 1024 cubed on H100 for shape plus material generation. Our end-to-end targets are deliberately higher because preprocessing and GLB extraction also cost time.

## Required implementation

### 1. Keep one resident model per GPU container

Retain `@app.cls` and `@modal.enter`. Load the pipeline once in `load_model()` and reuse it for all calls handled by that container. Never download weights or call `from_pretrained()` inside `generate()`.

Set production defaults initially to:

```python
gpu="H100"
min_containers=1
buffer_containers=0
scaledown_window=1200
max_containers=1
```

Keep development at `min_containers=0` to avoid burning credits while idle. Make GPU type and warm-pool values environment-driven. Do not enable concurrent GPU inference in one container: TRELLIS.2 has a large memory footprint and two simultaneous jobs can cause OOM or latency spikes. Scale to additional containers later only after one-container reliability is measured.

### 2. Download weights before serving

Add a Modal image build/download function that snapshots all required Hugging Face repositories into the existing `trellis2-hf-cache` Volume:

- `microsoft/TRELLIS.2-4B`
- the exact DINOv3 repository loaded by the pinned TRELLIS.2 commit
- the exact background-removal repository loaded by that commit

Use pinned revisions. Set `HF_HUB_OFFLINE=1` for serving only after a deployment smoke test proves every artifact is cached. A serving container must fail clearly if an artifact is missing; it must not silently download several gigabytes on the first user request.

### 3. Preserve the optimized CUDA path

Keep the current CUDA 12.4/PyTorch 2.6 combination and pinned native dependencies until benchmarks justify a change. Preserve:

```text
ATTN_BACKEND=flash_attn
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

The image build must compile FlashAttention, CuMesh, FlexGEMM, nvdiffrast and O-Voxel ahead of serving. Do not perform compilation on container boot or on the first request.

In `load_model()`:

- call `torch.set_grad_enabled(False)`;
- enable TF32 for CUDA matmul where it does not alter dental acceptance results materially;
- load the pipeline, move it to CUDA, and run one small deterministic 512 warm-up inference if this is stable;
- record separate import, load, CUDA-transfer and warm-up timings.

Do not add `torch.compile` yet. TRELLIS uses custom sparse/CUDA operations and compile time can make cold starts worse. Add it only behind an experiment flag and retain it only if a five-run benchmark proves lower total latency.

### 4. Add explicit quality presets

Replace the single global output configuration with validated server-side presets. The API may accept `quality`, but must not accept arbitrary sampler or memory parameters from the browser.

```python
QUALITY_PRESETS = {
    "preview": {
        "pipeline_type": "512",
        "steps": 8,
        "decimation_target": 100_000,
        "texture_size": 1024,
    },
    "standard": {
        "pipeline_type": "1024_cascade",
        "steps": 12,
        "decimation_target": 300_000,
        "texture_size": 2048,
    },
    "final": {
        "pipeline_type": "1024_cascade",
        "steps": 12,
        "decimation_target": 1_000_000,
        "texture_size": 4096,
    },
}
```

Benchmark 8 versus 12 sampler steps on a fixed dental validation set before making preview the default. The preview result is for authoring feedback, not final anatomical approval.

### 5. Remove avoidable work from the critical path

- Decode and normalize the uploaded image once.
- Continue passing `preprocess_image=False` after explicit preprocessing.
- Validate MIME type, pixel count and file size before GPU work.
- Do not render preview turntable videos in the generation request.
- Do not call `torch.cuda.empty_cache()` after every successful request. It can reduce reuse performance. Reserve it for OOM recovery or the 1024-to-512 retry path, and verify GPU memory across 20 sequential calls.
- Keep the nvdiffrast face-limit simplification, but do not simplify twice.
- Measure `to_glb` separately because decimation, remeshing and texture baking can dominate after the diffusion stage.
- Export GLB with WebP textures if supported by the pinned exporter and all current viewers; otherwise keep the compatible encoding.

### 6. Stop returning large GLBs as base64 in JSON

Base64 increases payload size and forces additional copies in Python, Next.js and the browser. Change the production contract to:

1. create a generation job;
2. Modal produces the GLB;
3. upload the GLB to the existing private S3 asset bucket;
4. save the result URL/key and timing metadata in job status;
5. return a short-lived signed URL to Next.js.

Keep base64 only behind a development compatibility flag until the Next.js route has migrated. Do not expose a permanently public object URL.

### 7. Make generation asynchronous

The public create endpoint should return `202` plus `jobId` quickly. Spawn GPU work and use the existing job-status pattern. Report these stages:

```text
queued -> starting -> preprocessing -> generating_shape -> generating_material
-> extracting_mesh -> uploading -> completed | failed
```

The UI should show a fast preview option first and allow a user to request Final quality only when needed. A cancelled browser request must not corrupt job state.

### 8. Add production telemetry and a benchmark command

For every request record:

- quality and actual pipeline type;
- GPU model;
- cold versus warm container;
- queue time if available;
- preprocessing, generation, GLB extraction, serialization and upload seconds;
- input/output byte sizes;
- peak allocated and reserved CUDA memory;
- fallback/retry reason;
- seed and pinned TRELLIS commit.

Add `dentalsculptor-ml/scripts/benchmark_trellis_modal.py`. It should run the same 10 representative tooth images with fixed seeds on L40S, A100-40GB and H100, with one cold run and five warm runs per preset. Produce JSON and Markdown with p50, p95, failure rate, peak VRAM and estimated cost per successful model.

Do not choose H100 or L40S from intuition alone. Select the production GPU from measured standard-preset latency, success rate and cost. H100 is the expected latency leader; Modal recommends L40S as the general inference cost/performance starting point.

## Dental quality gates

Speed changes cannot ship based only on attractive meshes. Use a fixed set containing anterior teeth, premolars, molars, partial occlusion, reflective enamel and imperfect backgrounds. For each configuration compare:

- silhouette fidelity from at least four views;
- crown/root completeness where visible in the source;
- cusp and fissure preservation;
- holes, disconnected components and non-manifold geometry;
- editability and successful GLB-to-STL export;
- educator blind preference against the current standard preset.

The 512 preview can be accepted with lower surface detail, but it must not introduce a misleading tooth class or gross anatomy.

## Delivery sequence

1. Add benchmark and observability without changing output.
2. Benchmark current A100-40GB baseline.
3. Add quality presets and remove per-success `empty_cache()`.
4. Pre-cache all weights and introduce the environment-driven warm-pool configuration.
5. Benchmark H100, A100-40GB and L40S.
6. Switch production GPU based on results.
7. Migrate base64 response to async S3 result URLs.
8. Run 20 sequential standard jobs and the dental quality gate.

## Acceptance criteria

- No model/network download or native compilation occurs in a user request.
- The second request in the same container does not reload the pipeline.
- Twenty sequential standard jobs complete without increasing memory indefinitely.
- The API returns structured stage and timing data.
- Preview, standard and final presets are covered by tests.
- The old base64 contract remains available only during migration and is removed after the Next.js client switches.
- Benchmark evidence, including cold and warm results, is committed under `docs/benchmarks/`.
- Documentation states the chosen GPU, measured latency, estimated cost per success and the warm-container monthly burn rate.

## Prompt to paste into Cursor

```text
Implement docs/CURSOR_TRELLIS_MODAL_SPEED_BRIEF.md in this repository.

Start by reading the four existing TRELLIS files listed at the top of the brief and the Next.js Modal provider/routes. Preserve existing authentication, fallbacks and unrelated worktree changes. Work in the delivery sequence from the brief. Do not deploy ComfyUI and do not replace direct Trellis2ImageTo3DPipeline inference.

First commit-sized outcome: add observability, environment-driven Modal GPU/warm-pool settings, quality presets, safe CUDA inference settings, removal of successful-request empty_cache(), tests, and the benchmark script. Do not change the production response contract in that first outcome.

Second outcome: implement the asynchronous S3 result-URL contract end to end behind a feature flag, including database/job-state migration and backward compatibility. Never make the bucket public.

Before claiming success, run relevant Python and Next.js tests and report exact results. If Modal credentials are available, deploy a development app and execute the benchmark matrix. If they are unavailable, stop before deployment and give the exact commands I should run. Do not invent latency numbers.
```

## Sources

- Video reviewed: https://www.youtube.com/watch?v=KUNLitkYdwM
- ComfyUI wrapper demonstrated by the workflow: https://github.com/PozzettiAndrea/ComfyUI-TRELLIS2
- Official TRELLIS.2 implementation and H100 timings: https://github.com/microsoft/TRELLIS.2
- Modal GPU selection: https://modal.com/docs/guide/gpu
- Modal cold-start controls: https://modal.com/docs/guide/cold-start
- Modal model-weight storage and `@modal.enter`: https://modal.com/docs/guide/model-weights
- Modal Volumes: https://modal.com/docs/guide/volumes
- Modal Memory Snapshots: https://modal.com/docs/guide/memory-snapshots
