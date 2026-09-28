# DentalSculptor — Development Progress

Shared status for the product app, research datasets, and TRELLIS.2 fine-tuning prep.

**Last updated:** 20 September 2026

**Live app:** https://dentalsculptor.vercel.app
**Research policy:** Non-commercial QMUL research. Do not mutate production TRELLIS deployment or production checkpoint.

Related docs: [SPRINT_ROADMAP.md](./SPRINT_ROADMAP.md) · [MILESTONE_E0_E2.md](./MILESTONE_E0_E2.md) · [dentalsculptor-ml/finetune/README.md](../dentalsculptor-ml/finetune/README.md) · [MODAL_SETUP_GUIDE.md](./MODAL_SETUP_GUIDE.md)

Research design: [DENTAL_TRELLIS_RESEARCH_REPORT_PROTOCOL.md](./DENTAL_TRELLIS_RESEARCH_REPORT_PROTOCOL.md) records the source-code-derived experiment matrix, paper structure and reproducibility bundle.

---

## Current focus

**E10 G1 integration — passed:** route canary `ap-ZUpbiJpgrzNasPW6AkgeM0` identified and sealed the effective loss override in `sparse_flow_matching.py`. Corrected one-tooth/one-step G1 v4 (`ap-jslVNUXToNKSke1EdSPVZk`) passed. The pre-update receipt proved exact student/teacher identity; the read-only post-update probe ran in `ImageConditionedSparseFlowMatchingCFGTrainer` with four populated axial bands, finite balanced MSE `0.4110561`, frozen-teacher MSE `0.00023281`, and teacher contribution ratio `0.0499999991`. Exactly one optimizer step was taken. The 5.169 GB EMA checkpoint strictly reloaded, the persisted sparse hash matched, two raw decodes were bit-identical, and the non-empty raw PLY was sealed with SHA-256 `78d1b791...624e`. The evidence explicitly sets `g2Authorized=true`. G2 may now run; G3, clinical claims and production remain locked.

**All-tooth dental anatomy shape-prior training (v1)** — FDI-16 + Teeth3DS, without TADPM for now.

**Whole-tooth extension underway:** the official ToothFairy2 archive is locally verified (SHA-256 `a720914e...c00434`). The two-subject canary and deterministic 20-subject F/P pilot have completed. The pilot produced 437 meshes; 108 boundary contacts and one non-watertight mesh were quarantined, leaving 328 for clinical review (273 in the training split). Six-view full-surface review sheets, hashes and an editable clinical-review form are generated. Training remains locked because no asset is clinically accepted/root-complete yet. See `TOOTHFAIRY_MINIMAL_DATA_METHOD.md` and `research-artifacts/anatomy-v1/toothfairy-canary/PILOT_20_REPORT.md`.

**Provisional minimal-data spike — completed and rejected:** the mechanically screened engineering-only `TF-PW32` cohort is frozen with 8 teeth per family, 8 per FDI quadrant, a four-teeth-per-subject cap and fingerprint `9ad9a8f8...feb32`. Preprocessing and the two-step trainer smoke passed. A bounded 50-step H100 run then completed with 50 finite losses; denoiser, EMA and optimizer checkpoints were saved and the step-50 checkpoint reloaded. The EMA checkpoint was strictly loaded into only TRELLIS's 512 image-to-shape slot and evaluated on the exact same four frozen images, seeds and 1024-cascade settings as the raw baseline. It failed the preliminary screen: Chamfer improved only 0.68% relative, while HD95 worsened 0.25%, F2 worsened 0.52%, extent error worsened 3.22%, and every output remained severely fragmented. Production and clinical promotion remain prohibited. See `research-artifacts/anatomy-v1/toothfairy-tf-pw32/PIPELINE_GATE_REPORT.md` and `candidate_tf_pw32_step50_v2_report.json`.

**Raw-model baseline finding:** mean Chamfer on the four-case family canary was 4.30% of reference diagonal, but all four GLBs are materially fragmented. The largest connected component contains only 2.9–4.7% of prediction surface area and the ten largest contain only 20–31%; selecting a main component is therefore not a safe repair. The paired step-50 candidate evaluation is now complete and did not correct this defect. See `research-artifacts/anatomy-v1/baseline/BASELINE_CANARY_REPORT.md` and `baseline_topology_analysis_v1.json`.

**E0/E1 localisation — implemented and running:** the frozen 512 shape-SC-VAE four-family E0 canary completed without flow, texture, optimization or GLB postprocessing. Mean Chamfer was 0.438071% of reference diagonal, HD95 0.850944%, F1 0.980912 and F2 1.0, indicating strong global representation fidelity on this small engineering sample. Decoded topology was already imperfect. The latest unchanged-model E1 512 trace found 811 decoded geometry components, improved to 53 after remeshing. Final indexed GLB topology reported 8,901 components, but coincident-position welding recovered 43 geometry components: 8,858 were UV/index seam inflation. The harness now writes immutable named trials, refuses overwrite, pins A100-80GB, asserts deterministic CUDA controls after model load, and records the exact GPU subtype/runtime. Two strict trials on PCIe versus SXM4 A100-80GB were not byte-identical; their final surface metrics were close but topology differed by six welded components, so repeatability remains failed pending direct pairwise geometry and same-device replication. Machine reports include `representation_ceiling_e0_report.json`, `topology_trace_e1_512_report.json`, the two strict trial reports, and `topology_trace_e1_512_strict_repeatability.json` (SHA-256 `a40879c1...a5b18`).

Parallel implementation track: **external reconstruction benchmark + deterministic teaching-case engine**.

| Track | Status | Notes |
|-------|--------|-------|
| Local dataset ingestion & QC | ✅ Done | Manifests, canonical meshes, balanced mix built locally |
| Modal volume assembly | ✅ Done | 14,590-asset dataset assembled and passed fail-closed audit |
| TRELLIS preprocessing (~14.6k meshes) | 🟨 In progress | Dual grids and shape latents complete; conditional renders must now run through receipt-backed persistent batches |
| H100 shape-flow training (`dental-alltooth-v1`) | 🔲 Not started | Candidate checkpoint only; separate Modal app for deploy |
| H100 optimizer/checkpoint smoke gate | ✅ Passed | Two finite steps, three step-2 checkpoint files, and pinned-trainer reload proven |
| ToothFairy TF-PW32 preprocessing | ✅ Passed | 32/32 dual grids, latents and eight-view render sets; engineering-only |
| ToothFairy TF-PW32 learning run | ❌ Rejected | 50 steps completed; 4-case paired screen failed anatomy non-regression and topology remained fragmented |
| Frozen representation ceiling (E0) | ✅ 4-case canary | Strong global surface fidelity; topology/clinical adequacy not established |
| Topology stage trace (E1) | 🟨 512 complete | Direct 1024 and 1024-cascade remain; indexed + welded controls required |
| TADPM comparison (v2) | ⏸ Deferred | DUA submitted; awaiting Zenodo access |

---

## Research datasets (local)

### FDI-16 pilot (`fdi16-pilot-v1`)

| Item | Value |
|------|-------|
| Location | `research/datasets/fdi16-v2/` |
| Meshes | 750 (molar-only pilot) |
| QC | 750 admitted, 0 rejected |
| Manifest | `prepared-v1/anatomy_manifest.json` |
| Canonical meshes | `prepared-v1/meshes_canonical_mm/` |
| License | CC-BY-NC-SA-4.0 (research-approved) |
| Splits | train 500 · validation 125 · test 125 |

### Teeth3DS (`teeth3ds-pilot-v1`)

| Item | Value |
|------|-------|
| Location | `research/datasets/teeth3ds-v1/` |
| OSF parts | 1–6 downloaded and merged |
| Crown extraction | 16,013 crowns → `crowns-v1/` |
| QC | 14,068 admitted · 1,945 rejected (mostly `very-small-surface-area`) |
| Manifest | `prepared-v1/anatomy_manifest.json` |
| Train family counts (admitted) | incisor 2800 · canine 1567 · premolar 3613 · molar 3325 |
| License | CC-BY-NC-ND-4.0 (research-approved with attribution) |
| Splits | train 11305 · validation 2763 · test 0 (official test sealed) |

### Combined training mix (`dental-anatomy-v1`)

| Item | Value |
|------|-------|
| Mix manifest | `research/datasets/balanced-dental-anatomy-mix.json` |
| Total assets | **14,590** (all four tooth families) |
| Splits | train 11,577 · validation 2,888 · sealed test 125 |
| Train family counts | incisor 2,800 · canine 1,567 · premolar 3,613 · molar 3,597 |
| Unique groups / meshes | 1,438 / 14,590 |
| Label roles | 647 verified `healthy-base` · 13,943 diagnosis-neutral `anatomy-base` |
| Builder | `scripts/build_anatomy_training_mix.py` |
| Run plan | `dentalsculptor-ml/finetune/config/training_run_plan.json` |

### Deferred: TADPM

- DUA signed and emailed; Zenodo access pending.
- Planned as **v2** A/B comparison after `dental-alltooth-v1`, not a blocker for v1.

---

## Modal infrastructure

| Resource | Name / ID |
|----------|-----------|
| Profile | `dentalsculptor` |
| Training app | `dentalsculptor-anatomy-training` (`modal_app/train_anatomy.py`) |
| Dataset volume | `dentalsculptor-anatomy-datasets-v1` |
| Checkpoint volume | `dentalsculptor-anatomy-checkpoints-v1` |
| TRELLIS commit (pinned) | `1762f493fe7731a3b7cc6b79ad5da7b015b516c1` |
| Planned run name | `dental-alltooth-v1` |
| Training code commit | `75fbf0183001ed9876c8dbb35de6b68552ee08bd` |
| Base shape-flow checkpoint | `ckpts/slat_flow_img2shape_dit_1_3B_512_bf16` at model revision `af44b…` |

### Volume folders (expected layout)

| Path on volume | Status |
|----------------|--------|
| `fdi16-pilot-v1/` | ✅ Uploaded; TRELLIS prep **partial** (~73% `render_cond` on last check) |
| `teeth3ds-research-v1/` | ✅ Ingested |
| `teeth3ds-crowns-v1/` | ✅ Crown extraction done |
| `teeth3ds-pilot-v1/` | ✅ Corrected QC + manifest complete (14,068 admitted / 1,945 rejected) |
| `dental-anatomy-v1/` | ✅ Assembled and audited; A100 preprocessing active |

### Modal functions (`train_anatomy.py`)

| Function | Purpose |
|----------|---------|
| `ingest_fdi16` | Verify archive MD5, bounded mesh subset |
| `ingest_teeth3ds` | OSF download, merge, official splits |
| `extract_teeth3ds_crowns` | Per-tooth crown PLY extraction |
| `qc_and_prepare_teeth3ds` | QC crowns → `teeth3ds-pilot-v1` manifest |
| `assemble_dental_anatomy_v1` | FDI-16 + Teeth3DS → `dental-anatomy-v1` |
| `validate_anatomy_dataset` | Fail-closed duplicate, leakage, label, family, count and file audit |
| `build_reference_benchmark` | Seal 32 held-out meshes (8 per tooth family) with group/hash leakage guards |
| `preprocess_anatomy` | TRELLIS data_toolkit (A100, resumable 24h passes) |
| `validate_training_runtime` | CPU preflight for pinned training source, imports, config and checkpoint files |
| `prepare_training_smoke_inputs` | Seal train-only 2-per-family smoke cohort with latents and 24-view renders |
| `smoke_train` | Bounded 2-step H100 optimizer/checkpoint gate; cannot start a full run |
| `verify_smoke_checkpoint` | Reload-only validation of canonical losses and all step-2 checkpoint state |
| `train` | Shape-flow only (H100, separate checkpoint volume) |
| `plan` | Print exact training command before GPU spend |

### 15 September deployment and active run

- Isolated training app redeployed successfully; production generation app was not changed.
- Modal's 24-hour function limit is now respected; preprocessing uses resumable 24-hour passes.
- QC image now includes both SciPy and NetworkX, required by trimesh component and boundary analysis.
- Corrected detached CPU QC run `ap-CxrzOMtobX1m2QGTjyMWdk` completed: 16,013 examined,
  14,068 admitted, 1,945 rejected and 64 uncertain.
- QC boundary detection now uses face incidence rather than the previous erroneous 1 mm edge-length test;
  regression coverage verifies watertight meshes report zero boundary ratio.
- Expected open cervical boundaries remain recorded as observations but no longer mark every isolated IOS crown
  as uncertain; heavy/open-boundary anomalies still trigger review or rejection.
- Teeth3DS geometry-QC admissions are labelled `condition=unspecified`, `trainingRole=anatomy-base`.
  They are no longer presented as clinically verified healthy teeth. FDI-16 healthy-base metadata remains separate.
- `dental-anatomy-v1` passed the remote fail-closed audit: 14,590 unique meshes, 1,438 groups,
  all four families above minimum, no missing files, duplicate hashes, split leakage, pathology roles or
  role/condition contradictions.
- Active detached A100 preprocessing call: `fc-01M2RNRFKEQHVHEACBFBBWVC3X` in isolated app
  `dentalsculptor-anatomy-training` (`ap-VDwZUJjiSYrqEd84JMF8YP`). Blender startup passed and real conditional
  rendering was observed at about 3.42 seconds/mesh. Production remains untouched with zero active tasks.
- The H100 path now uses upstream `finetune_ckpt` rather than random initialization, a bounded 20,000-step
  schedule at learning rate `1e-5`, and 1,000-step checkpoints. A train-only metadata overlay prevents the
  upstream loader from seeing validation/test hashes. The invalid `asset_stats.json` data-root entry was removed.
- Production app `dentalsculptor` was not redeployed. H100 training remains locked until preprocessing writes
  a matching `preprocess_status.json` for all 14,590 assets at resolution 512.
- Added deterministic reference-cohort selection (`build_reference_benchmark_manifest.py`): 8 unique,
  optimizer-excluded groups per tooth family from validation/test only. Local tests pass; remote sealing is
  pending because Modal CLI connectivity failed on three retries on 15 September. No production state changed.
- Added `validate_training_runtime`, a no-H100 preflight for the exact official training source/config,
  `trellis2.trainers` import and both pinned base checkpoint files. Local contract tests pass; its isolated
  deployment/run is pending the same Modal CLI connectivity recovery.
- The earlier conditional-render attempts were invalid: the apparent 14,590/14,590 completion consisted of
  14,590 error rows because Blender was absent, and final metadata assembly failed on missing `cond_rendered`.
  Call `fc-01M2Q7K1P8ZZ8G6ZZH57E31SX5` must therefore **not** be treated as successful preprocessing evidence.
- The isolated image now installs the pinned official Blender 3.0.1 binary and verifies its executable before
  rendering. Recovery removes only error-only render metadata and empty shards, preserving the 14,590 completed
  dual grids and latents. A fail-closed validator now requires exactly 14,590 unique successful conditional
  renders before `preprocess_status.json` can be written. Corrected call `fc-01M2RNRFKEQHVHEACBFBBWVC3X` is the
  first legitimate full conditional-render pass.
- After the earlier wasted render attempt, preprocessing gained a mandatory two-asset end-to-end canary. It uses
  the exact deployed image, Blender binary, TRELLIS renderer, dataset adapter and metadata merger used by the full
  job. The 14,590-asset render cannot begin unless both canary assets produce `cond_rendered=True`. H100 training
  independently requires the final successful-render count to equal the manifest asset count and requires the
  canary receipt. The isolated app was redeployed with these gates on 17 September; 50/50 ML tests pass.
- **18 September render incident resolution:** the 14,590-attempt pass produced no certified renders because
  Blender could not load `libXi.so.6`; upstream TRELLIS suppresses Blender stdout/stderr and its progress bar
  counts attempts. A new diagnostic function exposes the subprocess output and validates actual PNG files,
  `transforms.json`, frame counts, camera matrices and non-empty image bytes. The isolated image now contains the
  complete TRELLIS Blender runtime library set (`libxrender1`, `libxi6`, `libxkbcommon-x11-0`, `libsm6`,
  `libxfixes3`, `libgl1`). One-tooth/4-view validation passed, followed by a balanced incisor/canine/premolar/molar
  24-view pilot: **4/4 teeth, 96/96 images and 4/4 camera manifests valid**, minimum image size 524,904 bytes.
  Full rendering remains locked until committed batch rendering and a tiny end-to-end training smoke test pass.

### 2026-09-18 — committed render-batch gate passed

- Added receipt-backed, train-only conditional rendering in
  `dentalsculptor-ml/scripts/render_conditional_batches.py` and isolated Modal functions
  `render_conditional_batch` / `audit_conditional_batches`.
- Batches are sorted and deterministic, limited to 100 assets, validate every image and 4x4 camera
  transform, atomically write a fingerprinted receipt, and commit the dataset volume even when a later
  render fails. Renderer progress counters are not accepted as evidence.
- The full ML test suite passes: **59/59**.
- Isolated live batch `ap-u6Bxw8BFAxYXnk2MVkttsU` rendered four teeth at 24 views: **96/96**
  images, **4/4** manifests, zero failures, minimum image sizes 530,751–552,387 bytes.
- Resume run `ap-RSG2Yp4E6FFhoo8mIFWMQQ` returned `resumed: true` from the committed receipt and
  revalidated all artifacts without invoking Blender.
- Production Modal was not changed. Full rendering and full H100 fine-tuning remain locked. The next
  gate is a sealed four-family training view and a short H100 optimizer/checkpoint smoke test.

### 2026-09-18 — H100 optimizer/checkpoint smoke gate passed

- Sealed `dental-anatomy-v1/smoke_training_v1`: **8 train-only assets**, exactly two each for
  incisor, canine, premolar and molar, with **192/192 conditional PNGs**, eight camera manifests and
  corresponding shape latents. An inspection caught and rejected an earlier selector that included two
  sealed-test molars before H100 training began; the selector and remote gate now require `split=train`.
- Added the official TRELLIS.2 `shape_latent_tokens` contract from each NPZ `coords.shape[0]`.
  The sealed cohort contains 2,001–2,657 tokens per tooth, below the 8,192-token limit.
- Added a trainer checkpoint adapter: the pinned Hugging Face safetensors state dictionary is converted
  to the `.pt` state dict required by TRELLIS.2's `torch.load` fine-tuning path. The same adapter is used
  by the future full candidate run.
- The smoke-only runner disables TRELLIS.2's unconditional startup/final visualization, which otherwise
  requests 64 samples and fails on the intentionally minimal eight-item cohort. The patch exact-matches
  the pinned trainer source, fails closed if upstream changes, and is restored immediately after each subprocess.
  Optimization, logging and checkpoint saving are unchanged.
- Isolated run `ap-WNVGBjry6qmLkL3kN1AVR3` completed exactly **2/2 optimizer steps**. Canonical
  finite losses were **0.417495921254158** and **0.5009540766477585**.
- Step-2 artifacts were persisted on `dentalsculptor-anatomy-checkpoints-v1`:
  `denoiser_step0000002.pt` (5,169,220,934 bytes),
  `denoiser_ema0.9999_step0000002.pt` (5,169,227,438 bytes), and
  `misc_step0000002.pt` (10,338,598,374 bytes).
- Reload-only run `ap-dEgTuV9EsmMBeXklsgb7pR` loaded checkpoint step 2 through the pinned trainer
  (`Loading checkpoint from step 2... Done.`) and exited without another optimizer step. Receipt:
  `/checkpoints/dental-anatomy-smoke-v1/smoke-evidence.json`.
- Full ML suite: **67/67 passed**. Production Modal and the production checkpoint were not changed.
  Full fine-tuning is still locked until receipt-backed rendering and audit cover the entire train cohort,
  the sealed baseline benchmark is recorded, and the full-training launch plan is explicitly approved.

### 2026-09-18 — full-cohort renderer concurrency gate passed

- Repartitioned the 11,577-item train cohort into **464 deterministic batches of at most 25 assets**.
  Batch size 25 keeps each call inside the one-hour safety timeout and limits the amount of work that can
  be lost before a durable receipt.
- Batches 0–4 are independently committed and revalidated: **125/125 assets**, **3,000/3,000 conditional
  PNGs**, **125/125 camera manifests**, and zero failures. Receipt fingerprints are unique and bind the
  sorted asset hashes plus the required 24-view count.
- Four concurrent Blender batches completed without corrupting each other's Volume commits. Direct receipt
  reads and the independent audit agree: `validatedAssetCount=125`, `validReceiptCount=5`. The remaining
  459 batches are reported as missing rather than being mistaken for successful work.
- Added `render_conditional_window`, a resumable scheduler capped at four concurrent containers. Each window
  blocks on its four child calls and reports the next resume cursor; each child still writes and commits its
  own receipt. Audit failure output is bounded while retaining the exact failure count.
- Deployed these changes only to `dentalsculptor-anatomy-training`; production generation and its environment
  were not changed. The next four-batch window (batches 5–8) is running under Modal run
  `ap-fhiOp73NxY54bklOz0nFUB`.
- Full ML suite after the scheduler/audit changes: **70/70 passed**.

---

## ML scripts added (dentalsculptor-ml)

| Script | Purpose |
|--------|---------|
| `teeth3ds_ingest.py` | OSF download, merge, split binding |
| `download_teeth3ds.py` | Local CLI wrapper |
| `extract_teeth3ds_crowns.py` | OBJ+JSON → per-tooth PLY |
| `prepare_teeth3ds_manifest.py` | All-tooth anatomy manifest |
| `canonicalize_anatomy_meshes.py` | Unit-box normalization + `canonicalSha256` |
| `bootstrap_trellis_metadata.py` | TRELLIS `metadata.csv` |
| `preprocess_anatomy_trellis.py` | TRELLIS data_toolkit orchestration |
| `trellis_dataset_dental_anatomy.py` | TRELLIS dataset adapter |
| `prepare_combined_anatomy_dataset.py` | Assemble `dental-anatomy-v1` from mix |
| `build_anatomy_training_mix.py` | Leakage-safe multi-dataset mix |
| `reconstruction_benchmark.py` | Reference-mesh Chamfer, HD95, F-score and proportion metrics |
| `build_reference_benchmark_manifest.py` | Deterministic 32-case, family-balanced sealed reference cohort |
| `validate_anatomy_dataset.py` | Fail-closed dataset and split audit before preprocessing/training |

Benchmark contract: `dentalsculptor-ml/finetune/config/reconstruction_benchmark_contract.json`.
It defines held-out family-balanced cohorts, blinded educator scoring, repeatability metrics and promotion gates
that apply equally to TRELLIS candidates and future ground-up models.

Preprocessing fixes already applied: bootstrap `data_toolkit` from TRELLIS.2 main tarball; skip Blender `dump_mesh`
(direct PLY→pickle); `foreach_instance(no_file=True)` adapter; correct CLI flags; skip existing pickles on re-run;
install and verify pinned Blender 3.0.1 for conditional rendering; remove error-only render metadata and empty
record shards; require an exact successful-render count before marking preprocessing complete.

---

## Commands to run (when Modal is connected)

From `dentalsculptor-ml/` with UTF-8 on Windows:

```powershell
$env:PYTHONIOENCODING='utf-8'
$modal = 'C:\Users\joboy\Desktop\DentalSculptor\.tools\modal-venv\Scripts\modal.exe'
cd C:\Users\joboy\Desktop\DentalSculptor\dentalsculptor-ml

# Re-auth if needed
& $modal token new --profile dentalsculptor

# Step-by-step (recommended for long jobs)
& $modal run -m modal_app.train_anatomy::qc_and_prepare_teeth3ds
& $modal run -m modal_app.train_anatomy::assemble_dental_anatomy_v1
& $modal run --detach -m modal_app.train_anatomy::preprocess_anatomy --dataset-name dental-anatomy-v1 --resolution 512 --num-cond-views 24
# Re-run the same command if a 24h pass ends before all checkpointed stages complete.

# After preprocess completes
& $modal run -m modal_app.train_anatomy::plan --dataset-name dental-anatomy-v1 --run-name dental-alltooth-v1
& $modal run --detach -m modal_app.train_anatomy::train --dataset-name dental-anatomy-v1 --run-name dental-alltooth-v1 --resolution 512

# One-shot (requires PC connected for full orchestration)
& $modal run -m modal_app.train_anatomy::build --skip-train
```

Use `--detach` on long steps so the job continues on Modal after submit. Monitor at [modal.com/apps](https://modal.com/apps).

---

## Blockers & known issues

| Issue | Impact | Mitigation |
|-------|--------|------------|
| VS Code Modal CLI intermittently cannot connect | User terminal cannot reliably reach Modal; Codex process can | Use `.tools/modal-venv`; capture `MODAL_LOGLEVEL=DEBUG` + `MODAL_TRACEBACK=1`; check TLS interception/VPN/firewall |
| Local client disconnects on long jobs | Log streaming stops; one-shot `build` may not chain steps | Run steps individually with `--detach` |
| FDI-16 `render_cond` incomplete on volume | Partial pilot preprocess only | Finish via full `dental-anatomy-v1` preprocess or re-run on `fdi16-pilot-v1` |
| Teeth3DS QC summary uses wrong `datasetId` in one path | Cosmetic logging only | No training impact |

---

## Tests (dentalsculptor-ml)

Passing coverage for the anatomy pipeline:

- `test_fdi16_ingest.py`
- `test_teeth3ds_ingest.py`
- `test_build_anatomy_training_mix.py`
- `test_train_anatomy.py`
- `test_prepare_combined_anatomy_dataset.py`
- `test_prepare_anatomy_dataset.py`
- `test_anatomy_quality.py`
- `test_blind_model_comparison.py`
- `test_reconstruction_benchmark.py`
- `test_validate_anatomy_dataset.py`
- `test_real_generated_variant_geometry.py`

Current result: **123 tests passed**. The real-mesh deterministic regression uses two checked-in DentalSculptor
reconstructions and verifies a non-zero bounded fracture, cap creation, exact preservation of at least 80% of
source vertices, repeatable geometry, immutable master inputs and a valid GLB export.

---

## Product app status (summary)

Detailed checklists live in [SPRINT_ROADMAP.md](./SPRINT_ROADMAP.md). High-level:

| Area | Status | Notes |
|------|--------|-------|
| Auth & pilot | ⬜ Partial | Supabase OAuth setup; production smoke tests pending |
| Research role gating | ✅ Done | `/research` locked to RESEARCHER/ADMIN |
| TRELLIS generation (Modal) | ✅ Core path | GPU warmup, async S3 jobs, invite-gated pilot |
| Nano3D edit UI | ✅ Mostly done | Presets, mask paint, 2D preview, revision stack |
| Nano3D GPU worker (Case 3) | ⬜ Pending | CPU stub; `NANO3D_GPU` flag |
| Export wizard (E1) | ✅ Mostly done | STL + Simodont presets; PLY / teaching bundle pending |
| Placement studio (E2) | ⬜ Not started | Jaw templates, FDI socket map |
| Multilayer editing | ⬜ Research | Strategy doc only |
| Editor polish (Phase A) | ✅ ~85% | Dark chrome, SFX, part sync; undo/redo deferred |

**Production TRELLIS / checkpoint:** unchanged. Candidate deploy only via `deploy-candidate.ps1` after blinded evaluation passes.

---

## Promotion path (after training)

1. Preprocess completes on `dental-anatomy-v1`
2. Train `dental-alltooth-v1` on H100 (candidate volume only)
3. `scripts/blind_model_comparison.py` → educator review
4. `scripts/evaluate_finetune_candidate.py` → promotion gate
5. `scripts/deploy-candidate.ps1` → scale-to-zero candidate app (not production)

See [finetune/README.md](../dentalsculptor-ml/finetune/README.md) and `config/anatomy_contract.json`.

---

## Next actions (priority order)

1. **Complete reviewed dental landmark annotations.** Axial crown/root proxy metrics are implemented and show that cascade improves the apical-root region while degrading the crown. True CEJ/cusp/furcation/apex metrics fail closed until `dental_landmark_annotation_contract.json` is satisfied.
2. **Integrate the per-region stopping gate, then run E3 on 1024 cascade only.** The bounded plan is frozen in `e3_stage_ablation_plan.json`; start at 50 steps and advance to 250/500 only when every crown, root, topology and repeatability gate passes.
3. **Complete blinded clinical review and patient-separated validation/test selection**; TF-PW32 remains engineering-only.
4. **Run the E3 sparse-structure/shape-flow ablation** only after the above gates identify the responsible stage.
5. **Enter the nested two-seed sample-efficiency ladder** only with a topology-capable candidate and prospective early stopping.
6. **Promote only if the candidate wins every required gate**; otherwise leave production unchanged.

---

## 2026-09-19 — E3 sparse-structure runtime qualified

- Encoded and validated official TRELLIS.2 sparse-structure latents for all
  **32/32** TF-PW32 whole teeth. Receipt:
  `e3_sparse_structure_latent_receipt.json` (SHA-256
  `84bac5891f8009c27a35780a501c6e9413f9b8b28a0727425ff52f8e5b2fa290`).
- The first official-trainer tryrun stopped before optimization because the
  published sparse-flow checkpoint omits `rope_phases`, although the pinned
  trainer strictly requires every registered buffer. Pinned source inspection
  confirmed that this buffer is deterministically derived from the fixed model
  config and coordinate grid, not learned anatomy.
- Added a fail-closed compatibility adapter that restores only `rope_phases`
  from a freshly constructed official `SparseStructureFlowModel`, then retains
  strict checkpoint loading. Any other missing key or upstream source change is
  rejected. Corrected no-optimizer run `ap-Y4X9DOq0h0j4zCQdKQRtE6` passed.
- The sealed two-step H100 smoke run `ap-K4ysX6iD4TKRzitsVbjykL` completed with
  finite canonical losses **0.0393548822** and **0.0560276359**, saved non-empty
  model, EMA and optimizer checkpoints, and strictly reloaded step 2. Evidence:
  `e3_sparse_smoke_evidence.json` (SHA-256
  `5eab4ce403bca748732278b27a1cf3a2237aeac51836b0302f832ba355c14923`).
- This qualifies E3-B for a bounded 50-step engineering canary only. It is not
  evidence of anatomical improvement, makes no clinical claim, and does not
  authorize production deployment. Candidate inference and the registered
  global/regional/topology/repeatability evaluation must be wired before the
  50-step run is launched.

### E3-B 50-step outcome

- The sealed E3-B run `ap-e3CpihT0b8dAJbkoLgh4xD` completed **50/50 finite
  optimizer steps**, persisted model/EMA/optimizer checkpoints, and strictly
  reloaded step 50. Training receipt SHA-256:
  `020a6b97206c7d53b5835ea3b6ed208e2805d732410e56d2722d014dd5b7c6d6`.
- Candidate evaluation changed only `sparse_structure_flow_model`; the pinned
  shape and texture stages, input, seed, quality and 1024-cascade path were held
  fixed. The first attempt exposed a PyTorch inference-buffer copy constraint
  before generation; the corrected strict loader performs that copy inside
  inference mode and retained strict key validation.
- The prospective evaluation stopped after the first complete same-container
  incisor pair because fixed-seed outputs were not byte-identical. The two GLB
  SHA-256 values were `822fee17...a3b934` and `a8a35c29...a1906`.
- Independent failure evidence also showed apical-root F2 regression,
  middle-root and crown sample-share regression, welded component-count and
  largest-component-area regression, and non-manifold-edge regression. The
  candidate incisor had global Chamfer **7.465661%**, HD95 **15.967125%**, F2
  **0.128973**, and 11 welded components.
- Decision: **E3-B step 50 rejected early**. Step 250, E3-C continuation,
  clinical claims and production promotion are all forbidden. The remaining
  six generations were cancelled to honor the pre-registered stopping rule.
  Evidence: `e3_sparse_step50_early_stop_report.json` (SHA-256
  `166686299e7169ac4e2c42a57981773edc19d9cfac8b26345f4ae9bb950cc82c`).

### E3-B representation-boundary diagnosis

- The early stop correctly prevented further compute, but the original
  serialized-GLB byte comparison was too strict to identify anatomical
  nondeterminism. Two sealed boundary diagnostics now separate learned geometry
  from texture/post-processing/serialization.
- Sparse occupancy run `ap-6YYkiDJZCLWI26T5eRtp32` showed that two candidate
  samples are exactly identical at the 32-grid occupancy boundary (2,028
  voxels, identical coordinate SHA-256). Relative to the pinned base, however,
  the candidate added 432 voxels, removed 240, increased occupied volume by
  **10.4575%**, shifted the centroid by **1.2809 voxels** (**4.0028%** of the
  grid), and achieved only **0.703704 voxel IoU**. Both base and candidate were
  single 6-connected components. Evidence:
  `e3_sparse_occupancy_diagnostic_v1.json` (SHA-256
  `46518edc6b5e5aac284fdc10406f95a3d3017538d0abc1909b0951291fddfd08`)
  and the exact coordinate artifact `e3_sparse_occupancy_diagnostic_v1.npz`
  (SHA-256 `1f74c5405b4b51ec0cb23885f07e5ccfac9b163da01de7362312265c7811cf2b`).
- Shape-boundary run `ap-AVZhIFNFfi2jTL3CgvYcDg` showed bit-identical sparse
  coordinates, 1024-cascade shape-latent coordinates and features, raw mesh
  vertices (1,969,965), raw faces (3,943,650), and all four decoded
  substructure levels across two trials. Evidence:
  `e3_shape_boundary_diagnostic_v1.json` (SHA-256
  `79d78fdae9c3ac8bc49b697cb4d71cbb0a1c89f38e0ae836ef11dbb96d14748e`).
- Corrected conclusion: the candidate geometry is deterministic; the different
  GLB byte hashes arise after raw shape decode (texture, post-processing, or
  serialization). E3-B nevertheless remains rejected because its repeatable
  occupancy drift coincides with the independently measured crown/root and
  welded-topology regressions. Future repeatability gates compare raw geometry,
  while serialized asset stability is tracked separately as an export concern.
- No production service, production model, or production checkpoint changed.

### E4 sparse trust-region screen

- Reused the rejected 50-step update as a task vector instead of spending on a
  new training run. Three immutable checkpoints were materialized as
  `base + alpha * (candidate - base)` for alpha **0.05, 0.10 and 0.20**.
  `rope_phases` remained the fixed derived buffer and every learned tensor was
  schema checked. Materialization run: `ap-nVUuYsnX0UyuADCPZfpGvh`.
- The prospective occupancy-only screen `ap-I9k2Imlgsq6NMcF0GspKkX` required
  voxel IoU >= 0.95, absolute voxel-count change <= 2%, centroid shift <= 1%
  of the grid, and one 6-connected component before any mesh generation.
- No checkpoint passed. Alpha 0.05 was closest (IoU **0.949420**, volume
  **+1.5251%**, centroid shift **0.5635%**, one component) but failed the IoU
  threshold. Alpha 0.10 and 0.20 produced substantially larger drift. The
  threshold was not relaxed after seeing the result, no candidate was selected,
  and no full mesh evaluation was run.
- The non-monotonic voxel response means the next permitted experiment is a
  pre-registered smaller alpha bracket screened across all four tooth families;
  it is not permission to promote alpha 0.05 or resume E3 training.
- Evidence: `e4_sparse_task_vector_materialization_receipt.json` (SHA-256
  `48d18e6071efcacc0d6827e4ca19a9d179c5d9df2ee9861044e4a702d833adfd`)
  and `e4_sparse_trust_region_screen_v1.json` (SHA-256
  `fbedc2bf2274e158d95908c34169cb847e8f172cd5d23aa969bf74fb86d2756f`).

### E4 four-family refinement outcome

- Pre-registered alpha **0.01, 0.025 and 0.04** checkpoints were materialized
  without optimization (`ap-xPXkg9zkh6lCX9twZERNnc`) and screened against the
  frozen incisor, canine, premolar and molar inputs (`ap-lekdcoVJi3T6ktwlZLerCG`).
- No alpha passed the unchanged occupancy-preservation gate for every family.
  Alpha 0.025 passed canine, premolar and molar, but the incisor remained below
  the required IoU. Alpha 0.01 failed incisor and premolar; alpha 0.04 failed
  incisor, canine and premolar. All outputs remained one 6-connected component.
- The response was non-monotonic across alphas. Because the source checkpoints
  are reduced precision, post-hoc interpolation followed by recasting creates
  discrete parameter changes and cannot serve as a reliable anatomical trust
  region. E4 is rejected; no selected checkpoint, mesh evaluation, clinical
  claim or production promotion is permitted.
- The next method must constrain drift during optimization using full-precision
  master weights, with a two-step smoke and parameter-drift gate before any
  anatomical evaluation.
- Evidence: `e4_sparse_task_vector_refinement_receipt.json` (SHA-256
  `e45faae85d58a15b1f73045a823e52fe61a99ba4dc445d6d12cf92104dc8f9f8`)
  and `e4_sparse_trust_region_refinement_v1.json` (SHA-256
  `e30b0309833f35b937087c2125d6ed43f1dcfd7af00a7a87b87fcbf51a02c860`).

### E5 training-time FP32 trust-region outcome

- Added a fail-closed patch to the pinned TRELLIS.2 trainer that keeps FP32
  optimizer master weights and FP32 anchor weights, applies a hard relative-L2
  projection after every step, and synchronizes the projected parameters back
  to the inference model. Forward/backward runs under BF16 autocast so
  FlashAttention receives a supported dtype.
- The first smoke attempt (`ap-BiEkBYBpRzDWzvyrQvB1z1`) stopped before its first
  optimizer step because upstream `inflat_all` did not autocast the forward
  pass. It produced no candidate. The corrected two-step smoke
  (`ap-4EbZxlCSBwJ3tYVkxZdc6M`) completed with finite losses, projected both
  updates, independently measured persisted model and EMA displacement inside
  the registered `1e-5` radius, and strictly reloaded step 2.
- The smoke-authorized 10-step canary (`ap-o4IwUS0wD2StNHoJIU1m5w`) completed
  10/10 finite steps. Every step activated the hard projection. Persisted model
  relative L2 was **1.0000043e-5** (within the registered numerical tolerance)
  and EMA relative L2 was **3.8429587e-7**; strict reload passed.
- The unchanged four-family occupancy gate (`ap-ZYmElDeLdtiHgGhqAYL8m1`)
  rejected the EMA candidate. Canine passed (IoU **0.97**) and molar passed
  (IoU **1.00**), but incisor failed (IoU **0.89**, about **+3%** occupied
  voxels) and premolar failed (IoU **0.91**, about **+5%** occupied voxels and
  about **2%** grid-normalized centroid shift). All remained one connected
  component.
- Decision: **E5 rejected before mesh generation**. A very small global
  parameter displacement is not a reliable proxy for cross-family anatomical
  preservation. Full mesh evaluation, clinical claims and production promotion
  remain forbidden. The next experiment must constrain output behaviour during
  training (teacher/base sparse-prediction consistency), not only parameter
  distance.
- Evidence: `e5_sparse_trust_region_smoke_evidence.json` (SHA-256
  `5995bc68a856302e29d795f86e549e1ceef0470665fd99d588baaad16ea0515d`),
  `e5_sparse_trust_region_step10_evidence.json` (SHA-256
  `4f5ea848245394b0d8f2bdc56285d985b5eb4790e9277186e240cfe1871679be`),
  and `e5_sparse_trust_region_step10_occupancy_v1.json` (SHA-256
  `5edcd225f1c6f08fbb9efd41ab46c94522da32692e1d8e0f2800b72dc6823f99`).
- Production services, environment variables, model registry and production
  checkpoint were not changed.

### Immutable sparse-base benchmark

- Implemented a fail-closed, inference-only materialization step that samples
  every frozen tooth-family case twice before persisting anything. The Modal
  run `ap-gTBeDea6BfGOg9TH5KDxji` passed exact coordinate repeatability for
  incisor, canine, premolar and molar and executed no training.
- Four content-addressed coordinate arrays now live at
  `/datasets/dental-anatomy-v1/frozen_sparse_base_v1/` on the research volume.
  Their ordered cohort SHA-256 is
  `d1a80b442b9cfb460ad86fb7f301b96e9110c02b3e6b5769bb3efeb3355d98a1`.
  Future candidate gates must load these arrays instead of resampling the base.
- Frozen voxel counts are incisor **1,836**, canine **2,105**, premolar
  **3,128**, and molar **2,359**. This converts the earlier cross-container
  ambiguity into a controlled, immutable comparison boundary.
- Local evidence: `frozen_sparse_base_v1_receipt.json` (SHA-256
  `c59b3d8edb71e9196073c35079a4f2979d247c1b254f8d7dc0eb34534ec27e94`).
  Production remains untouched.

### E6 frozen-teacher output-consistency outcome

- Added a fail-closed patch to the pinned flow-matching loss. A frozen copy of
  the pinned base sparse denoiser receives the exact same noisy latent,
  timestep, and processed image condition as the trainable student. The teacher
  is excluded from optimizer parameters, EMA parameters and checkpoint state.
- The sealed two-step H100 smoke (`ap-wVZ0wQLDT3BcpnKVPIyftJ`) passed. Teacher
  consistency was exactly zero before the first update and **4.50318e-5** after
  the student moved. Supervised, consistency and total losses were separately
  finite and logged; checkpoints were complete and strict reload passed.
- The smoke-authorized 10-step canary (`ap-qDoOpNIdrsLYrEGwKEUyGm`) completed
  10/10 finite steps. Final teacher-consistency MSE was **4.35234e-5**, model
  relative L2 was **6.60720e-5**, EMA relative L2 was **3.82450e-7**, and strict
  reload passed.
- The same sealed four-family occupancy evaluator (`ap-ixT6PpATQ2YTEzmWqFtdHf`)
  accepted canine (IoU **0.98**), premolar (IoU **0.96**) and molar (IoU
  **1.00**) but rejected incisor (IoU **0.80**, approximately **+14%** occupied
  voxels and approximately **2%** grid-normalized centroid shift).
- Decision: **E6 rejected before mesh generation**. With weight 1.0, the
  consistency loss was about three orders of magnitude smaller than the
  supervised loss, so the output constraint was not strong enough to preserve
  incisor occupancy. The next experiment must pre-register a scale-normalized
  consistency contribution and a family-balanced frozen anchor batch, then pass
  a two-step loss-ratio smoke before any longer canary.
- Evidence: `e6_sparse_teacher_consistency_smoke_evidence.json` (SHA-256
  `32931ab4fb98e30c8e94d89200e753f7de6cfbfeb337edc00f1954929604daac`),
  `e6_sparse_teacher_consistency_step10_evidence.json` (SHA-256
  `623ba03aeff3a5683389f5dae0eed3c3d61f2cd0313de74715fa017657a86dae`),
  and `e6_sparse_teacher_consistency_step10_occupancy_v1.json` (SHA-256
  `f8f3317bcb53cbe6bf5cf51223b15e3e9411ecf44458cbf461f68837d7f9c950`).
- Production services, environment variables, model registry and production
  checkpoint were not changed.

### E7 scale-normalized, family-balanced anchor outcome

- Materialized an immutable eight-tooth sparse anchor containing exactly two
  incisors, two canines, two premolars and two molars. Each sparse latent is
  content hashed and the ordered cohort is sealed by SHA-256
  `451d21fd3e4d459ddfef15ce06f5c146093534428e1f380e1d5c0021a0eab488`
  (`ap-Og6IgbtFFwy28mFZdLVF52`).
- Added a fail-closed frozen-teacher loss whose effective scale is computed
  from detached supervised and consistency losses, clamped to `[1, 250]`, and
  registered to contribute 10% of supervised MSE. The two-step H100 smoke
  (`ap-1rMkc5romvogTtYGFfv4M3`) achieved a measured step-2 share of
  **0.1000000015** at scale **106.87**; checkpoint save and strict reload passed.
- The authorized ten-step canary (`ap-DbrHgJkAerzEM2Pjqoqiyl`) kept every active
  consistency share between **0.0999789 and 0.1000001**, with scales between
  **105.62 and 152.75**. Persisted model relative L2 was **5.48450e-5**, EMA
  relative L2 was **3.82404e-7**, and strict reload passed.
- The unchanged four-family occupancy gate (`ap-7fqhwbABt98nvAfEATqqOB`)
  accepted canine (IoU **0.977**), premolar (**0.952**) and molar (**0.996**),
  but rejected incisor (IoU **0.725**, **+26.91%** occupied voxels and **6.59%**
  grid-normalized centroid shift). All outputs remained one connected component.
- Decision: **E7 rejected before mesh generation**. Making global teacher
  consistency numerically meaningful did not prevent severe family-specific
  incisor drift. The next experiment must directly constrain sparse occupancy
  with family-specific normalization or sampling and must pass an
  incisor-focused two-step gradient/occupancy smoke before any longer run.
- Evidence: `e7_sparse_anchor_receipt.json` (SHA-256
  `a374c0075bad0e4179e60cf5a0c0615197862de183fc4485347c8af80c47b7fb`),
  `e7_sparse_calibrated_anchor_smoke_evidence.json` (SHA-256
  `7f74375f5e123708dfc5303d9958a30216d5dab8498e846f1cdf48a3dcc82e84`),
  `e7_sparse_calibrated_anchor_step10_evidence.json` (SHA-256
  `4d095177c729463d2a43873557db842da2cc978e1f6953deca886d3d788b6760`),
  and `e7_sparse_calibrated_anchor_step10_occupancy_v1.json` (SHA-256
  `3120a28f48196726a359d5cc48bda718ce98e9e100fb8163312f550e401bc73e`).
- Production services, environment variables, model registry and production
  checkpoint were not changed.

### E8 decoded-occupancy outcome and benchmark correction

- Added a fail-closed objective at the actual TRELLIS.2 sparse inference
  boundary. It reconstructs the predicted clean sparse latent, decodes it with
  the pinned frozen sparse decoder, and applies BCE-with-logits plus soft Dice
  against detached decoded ground-truth occupancy. Its detached scale was
  registered to contribute 10% of supervised MSE.
- The sealed two-step smoke (`ap-B9zD91fQjDSJFlUoEGS9Sw`) completed with finite
  losses, measured occupancy shares of **0.1000000** on both steps, model
  relative L2 **2.40281e-5**, EMA relative L2 **7.76278e-8**, and strict
  checkpoint reload. This qualified only the step-2 occupancy screen.
- The first screen exposed a benchmark defect: repeatability was only measured
  after anatomy gates passed, leaving failed candidates without repeatability
  evidence. The evaluator now unconditionally samples both base and candidate
  twice, records both comparisons, and makes exact repeatability part of
  `benchmarkValid` and the promotion decision.
- The corrected paired screen (`ap-lkNvFtSEYmhNPVK4Elf3xo`) was exactly
  repeatable for base and candidate across all four families inside the same
  container. Canine (IoU **0.9710**) and molar (**0.9949**) passed, but incisor
  (IoU **0.8190**, **-4.67%** occupied voxels, **2.63%** centroid shift) and
  premolar (IoU **0.9171**) failed.
- Decision: **E8 rejected after two steps**. No ten-step run, mesh generation,
  clinical claim or production promotion is permitted. The next permitted work
  is a no-optimizer, family-by-timestep gradient diagnostic; it must determine
  where the decoded objective is meaningful before an E9 loss is registered.
- Cross-container baseline identity is not yet proven: historical runs can
  produce different base occupancy counts despite exact repeatability within a
  container. Paper-grade comparisons must persist immutable base coordinates
  or evaluate all candidates against one shared persisted base.
- Evidence: `e8_sparse_decoded_occupancy_smoke_evidence.json` (SHA-256
  `0ca6f6aae3520d8e7cc5d32fd5f0595bf98b5f91e68e5c7b30340a61d0006c88`)
  and `e8_sparse_decoded_occupancy_step2_screen_v2.json` (SHA-256
  `3036cb9d6780b30943b40c586d63c3d1feadb6037a5e5c64d320fc096fcea9d0`).
- Production services, environment variables, model registry and production
  checkpoint were not changed.

### E9 family-by-timestep gradient diagnostic

- Implemented a sealed, zero-update diagnostic at the official TRELLIS.2
  sparse-flow training boundary. For one immutable whole-tooth anchor in each
  family, it evaluates fixed timesteps `0.05`, `0.25`, `0.5`, `0.75` and
  `0.95`, reconstructs predicted clean latents, decodes occupancy with the
  pinned frozen decoder, and measures gradient cosine and calibrated
  occupancy-to-MSE gradient norm ratio.
- Two engineering attempts were discarded before scientific interpretation:
  `ap-iYHe2BXMi03FXkJQvzdbwH` lacked the derived RoPE buffer and
  `ap-loqumOsaEg4IaM1rFqYxWk` logged the sealed timestep in BF16. Neither
  changed weights or wrote a candidate checkpoint. The corrected run
  `ap-A1qFK336C0J8KsCuxU1i5C` completed all 20 registered observations with
  optimizer learning rate zero.
- At `t=0.05` and `t=0.25`, decoded occupancy remained highly faithful
  (family Dice ranges **0.871-0.913** and **0.980-0.997**) but the calibrated
  auxiliary gradient ratio was **0.976-1.352** and **1.096-3.262**, far above
  the registered maximum **0.25**. At `t=0.5`, every family also exceeded the
  gradient-ratio gate (**0.343-0.416**).
- Only `t=0.95` passed the originally registered gradient rules across every
  family, so there was no required adjacent safe pair. Moreover, its decoded
  occupancy Dice was only **0.000410-0.000886**. This post-diagnostic finding
  does not rewrite the registered decision; it establishes that future
  protocols must also preregister a minimum semantic-validity/Dice gate.
- Decision: **E9 rejected before training**. No optimizer update, candidate
  checkpoint, mesh evaluation, clinical claim, deployment or production
  mutation is permitted. Direct sparse decoded-occupancy supervision is not a
  viable next experiment under this method. The next registered experiment
  must test a shape-stage or suitable latent-consistency objective with both
  gradient-safety and semantic-validity gates before optimization.
- Evidence: `e9_occupancy_gradient_diagnostic_v3.json` (SHA-256
  `45cb90443e178a42f60e2f7631db1aff8efe130322571812b0cb62f10b89cb9d`);
  the immutable Modal source report has SHA-256
  `6d56149107254b77d69853da44e28039b2746250f88b401a70353ce7afddcdca`.
- Production services, environment variables, model registry and production
  checkpoint were not changed.

### Mixed-data curriculum Stage 0

- Corrected the previous `dental-alltooth-v1` plan: DTU FDI16 and Teeth3DS
  are both IOS-derived crown sources and cannot support a root or all-tooth
  claim. That plan is now marked `superseded-do-not-run` and the replacement
  source-aware curriculum is recorded in `mixed_anatomy_curriculum_v1.json`.
- Added a deterministic 12-case frozen representation-ceiling cohort: four
  family-balanced ToothFairy whole teeth, four family-balanced Teeth3DS crowns
  and four distinct DTU FDI16 crowns. Crown cases explicitly carry
  `rootSupervision=false`; no optimizer or candidate checkpoint is available
  in this stage.
- The A100 ceiling run `ap-inCI7kVlojKjZkCsa8pzGU` completed. Mean symmetric
  Chamfer was **0.441%** of diagonal for ToothFairy, **0.389%** for Teeth3DS
  and **0.430%** for DTU; every source achieved mean F-score **1.0** at 2%.
- Raw shape-decoder meshes contained many tiny fragments and non-manifold
  edges, but the smallest main-component surface share was **99.351%**. The
  CPU-only qualification `ap-G15tgjLp7DD2cOyoi6DNWI` removed only subsidiary
  components and all **12/12** cases retained F-score at least **0.99** and
  stayed within the fixed Chamfer tolerance.
- Decision: **Stage 0 passed as an engineering representation test**. This
  does not authorize training on the unreviewed TF-PW32 cohort. Stage 1 begins
  only after a patient-disjoint, root-complete, clinically accepted TF-W128
  whole-tooth cohort is sealed. Production remains unchanged.
- Evidence: `mixed-stage0-representation-ceiling-v1.json`; immutable Modal
  report SHA-256 values are
  `a157e9703a5301e7d50701f74067bc7b188726c7da264a31301242c3617e5011`
  and `1f7aba2f05ba50f3548f552575fc2d82cd88f750809bb19f59862c9cf04fb8ba`.

### Mixed-data curriculum Stage 1 cohort preparation

- Expanded ToothFairy staging deterministically from 20 to 50 subjects (25 per
  acquisition set) using seed `20260918`. `ToothFairy2P_547` contained no
  permanent FDI labels, was explicitly excluded, and was replaced by the next
  same-set hash-ranked reserve, `ToothFairy2P_075`.
- Added bounded process-parallel, SHA-verified resume support to ToothFairy
  ingestion. The versioned extraction contains **1,164** whole-tooth meshes
  from **50** patients: 948 train, 74 validation and 142 test. No split is made
  at tooth level.
- The registered provisional target `TF-PW128` now exists: **128 teeth**, 32
  per family, from **37 patients**, maximum four teeth per patient. Its sealed
  fingerprint is
  `eae29f525dc9708fb7a3a63149b23ca7ae6e54a68a45ca9c502b07c0977f4d8a`.
- To tolerate clinical exclusions, a nested `TF-PW160` reserve was sealed with
  40 teeth per family from 41 patients. All **160/160** six-view review sheets
  were rendered; integrity verification found zero missing files and zero hash
  mismatches.
- **Current gate:** human clinical review is required. The CSV is deliberately
  blank and no item has been auto-approved. Stage-1 optimization remains
  forbidden until the review is applied and a balanced, root-complete,
  clinically accepted `TF-W128` is rebuilt and revalidated.
- Evidence: `mixed-stage1-cohort-preparation-v1.json`. Production services,
  checkpoints, environment variables and the model registry were not changed.

### Mixed-data curriculum Stage 1 clinical acceptance

- Job Oyebisi explicitly attested all 160 reserve cases after review: identity,
  crown and root/apex complete; no leakage; artifact severity none. The original
  blank form was retained and a separate attested form plus SHA-linked receipt
  was created. Validation accepted **160/160**, with zero rejected or pending.
- Rebuilt the registered clinical `TF-W128`; its fingerprint exactly matches
  the prereview target (`eae29f...f4d8a`), confirming review application did
  not change selection. The 128 canonical, watertight meshes were materialized
  as `toothfairy-tf-w128-v1` and uploaded to the versioned Modal dataset path.
- Remote Modal connectivity and the uploaded manifest/mesh directory were
  verified. No preprocessing or optimizer was launched.
- Preflight caught a remaining evaluation gap: the accepted training cohort is
  correctly train-only, but a valid experiment also needs clinically reviewed,
  patient-disjoint heldout data. Deterministic review packs are ready for
  `TF-PV12` (three per family, three validation patients) and `TF-PT24` (six per
  family, six test patients). Stage-1 optimization remains forbidden until
  those 36 cases are reviewed and the remote no-optimizer preflight passes.

### Mixed-data curriculum Stage 1 preprocessing and seed-A canary

- Job Oyebisi attested the sealed heldout review packs: `TF-PV12` accepted
  **12/12** (three per family) and `TF-PT24` accepted **24/24** (six per
  family). The final `toothfairy-stage1-v1` dataset contains **164 teeth from
  46 patients**: 128 train, 12 validation and 24 test, with zero patient or
  mesh-hash leakage. Its manifest SHA-256 is
  `21d3538deca6f914fc7195a2e7467608490a5596bb893a1d2bab6c625ee6fe88`.
- Remote dataset validation passed (`ap-GMPuYVsOZ2xl4PaBEsMReb`) and the
  eight-tooth Blender canary passed (`ap-UGmMZWzTCcbXqNxYpvbxOD`). The staged
  preprocessing produced and revalidated **164/164 mesh dumps, dual grids and
  shape latents**. Six receipt-backed render batches independently validated
  all **128/128** training teeth and all eight conditioning images per tooth
  (`ap-RR3pbENgCXxC12i7j5e0u0`, `ap-1Hs9Ch5st9XXU52NS1AJ2j`, audit
  `ap-dtfzmPtto4NqMXM3E1kstj`). Finalization passed in
  `ap-g4u5R0B4lxTf0rXBtFNmHz`; no optimizer was involved.
- A boundary request for nonexistent render batch 6 failed before work. The
  window entrypoint now obtains a remote deterministic batch plan and clamps
  the requested window to the real six-batch range. No accepted artifact was
  lost or corrupted.
- The fixed eight-tooth, two-per-family smoke cohort reused the audited
  renders. The two-step H100 gate (`ap-D2LAr2rrlyKkBCA95mtHyx`) emitted finite
  losses, wrote model/EMA/misc checkpoints and strictly reloaded step 2.
- The official TRELLIS.2 trainer seeds only by process rank. A fail-closed,
  tested source patch now adds the preregistered experiment seed, allowing two
  genuinely distinct, reproducible research seeds without silently changing
  the pinned trainer.
- Registered seed-A canary `toothfairy-stage1-shape-step50-seed1724708096-v1`
  (`ap-wh38sEAfomOh6LEyRR4RdM`) completed **50/50** finite steps over the 128
  balanced whole teeth, wrote complete step-50 checkpoints and passed strict
  reload. This is a training-success result only: no anatomical improvement,
  clinical or production claim is permitted yet.
- **Current gate:** compare unchanged base and seed-A candidate on the 12
  patient-disjoint validation whole teeth, with whole-tooth, crown and root
  metrics plus topology/repeatability gates. Seed B, longer optimization and
  deployment remain forbidden until that paired evaluation passes.

### Stage-1 seed-A held-out validation correction

- The first paired final-GLB validation attempt (`ap-myO7Ur89idfpsbFDCc7nZA`)
  was stopped after its first same-seed control showed that byte-identical GLB
  output is not a valid geometry-repeatability criterion. A second preregistered
  attempt (`ap-9KDv3QdNq8GjNnogsvM2ez2`) saved both meshes and measured
  **0.584865% of tooth diagonal symmetric Chamfer** between identical
  base-model requests (HD95 **1.06117%**) despite near-identical extents. This
  extraction noise is larger than the absolute change corresponding to the
  planned 5% relative improvement gate on that case, so loosening the threshold
  would permit a false anatomical result. Both runs were stopped early to
  protect compute.
- The corrected evaluator `evaluate_stage1_seed_a_raw_validation` measures at
  TRELLIS.2's raw shape-decode boundary, before texture sampling, CuMesh
  remeshing and GLB serialization. This follows the earlier sealed E3 boundary
  diagnosis, where sparse coordinates, shape-latent coordinates/features, raw
  vertices and raw faces were bit-identical and drift began only downstream.
  It persists binary PLY artifacts and content hashes, requires exact raw-shape
  repeatability in all four tooth families, verifies identical sparse
  conditioning for every base/candidate pair, and retains paired whole-tooth
  Chamfer, 10,000-sample bootstrap, canonical crown/root axial proxies and
  welded-topology non-regression gates. Case receipts are hash-checked and
  resumable.
- Corrected Modal run `ap-TxU1lZJSELfNkaas9M2ez2` completed and committed eight
  of twelve unchanged-base cases before the local Modal client lost HTTPS
  connectivity to all Modal API addresses (`Errno 10013` on port 443). This was
  a client/network interruption, not a recorded model exception. Resume the
  same function when connectivity returns; it will reuse the seven sealed
  receipts. Seed B, longer training, clinical claims and production promotion
  remain unauthorized until the complete raw-boundary report passes.

### Stage-1 seed-A raw validation stopping result

- Detached resumable run `ap-JC0U5QWkP5AGEwwSMmVopK` completed all **12/12**
  unchanged-base and **12/12** seed-A raw decoded mesh receipts, but correctly
  stopped before writing a comparison report. One paired molar case,
  `toothfairy2-stage50-whole-tooth-v1-ToothFairy2F_015-fdi37`, did not reproduce
  the same sparse-structure coordinate hash between the unchanged-base and
  candidate passes. The other 11 pairs matched exactly.
- Because sparse occupancy is upstream of the fine-tuned shape-flow checkpoint,
  that one mismatch means the two molar meshes were conditioned on different
  coarse geometry. Their apparent metric difference cannot be attributed to
  fine-tuning. The run therefore failed closed with `Sparse condition drifted`
  and produced no `stage1_seed_a_raw_validation_v1.json` promotion artifact.
- The 24 raw mesh/receipt artifacts remain preserved for diagnosis, but their
  aggregate changes are observational only and must not be used as evidence of
  improvement. Seed B, longer optimization, clinical claims and production
  promotion remain **unauthorized**. The next valid evaluator must materialize
  each unchanged-base sparse coordinate tensor once and feed that exact frozen
  tensor to both the base and candidate shape samplers, rather than resampling
  sparse structure twice.

### Stage-1 seed-A frozen-condition rerun

- Implemented validation contract `stage1-raw-paired-validation-v2`. Each of the
  12 heldout cases now gets one persisted, content-hashed sparse-coordinate
  tensor. The unchanged base, seed-A candidate and their family-repeatability
  passes all consume that same tensor; the evaluator fails closed unless the
  persisted and observed hashes are identical in every role.
- Added a regression test that deliberately changes the candidate's observed
  sparse hash and proves the pairing gate rejects it. The complete focused
  training test module passes **37/37** tests.
- Initial v2 run `ap-XKnjzk2uG5ygH9TPF3lh8C` materialized and committed all 12
  frozen conditions, then failed before base-model evaluation because TRELLIS
  returns conditioning as a nested mapping rather than a tensor with `.device`.
  No metric or checkpoint was produced. Device resolution now comes from the
  actual 512 shape-flow module; syntax and all 37 focused tests pass.
- Replacement run `ap-m9cfhUhUCDxJZL0F4WyyVs` reached the first repeatability
  pass, then exposed TRELLIS sequential CPU offloading: resolving the coordinate
  device from an offloaded shape module restored the frozen tensor to CPU while
  CUDA attention remained active. It stopped before committing any metric.
  Frozen inputs are now restored explicitly to the current CUDA device, while
  their bytes and hashes remain unchanged.
- Detached A100 evaluation `ap-9zB0NdU7AzCJUcBlwT5Us8` is active and reuses
  the same 12 verified frozen conditions. Its only
  permitted terminal artifact is `stage1_seed_a_raw_validation_v2.json` after
  all pairing, repeatability, anatomy and engineering gates run. Seed B remains
  unauthorized unless that report explicitly sets `seedBAuthorized=true`.

### Stage-1 seed-A terminal decision

- Frozen-condition run `ap-9zB0NdU7AzCJUcBlwT5Us8` completed with **12/12**
  base/candidate sparse-coordinate identities and exact raw repeatability in all
  four families. The sealed report is
  `stage1_seed_a_raw_validation_v2.json`, SHA-256
  `29b71576a7574e2578cc3e0a1c730a875885cdd0c19620454f7b750735b815b9`.
- Median paired Chamfer improvement was **-0.0202%** (relative fraction
  `-0.0002016`), with bootstrap 95% interval **[-1.1029%, +1.6448%]**. The
  interval crosses zero and the registered minimum improvement was not met.
  Family medians were incisor **-0.3900%**, canine **+0.4403%**, premolar
  **-0.2633%**, and molar **+1.6759%**.
- Raw repeatability passed, but regional crown/root non-regression and topology
  non-regression failed. No family had all three heldout cases pass the complete
  engineering gate. Therefore the valid report sets `passed=false` and
  `seedBAuthorized=false`.
- **Decision:** the 50-step Seed-A objective is rejected and closed. Seed B,
  longer optimization, clinical claims and production promotion are forbidden.
  The next experiment must use a materially different objective and pass, in
  order: one-tooth end-to-end evaluator integration; four-family frozen-pair
  evaluation; and a two-step training-plus-anatomy screen including crown,
  complete-root and topology non-regression. No 50-step run is authorized
  before those checks pass.
- Modal currently has zero active tasks. Production services and the production
  checkpoint were not changed.

### E10 anatomy-balanced shape objective — G0

- Registered `stage1-e10-axial-balanced-shape-v1` as the next materially new
  experiment. Standard token-mean flow loss is replaced by an equal-weight mean
  over four bands on each sample's longest sparse-coordinate axis. This is
  direction-independent, so upper/lower and left/right teeth do not need a
  shared crown-up sign, while slender terminal/root regions cannot be drowned
  out by a token-dense body or crown.
- Added a frozen unchanged-base teacher with a detached, sealed **5%** target
  contribution. The preservation term constrains broad functional drift while
  the band-balanced supervised term supplies the dental adaptation signal.
- The patch fails closed if the pinned upstream initialization, prediction or
  loss paths change; it also rejects coordinate drift and samples that do not
  occupy all four bands. Local syntax, configuration and the focused training
  suite pass **38/38** tests.
- G0 is complete. No GPU job was launched. G1 is limited to one optimizer step
  on one training tooth, strict checkpoint reload and immediate frozen-condition
  raw decode. A 2-step four-family screen and any 50-step canary remain locked.
- G1 implementation now materializes one deterministic training tooth, performs
  exactly one optimizer step at learning rate `1e-6`, requires a measured 5%
  teacher contribution, strictly reloads all step-1 checkpoint state, and then
  decodes one heldout tooth twice from the same persisted sparse condition. It
  authorizes G2 only when both raw boundaries are bit-identical and non-empty.
  Local syntax and focused tests pass **39/39**. Detached H100 run
  `ap-Or2fenYM7BSCNueAKm8xu2` is active; production remains untouched.

### E10 anatomy-balanced shape objective — G1 passed / G2 active

- Corrected G1 v4 (`ap-jslVNUXToNKSke1EdSPVZk`) passed the complete one-step
  integration gate: the initial teacher term was exactly zero, the read-only
  post-update probe measured the sealed 5% contribution ratio, all four axial
  bands were populated, the teacher remained frozen, checkpoint reload passed,
  and two raw decodes from one persisted sparse condition were bit-identical.
  Its non-empty PLY artifact SHA-256 is
  `78d1b791948366ed93737e3ce701a21d9aa386811ce0cf1901e3cec85423624e`.
- G2 is implemented as a single sealed research run. It selects one training
  tooth per family by joining TRELLIS metadata hashes to the clinical manifest,
  permits exactly two optimizer steps at `1e-6`, strictly reloads step 2, then
  compares unchanged base and candidate on one patient-disjoint validation
  tooth per family. Both roles consume the same already-persisted sparse tensor
  and must reproduce the complete raw boundary exactly on a second decode.
- G3 is authorized only if **every** incisor, canine, premolar and molar passes
  crown/root regional and welded-topology non-regression. This four-case screen
  is an engineering safety gate, not an efficacy or clinical claim. The focused
  G2 tests pass **2/2**; the broader module has 41 passing tests plus two
  environment-only `tmp_path` setup errors caused by the inaccessible host
  pytest temp directory.
- The first G2 launch (`ap-pK4TiooFswekd11697sh94`) stopped before training
  because the TRELLIS CSV intentionally omits tooth-family labels. No optimizer
  step ran. The selector now joins immutable mesh hashes to the sealed manifest.
  Corrected H100 run `ap-0srBjpiSqrl3jm6ploH6U0` is active. Production services
  and production checkpoints remain unchanged.

### E10 G2 terminal decision — rejected

- Corrected G2 run `ap-0srBjpiSqrl3jm6ploH6U0` completed normally and wrote
  sealed evidence at
  `/stage1-e10-g2-four-family-v1/g2-evidence.json`. It executed exactly two
  optimizer steps, observed teacher contribution ratio `0.0500000011`, kept
  the teacher frozen, strictly reloaded the step-2 checkpoint and passed exact
  raw repeatability for both model roles in all four tooth families. Candidate
  checkpoint SHA-256 is
  `e45ea47b852c258a92e69ec4c94b12251b49472ec0f3f409e1fb78c4e056491f`.
- Whole-tooth Chamfer changed by incisor **-0.2903%**, canine **+0.9008%**,
  premolar **+0.8650%**, and molar **+0.7672%**. These small aggregate gains do
  not override the preregistered regional safety gates.
- Incisor and canine failed root/cervical regional gates and welded-topology
  checks. Molar preserved welded topology but failed apical/cervical regional
  checks. Premolar preserved welded topology but regressed in the registered
  crown and root proxies. Consequently zero of four families passed the full
  engineering gate.
- **Decision:** `g3Authorized=false`. The E10 two-step candidate is rejected;
  the 50-step G3 canary, clinical claims and production promotion remain
  forbidden. The result indicates that axial band balancing produces a small
  whole-tooth signal in three families but is insufficiently anatomy-aware:
  the next objective must constrain regional crown/root geometry and topology
  directly rather than relying only on axial token reweighting plus a global
  teacher term.

### E11 bandwise preservation objective — G0

- G2 localized the next correct change. E10 gave the supervised flow target
  equal weight across four principal-axis regions, but its frozen-teacher
  preservation loss remained a global token mean. Dense crown/body tokens
  could therefore satisfy the global 5% preservation contribution while a
  sparse root, apex or terminal crown band crossed a geometry/topology boundary.
- E11 applies the frozen teacher loss with the same equal per-sample,
  per-four-band aggregation as the supervised term, then calibrates that
  band-balanced preservation total to the sealed detached 5% contribution.
  The objective remains orientation independent and now records minimum and
  maximum band teacher MSE in its immutable receipt.
- Direct decoded-occupancy supervision is deliberately not revived: E9 showed
  that semantically meaningful timesteps exceeded the registered safe gradient
  ratio, while the only gradient-safe timestep had near-zero occupancy Dice.
  Direct welded-topology loss is also unavailable at this boundary because raw
  mesh extraction is non-differentiable.
- The pinned-source patch fails closed and the focused E10/E11 tests pass
  **3/3**. G0 is complete. G1 is restricted to one tooth, one optimizer step,
  a read-only post-update objective probe, strict reload and exact repeated raw
  decode. No four-family or longer run is authorized until G1 passes.
- Research-only H100 G1 run `ap-8nrulojuuPM2y29FFB4RDN` is active. It is
  limited to one optimizer update and cannot alter production.
- E11 G1 `ap-8nrulojuuPM2y29FFB4RDN` completed and passed. The post-update
  probe ran in `ImageConditionedSparseFlowMatchingCFGTrainer`, measured teacher
  contribution ratio `0.0500000018`, and recorded finite band MSE range
  `[0.0002269675, 0.0002334937]`. The teacher remained frozen, strict reload
  passed, and repeated raw decode was exact. Checkpoint SHA-256 is
  `a24029af8583bf007eededfbed6c10d842e4cc63248578ee1f4f831046254d2b`.
- The proven G2 evaluator was parameterized rather than duplicated. E11 G2 is
  now running as `ap-AOkmdFn5RXNPtFJydPjWvO`: exactly two optimizer steps over
  one training tooth per family, followed by paired repeated raw evaluation on
  one patient-disjoint heldout tooth per family. It must still pass every
  crown/root and welded-topology gate before any longer run is authorized.

### E11 G2 terminal decision — rejected

- E11 G2 run `ap-AOkmdFn5RXNPtFJydPjWvO` completed normally and wrote valid
  sealed evidence at `/stage1-e11-g2-four-family-v1/g2-evidence.json`, local
  SHA-256 `4c955a789b4778c46b87c11e7e581ade71aa035ee31b23a832bbdf4377cc2706`.
  It executed exactly two optimizer steps, observed the calibrated teacher
  contribution ratio `0.0500000032`, kept the teacher frozen, strictly reloaded
  the candidate checkpoint, and passed exact raw repeatability. Candidate
  checkpoint SHA-256 is
  `bf48f350b30372a96c630d79f63e618c695255cbf25ced219f6ab8e352c2446e`.
- Whole-tooth Chamfer improved for incisor **+0.1240%**, premolar **+0.9596%**
  and molar **+2.5112%**, but canine regressed **-0.4641%**. This is a stronger
  aggregate signal than E10, particularly for molars, but it is not sufficient
  evidence of safe anatomical improvement.
- All four families failed the preregistered complete engineering gate. Incisor
  regressed in the middle-root proxy and topology; canine regressed across
  apical, middle-root and cervical proxies; molar failed apical/middle-root/
  cervical checks and topology; premolar failed cervical/crown checks and all
  four registered topology checks.
- **Decision:** `g3Authorized=false`. E11 is closed without a longer run,
  clinical claim or production promotion. Bandwise frozen-teacher preservation
  improves the aggregate direction but still cannot reliably control decoded
  regional geometry and topology after only latent flow supervision. The next
  experiment must introduce a differentiable geometry-aware signal or change
  the adapted boundary; merely increasing E11 steps is not authorized.

### E12 native geometry decoder objective — G0 passed

- E12 changes the adapted boundary from the image-conditioned shape-flow model
  to the official TRELLIS.2 shape SC-VAE decoder. The base encoder is frozen
  before optimizer construction, preserving the latent contract consumed by the
  unchanged production flow model. Texture models also remain outside scope.
- The objective uses TRELLIS.2's native differentiable geometry supervision:
  dual-grid intersection BCE, vertex regression, multiscale subdivision BCE,
  and rendered silhouette, depth and normal losses (L1, SSIM and LPIPS). This is
  materially different from E10/E11 latent reweighting and directly observes the
  decoded whole-tooth surface, including roots.
- The fail-closed source anchors each occur exactly once in pinned TRELLIS.2
  commit `1762f493fe7731a3b7cc6b79ad5da7b015b516c1`. Syntax and configuration
  validation pass, and the focused E10/E11/E12 gate suite passes **4/4**. The
  immutable receipt requires every native geometry term to be finite and proves
  the optimizer contains decoder parameters only.
- **Decision:** G0 passed and a one-tooth, one-step G1 integration is authorized.
  G2, any longer training, clinical claims and production mutation remain
  locked until G1 proves encoder identity, strict decoder reload, exact repeated
  heldout-latent decode and a non-empty raw mesh.
- The first G1 worker attempt (`ap-0PL7GV6Xkyv1LX2c1YFnLX`) stopped during
  official dataset filtering, before model initialization or any optimizer
  update. Its one-tooth view lacked `dual_grid_converted`, `dual_grid_size` and
  `num_faces`. G1 v2 derives those fields from the sealed VXZ and mesh-dump
  artifacts. The failed v1 directory is retained as auditable non-evidence.
- G1 v2 (`ap-HEDEL0fWmmK4gA2HSvSyF1`) stopped before trainer initialization
  because the official shape-VAE loss module imports `lpips`, which was absent
  from the research image. It performed zero optimizer steps and is retained as
  auditable non-evidence.
- E12 now uses a dedicated derivative of the research image with
  `lpips==0.1.4` pinned, without changing any existing production or
  flow-training image. Image construction verifies LPIPS. Because importing the
  official trainer initializes Triton and requires an active GPU driver, the
  complete trainer import is checked in a separate T4-backed, zero-optimizer
  fail-fast gate before any H100 G1 launch. G1 v3 remains capped at one decoder
  optimizer step; G2 and production are still locked.
- The GPU import gate passed as Modal run `ap-ohw4rYMEq7g2ZiuPETXKgl`: CUDA
  initialized and the official `ShapeVaeTrainer` imported with LPIPS, with zero
  optimizer steps. Sealed G1 v3 is now running as
  `ap-EBWWLGswPTdX5NZO0YsicS` on H100. This is the first E12 attempt permitted
  to reach trainer initialization after both dependency gates; it remains
  limited to one update and cannot mutate production.
- G1 v3 (`ap-EBWWLGswPTdX5NZO0YsicS`) reached the official trainer, loaded the
  frozen base encoder and decoder, accepted the one-tooth dataset, and began its
  first loss evaluation. It then failed at native `bce_sub` computation because
  one multiscale subdivision ground-truth target was `None`. The optimizer never
  stepped, so v3 is infrastructure/data-contract evidence only and not a model
  result. Before another H100 attempt, a GPU zero-step data-contract gate must
  enumerate every native target and prove all required subdivision levels are
  populated for the selected tooth; alternatively it must select a reviewed
  training tooth that satisfies the unchanged official objective. Silently
  dropping the missing term is forbidden because it would change E12's sealed
  geometry objective. G2 and production remain locked.
- Pinned-source review identified the v3 cause: TRELLIS.2 registers each
  `subdivision` spatial-cache target inside `SparseSpatial2Channel` only when
  that encoder module is in training mode. E12 had frozen the encoder and also
  placed it in evaluation mode, unintentionally suppressing the official target
  cache. G1 v4 keeps the encoder in training mode for this required structural
  side effect while setting all encoder parameters `requires_grad=False` before
  optimizer construction. A fail-closed check now proves that every predicted
  subdivision level has a non-null target before any loss or optimizer step and
  records the level count in the objective receipt. The native objective and
  its weights are unchanged.
- Corrected sealed G1 v4 is running as `ap-clg2tMppwZaRTu0ZpvCOGc`. It is
  still capped at one decoder optimizer step and must pass finite native terms,
  frozen encoder identity, strict checkpoint reload, exact repeated heldout
  decode and non-empty raw mesh before G2 can be considered.
- G1 v4 stopped during the first backward pass with zero optimizer steps. The
  encoder training-mode correction worked: all native subdivision targets were
  present, the complete forward geometry objective ran, and LPIPS initialized.
  Backward then failed inside FlexGEMM `SubMConv3dFunction` because its neighbor
  cache lacked `valid_signal_i`. No candidate checkpoint or efficacy evidence
  was produced. The next gate must reproduce this boundary with a detached
  leaf latent that requests gradients (preventing gradients from reaching the
  frozen encoder while satisfying FlexGEMM's decoder-input backward-cache
  contract), and must prove decoder gradients are finite before authorizing
  another optimizer step. G2 and production remain locked.
- E12 v5 implements that boundary explicitly. The frozen encoder output is
  detached and reintroduced as a gradient-enabled leaf while retaining its
  spatial cache, so FlexGEMM can construct decoder-input backward metadata but
  no gradient path reaches the encoder. Immediately after backward and before
  clipping or optimizer execution, a fail-closed BasicTrainer gate requires a
  present finite gradient for every decoder parameter tensor and writes a
  separate gradient receipt. Local syntax/configuration and focused tests must
  pass before the one-step H100 run is launched.
- The v5 source patches match the exact pinned official trainer boundaries and
  the focused E12 suite passes **3/3**. Sealed one-step run
  `ap-BQlZIh2mAFWulTQnqHGmSg` is active. G2, clinical claims and production
  mutation remain locked pending its complete evidence contract.
- G1 v5 stopped at the same FlexGEMM backward boundary with zero optimizer
  steps. Upstream FlexGEMM source inspection localized the cause: sparse tensors
  carry a spatial cache across encoder and decoder, and a cache first built when
  gradients are disabled omits `valid_signal_i`, `valid_signal_o` and related
  backward metadata. Making the latent a grad-enabled leaf does not replace an
  already cached neighbor map.
- V6 retains subdivision and channel-to-spatial caches required by the official
  decoder but removes only keys prefixed `SubMConv3d_neighbor_cache_` at the
  frozen encoder boundary. Decoder convolution therefore rebuilds its own
  gradient-capable neighbor caches. The receipt records how many inference-only
  caches were removed, and the existing pre-optimizer finite-gradient gate
  remains mandatory. Objective weights and production remain unchanged.
- Sealed E12 G1 v6 (`ap-bhFNrtfIaVjMhdIxvrwOmU`) is terminal with **zero
  optimizer steps**. Selective neighbor-cache invalidation fixed the prior
  FlexGEMM backward-contract failure: the complete native forward and backward
  passes reached the explicit pre-optimizer gradient gate, and no decoder
  parameter gradient was missing. The gate then found non-finite gradients
  (the first reported affected parameter tensor indices were `2..17`) and
  correctly blocked the update. No candidate checkpoint or efficacy evidence
  was produced; G2 and production remain locked.
- This narrows the next investigation to numerical stability inside the native
  decoder objective/backward path, not sparse-cache construction. A new H100
  training retry is not authorized yet. The next zero-step diagnostic must
  backpropagate each sealed objective component independently, record the first
  decoder layer and term that introduces a non-finite gradient, and compare the
  current official FP16 path with a diagnostic numerically safe precision path.
  It must not change objective weights, execute an optimizer step, or mutate
  production. Only a finite full-objective backward may authorize G1 v7.
- The zero-step diagnostic is now implemented and locally verified. It uses
  `torch.autograd.grad` to differentiate every sealed native term independently
  against named decoder parameter tensors, then differentiates the unscaled
  aggregate loss. It records missing/non-finite gradient names and the maximum
  finite magnitude for each term, deliberately raises a sealed completion
  marker inside `training_losses`, and therefore cannot reach the trainer's
  normal backward or optimizer boundary. The focused E12 suite passes **4/4**;
  the broader training module suite has **46 passing tests**, with two unrelated
  fixture setup errors caused by the local Windows temporary-directory ACL.
- The single retained diagnostic is running on H100 as Modal app
  `ap-UWhNO191tpLXmKei3w4z59`. Two duplicate ephemeral submissions caused by
  Windows CLI selector behavior were stopped before being allowed to continue;
  they are not scientific evidence. The retained run performs zero optimizer
  steps and cannot mutate production.
- E12 component-gradient diagnostic `ap-UWhNO191tpLXmKei3w4z59` completed its
  sealed scientific boundary with **zero optimizer steps**. The immutable
  component receipt SHA-256 is
  `f95671e0e409aa39987769f0d7e3a1c04b2c1fc205d99d7ba73ca4dad364e372`.
  Every native term had zero non-finite gradients: direct intersection, direct
  vertex, rendered mask/depth/normal L1/SSIM/LPIPS, and subdivision levels
  `bce_sub0..3`. KL correctly had no decoder gradient because the encoder is
  frozen. Per-term missing gradients were confined to branches that the term
  does not address and are expected.
- The unscaled aggregate loss reached all **292/292** decoder parameter tensors
  with zero missing and zero non-finite gradients; maximum absolute gradient
  was `0.0024108386132866144`. Combined with v6—where the normal trainer
  backward made widespread `.grad` tensors non-finite—this localizes the fault
  after objective construction, specifically to the official FP16
  `inflat_all` scaled-backward path, rather than to any native geometry term.
  The wrapper remained alive after persisting the completed receipt, so the app
  was stopped to prevent idle H100 spend; this does not affect the committed
  receipt.
- G1 v7 is **not yet authorized**. The next bounded test is a zero-optimizer
  normal-backward probe with an explicitly controlled loss scale. It must prove
  complete finite decoder `.grad` tensors using the unchanged objective before
  any one-step optimizer retry.
- The controlled-scale probe is implemented at the exact pinned BasicTrainer
  boundary. Official `inflat_all` starts at `log_scale=20` (loss multiplier
  1,048,576); the probe is sealed to `log_scale=12` (4,096), runs the unchanged
  normal backward, records missing/non-finite/all-zero named decoder gradients,
  and deliberately stops before gradient clipping, master-gradient transfer or
  optimizer logic. The focused E12 suite passes **5/5**. A pass authorizes only
  the one-step G1 v7 integration, not E13 training or production.
- The single controlled-scale probe is running on H100 as Modal app
  `ap-jYcjdF3hs1C4x9GdWgVwPW`. It permits zero optimizer steps and leaves all
  production services and checkpoints unchanged.
- The scale-12 probe completed its sealed boundary with **zero optimizer
  steps**. Receipt SHA-256 is
  `127bf05e21a8c81d01cd4bb44ac56ef716846fc42e5333ef82bd14939b1eb9dd`.
  Normal `inflat_all` backward reached all **292/292** decoder parameter
  tensors: missing `0`, non-finite `0`, all-zero `0`. The largest scaled
  absolute gradient was `9.702435493469238`; the smallest nonzero scaled
  absolute gradient was the FP16 subnormal floor
  `5.960464477539063e-08`. This proves scale 12 avoids the scale-20 overflow,
  while retaining at least one nonzero gradient in every parameter tensor.
- `g1v7Authorized=true` for exactly one optimizer step using the unchanged E12
  objective and initial log scale 12. It does not authorize E13, a longer run,
  a clinical claim or production mutation. The wrapper remained alive after
  committing the sealed receipt and was stopped to prevent idle H100 spend.

### E12 G1 v7 one-step implementation ready

- The one-step decoder integration now applies the preregistered initial
  `log_scale=12` inside the normal TRELLIS.2 `inflat_all` training path. The
  pre-optimizer gate fails closed unless all 292 decoder parameter tensors have
  present, finite, and nonzero gradients and the runtime receipt reports the
  exact scale pair `logScale=12`, `lossScale=4096`.
- The post-step contract remains bounded to exactly one optimizer update,
  complete checkpoints, byte-identical frozen encoder state, strict decoder
  checkpoint reload, exact repeated decoding of the same held-out latent, and
  a non-empty raw mesh artifact. The run is sealed as
  `stage1-e12-g1-one-tooth-v7` and continues to reuse the immutable reviewed
  one-tooth data view rather than creating a new sample.
- Syntax validation and the focused E12 suite pass **6/6**. This implementation
  authorizes launching G1 v7 only; G2, E13, clinical claims, and production
  mutation remain locked pending sealed evidence.
- The single authorized G1 v7 run is active on Modal as
  `ap-Dhu6S0QTAsDecbSYn69Dal`. Its sealed evidence target is
  `/stage1-e12-g1-one-tooth-v7/g1-evidence.json` on the anatomy-checkpoints
  volume. No second run has been launched.
- G1 v7 is terminal and **did not authorize G2**. The one allowed optimizer
  step completed and checkpoints were written. The native objective was finite,
  and the pre-step receipt passed all 292 decoder tensors with missing `0`,
  non-finite `0`, all-zero `0`, `logScale=12`, and `lossScale=4096`.
- The wrapper then failed the frozen-encoder identity gate:
  `RuntimeError: E12 G1 changed the frozen encoder`. It stopped before strict
  reload and held-out raw-decode qualification, so no `g1-evidence.json` was
  sealed. This is a post-step verification failure, not evidence of anatomical
  improvement. G2 and E13 remain locked. The next action must diagnose whether
  the mismatch is an actual parameter mutation or a representation/dtype change
  introduced when the base checkpoint is loaded and saved; no optimizer retry
  is authorized until that distinction is proven with tensor-level evidence.
- A zero-optimizer encoder-identity diagnostic is now implemented. It compares
  every base/saved tensor for key and shape identity, raw equality, dtype
  changes, equality after casting the base tensor to the saved runtime dtype,
  and maximum absolute numeric difference. It classifies the result as exact,
  dtype/serialization-only, or genuine state change and fails closed on missing
  keys, unexpected keys, shape changes, or any canonical value difference.
  Focused E12 tests now pass **7/7**. The diagnostic may authorize qualification
  of the existing v7 decoder checkpoint, but cannot authorize G2 directly and
  executes no optimizer step.
- The zero-step diagnostic completed as Modal app
  `ap-j5mczGGhqLluVYtHZlNbJm`. All **284** encoder tensors have identical keys
  and shapes. Exactly **76** tensors were serialized in a different dtype, but
  after casting the base tensors to the saved runtime dtype there are **0**
  changed tensors and maximum absolute difference is **0.0**. The failure was
  therefore a dtype/serialization-only hash mismatch, not encoder learning.
- Qualification of the existing v7 decoder checkpoint is authorized without
  repeating its optimizer step. The qualification must perform a strict trainer
  reload, strict EMA decoder state load, two exact decodes of one sealed
  held-out latent, and persist a non-empty raw mesh before it may set
  `g2Authorized=true`.
- The zero-optimizer existing-checkpoint qualification is active on H100 as
  Modal app `ap-F0rJzJtfT3OjGu0HAGB9jt`. It performs no training and will reuse
  only the already-written v7 checkpoints.
- E12 G1 v7 existing-checkpoint qualification completed and sealed
  `g1-evidence.json`. Strict trainer reload and strict EMA decoder loading
  passed. Two decodes of the same held-out latent were byte-exact at both the
  vertex and face boundaries. The non-empty raw mesh contains **565,204
  vertices** and **1,130,106 faces**; artifact SHA-256 is
  `0fa21ab4b13b5292b30b33df892aa509a741f24157a4947baab95ebd9bc9dc86`.
- The candidate decoder SHA-256 is
  `8615011706a7d1c90c3f4779ed0114e7f6081f2111f951a54964e71506085368`.
  G1 now explicitly sets `g2Authorized=true`. This is engineering integration
  evidence only: it does not establish anatomical improvement, permit a
  clinical claim, authorize E13, or permit production mutation.
- E12 G2 is implemented as a **zero-optimizer**, paired decoder screen. It uses
  one patient-disjoint held-out incisor, canine, premolar and molar and sends
  the identical sealed shape latent through the unchanged base decoder and v7
  candidate decoder. Every role is decoded twice and must be byte-exact.
- The preregistered G2 pass rule requires every regional root/crown and welded
  topology non-regression check to pass, positive median crown Chamfer relative
  improvement, crown improvement in at least three of four families, and no
  median whole-tooth Chamfer regression. This remains an engineering screen,
  not a statistical or clinical improvement claim. The focused E10/E12 suite
  passes **10/10**.
- The authorized G2 screen is active on Modal as
  `ap-QfsT2rG3atriPs4gbkFZrt`. It performs zero optimizer steps and cannot
  mutate production.
- G2 v1 stopped before the first decode with
  `KeyError: 'canonicalSha256'`. The patient-disjoint validation receipt stores
  case ID, FDI number and reference-mesh path, while the implementation tried
  to read the canonical mesh digest directly from the case. No optimizer ran,
  no base/candidate comparison occurred, and this is not scientific evidence
  for or against the decoder. The correction is a fail-closed join from the
  validation case to its sealed manifest asset before resolving the latent.
  E13 remains locked.
- G2 v2 fixes the metadata boundary with a fail-closed unique case-ID join to
  the manifest. It verifies validation split, tooth family, patient/group, FDI
  number, canonical path and reference SHA-256 before resolving a latent. The
  real sealed metadata resolves exactly one incisor, canine, premolar and molar,
  and the focused suite passes **11/11**. V2 writes to new output/evidence paths
  and reuses the existing candidate without any optimizer step.
- Corrected G2 v2 is active on Modal as `ap-DdFNPdqBI1Mkk24bO2oFwQ`.
- G2 v2 completed with zero optimizer steps, exact repeated raw decodes, four
  positive meshes and identical frozen latent hashes for every base/candidate
  pair. The candidate nevertheless **failed the anatomical and engineering
  gates**. Median crown Chamfer relative improvement was **-0.6601%** and only
  the premolar improved crown Chamfer (**+1.0209%**); incisor, canine and molar
  regressed. Median whole-tooth Chamfer changed by **+0.0921%**.
- Engineering non-regression failed in every family: the incisor regressed
  middle-root/cervical sample share and component topology; the canine regressed
  boundary edges; the molar regressed middle-root, cervical, crown-share,
  coronal-pole and boundary-edge checks; the premolar regressed middle-root
  sample share and the apical-pole proxy. Therefore `passed=false` and
  `e13Authorized=false`. This candidate must not be deployed or used as evidence
  of anatomical improvement.
- The next permitted action is zero-optimizer decoder-delta localization, not
  E13 training. It compares the base and rejected v7 decoder tensor-by-tensor
  after runtime-dtype canonicalization and reports changed tensors, parameters,
  L2 delta and maximum absolute delta for `from_latent`, blocks 0-3 and the
  output stage. Only a fully recognized, non-empty late-stage delta may
  authorize a base-plus-late-delta hybrid screen. Focused tests pass **12/12**.
- Decoder-delta localization completed on Modal as
  `ap-rrFgYRt5rm8QIXShPrYhYC` with zero optimizer steps. All **292/292** decoder
  tensors changed after the one-step update, across only recognized stages.
  The update is dominated by early stages (`blocks.0` L2 `3.7709e-05`,
  `blocks.1` L2 `2.7079e-05`); the sealed late boundary contains **42** tensors
  (`blocks.3` L2 `4.8521e-06`, output L2 `1.3947e-06`). The report therefore
  sets `lateDeltaHybridAuthorized=true` while keeping E13 training, production
  mutation and clinical claims false.
- The next screen is implemented as a zero-optimizer base-plus-late-delta
  ablation. It restores the exact base state for `from_latent` and blocks 0-2,
  substitutes only the 42 v7 tensors in block 3/output, reuses the four sealed
  base receipts, and decodes every hybrid case twice. E13 remains locked unless
  the same crown, whole-tooth, root/cervical, topology and repeatability gates
  all pass. Focused localization/hybrid tests pass **2/2**.
- The late-delta hybrid completed as Modal app `ap-zpWAmUIiPy6Se9cJycqWrD`
  with zero optimizer steps. The sealed candidate used exactly **42** tensors
  from `blocks.3.*` and `output_layer.*`; all other decoder tensors came from
  the exact base. Four patient-disjoint families used identical frozen latent
  hashes, every base/candidate decode repeated exactly, and all meshes were
  non-empty.
- The hybrid was **rejected**. Median crown Chamfer relative improvement was
  **-2.2196%**, only the incisor improved (**+0.5103%**), and median whole-tooth
  improvement was **-0.2048%**. Engineering non-regression failed in all four
  families: incisor middle-root/crown sample-share; canine apical pole; molar
  cervical/crown sample-share, coronal pole and largest-component area; and
  premolar apical pole, boundary edges and non-manifold edges. Therefore
  `passed=false` and `e13Authorized=false`; no training or deployment is
  permitted.
- The next permitted ablation is still zero-training: evaluate the two output
  tensors alone against the same sealed base receipts. If output-only fails,
  separately evaluate the 40 `blocks.3.*` tensors only to localize whether the
  regression originates in final surface projection or late feature decoding.
  Neither result may authorize E13 unless every existing anatomy and engineering
  gate passes.
- Output-layer-only ablation `ap-Y8iCpmf6xD9SOzpdxxLXYu` completed with zero
  optimizer steps and exactly two candidate tensors. Frozen latent identity,
  exact repeated raw decoding and positive meshes passed for all four families.
  It was **rejected**: median crown Chamfer relative improvement was **-2.1832%**,
  only the premolar improved (**+0.2168%**), and engineering non-regression
  failed. Median whole-tooth Chamfer improved **+1.1169%**, demonstrating again
  that an aggregate gain cannot override crown, root-pole and topology failures.
  `e13Authorized=false`.
- The final permitted decomposition is `blocks.3.*` only: 40 candidate tensors
  with the output layer and all earlier decoder stages restored from the exact
  base. It uses the same base receipts and four-family gates with zero optimizer
  steps. A failure rejects reuse of the v7 one-step delta entirely.
- The blocks.3-only ablation completed as `ap-oXiBBcPI6ioo3Gxu7rH3PT` with zero
  optimizer steps, exactly 40 candidate tensors, four identical frozen latents,
  exact repeated raw decodes and positive meshes. It was **rejected**: median
  crown Chamfer relative improvement was **-1.5310%**, only the incisor improved
  (**+1.1561%**), and engineering non-regression failed. Median whole-tooth
  Chamfer improved **+0.7301%**, but molar middle-root/topology and multiple
  crown, cervical, pole and premolar topology gates failed.
- All three v7 decompositions are now negative: full late delta, output-only and
  blocks.3-only. The v7 one-step delta is rejected in its entirety and must not
  seed E13, production or an anatomical-improvement claim. The next phase must
  be a fresh E13 zero-step objective/gradient integration canary with base-state
  initialization, not another task-vector ablation or training run.
- The recovery plan was revised before any further training. R0 now measures
  the unchanged base decoder on all 12 sealed reference-mesh latents against
  the already-sealed unchanged-base image-conditioned reconstructions for the
  same teeth (three per family). This isolates the representation/decoder
  ceiling from the image-conditioned inference gap.
- The first R0 wrapper (`ap-ACqDOMLkx4TSowhiaRpdqJ`) stopped before any model
  evaluation because unrepeated product receipts correctly encode
  `repeatability: null`; the initial validator incorrectly treated that as a
  malformed dictionary. This is an integration failure and no scientific
  evidence. The validator now requires the sealed product contract of exactly
  one exact repeat per family and accepts the other eight sealed receipts.
- Replacement R0 run `ap-VmrYHCvIwQmoNR61eMZOm5` is active. It performs
  **zero** optimizer steps, repeats every raw oracle decode exactly, commits one
  receipt per tooth for safe resume, and cannot authorize training, a clinical
  claim, production mutation or deployment. The terminal evidence path is
  `/toothfairy-stage1-v1/stage_attribution_r0_v1.json` on
  `dentalsculptor-anatomy-datasets-v1`.
- Replacement R0 wrapper `ap-VmrYHCvIwQmoNR61eMZOm5` completed all 12 resumable
  oracle decodes but stopped during summary assembly. One sealed product receipt
  (`ToothFairy2P_478-fdi37`) marks the apical-root proxy unavailable and therefore
  has no regional Chamfer field; the initial summary assumed both proxy bands
  existed. This is an integration/metric-availability failure, not scientific
  evidence. No optimizer step ran and no final R0 evidence was written. The
  summarizer is corrected to compare the intersection of available paired root
  bands and explicitly report how many cases contain both bands. The 12 decoded
  receipts remain committed for a safe zero-compute resume; no replacement run
  was launched by the monitor.
- Corrected R0 resume launched as `ap-r7JVEthWhEqGAR0zCfzTYM` after the revised
  missing-region behavior passed all three focused R0 tests. It reuses the 12
  committed oracle artifacts and remains a zero-optimizer, non-production
  evidence assembly run.
- Corrected R0 completed with sealed evidence at
  `/toothfairy-stage1-v1/stage_attribution_r0_v1.json` and local copy
  `dentalsculptor-ml/artifacts/stage_attribution_r0_v1.json`. All 12 unique
  oracle/product IDs paired exactly; the cohort contains three cases per family;
  every oracle decode repeated exactly; all oracle meshes have positive vertex
  and face counts; and the product repeatability contract contains exactly one
  exact repeat per family. Eleven cases expose both root proxy bands and one
  exposes only the paired middle-root band. Source manifest, validation-input
  and product-report hashes are sealed in the report.
- Median oracle crown Chamfer is **0.558929%** of tooth diagonal versus
  **2.781558%** for the image-conditioned product path. The median product/oracle
  error ratio is **4.8622x** for crowns and **4.2899x** for the available paired
  root bands. Family median crown ratios are incisor **2.9438x**, canine
  **4.7216x**, premolar **5.0027x**, and molar **6.0997x**. The sealed conclusion
  is `dominantMeasuredBoundary=image-conditioned-generation` and the next
  training-boundary recommendation is `image-conditioned-shape-inference`.
  This is stage attribution, not a clinical-improvement or production-promotion
  claim.
- The next bounded experiment is **R0.1, zero-training conditioning
  decomposition**. For the same images and seeds, run the unchanged base shape
  inference twice: once with the sealed product sparse support and once with the
  reference-latent sparse support. Decode both with the unchanged base decoder.
  This isolates image-to-sparse-structure error from shape-feature inference
  error before choosing a LoRA/adapter target. No training is authorized by R0.
- R0.1 is implemented, covered by five focused R0/R0.1 tests, and launched as
  Modal app `ap-ZuFuPTDMa027ISzndE8n34`. The run changes only the sparse support:
  image, seed, unchanged shape-flow models, decoder and sampler settings remain
  fixed. It commits per-tooth meshes and receipts for safe resume and performs
  zero optimizer steps. Terminal evidence will be written to
  `/toothfairy-stage1-v1/stage_attribution_r01_v1.json`.
- R0.1 completed successfully with sealed evidence and zero optimizer steps.
  All 12 IDs pair exactly, all reference-support meshes are non-empty, and one
  exact repeated decode per family passed. Replacing only predicted sparse
  support with reference-latent support closed **93.2018%** of the median crown
  gap and improved all **12/12** cases. Family median gap closure was incisor
  **84.3775%**, canine **94.6953%**, premolar **91.8846%**, and molar
  **97.6262%**. Median reference-support/oracle crown error ratios were 1.2867x,
  1.2578x, 1.2974x and 1.1300x respectively.
- The sealed sub-boundary is `image-to-sparse-structure`; decoder and broad
  shape-feature adaptation are not the next target. This is causal stage
  attribution under ground-truth sparse support, not proof that a learned model
  can infer that support from a single image and not a clinical claim.
- The next minimal experiment is **R0.2 sparse-support error characterization**
  with zero optimizer steps: compare base predicted versus reference sparse
  coordinates by family and axial crown/cervical/root bands using occupancy
  precision, recall, IoU, connected components and extent/pole errors. Bind each
  sparse receipt to the R0.1 geometry response. Only after this identifies the
  missing/extra occupancy pattern may a crown-weighted, root-preserving sparse
  adapter canary be specified. This explicitly incorporates the earlier E3-E9
  failures instead of rerunning broad sparse-flow fine-tuning.
- R0.2 completed as CPU-only Modal app `ap-vquD57gyOGdHCOnE2O8prZ` with zero
  optimizer steps. All 12 source tensors and R0/R0.1 hashes paired exactly.
  Median exact sparse-support precision is **0.2321**, recall **0.2440**, IoU
  **0.1300**, and centroid shift **1.6506 voxels**. Globally, extra predicted
  occupancy is slightly dominant because recall exceeds precision.
- The crown proxy is decisively the weakest band: median precision **0.1176**,
  recall **0.1155**, and IoU **0.0438**. Median crown recall by family is incisor
  **0.0944**, canine **0.0000**, premolar **0.2973**, and molar **0.0151**. The
  apical proxy is also weak (median IoU **0.0706**), while middle-root and
  cervical proxy IoUs are **0.1328** and **0.1259**. These remain engineering
  axial proxies, not clinical tissue labels.
- R0.2 authorizes design, not an optimizer run. Exact coordinate overlap is
  sensitive to a small coordinate-frame displacement, and the observed median
  centroid shift is nontrivial relative to a 32-voxel grid. The next required
  diagnostic is **R0.3 integer-translation alignment decomposition**: find the
  bounded best rigid grid translation per case, recompute global and band IoU,
  and quantify how much error is alignment versus morphology/occupancy. Training
  before R0.3 would risk teaching a pose correction as anatomy.
- R0.3 is implemented and launched as CPU-only Modal app
  `ap-FZzY9WKgqZ0M0sSiH25bxo`. It searches the preregistered integer translation
  cube of +/-6 voxels per axis, breaks score ties toward the smallest movement,
  and recomputes global and proxy-band support overlap. It performs zero
  optimizer steps and writes terminal evidence to
  `/toothfairy-stage1-v1/stage_attribution_r03_v1.json`.
- R0.3 completed with sealed zero-optimizer evidence. Eleven of 12 cases chose a
  nonzero bounded translation and the median translation magnitude was 1.2071
  voxels, but translation closed only **2.5503%** of median global IoU error and
  **-0.2182%** of median crown IoU error. Family median crown-error closure was
  incisor **-1.1204%**, canine **0.0000%**, premolar **0.5591%**, and molar
  **-1.3986%**. Median aligned crown IoU remained 0.0213, 0.0000, 0.1052 and
  0.0000 respectively.
- The sealed conclusion is `morphology-and-occupancy`, not coordinate-frame
  alignment. The sparse support problem is therefore structural; canonical pose
  correction alone cannot recover the anatomy. This authorizes adapter-objective
  design but still does not authorize an optimizer step.
- The next minimal canary is **R0.4 sparse-adapter zero-step objective and
  parameter-influence qualification**. It must start from the exact base sparse
  structure flow, add only a small adapter/LoRA parameter set, use native flow
  supervision with crown-weighted missing/extra support terms, and use a frozen
  base teacher plus hard evaluation gates outside the crown proxy. It must prove
  finite nonzero gradients reach every intended adapter tensor while all base,
  shape-flow, decoder and texture weights remain byte-identical. No update is
  permitted until this zero-step receipt passes.
- R0.4 objective qualification completed in Modal app
  `ap-sGVyDCq1E5yuEsCG7zZrec` after one fail-closed pre-evidence attempt exposed
  an invalid assumption that every individual tooth must contain both error
  directions. The corrected preregistered behavior assigns an exact
  differentiable zero to an absent per-case category while requiring both
  missing and extra crown occupancy across the sealed cohort.
- The terminal receipt is
  `/toothfairy-stage1-v1/stage_attribution_r04_objective_v1.json` (local copy:
  `dentalsculptor-ml/artifacts/stage_attribution_r04_objective_v1.json`). All
  12/12 cases qualified, with 2,939 missing and 2,699 extra crown-proxy voxels
  across the cohort. Every one of the four rank-4 adapter parameter tensors had
  a finite nonzero total gradient in every case, all objective terms were
  finite, and the non-crown preservation gradient was active in all cases.
  Optimizer steps remained exactly zero.
- This receipt authorizes **R0.4B model integration only**. It does not prove
  that the real 1.3B sparse-flow adapter is wired correctly and does not
  authorize an update. R0.4B must attach the rank-4 adapter to a narrowly named
  sparse-flow module, freeze and hash every base tensor, execute one real
  forward/backward with zero optimizer steps, and prove complete adapter
  gradients plus byte-identical base, shape-flow, decoder and texture states.
  Only that receipt may authorize a one-tooth, one-step integration canary.
- R0.4B architecture sealing completed in Modal app
  `ap-0ppaYbVqmYxIqoQJrN53Fl`. The pinned official configuration contains 30
  sparse transformer blocks, fixing the only permitted rank-4 insertion point
  at `blocks.29.mlp.mlp.2`. The official config, model source, base revision,
  adapter rank and seed are hash-bound in
  `/toothfairy-stage1-v1/stage_attribution_r04b_architecture_v1.json`. This
  authorizes the real-model zero-step backward probe only; it still does not
  authorize an optimizer step.
- The first real-model R0.4B backward attempt (`ap-DRfyuF2d0gTmgMUzI3rH2R`)
  failed before trainer construction and before any forward, backward or
  optimizer operation. The injected LoRA wrapper was prepended ahead of the
  upstream module imports, so its class declaration referenced `torch` before
  `torch` was imported (`NameError` at `flow_matching.py:1`). No zero-step
  receipt or scientific evidence was produced. The correction is mechanical:
  inject the wrapper after the pinned import section (or prepend an explicit
  `import torch`) and use a new versioned run; the failed app must not be treated
  as adapter-gradient evidence.
- R0.4B v2 (`ap-b7XHevZXekxkjdu114rThp`) corrected import order and reached a
  fully initialized real 1.292B-parameter sparse model plus the sealed 8-case
  dataset. It then executed backward through the trainer's effective loss path,
  but the intended zero-step receipt hook was not on that effective method.
  Because the base parameters had correctly been frozen after trainer
  construction, the upstream BasicTrainer gradient scan encountered their
  expected `None` gradients and failed at `p.grad.isfinite()` before optimizer
  execution. No optimizer step or checkpoint mutation occurred, but no valid
  adapter-gradient receipt was produced. The next version must patch
  `BasicTrainer.run_step` to invoke the effective `training_losses` directly,
  collect adapter gradients, write the receipt and raise the sealed stop before
  BasicTrainer's global model-parameter gradient scan.
- R0.4B v3 completed successfully in Modal app `ap-F8Y1DHiLcR8WkHM3WGCVRx`.
  Its focused
  patch tests pass (`3 passed`), and the probe is now attached to the pinned
  official `BasicTrainer.run_step` immediately after the effective backward and
  before gradient clipping, the unsafe all-parameter scan, and every optimizer
  branch. The run is versioned at
  `/stage1-r04b-real-sparse-adapter-zero-step-v3`; it permits zero optimizer
  steps and cannot authorize production. A preceding packaging-only launch
  `ap-pfHyHyoukhTeq7DZuWHKXb` and `ap-jPuggbOgSVHRVe51EjJJqu` failed at Python
  package import before model work and are not scientific evidence. The active
  app used Modal's package-module invocation and mounted `PythonPackage:modal_app`.
  The sealed evidence at
  `/stage1-r04b-real-sparse-adapter-zero-step-v3/r04b-evidence.json` is valid:
  native MSE was `0.04546500742435455`; `lora_down` and `lora_up` had finite,
  nonzero gradient norms `1.589970963777887e-07` and
  `2.0150484658643109e-07`; all 640 frozen base tensors remained byte-identical;
  and optimizer steps remained exactly zero. The probe stopped at
  `BasicTrainer.run_step.after-effective-backward-before-gradient-clip`.
  Therefore the evidence explicitly sets `oneStepIntegrationAuthorized=true`.
  This authorizes only the next one-step integration gate—not anatomical claims,
  production promotion or production mutation.
- R0.4C exactly-one-step integration completed successfully in Modal app
  `ap-BGXlS8Dl0IQXna4HyavnNO`. The implementation passed four focused R0.4B/C
  safety tests. Only the two rank-4 adapter tensors are placed in the optimizer
  (`lr=1e-6`, zero weight decay). After exactly one update the adapter is merged
  into a full-schema sparse-flow checkpoint, the 640 frozen tensors are checked,
  and execution stops before scheduler/EMA work. The same held-out image must
  then strictly reload and generate the same non-empty raw model twice before a
  four-family screen may be authorized. The sealed evidence at
  `/stage1-r04c-sparse-adapter-one-step-v1/r04c-evidence.json` passed: exactly
  one optimizer step at `1e-6`; finite nonzero gradient norms of
  `1.589970963777887e-07` and `2.0150484658643109e-07`; finite nonzero adapter
  delta norms of `5.030445208831225e-06` and `1.2167111890448723e-05`; all 640
  frozen tensors byte-identical; and a 641-entry, 5,171,028,665-byte merged
  checkpoint strictly reloaded. Held-out case
  `toothfairy2-stage50-whole-tooth-v1-ToothFairy2F_015-fdi43` reproduced exactly
  and yielded 211,890 vertices and 414,058 faces. Therefore
  `fourFamilyScreenAuthorized=true`. This is engineering qualification only;
  production remains immutable and anatomical improvement is not yet proven.
- R0.4D four-family image-conditioned screening completed in Modal app
  `ap-nfbwDAnlM2zz8BLbiFVIgJ`; the sealed evidence is
  `/stage1-r04c-sparse-adapter-one-step-v1/r04d-evidence.json`. The evaluation
  performed zero new optimizer steps and compared the unchanged base with the
  strictly loaded R0.4C candidate on matched patient-disjoint incisor, canine,
  premolar and molar inputs. Images, references, seeds and quality settings
  matched in every pair, and both roles reproduced their raw geometry exactly.
  The efficacy gate failed: median crown Chamfer relative improvement was
  `-0.04767509266599791` (4.77% worse), only the premolar improved (`1/4`
  families), and median whole-tooth improvement was
  `-0.0026683631039675706`. Crown relative changes were incisor `-10.68%`,
  canine `-5.31%`, molar `-4.23%`, and premolar `+1.08%`. Root/cervical and
  welded-topology non-regression also failed. Therefore
  `boundedTrainingAuthorized=false`: the R0.4C update must not be extended,
  promoted, or deployed. The result indicates that a single unbalanced native
  sparse-flow update can perturb global occupancy despite a tiny adapter and
  learning rate. The next design must use the already-qualified regional
  crown-support objective during the actual update, with explicit frozen-base
  non-crown/root preservation and a pre-update matched base control.
- R0.5A v1 zero-step integration (`ap-ul6rADRkkhqDKfGCMK4w2i`) stopped before
  every optimizer boundary and produced valid diagnostic evidence, but did not
  authorize an update. Native and crown-extra terms were finite with nonzero
  adapter gradients; the final adapter gradient norms were `0.0037730341` and
  `0.0042995880`, and all frozen weights remained byte-identical. The sealed
  batch contained 3,796 extra crown voxels but zero voxels that were occupied
  by the reference and absent from the base reconstruction. Also, the
  frozen-base preservation MSE and its gradient were exactly zero at
  initialization, which is the correct identity condition rather than a failed
  preservation path. R0.5A v2 therefore replaces the batch-contingent
  missing-only term with reference-positive crown supervision, retains the
  extra-crown term, requires preservation MSE to be zero at initialization,
  and adds a controlled zero-update differentiability probe for the
  preservation path.
- R0.5A v2 zero-step integration (`ap-UFvW1xdgm8m00INUnh5hh9`) also stopped
  before every optimizer boundary and did **not** authorize training. The
  corrected preservation probe reached both adapter matrices with finite,
  nonzero gradients (`7.9912809e-08`, `1.0885397e-07`), while the real
  non-crown teacher MSE remained exactly zero at initialization as required.
  Native MSE and the 3,796-voxel crown-extra penalty also had finite, nonzero
  adapter influence, and all 640 frozen tensors remained byte-identical.
  However, the selected training example again produced zero
  reference-positive crown voxels, so `crownPositiveBce=-0.0` and both of its
  adapter-gradient norms were zero. Consequently
  `everyRequiredComponentHasFiniteNonzeroAdapterInfluence=false` and
  `correctedOneStepAuthorized=false`. This is now a data/coordinate-contract
  failure at the regional objective boundary, not a numerical-backward or
  preservation-path failure. The next run must first validate a non-empty
  reference-positive crown support after reference-to-decoder-grid alignment;
  no optimizer step is permitted until that preflight passes.
- R0.5A v3 corrects the measured mask-contract defect: crown bands are now
  normalized to the decoded reference tooth's occupied long-axis bounds rather
  than the full 64-cubed tensor, and the wider terminal is selected as the
  crown proxy. The receipt records reference/support/crown voxel counts,
  selected spatial axis and tensor dimension, occupied axial bounds, both
  terminal counts and crown direction. Focused source-patch testing passes; the
  full local file reports 66 passes plus two unrelated Windows temporary-folder
  permission setup errors. Zero-step Modal qualification is running as
  `ap-2Y6iGqRyMWvN3aFWEe5s0g`; no optimizer or production mutation is permitted
  until its sealed evidence authorizes the next gate.
- R0.5A v3 completed successfully (`ap-2Y6iGqRyMWvN3aFWEe5s0g`) and sealed
  `correctedOneStepAuthorized=true` with zero optimizer steps. The decoded
  reference occupied 3,922 voxels; the union contained 24,206 voxels; the
  occupancy-relative crown proxy contained 5,545 union voxels, including
  1,367 reference-positive and 4,178 base-extra crown voxels; 18,661 non-crown
  voxels were protected. The long axis was tensor dimension 4 (spatial offset
  2), occupied bounds `[0,31]`, with the lower terminal selected as crown
  (`1,367` versus `779` reference voxels). Native, crown-positive,
  crown-extra, and controlled preservation-probe gradients were finite and
  nonzero for both rank-4 adapter matrices. The real preservation MSE remained
  exactly zero at initialization, and all 640 frozen tensors remained
  byte-identical. This authorizes only the preregistered exactly-one-step
  integration canary; it is not evidence of anatomical improvement and does
  not authorize production deployment.
- R0.5B implements the authorized exactly-one-step regional-objective canary.
  It restricts AdamW (`lr=1e-6`, zero weight decay) to the two rank-4 adapter
  matrices, uses the qualified occupancy-relative crown objective, stops after
  the first optimizer step before scheduler/EMA work, and seals gradients,
  parameter deltas, frozen-state hashes and a merged checkpoint. It then
  requires strict checkpoint reload, exact repeated held-out raw generation
  and a non-empty mesh. Focused R0.5A/R0.5B patch tests pass (`2 passed`). The
  Modal run is `ap-N9nOBeRYvh0fiEbwDhx5Q1`; it cannot authorize broader
  evaluation unless every engineering gate passes, and cannot authorize
  clinical claims or production deployment.
- R0.5B completed successfully (`ap-N9nOBeRYvh0fiEbwDhx5Q1`) and sealed
  `fourFamilyScreenAuthorized=true`. Exactly one optimizer step changed both
  adapter matrices with finite delta norms (`0.0001752621`, `0.0000778051`)
  and finite gradient norms (`0.0012198996`, `0.0021832639`), while all 640
  frozen tensors remained byte-identical. The merged 5.17 GB sparse-flow
  checkpoint loaded strictly; repeated held-out raw generations were exactly
  identical; and the mesh contained 211,880 vertices and 414,012 faces. This
  authorizes only a zero-training, matched four-family base-versus-candidate
  anatomy screen. It does not yet establish anatomical improvement or permit
  production deployment.
- R0.5C is the authorized zero-training matched four-family screen. It reuses
  the sealed patient-disjoint incisor, canine, premolar and molar cases, fixed
  seeds, exact-repeat generation, 5,000-point mesh metrics, and welded-topology
  audit from R0.4D while comparing the unchanged base against the R0.5B
  regional-objective checkpoint. Crown improvement cannot override any root,
  cervical, topology, or repeatability regression. Modal run
  `ap-368ZuWTj5v8odktI6Hrubg` is active; no further training or production
  mutation is authorized while its evidence is pending.
- R0.5C completed (`ap-368ZuWTj5v8odktI6Hrubg`) with exact raw repeatability
  and strict candidate checkpoint loading, but rejected the R0.5B candidate.
  Crown Chamfer relative changes were incisor `+2.733%`, canine `-7.082%`,
  molar `-2.556%`, and premolar `-8.507%`; median crown change was `-4.819%`
  with only one of four families improving. Median whole-tooth change was
  `-2.479%`. Regional root/cervical non-regression failed in every family, and
  welded-topology checks failed for canine, molar, and premolar. Therefore
  `boundedTrainingAuthorized=false`: this checkpoint must not receive more
  steps, be deployed, or support an anatomical-improvement claim. The result
  proves that a correct crown mask and differentiable regional loss are not
  sufficient when applied through one global sparse-flow adapter: its update
  still perturbs whole-tooth support. The next experiment must change the
  parameterization/gradient routing, not increase step count.
- E14 is now preregistered in
  `finetune/config/stage1_e14_crown_residual_curriculum_v1.json`. It replaces
  global sparse-flow adaptation with a crown-only residual support refiner:
  base logits are copied exactly through the root/non-crown region, the learned
  residual is tapered across the CEJ transition, and only crown support can
  change. Sampling is intentionally weighted toward molars (40%) and premolars
  (35%), while retaining incisors (15%) and canines (10%). Objectives cover
  crown support/surface, premolar-molar occlusal relief and landmarks, incisor
  crown envelope, and CEJ continuity. The bounded ladder is 0 steps, 1 step,
  100 steps, 2,000 steps, then at most 12,000 steps per seed with validation
  early stopping. Only G0 is currently authorized; no long GPU training may
  start until the spatial composition and bitwise root invariant are proven.
- E14 G0 v1 (`ap-IawfHkrKgz4PqIpDaetVCa`) failed before its first case receipt
  because the local tensor variable `root` shadowed the dataset root path while
  building artifact-relative paths. It performed zero optimizer steps and
  produced no scientific evidence. The correction renames the tensor to
  `root_mask` and versions the rerun as `stage1-e14-g0-crown-composition-v2`;
  the partial v1 directory is retained rather than overwritten.
- Corrected E14 G0 v2 completed as `ap-h02L3v1y12e77TzdLYGw82` and sealed
  `/toothfairy-stage1-v1/stage1-e14-g0-crown-composition-v2/g0-evidence.json`.
  The zero-optimizer proof is valid across 32 distinct patients, balanced at
  eight incisors, canines, premolars and molars. All 32 cases had finite,
  non-zero crown gradients (`0.0008880675` to `0.0008880979`), zero non-zero
  root-gradient entries, and byte-identical root logits. The sealed decision is
  `g1Authorized=true`. This proves spatial composition and gradient isolation;
  it does **not** show anatomical improvement, validate a learned residual
  refiner, or permit a clinical/production claim. G1 must now integrate the
  actual parameterized crown refiner and perform exactly one optimizer step,
  followed by strict reload, repeatability, non-empty mesh and root-invariance
  checks.
- E14 G1 v1 (`ap-VQKX1Iud5BsvgZqZF7UXn3`) stopped before dataset loading or
  any optimizer step because the isolated research image did not include
  `scikit-image`, which the mesh-validity check imports. It produced no
  checkpoint or scientific evidence. The corrected research-only image now
  declares `scikit-image` and `trimesh`; the rerun is versioned as
  `stage1-e14-g1-crown-refiner-one-step-v2` so the infrastructure failure is
  never conflated with experimental evidence.
- E14 G1 v2 (`ap-B79nEKTaSasBN6Th3KbdW5`) also stopped before dataset loading
  or optimization. The new dependency image was built successfully, but a
  broad decorator edit had attached it to the older E4 materialization job
  rather than G1, so G1 still used the original image. The E4 decorator is
  restored, G1 is now explicitly bound to `e14_training_image`, and the clean
  rerun is versioned `stage1-e14-g1-crown-refiner-one-step-v3`. Neither failed
  launch is scientific evidence and neither took an optimizer step.
- Corrected E14 G1 v3 completed as `ap-IKbY2iaVVaNj4ivv1iy3sj` and sealed
  `/stage1-e14-g1-crown-refiner-one-step-v3/g1-evidence.json`. Exactly one
  optimizer step at `1e-6` changed only the refiner output tensors
  (`net.4.weight` and `net.4.bias`); all gradients were finite, with the
  zero-initialized output layer correctly preventing hidden-layer gradients on
  this first step. The 10,417-parameter checkpoint strict-reloaded, held-out
  raw decoding repeated exactly, the resulting mesh had 3,100 vertices and
  6,142 faces, and held-out root logits remained byte-identical. The sealed
  decision is `g2Authorized=true`. This is an integration result only: its
  canary input was reference support, so it is not anatomical-improvement
  evidence. G2 must use frozen-base image-conditioned predictions as refiner
  inputs and patient-disjoint references as targets.
- E14 G2 frozen-base support materialization completed as
  `ap-IzJTq9nlPe7keUi9wpwQvi` and sealed
  `/toothfairy-stage1-v1/stage1-e14-g2-frozen-base-support-v1/cache-evidence.json`.
  The zero-optimizer cache contains 76 hashed image-to-sparse pairs: 64
  training teeth from 35 patient groups and all 12 validation teeth from three
  patient groups, with zero train/validation group overlap. Training is
  deliberately crown-priority weighted (26 molars, 22 premolars, 10 incisors,
  6 canines); validation remains balanced at three per family. All base and
  reference coordinate sets are non-empty, every receipt includes input,
  coordinate, artifact and pinned-model hashes, and the 24-case test split is
  untouched. The sealed decision is `g2TrainingAuthorized=true`. This cache is
  reproducible input evidence, not an anatomical-improvement result.
- E14 G2 response launch `ap-GR6K7zWXNsJBYI4cJN58Ax` did not reach the
  scientific function boundary: Modal reports zero active tasks, the app log is
  empty, and `/stage1-e14-g2-short-response-v1` was never created on the
  checkpoint volume. Therefore it executed no evidenced optimizer steps and
  produced no scientific result. Treat this as a detached-dispatch failure,
  not a rejected or passing G2 experiment; a versioned/relaunched invocation
  must first prove that the remote function entered before training is assessed.
- The corrected G2 response invocation is versioned
  `stage1-e14-g2-short-response-v2` and must be launched with the foreground
  CLI session retained until the remote function visibly enters. This changes
  dispatch handling only; the preregistered 100-step objective and gates are
  unchanged.
- Corrected E14 G2 v2 completed as `ap-BcJll3hDgXiPDi4FTeUsUo` and sealed
  `/stage1-e14-g2-short-response-v2/g2-evidence.json`. It executed exactly 100
  finite optimizer steps and evaluations at 0/25/50/75/100; the checkpoint
  strict-reloaded. Root logits stayed byte-identical, raw decode repeated
  exactly, and final topology passed. However, the final median crown Chamfer
  relative improvement was `-1.31688927159368`: incisors (`+0.4441640682`) and
  canines (`+0.4292820518`) improved, while premolars (`-6.3277665517`) and
  molars (`-2.0455328442`) regressed severely. The pattern was already present
  at step 25 and did not recover; one molar had no candidate surface in the
  measured crown region. Therefore `summaryPassed=false`, `g3Authorized=false`,
  and this checkpoint must not be deployed. This rejects longer training of
  the same shared objective, not the root-preserving residual architecture.
- The next bounded step is the zero-optimizer 76-case E14 alignment/crown-mask
  audit `stage1-e14-g2-alignment-mask-audit-v1`. It measures bounded integer
  registration, reference coverage by the generated-tooth crown mask, and
  family-specific failure patterns before another training dollar is spent.
  The next learner must use family-specific heads plus a base trust region; it
  must also align references to frozen-base coordinates if this audit finds
  alignment-dominant supervision error.
- Corrected audit v2 completed as `ap-4msdYgv8ezzODhuG3qnkyz` with zero
  optimizer steps across all 76 cached pairs. Although 69 pairs had a non-zero
  best integer translation (median magnitude `2.2361` voxels), translation
  closed only `0.02892` of median global IoU error and `0.0` of median crown
  IoU error. Therefore alignment is not the dominant boundary and references
  must not be shifted merely because a non-zero optimum exists. The sealed
  next design is `use-family-specific-heads-with-base-trust-region`: isolate
  each dental family and explicitly penalize changing crown voxels the frozen
  base already predicts correctly.
- E14 G2B completed as `ap-H7IF2cJg12JeGojA03EEl7` and sealed
  `/stage1-e14-g2b-family-trust-region-v1/g2b-evidence.json`. It performed
  exactly four optimizer steps at `1e-4`, one per family. Every step had finite
  gradients and changed only the selected family's output tensors; roots were
  byte-identical and repeated logits were exact for all four cases. The
  family-specific checkpoint strict-reloaded, so `g2cResponseAuthorized=true`.
  This is an integration result, not anatomical-improvement evidence; G3 and
  production remain locked. The next run is a short family-balanced response
  screen using this architecture and the explicit base trust region.
- E14 G2C completed as `ap-BRyKmgK18nLS0kBLNrnHv8` and sealed
  `/stage1-e14-g2c-family-response-v1/g2c-evidence.json`. It executed exactly
  40 additional updates, ten per family, with evaluations at 0/10/20/40 and a
  strict-reloadable checkpoint. Root identity, repeatability and topology all
  passed at every evaluation. However, crown Chamfer improvement remained
  exactly `0.0` for every family at every step, and losses stayed near `0.826`.
  Thus `summaryPassed=false` and `g3Authorized=false`. The family isolation
  fixed destructive interference, but the conservative residual stayed below
  the binary occupancy threshold and produced no geometry response. Do not add
  steps blindly. The next bounded experiment is a zero-optimizer response/margin
  diagnostic that measures logit direction, magnitude and counterfactual
  threshold crossings before changing learning rate or trust-region strength.
- E14 G2D completed as `ap-6SEU0asbHfkI5xIDwPfC6i` with zero optimizer steps
  and sealed `/stage1-e14-g2d-response-margin-v1/g2d-evidence.json`. Residual
  scales `1/2/4/8/16` all produced zero occupancy crossings and zero crown
  Chamfer change. Median held-out directional agreement was `0.6247`; family
  medians were incisor `0.7894`, canine `0.7057`, premolar `0.6197`, and molar
  `0.5233`. Maximum absolute residuals were only about `0.0009-0.0021`, far
  below the `0.25` base-logit margin. Roots remained byte-identical, but no
  scale was eligible: `scaledCanaryAuthorized=false` and
  `objectiveRedesignRequired=true`. The next bounded design must replace the
  disagreement BCE with an explicit signed occupancy-margin objective while
  retaining family isolation and the agreement-voxel/root trust region.
- E14 G2E launch `ap-qL9mc3Vtxe3NnoXv1nq9jC` never acquired a T4 worker. It
  remained queued from 14:26 to 14:32 BST, then Modal stopped the ephemeral app
  when the local client disconnected. The checkpoint directory and
  `g2e-evidence.json` were never created, so this launch executed zero evidenced
  optimizer steps and is not scientific evidence for or against the signed
  margin objective. A replacement must use detached execution (or retain the
  foreground client) and a new versioned run name before G2E can be assessed.
- Corrected E14 G2E v2 completed as `ap-IEQX723s0Lk3ytK8esd19B` and sealed
  `/stage1-e14-g2e-signed-margin-canary-v2/g2e-evidence.json`. It executed
  exactly 20 optimizer steps (five per tooth family), produced finite losses,
  strictly reloaded checkpoint SHA-256
  `4c90b636a8314985a506868b72291630f4110ac189b7b44ac541bf5738ac4319`,
  preserved all root logits byte-for-byte, repeated every raw decode exactly,
  and passed the topology checks. The learned direction was anatomically
  informative (held-out directional agreement: incisor `0.7894`, canine
  `0.7057`, premolar `0.6197`, molar `0.5233`) but remained below the binary
  surface boundary: maximum residuals were only about `0.0191-0.0476` against
  a `0.25` base-logit margin and all 12 cases had zero occupancy crossings.
  Consequently `g2fAuthorized=false` and `g3Authorized=false`; this is safe but
  not an anatomical improvement. E14 G2F is implemented as a zero-optimizer,
  held-out gain calibration over `1/2/4/6/8/12/16`. It may authorize a bounded
  follow-up only when real surface crossings improve both premolar and molar
  crown Chamfer, regress no family beyond `0.5%`, preserve root logits exactly,
  repeat exactly, and pass topology. Production remains unchanged.
- E14 G2F completed as `ap-aQvCj8cUQ1KosGTLWefDhS` with zero optimizer steps
  and sealed `/stage1-e14-g2f-signed-margin-gain-v1/g2f-evidence.json`.
  Gains `1/2/4` made no surface change. Gain `6` produced 230 crossings but
  failed topology. Gain `8` regressed median premolar crown Chamfer by `44.0%`;
  gains `12/16` regressed premolars by `258.0%/540.6%` and molars by
  `64.2%/94.3%`. Roots remained byte-identical and all raw decodes repeated
  exactly, so spatial root preservation is proven, but the learned crown
  direction is not anatomically safe. `selectedGain=null`,
  `boundedTrainingAuthorized=false`, and `g3Authorized=false`. No gain-scaled
  checkpoint may be reviewed or deployed. The next bounded response run must
  balance missing-versus-extra crown support per case and per family, retain
  the hard root copy, and select checkpoints from held-out surface metrics
  rather than directional agreement alone.
- E14 G2G completed as `ap-MEa9td9oD9GlfT86WJZqj7` with 400 optimizer steps,
  100 per family, and sealed
  `/stage1-e14-g2g-class-balanced-family-response-v1/g2g-evidence.json`.
  Missing and extra crown support were weighted equally, all losses and
  gradients were finite, roots remained structurally isolated, and topology
  stayed valid; nevertheless every evaluation at `0/40/80/160/240/400` had
  zero occupancy crossings and zero crown Chamfer response. The selected safe
  checkpoint is therefore step 0 and `expertReviewPackAuthorized=false`.
  This exposes an architectural mismatch: the family refiner consumes base
  support plus coordinates, but no source-image features, so it cannot infer
  case-specific cusps, ridges or crown envelope from the photograph. E14 G2H
  adds a small image-conditioned crown adapter with three orthogonal projected
  feature planes, retains family-specific heads and balanced add/remove
  margins, and still copies all root-side logits exactly. It remains a bounded
  held-out experiment; production and clinical claims stay locked.
- E14 G2H completed as `ap-qhzKHBkMpAtkq69e09X399` with 800 optimizer
  steps, 200 per family, and sealed
  `/stage1-e14-g2h-image-conditioned-crown-adapter-v1/g2h-evidence.json`.
  Image conditioning produced the first useful held-out family response: at
  step 800, median molar crown Chamfer improved `12.32%` and canine improved
  `8.12%`. The result is not promotable: premolars regressed `152.99%`,
  incisors regressed `2.51%`, and raw topology failed. The selected safe step
  remains 0, `expertReviewPackAuthorized=false`, and `g3Authorized=false`.
  This shows that image information is necessary but full-volume occupancy
  disagreement remains the wrong crown objective: it rewards large volume
  changes even when the base and reference surfaces are already close (most
  visibly for premolars). The next implementation must supervise a narrow
  union-of-surfaces band, preserve logits outside that band, and evaluate an
  explicit crown-only connected-component projection before any expert pack.
- E14 G2I completed as `ap-R9IJ4Jt4bsAHYNY1es2C2i` with 600 additional
  optimizer steps and sealed
  `/stage1-e14-g2i-surface-band-crown-adapter-v1/g2i-evidence.json`. The
  connected-root projection made every held-out result single-component and
  retained exact root-side composition, but the narrow surface objective still
  produced no premolar or molar gain through step 400; at step 600 premolars
  regressed `21.7%`. Therefore `expertReviewPackAuthorized=false` and the safe
  selected step remains the source boundary. This closes further tuning of the
  32^3 family-average support refiner as a general crown solution. A bounded
  molar-only qualification may reuse G2H step 800 because all three held-out
  molars improved (`9.39%-12.63%`, median `12.32%`), but it must first pass
  connected projection and the real TRELLIS decoder. Premolars and all other
  families remain on the frozen base model. Fine occlusal ridges and grooves
  require a higher-resolution decoded-geometry objective, not more 32^3 steps.
- E14 G2J molar-only real-decoder qualification was launched as
  `ap-C5ZtwVVYD67r8kYXnNixAP`. It freezes all production models, executes zero
  optimizer steps, and decodes matched base/candidate meshes for the three
  held-out molars with identical image, seed and 12-step shape-sampler settings.
  The sealed artifact is
  `/stage1-e14-g2j-molar-decoder-qualification-v1/g2j-evidence.json`. Promotion
  to a blinded expert pack requires at least `5%` median decoded crown-proxy
  Chamfer improvement, at least two of three molars improved, all canonical
  root/cervical non-regression gates, and exact sparse root-logit identity.
  The app finished, but the only function call was cancelled before evaluation:
  call `fc-01M36CCMPCJ8QSGD9WM8SXFEYC` started at `2026-09-23 06:39:09 BST`,
  loaded the H100/TRELLIS runtime, completed the 12-step shape-SLat sampler,
  received a Modal cancellation signal at `06:41:16`, and the runner terminated
  at `06:42:28`. The intended `g2j-evidence.json` was not sealed. This is an
  orchestration failure, not anatomical evidence: no crown, root, cervical or
  topology metric may be inferred from it, and no expert-review pack is
  authorized. A versioned relaunch must be truly server-detached and must write
  an early run receipt before loading weights. Production remains untouched.
- G2J v2 implements that recovery. The function now seals
  `/stage1-e14-g2j-molar-decoder-qualification-v2/run-receipt.json` before
  loading TRELLIS, and the deployed function was submitted directly with
  `modal.Function.from_name(...).spawn()` so its lifecycle is independent of
  the local CLI. Initial call `fc-01M37AWYTTS6CTPZT5YT2T4DEA` never entered the
  function: fourteen deployment-v43 containers failed at import with
  `ModuleNotFoundError: No module named 'modal_app'`. That call was cancelled.
  A first packaging workaround reached the function, but call
  `fc-01M37CF24VD8NM8JA0NY8DBCJT` failed while importing NumPy and produced no
  scientific evidence. Root cause was the TRELLIS image replacing `PYTHONPATH`
  with only `/opt/TRELLIS.2`, excluding Modal's `/root` source mount. The durable
  fix keeps `/opt/TRELLIS.2:/root` and adds a build-time NumPy/SciPy/
  scikit-image/trimesh import gate. Corrected call
  `fc-01M37CQ5DP69FR7EKF773DY8V5` entered the real pipeline and decoded the
  first frozen-base molar mesh, but the candidate path stopped inside the
  upstream FlexGEMM decoder because a sampled sparse-coordinate view was not
  contiguous. It sealed no scientific evidence. This is a tensor-layout
  integration failure, not an anatomical result. G2J v3 adds a local,
  reversible decoder-boundary guard that reconstructs each shape-SLat with
  contiguous coordinates immediately before upsampling, verifies that the
  guard is exercised for every matched base/candidate decode, and restores the
  original method after each call. The clean v3 run was submitted as
  `fc-01M37DWDQBKTGH69BQK7PKZBEM`; its intended evidence is
  `/stage1-e14-g2j-molar-decoder-qualification-v3/g2j-evidence.json`. The
  complete local contract suite passes (`86 passed, 1 skipped`). No expert
  review or production promotion is authorized until v3 seals and passes the
  preregistered decoded crown/root/cervical/topology gates.
- G2J v3 completed and sealed valid zero-optimizer evidence at
  `/stage1-e14-g2j-molar-decoder-qualification-v3/g2j-evidence.json`. All six
  matched base/candidate decodes produced positive meshes at resolution 1024,
  used 12 shape-sampler steps, exercised the sparse-coordinate guard, and kept
  the support-space root logits byte-identical. Decoded crown-proxy Chamfer
  improved in all three held-out molars; the paired improvements were `16.82%`,
  `66.37%`, and `21.36%` (median `21.36%`). However, none of the three cases
  passed the preregistered decoded regional non-regression gate. Failures
  included apical/middle-root and cervical HD95 or sampling-share regression,
  and two cases regressed robust pole proxies. Therefore
  `expertReviewPackAuthorized=false`, G3 and production remain locked, and the
  candidate must not be represented as a clinically improved model. The result
  is nevertheless important evidence: the bounded adapter carries a strong
  molar-crown signal through the real decoder, but sparse support identity does
  not guarantee decoded root preservation. The next experiment must preserve
  or splice the frozen-base decoded root/cervical geometry rather than relying
  only on a support-space root invariant.
- E14 G2K is the bounded recovery from that finding. It performs zero training
  and uses one preregistered composition rule: keep baseline vertices through
  normalized height `0.72`, smoothly transfer toward the candidate from `0.72`
  to `0.82`, cap displacement at `5%` of the baseline diagonal, and retain the
  complete baseline face array. Local preservation and integration contracts
  pass (`89 passed, 1 skipped`). Research call
  `fc-01M39CMQPBGAS4B6WACBSSQ57E` will seal
  `/stage1-e14-g2k-topology-preserving-crown-composition-v1/g2k-evidence.json`.
  An engineering review pack requires at least `5%` median composed crown
  improvement, at least two of three molars improved, positive meshes, and
  byte-identical protected vertices and connectivity. This cannot authorize a
  clinical claim or production deployment; the `0.72` boundary remains an
  axial proxy until expert-reviewed CEJ annotations exist.
- G2K completed and sealed valid zero-training evidence. All three composed
  meshes were positive, every protected vertex remained byte-identical, and
  every face array remained byte-identical to its frozen baseline. However,
  crown-proxy Chamfer regressed in all three cases; the median relative change
  was `-2.92%`. Consequently `expertEngineeringReviewPackAuthorized=false`.
  The failure is informative: G2J's crown gain was measured after rigid ICP,
  whereas G2K transferred candidate vertices in their raw decoder frame. The
  next bounded ablation must first rigidly register the candidate to the
  baseline using only protected root vertices, then apply the same sealed crown
  transfer. G2K is rejected and will not be parameter-swept or promoted.
- E14 G2L implements that single preregistered correction: rigid ICP uses only
  candidate/baseline vertices at or below axial height `0.72`, applies no scale,
  and then reuses G2K's unchanged `0.72/0.82/5%` topology-preserving transfer.
  The expanded local suite passes (`91 passed, 1 skipped`). Research call
  `fc-01M39CZ5R7RAJWEGAVYC0YTSRD` will seal
  `/stage1-e14-g2l-root-registered-crown-composition-v1/g2l-evidence.json`.
  It cannot authorize a clinical claim or production deployment.
- G2L completed and sealed valid zero-training evidence. Rigid root-only ICP,
  protected-vertex identity, unchanged connectivity, displacement limits and
  positive-mesh gates all passed. Nevertheless, crown-proxy Chamfer regressed
  in all three cases (median `-1.97%`), so
  `expertEngineeringReviewPackAuthorized=false`. This rejects nearest-surface
  vertex transfer even after root registration. The useful G2J crown signal is
  represented by the candidate crown surface itself and is not recoverable by
  deforming the baseline crown topology toward nearest candidate vertices.
  Stop this deformation branch. The next scientifically defensible boundary is
  either an actual cut/stitch crown graft with seam-specific validation, or a
  decoder trained/evaluated with explicit decoded root preservation. Neither is
  authorized for overnight production without a fresh bounded qualification.
- E14 G2M implements the true graft boundary: root-only rigid registration,
  baseline geometry below axial height `0.72`, candidate geometry above it,
  and a zipper-triangulated seam joining the two cut loops. The local contracts
  pass (`94 passed, 1 skipped`), including zero boundary edges, zero
  non-manifold edges and a watertight synthetic graft. Research call
  `fc-01M39DHP869HGV8NEN9ESTEHSY` will seal
  `/stage1-e14-g2m-cut-stitch-crown-graft-v1/g2m-evidence.json`. Advancement
  requires at least `5%` median crown gain, at least two of three molars
  improved, positive meshes and valid seams on every real case. Clinical claims
  and production mutation remain prohibited.
- G2M v1 stopped before anatomical evaluation with `cut boundary is not a
  simple manifold loop`. It sealed only the early run receipt; no G2M evidence
  or efficacy conclusion exists. The decoded production-scale mesh contains
  near-duplicate/T-junction cut vertices that the synthetic watertight fixture
  did not expose. Recovery must consolidate cut-plane vertices and remove
  degenerate/duplicate faces before loop extraction, while retaining the same
  one-loop, zero-boundary, zero-non-manifold fail-closed gate.
- G2M v2 applies that recovery without changing the anatomical rule: cut-plane
  vertices are consolidated to six decimal places, degenerate and duplicate
  faces are removed, and the one-loop/manifold requirements remain unchanged.
  Research call `fc-01M39DS815Q65KEGDAV6KXCV3F` targets
  `/stage1-e14-g2m-cut-stitch-crown-graft-v2/g2m-evidence.json`.
- G2M v2 also stopped before anatomical evaluation with the same non-simple
  cut-loop boundary. Stronger consolidation did not change the failure, which
  means this is not merely floating-point duplication: the decoded mesh is not
  manifold enough at the chosen axial section for a direct single-loop graft.
  No evidence artifact or efficacy claim was produced. Stop the direct graft
  branch. A future graft requires an explicit local manifold remesh around the
  seam (and a new remeshing non-regression protocol); the model-development
  route should instead impose root preservation at decoded-geometry training
  time. Production remains the frozen baseline for the pilot.

### E13 crown-detail / root-preservation objective — preregistered design

- Two dental experts independently reported the same product-level pattern:
  current TRELLIS.2 reconstructions preserve roots better than enamel, cusps,
  ridges and occlusal anatomy. This is recorded as a qualitative prospective
  signal, not yet a quantitative efficacy result. Future reviews must bind the
  rubric, input and generated model hashes.
- The closest prior work is a combination, not a single experiment. E11 proves
  that preservation must be regional and family-gated; E12 provides the correct
  differentiable decoded-geometry boundary. E10's equal axial bands remain an
  engineering mask and safety control, but cannot be represented as a true CEJ,
  enamel or occlusal annotation. E3-E9 show why sparse/flow adaptation is the
  wrong first boundary for this local-detail objective.
- E13 is preregistered in
  `finetune/config/stage1_e13_crown_detail_root_preservation_v1.json`. It freezes
  the encoder, flow and texture models plus decoder blocks 0-2, and proposes
  adapting only the highest-resolution decoder block and final output layer.
  Crown/native rendered supervision is paired with a root-masked frozen-base
  teacher and whole-root non-regression. Crown-only Teeth3DS and DTU assets are
  explicitly forbidden from supplying root supervision.
- Engineering qualification may use the existing canonical axial regions, but
  clinical or paper-grade crown/root claims remain blocked until the reviewed
  CEJ, cusp, root-tip and furcation annotation contract is satisfied. This
  prevents proxy-region improvements from being mislabeled as enamel or
  occlusal anatomical improvement.
- E13 G1 remains locked behind E12's controlled-loss-scale zero-step probe.
  After numerical backward is qualified, E13 begins with a zero-step regional
  parameter-influence test, then one optimizer step, then a two-step four-family
  screen. No 50-step or two-seed run is allowed until every crown, root,
  cervical, topology and repeatability gate passes.

### E15 decoded crown-detail / root-preservation recovery

- The G2J result is now treated as a useful crown-learning signal, not a
  deployable model: all three held-out molars improved in crown-proxy Chamfer
  (`16.82%`, `66.37%`, `21.36%`; median `21.36%`), while every decoded
  root/cervical gate failed. Identical sparse root logits therefore do not
  establish decoded root preservation.
- G2K and G2L rejected nearest-surface deformation, and G2M rejected direct
  cut/stitch grafting on the real non-manifold decoded meshes. The active path
  now moves preservation into the differentiable decoder objective rather than
  attempting to repair the mesh after decoding.
- `stage1_e15_regional_decoder_v1.json` preregisters the recovery. Only
  `blocks.3.*` and `output_layer.*` may train. Crown proxy cells use the
  official dual-grid intersected and vertex targets; cervical and root proxy
  cells use the detached frozen base decoder as teacher, with cervical
  consistency weighted twice. These are explicitly engineering axial proxies,
  not reviewed enamel/CEJ/root labels.
- E15 G0 is implemented as a fail-closed zero-step gate in
  `modal_app/train_anatomy.py`. It asserts exact candidate/target/teacher sparse
  coordinate alignment; non-empty crown, cervical and root bands; finite
  non-zero crown gradients on every intended late-decoder tensor; exactly zero
  teacher loss and gradient at initialization; finite non-zero protected-region
  perturbation-probe influence; and zero optimizer steps. The local source and
  command contract suite passes (`90 passed, 1 skipped`). No production model
  or service has been changed.
- The first launch (`fc-01M39EAH5N6AH1DQ59W6KSHVT1`) stopped before model
  evaluation because the source hook required a synthetic blank-line layout
  that differed from the pinned official trainer. No scientific evidence or
  optimizer step was produced. The corrected v2 hook binds to the unique
  decoder-forward statement and remains fail-closed.
- E15 G0 v2 (`fc-01M39EDTAWX7FBY5E3KRZ95R6J`) also stopped before any
  backward or optimizer step. The candidate training decoder returned the
  expected five training outputs, but the frozen teacher was put in evaluation
  mode and therefore returned its single inference output. The sealed failure
  boundary is `teacher decoder train/eval return-contract mismatch` at the
  attempted five-value unpack. No zero-step receipt or scientific evidence was
  produced, and one-step training remains unauthorized. The correction is to
  keep the frozen teacher weights gradient-disabled while invoking its training
  return contract; this requires a fresh immutable v3 run.

---

## Quick reference paths

| What | Where |
|------|-------|
| FDI-16 local | `research/datasets/fdi16-v2/` |
| Teeth3DS local | `research/datasets/teeth3ds-v1/` |
| Combined mix | `research/datasets/balanced-dental-anatomy-mix.json` |
| Dataset registry | `dentalsculptor-ml/finetune/config/datasets.json` |
| Training run plan | `dentalsculptor-ml/finetune/config/training_run_plan.json` |
| Pathology/internal-anatomy plan | `dentalsculptor-ml/finetune/config/pathology_dataset_plan.json` |
| Modal training app | `dentalsculptor-ml/modal_app/train_anatomy.py` |
| Modal venv (Windows) | `.tools/modal-venv/Scripts/modal.exe` |
