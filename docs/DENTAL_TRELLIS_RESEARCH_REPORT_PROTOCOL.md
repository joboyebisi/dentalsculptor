# DentalSculptor anatomical reconstruction research protocol

**Status:** prospective protocol revision after the TF-PW32 step-50 canary
**Date:** 19 September 2026
**Claim boundary:** external whole-tooth morphology for education; not diagnosis, treatment planning, or restoration manufacture
**Production policy:** no candidate reaches production until the registered gates pass on two training seeds

## 1. Research question

What is the smallest clinically reviewed, patient-separated and tooth-family-balanced dataset that can improve image-conditioned whole-tooth reconstruction over unchanged TRELLIS.2 without degrading crowns, roots, mesh usability, or fixed-input repeatability?

The primary estimand is the paired change in whole-tooth symmetric surface distance on a sealed external test set. Crown and root regions, tooth family, source domain and viewpoint are pre-specified strata rather than post-hoc subgroups.

## 2. Upstream implementation pinned for reproduction

| Component | Pinned value |
|---|---|
| Base model | `microsoft/TRELLIS.2-4B` |
| Base model revision | `af44b45f2e35a493886929c6d786e563ec68364d` |
| TRELLIS.2 inference commit | `1762f493fe7731a3b7cc6b79ad5da7b015b516c1` |
| TRELLIS.2 training commit | `75fbf0183001ed9876c8dbb35de6b68552ee08bd` |
| Training objective | official flow-matching implementation |
| Image encoder | frozen DINOv3 ViT-L/16, revision recorded in each run receipt |
| Shape latent normalization | official 32-channel mean/std from the pinned config |
| Default production inference | `1024_cascade`, 12 sampler steps, fixed image-derived seed |

Every run must additionally record the repository commit, complete resolved config, command line, container image digest, CUDA/PyTorch versions, GPU type, world size, dataloader worker count, dataset/cohort fingerprint, checkpoint hashes, sampler parameters and wall-clock/GPU time.

## 3. Source-code findings that change the experimental design

### 3.1 Establish the representation ceiling before flow fine-tuning

TRELLIS.2 first encodes geometry into O-Voxel/SC-VAE latents and only then learns image-conditioned flow. The official paper trains the shape VAE with geometric terms plus high-resolution rendered mask, depth, normal, SSIM and LPIPS supervision. A flow model cannot recover anatomical information that the frozen encoder/decoder already destroys.

**Required E0 test:** for every frozen validation/test mesh, run mesh → O-Voxel → frozen shape encoder → frozen shape decoder → mesh, then compare the reconstruction with the source. Report whole-tooth, crown and root metrics. If cusps, root count, furcations or apices fail here, evaluate SC-VAE adaptation before spending on flow fine-tuning.

### 3.2 Isolate 512 learning from cascade behaviour

Official `1024_cascade` inference uses the 512 shape-flow model first and then the separate 1024 shape-flow model. TF-PW32 changed only `shape_slat_flow_model_512`; the unchanged 1024 stage can attenuate, overwrite or transform that effect.

Every 512 candidate therefore requires both:

1. a direct `pipeline_type=512` paired evaluation, measuring whether the trained component learned; and
2. a `pipeline_type=1024_cascade` paired evaluation, measuring end-product utility.

If 512 passes but cascade does not, use the official 1024 fine-tuning config initialized from the accepted 512 checkpoint. Do not interpret a cascade-only result as a clean test of the 512 model.

### 3.3 Treat conditioning views correctly

The official `ImageConditionedMixin` randomly selects **one** available conditioning render per item on each access. Eight or sixteen stored views are therefore a viewpoint-augmentation pool, not simultaneous multiview conditioning. The study must report the camera distribution and number of unique views actually observed during training. Real-photo evaluation remains separate because synthetic renderer views do not establish clinical-photo domain generalization.

### 3.4 Audit token and latent distributions

The official 512 shape dataset excludes assets above 8,192 structured-latent tokens; the 1024 configuration permits 32,768. Whole teeth with multiple roots may sit near or beyond these limits. For every cohort report:

- tokens per tooth and exclusion counts by family/root count;
- per-channel latent mean/std and standardized distance from the base normalization;
- active voxel counts and spatial occupancy;
- whether token filtering disproportionately removes molars or complex roots.

No silent family-dependent filtering is allowed.

### 3.5 Fail closed on data-loader errors

The official dataset base catches a loading exception and substitutes a random item recursively. This is convenient for large web-scale training but can silently alter a 32–128 item medical-anatomy cohort. All files must be read and decoded in a preflight, and the research wrapper must count substitutions and abort if the count is non-zero.

### 3.6 Separate topology stages

Official GLB postprocessing with `remesh=True` performs narrow-band dual-contouring remeshing and simplification. Unlike the non-remesh branch, it does not subsequently call the small-component-removal and non-manifold-repair sequence. Topology must be measured at:

1. decoded mesh before GLB postprocessing;
2. post-remesh mesh before UV unwrapping;
3. final GLB after UV unwrapping/export.

Report connected components, component surface-area distribution, boundary-loop count and boundary-loop size. Report both exact indexed topology and a coincident-position welded control because UV charts duplicate vertices. Never substitute the welded number for the exact export, and do not use largest-component deletion as an anatomical repair. The first E1 trace showed both phenomena: genuine fragmentation was already present in the decoded geometry, while final GLB UV indexing greatly inflated the apparent component count.

### 3.7 Preserve official optimization controls unless ablated

The pinned 512 shape-flow config uses bf16 AMP, AdamW, EMA `0.9999`, classifier-free condition dropout `0.1`, uniform flow time sampling, adaptive 95th-percentile gradient clipping and an effective per-GPU batch of eight split into two micro-batches. The sparse-structure model uses a different logit-normal time schedule and four-way batch splitting. These are stage-specific controls and must not be casually interchanged.

## 4. Registered experiment matrix

### E0 — representation ceiling

- Frozen SC-VAE encode/decode of source meshes.
- No image conditioning and no flow sampling.
- Primary purpose: determine whether the base latent representation preserves dental morphology.
- Implemented as `evaluate_shape_vae_representation_ceiling`; it consumes the
  previously sealed official encoder latents and calls only the frozen shape
  decoder. Flow, texture and GLB postprocessing are explicitly absent.

### E1 — inference and postprocessing ablation

- Raw model at `512`, `1024`, and `1024_cascade`.
- `remesh=True` and the official non-remesh cleaning branch, where export compatibility permits.
- Geometry measured before and after postprocessing.
- Fixed image, seed and sampler parameters.
- Implemented as `trace_generation_topology_stages`; each stage is persisted,
  hashed and compared with the same reference mesh. Exact indexed topology and
  a coincident-vertex welded geometry control are both retained.

## 4.1 First executed E0/E1 evidence (19 September 2026)

The family-balanced four-case TF-PW32 E0 engineering canary completed on the
pinned frozen 512 shape SC-VAE. Mean symmetric Chamfer was **0.438071%** of the
reference diagonal, HD95 **0.850944%**, F-score at 1% **0.980912**, F-score at
2% **1.0**, and sorted-extent relative error **0.000132**. This supports a
narrow engineering conclusion: the frozen representation retains global
whole-tooth surface geometry on these four cases well enough that another
shape-flow experiment is not automatically blocked by a gross representation
ceiling. It does not establish landmark, crown/root regional, or clinical
adequacy.

Topology is not clean at that ceiling. The decoded incisor, for example, was
non-watertight with 105 indexed components, 520 boundary edges and 258
non-manifold edges even though 99.98% of area remained in its largest
component. The decoder/dual-grid path therefore needs topology-aware handling
even when surface-distance metrics are strong.

The latest unchanged-model E1 `512` trace used the same seed and one sealed
incisor render. The pipeline-decoded mesh had 811 coincident-welded geometry
components. Narrow-band remeshing reduced this to 53; the main component held
more than 99% of surface area. The final indexed GLB reported 8,901 components,
but coincident-position welding reduced it to 43 components; 8,858 apparent
components were UV-seam/index splits. Thus:

1. real fragmentation originates before GLB export in image-conditioned
   generation;
2. remeshing substantially consolidates it but leaves non-manifold/disconnected
   geometry; and
3. indexed GLB component count alone is not a valid geometry-fragmentation
   metric without the welded control.

These are engineering canaries, not the frozen clinical validation cohort.
They reject the earlier plan to respond by merely training longer or deleting
all but the largest component.

Two nominally identical fixed-seed 512 diagnostic launches did not produce the
same topology distribution. Because the initial harness reused one output path,
only the latest canonical report remains on the research volume. This is a
protocol deviation and a repeatability-gate failure, not evidence to average
away. E1 now requires a unique immutable `trial_id`; rerunning an existing ID
fails closed. At least two preserved trials per retained configuration are
required before interpreting stage metrics.

Strict deterministic controls are now applied after model loading (the service
loader otherwise re-enables TF32): CUBLAS workspace `:4096:8`, TF32 disabled
for matmul and cuDNN, deterministic cuDNN, and PyTorch deterministic algorithms.
The runtime state is asserted and recorded. Two strict trials landed on
different Modal A100-80GB variants (PCIe versus SXM4), so they form a
cross-hardware test rather than a same-device proof. Their artifacts were not
byte-identical. Final-stage reference deltas were small (Chamfer +0.000115
percentage points, HD95 +0.09333, F2 +0.003739), but welded component count
differed by six. Direct trial-to-trial comparison, calibrated against
independent surface-sampling noise, subsequently passed at decoded, remeshed
and final stages. The final meshes had F-score 0.999625 at 2% of tooth diagonal
and extent error 0.004135.

A stronger paired experiment then ran the same input and seed twice
sequentially inside one container, after one model load, on the same A100 PCIe.
The two raw decoded PLY files were byte-identical (the same SHA-256), with
identical 1,893,814-face topology. Fixed-runtime 512 generation therefore
passes the repeatability gate. Cross-hardware byte identity is not claimed;
fixed hardware, software and determinism controls remain part of the contract.

Repeatability does not solve the topology defect: the identical decoded result
still contained 725 coincident-welded components, 26,249 boundary edges and
26,329 non-manifold edges. E1 localizes the main blocker to generated/decoded
geometry rather than random reruns or GLB serialization.

The subsequent resolution ablation rejected direct 1024: although final
Chamfer/F2 improved, welded components increased from 52 at 512 to 1,292 and
largest-component area fell to 69.46%. The 1024 cascade retained 99.80% in its
largest component and reduced final welded components to 45, with better
Chamfer and F2 than 512, but HD95 and extent error regressed. Cascade is thus
the only retained architecture for E3; the result is not a promotion pass.

### E2 — family-homogeneity pilot

- Four separate clinically accepted 32-tooth cohorts: incisor, canine, premolar, molar.
- One combined 128-tooth cohort containing exactly the same teeth.
- Patient-separated training/validation/test sets.
- This tests whether small homogeneous cohorts learn more efficiently than a heterogeneous cohort.

### E3 — model-stage ablation

- Shape-flow only.
- Sparse-structure-flow only.
- Sparse structure followed by shape flow.
- Optional 1024 shape-flow adaptation only after a 512 checkpoint passes.
- Texture flow remains frozen for the anatomy study.

### E4 — sample-efficiency ladder

- Nested clinically accepted cohorts: 32, 64, 128, 256 and 500.
- Equal example exposure as the main comparison; equal optimizer-step results reported separately.
- Two training seeds per retained configuration.
- Checkpoints evaluated at prospective intervals, initially 250, 500, 1,000 and 2,000 steps.
- Stop early on validation, root, family or topology regression.

### E5 — external and educator validation

- External real photographs not used for synthetic conditioning renders.
- Tooth-family and viewpoint strata fixed in advance.
- Blinded, randomized side-by-side educator assessment.
- Report inter-rater reliability and adjudication procedure.

## 5. Outcomes

### Primary

- Paired symmetric point-to-surface distance on the sealed external whole-tooth set, normalized by reference bounding-box diagonal.

### Required geometric non-regression

- HD95 and surface F-score at 1% and 2% reference diagonal;
- point-to-mesh distance and F-score where internal structures are evaluated;
- separate crown and root surface distances;
- crown/root length and volume ratios;
- root count, furcation preservation and apex completeness;
- sorted-extent error;
- normal-map PSNR/LPIPS for surface-detail preservation;
- decoded/pre-remesh/final topology measures;
- valid-mesh and successful-export rates;
- fixed-image/fixed-seed byte or geometry repeatability.

### Statistical reporting

- Paired per-case differences, not only aggregate means;
- median, mean, standard deviation and stratified-bootstrap 95% intervals;
- family-level estimates even when the overall mean improves;
- correction or hierarchical modeling for multiple secondary outcomes;
- effect sizes and intervals alongside p-values;
- all failures retained in the denominator.

The provisional sample-efficiency threshold remains at least 5% median Chamfer improvement with its stratified-bootstrap interval excluding zero and no required endpoint regressing on both training seeds. Production retains the stricter promotion gate.

## 6. Paper structure

The manuscript should adopt the useful features of Zamani et al., *End-to-End Fine-Tuning of 3D Texture Generation using Differentiable Rewards* (arXiv:2506.18331v3)—a mathematical method description, explicit algorithm, qualitative and quantitative comparisons, repeated experiments, user study and failure/regularization appendices—while disclosing more implementation detail.

1. **Abstract:** pre-specified question, datasets, sample sizes, model stages, primary result and claim boundary.
2. **Introduction:** educational need, whole-tooth reconstruction gap and minimal-data hypothesis.
3. **Related work:** image-to-3D, dental mesh/CBCT datasets, O-Voxel/TRELLIS.2, domain adaptation and anatomical evaluation.
4. **Data:** licences, archive hashes, inclusion/exclusion, clinical review, patient splits, cohort construction and leakage audit.
5. **Method:** representation conversion, model stage, losses, conditioning views, training schedule and export path, with pseudocode.
6. **Prospective evaluation:** frozen endpoints, statistical plan, stopping and promotion rules.
7. **Results:** cohort flow diagram, E0 ceiling, stage ablations, learning curve, per-family results, failure rates and compute.
8. **Educator study:** recruitment, expertise, blinding, randomization, questions, inter-rater agreement and analysis.
9. **Discussion:** what improved, what did not, domain shift, CBCT limits and educational—not clinical—scope.
10. **Limitations and negative results:** include TF-PW32 step-50 and unsuccessful configurations.
11. **Reproducibility statement:** exact commands/configs, environment lock, hashes, seeds, splits, checkpoints and artifact availability.
12. **Appendices:** preprocessing receipts, hyperparameter tables, metric definitions, additional cases, protocol deviations and complete failure gallery.

## 7. Reproducibility artifact bundle

Each reported experiment must publish or retain, subject to dataset licences:

- protocol and dated amendments;
- machine-readable inclusion/exclusion manifest;
- patient-level split manifest and leakage audit;
- source, canonical mesh, render and latent hashes;
- resolved training and inference configs;
- exact command, code/container/model revisions and dependency lock;
- RNG seeds, world size and hardware;
- complete loss/gradient/validation logs;
- raw and EMA checkpoint identities;
- per-case predictions and metrics, including failures;
- analysis script and environment;
- blinded educator-study instrument and anonymized responses;
- compute time, GPU-hours and estimated cost.

## 8. Current evidence boundary

TF-PW32 step-50 is a valid negative engineering result. It demonstrated end-to-end checkpoint creation and strict inference loading but failed the registered preliminary anatomy screen. Its 0.68% relative Chamfer movement is below the 5% research threshold, while HD95, F-score and whole-tooth extent error regressed. It is not evidence of anatomical improvement and remains excluded from production.

## References used to revise this protocol

- Microsoft, TRELLIS.2 source and training documentation: https://github.com/microsoft/TRELLIS.2
- Xiang et al., *Native and Compact Structured Latents for 3D Generation*: https://arxiv.org/abs/2512.14692
- Zamani et al., *End-to-End Fine-Tuning of 3D Texture Generation using Differentiable Rewards*: https://arxiv.org/abs/2506.18331
- DataMeister, *Three Challenges in Finetuning Trellis*: https://datameister.ai/blog/three-challenges-in-finetuning-trellis/
- TRELLIS.2 community fine-tuning report: https://github.com/microsoft/TRELLIS.2/issues/138
