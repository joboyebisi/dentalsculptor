# ToothFairy whole-tooth minimal-data method

**Protocol status:** pre-registered; first bounded candidate evaluated and rejected
**Purpose:** improve whole-tooth external morphology while identifying the smallest sufficient training cohort.
**Production policy:** research candidate only; the deployed reconstruction model remains unchanged until every promotion gate passes.

## Claim boundary

ToothFairy CBCT labels can supply all-family crown-and-root geometry after conversion to individual meshes. They do not have the same surface fidelity as intraoral scans, and a CBCT segmentation is not accepted merely because it can be meshed. Each tooth requires physical-space extraction, apex/FOV checks, topology review and clinical acceptance.

The study concerns anatomical reconstruction for education. It does not validate diagnosis, patient-specific treatment or restoration manufacture.

## Frozen research question

What is the smallest clinically audited, family-balanced whole-tooth cohort that produces a reproducible improvement over the unchanged base model without degrading crowns, roots, any tooth family, mesh validity or fixed-input repeatability?

The **minimum sufficient cohort (MSC)** is the smallest nested cohort passing every registered gate on two independent training seeds. We will not call the best-looking checkpoint the MSC, change thresholds after observing results, or use the sealed benchmark for model selection.

## Data path and evidence

1. Obtain the official ToothFairy2 July 7, 2024 challenge release under its account-gated terms and record the download source, release, licence and archive hashes. The converter supports its native `.mha` files; no lossy intermediate volume conversion is required.
2. Retain the original CBCT and FDI label volumes read-only.
3. Extract each permanent tooth with `scripts/toothfairy_ingest.py`.
4. Apply the NIfTI affine so vertices remain in physical world millimetres.
5. Save unsmoothed per-tooth PLY files and a subject receipt before repair or canonicalisation.
6. Flag every label touching a volume boundary as possible root/apex truncation.
7. Clinically review tooth identity, crown/root completeness, gross segmentation leakage, restorations, impactions and artifacts.
8. Canonicalise accepted meshes in a separately versioned stage; never overwrite raw meshes.
9. Generate identical 24-view conditioning renders and TRELLIS preprocessing receipts.
10. Exclude all benchmark patient IDs, group IDs and mesh hashes before cohort construction.

Every exclusion retains a machine-readable reason. Dataset and cohort manifests, source hashes, code commit, container identity and derived artifact hashes belong under `docs/research-artifacts/anatomy-v1/`.

## Cohort ladder

The training cohorts are strict supersets selected deterministically with seed `20260918`:

| Cohort | Total | Target per family |
|---|---:|---:|
| TF-W32 | 32 | 8 |
| TF-W64 | 64 | 16 |
| TF-W128 | 128 | 32 |
| TF-W256 | 256 | 64 |
| TF-W500 | 500 | 125 |

Initially exclude third molars. Cap selection at four teeth per patient so one scan cannot dominate. Balance upper/lower, left/right and FDI position inside each family where availability permits. Patient-level splitting is mandatory.

## Experiments

### Phase A — conversion canary

Convert 2 subjects, then 20 subjects. Deliberately include both P and F/Set-B cases: the official documentation says Set B has the broader field of view and complete upper-tooth segmentations. Confirm physical dimensions, FDI identity, all-family availability, apex retention, raw/canonical traceability, valid Blender renders and successful structured-latent preprocessing. Stop on any systematic orientation or label error.

### Phase B — learning curve

For TF-W32 through TF-W500, use identical base initialization and evaluate:

- equal optimizer updates;
- equal example exposure;
- two independent training seeds;
- immutable checkpoints evaluated outside training.

### Phase C — source-mixture ablation

At the first promising whole-tooth size compare:

- whole-tooth only;
- whole-tooth plus 25% audited Teeth3DS crowns;
- whole-tooth plus 50% audited Teeth3DS crowns.

This tests whether high-resolution crown data complements CBCT roots. Crown-only data is never relabelled as whole-tooth supervision.

## Outcomes and stopping rule

Primary endpoint: paired symmetric Chamfer distance on the sealed family-balanced external-morphology benchmark.

Required non-regression endpoints:

- valid-mesh rate;
- HD95 and F-score at 2% diagonal;
- each tooth-family median;
- crown-region and root-region distances separately;
- crown/root proportion, root count and apex completeness;
- fixed-input/fixed-seed repeatability;
- blinded educator assessment for the final candidate.

Continue beyond a cohort only if the current cohort fails or its uncertainty is inconclusive. A cohort is provisionally sufficient only if median Chamfer improves at least 5%, the stratified-bootstrap 95% interval excludes zero, and all non-regression gates pass for both seeds. Final production promotion retains the stricter existing 10% improvement and educator-review criteria.

## Bias and leakage controls

- Split by patient, never tooth.
- Detect ToothFairy2/ToothFairy3 subject overlap before combining releases.
- Keep conversion/QC reviewers blind to training results.
- Do not discard difficult benchmark failures as missing values.
- Report CBCT scanner/domain, voxel spacing and artifact distribution.
- Report accepted and rejected counts by family and FDI number.
- Treat smoothing/repair settings as experimental parameters with hashes.
- Do not publish derived meshes or checkpoints until source licences and share-alike/non-commercial implications are reviewed.

## Implemented controls

- `scripts/toothfairy_ingest.py`: FDI extraction, affine-to-mm conversion, boundary-contact flag, subject receipts and patient-level split audit.
- `scripts/stage_toothfairy_pilot.py`: deterministic balanced F/P selection, bounded safe extraction and per-volume hash receipt.
- `scripts/build_sample_efficiency_cohorts.py`: audited-only, nested, balanced and subject-capped cohorts.
- `finetune/config/toothfairy_small_data_study.json`: machine-readable frozen study contract.
- Tests verify physical scaling, boundary flags, split-leakage rejection, eligibility and nested repeatability.

## Current gate (19 September 2026)

The deterministic 20-subject pilot and mechanically screened `TF-PW32` engineering cohort are complete. `TF-PW32` passed source-hash, watertightness, canonicalisation, Blender render, dual-grid, shape-latent, trainer-smoke and checkpoint/reload gates. A bounded 50-step run from the pinned base checkpoint also completed with finite loss and a strictly reloadable EMA checkpoint.

The candidate was evaluated on the identical sealed four-family images, seeds and 1024-cascade generation settings used by the unchanged raw model. Mean Chamfer changed from 4.298418% to 4.269175% of reference diagonal (0.68% relative improvement), but HD95 changed from 9.654302% to 9.678655%, F2 from 0.326313 to 0.324607, and sorted-extent error from 0.057086 to 0.058923. All four candidate meshes remained non-watertight and severely fragmented; the molar contained 22,042 components. The registered non-regression rule therefore rejects this candidate. It is not deployed, does not support an anatomical-improvement claim, and must not be extended merely because one aggregate metric moved slightly.

The frozen shape-SC-VAE ceiling and first stage-localisation canaries are now
implemented and executed. Four-family E0 surface fidelity was high (mean
Chamfer 0.438071% of reference diagonal and F2 1.0), but decoded topology was
already imperfect. The first E1 512 case showed genuine fragmentation in the
image-conditioned decoded mesh, improvement after narrow-band remeshing, and a
large additional indexed-component inflation caused by GLB UV seams. Exact and
coincident-welded topology are therefore both mandatory going forward.

The next admissible research step is not a longer run on this unaudited cohort.
First: complete blinded clinical root/crown review, add crown-versus-root
regional and landmark metrics, finish E1 at direct 1024 and 1024-cascade, and
test sparse-structure versus shape-flow responsibility. Only then may the
registered `TF-W*` two-seed learning curve proceed.
