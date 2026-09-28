# DentalSculptor anatomy fine-tuning spike plan

**Status:** pre-registered plan before baseline generation or candidate training
**Production policy:** production model and endpoint remain unchanged until every promotion gate passes
**Primary question:** does a small, clinically audited dental cohort measurably improve external crown anatomy without reducing whole-tooth validity, root anatomy, repeatability, or non-molar performance?

**Sealed reference cohort:** `docs/research-artifacts/anatomy-v1/protocol/benchmark_reference_manifest.json` — 32 optimizer-excluded cases, 8 per family, selection seed 20260915, SHA-256 `9151d6a010ddbd4d72f0c81a8031e1e88894f13dd6a01314a8e2190c1c62404f`.

**500-item pre-audit result:** selection fingerprint `718190bef469ff22a0feb4649f32ee7589b8cf77592aaabe8d081b5636e04faf`; 125 items per family, 339 unique groups, but **487 crown-only and 13 whole-tooth items**. Status remains `pending`; this cohort is not authorized for H100 training. Permanent manifest SHA-256: `016c197b40874f2a97babf93fc18a416afb47dcb41f710baab4bcef97a153837`.

## 1. Critical dataset distinction

The current combined dataset is not anatomically uniform:

- Teeth3DS contributes segmentation-derived **crowns**. These improve crown identity, cusps, ridges and grooves but do not supervise roots.
- FDI-16 contributes whole-tooth FDI 16 molars and can supervise crown/root proportion for that tooth class only.
- A renderer receipt proves that images, transforms and files are present. It does **not** prove that the source mesh is clinically suitable.

The displayed certified sample `000173...c8bc8` is Teeth3DS `000930_fdi23`: an upper-left canine crown, 4,459 vertices, 8,643 faces, approximately 7.65 x 7.90 x 8.34 mm. It is untextured, rendered with synthetic grey lighting, has no root, and is flagged `reviewRequired` with `open-mesh-expected-for-ios-segment`.

Therefore v1 must be described as a **crown-anatomy shape-prior experiment**, not evidence of all-tooth root reconstruction. Root preservation is an explicit non-regression gate.

## 2. Shortened, fail-closed decision path

### Gate A — freeze evidence before training

1. Seal 32 subject-disjoint reference meshes: 8 per family.
2. Seal at least 20 licensed/consented clinical images.
3. Record dataset IDs, source groups, hashes, FDI labels, crown/whole-tooth scope and review flags.
4. Generate the unchanged base model with fixed inputs, seeds and quality settings.
5. Store original input, GLB, four turntable images, generation settings, latency and validation report.

Training cannot start if the benchmark hashes or base outputs are missing.

### Gate B — clinically audit a balanced 500-item spike cohort

- 125 incisors, 125 canines, 125 premolars and 125 molars.
- Subject/group-disjoint from reference, clinical and official test cohorts.
- Record crown-only versus whole-tooth scope explicitly.
- Produce a family-stratified contact sheet and review outliers before admission.
- Exclude corrupt, mislabeled, grossly incomplete and implausible meshes.
- Keep expected open cervical boundaries as a declared crown representation, not as whole teeth.
- Require 24/24 views, camera transforms, shape latent, dual grid and receipt for every admitted item.

The initial pre-audit selection failed the whole-tooth supervision check (487 crown-only / 13 whole-tooth). It may be used only for a clearly labelled crown-specialisation experiment. It must not be treated as an all-tooth training cohort or promoted to the whole-tooth production endpoint.

### Gate C — time and validate a bounded H100 calibration

- 100–200 optimizer steps, fixed seed and immutable base checkpoint.
- Record mean/p95 step time, data wait, peak memory, finite loss, checkpoint duration and projected 20k duration.
- Reload the checkpoint in a separate call.
- Abort on non-finite loss, missing state, data leakage, changed code/config pins or incomplete evidence.

### Gate D — small-data spike

Evaluate immutable checkpoints at 250, 500, 1,000 and 2,000 steps. Do not select by training loss alone.

Spike continuation requires:

- valid-mesh rate not below base;
- median reference Chamfer at least 5% better than base;
- HD95 and F-score@2% not worse;
- no tooth-family median regression greater than 2%;
- crown/root proportion not worse on whole-tooth references;
- fixed-seed repeatability at most 0.25% of mesh diagonal;
- visibly improved or preserved cusp/ridge/groove anatomy in blinded review;
- checkpoint reload and deterministic evaluation reproduction.

If the spike fails, stop full rendering/training and revise data or representation. If it passes, continue the remaining preprocessing and full candidate run.

## 3. Parallel work that shortens calendar time

Run these independently:

- CPU/concurrency render benchmark and the balanced 500-item render.
- Reference cohort sealing and unchanged-base generation.
- Clinical-image consent/licence audit.
- Educator scoring form and blinded A/B viewer.
- Automated metric and report verification.

This makes the first meaningful go/no-go decision possible in approximately 24–36 hours, rather than waiting for all 11,577 training items.

## 4. Full candidate only after the spike passes

1. Finish receipt-backed rendering using the fastest certified CPU/container configuration.
2. Write final preprocessing evidence only after exact train-set coverage.
3. Train a versioned candidate from the pinned base checkpoint; never overwrite production.
4. Evaluate checkpoints at 1k, 3k, 5k, 10k and 20k steps with early stopping.
5. Run automated reference metrics, clinical-image validity/repeatability and blinded educator review.
6. Deploy to a separate scale-to-zero candidate endpoint.
7. Promote by configuration only after all gates pass; retain the immutable base revision for rollback.

## 5. Longer representation experiments

The small-data TRELLIS spike is an experiment, not the final model architecture. Run later experiments against the same frozen benchmark:

| Experiment | Representation | Hypothesis |
|---|---|---|
| R0 | Current TRELLIS sparse latent | Establish reproducible fine-tuning baseline |
| R1 | Crown-only quality-filtered cohort | Better occlusal anatomy with less noisy supervision |
| R2 | Crown/root part-aware latent or two-stage model | Preserve roots while specializing crown anatomy |
| R3 | Canonical dental coordinates from CEJ, long axis and landmarks | Reduce pose variance and improve correspondence |
| R4 | Surface points + normals + curvature weights | Preserve cusp tips, grooves and marginal ridges |
| R5 | Landmark/curve graph auxiliary head | Explicitly supervise cusps, pits, ridges, grooves, CEJ and apices |
| R6 | SDF/occupancy or tetrahedral representation | Improve watertightness, thickness and preparation geometry |
| R7 | Statistical-shape/template deformation baseline | Test whether correspondence-driven anatomy beats unconstrained generation |
| R8 | Retrieval plus constrained deformation | Increase repeatability from a single photograph while retaining plausible anatomy |
| R9 | Multi-view/photo-plus-FDI conditioning | Separate visual evidence from tooth identity and expected morphology |

Each experiment changes one major factor at a time, uses identical seeds and held-out cases, and produces an ablation table. Do not compare runs trained on different splits without a clearly labelled secondary analysis.

## 6. Research artifact structure

Store permanent evidence under `docs/research-artifacts/anatomy-v1/`:

```text
protocol/              frozen contracts, hypotheses and analysis plan
data-audit/            provenance, licences, hashes, splits, QC and exclusions
render-gallery/        family-stratified conditioning contact sheets
baseline/              unchanged-model inputs, outputs, settings and metrics
spikes/<run-id>/       config, code pins, logs, losses, checkpoints and reports
candidate/<run-id>/    final candidate evidence
blinded-review/        public A/B cases, private key and completed ratings
statistics/            paired metrics, confidence intervals and family analyses
deployment/            candidate smoke test, promotion record and rollback receipt
```

Never put research evidence only in `test-tmp-*`. Temporary files may be regenerated, but every cited figure and table must be copied into the permanent evidence tree with a manifest and SHA-256 hash.

## 7. Final promotion thresholds

The full candidate must meet the existing contract:

- at least 32 reference cases and 20 clinical cases;
- valid-mesh rate not worse than production;
- at least 10% median Chamfer improvement;
- HD95 and F-score@2% not worse;
- fixed-seed repeatability no greater than 0.25% diagonal;
- at least 60% blinded educator preference;
- no tooth-family median regression;
- explicit whole-tooth/root non-regression.

Failure leaves production unchanged and becomes documented negative experimental evidence.
