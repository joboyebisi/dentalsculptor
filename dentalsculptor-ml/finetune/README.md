# DentalSculptor TRELLIS.2 fine-tuning workflow

This directory is a promotion-controlled research workflow. Training never
overwrites the currently served checkpoint. Base, candidate and last-known-good
revisions are immutable references in `config/model_registry.json`.

## 1. Data admission

Do not automate downloads until the dataset owner’s terms have been reviewed.
The current shortlist is recorded in `config/datasets.json`:

1. **DTU 3Shape FDI 16** — first 500-mesh spike and molar-shape evaluation.
   It has 7,732 FDI 16 meshes, but they are open IOS-derived surfaces and the
   CC BY-NC-SA licence is not a safe assumption for commercial model weights.
2. **Teeth3DS/3DTeethSeg22** — later tooth-class diversity. Keep its official
   patient split and confirm its current access/licence terms before use.
3. **ToothFairy2** — CBCT/internal-anatomy research only. It is not a substitute
   for paired photo-to-surface data.

For the approved non-commercial FDI-16 research pilot, ingest directly inside
Modal because the official archive is 7.16 GB and local extraction requires
substantially more free disk. The ingestion job verifies the publisher MD5,
extracts only a bounded mesh subset, records CC BY-NC-SA 4.0 and the required
citation, and commits it to the research dataset volume:

```powershell
modal run -m modal_app.train_anatomy::ingest_fdi16 --max-meshes 750
```

After manually extracting an approved dataset:

```powershell
python scripts/prepare_dental_finetune.py `
  --source D:\approved-data\dtu-fdi16 `
  --output D:\dentalsculptor-training\dtu-fdi16-v1 `
  --dataset-id dtu-fdi16-v1 `
  --license CC-BY-NC-SA-4.0
```

For anatomy-conditioned runs, use the stricter canonicaliser with explicit
clinician-confirmed crown and mesial axes:

```powershell
python scripts/prepare_anatomy_dataset.py `
  --source D:\approved-data\dtu-fdi16 `
  --metadata D:\approved-data\dtu-fdi16\metadata.csv `
  --output D:\dentalsculptor-training\dental-anatomy-v1 `
  --dataset-id dental-anatomy-v1 `
  --license CC-BY-NC-SA-4.0
```

Upload that output to the `dentalsculptor-anatomy-datasets-v1` Modal volume
under `/dental-anatomy-v1`, then inspect the exact pinned command before paying
for a GPU run:

```powershell
modal run -m modal_app.train_anatomy::plan --dataset-name dental-anatomy-v1
modal run -m modal_app.train_anatomy::validate_anatomy_dataset --dataset-name dental-anatomy-v1 --minimum-per-family 100
modal run -m modal_app.train_anatomy::build_reference_benchmark --dataset-name dental-anatomy-v1 --per-family 8
modal run -m modal_app.train_anatomy::validate_training_runtime
modal run -m modal_app.train_anatomy::train `
  --dataset-name dental-anatomy-v1 --run-name fdi16-spike-v1 --resolution 512
```

The reference builder seals 32 unique held-out subject groups (eight per tooth
family) and rejects optimizer overlap. Archive the generated manifest hash before
reviewing candidate output. The runtime validation uses no GPU and must pass before
the H100 training call is launched.

The job refuses fewer than 500 admitted anatomy training meshes at 512, invalid
identifiers, a missing immutable manifest, split leakage, duplicate hashes,
pathology-role contamination, missing mesh files, or incomplete preprocessing.
Before launch it creates a train-only metadata overlay for every path read by the
upstream loader; validation and sealed-test hashes remain available for evaluation
but are never visible to the optimizer. It trains shape flow only and writes run
evidence to a separate checkpoint volume.

Supply `--group-map subjects.csv` whenever multiple meshes can belong to one
patient. The generated manifest hashes every asset and assigns an entire group
to one split, preventing train/test leakage.

## 2. Prepare TRELLIS.2 inputs

Use the inference repository commit pinned in `modal_app/trellis_config.py` for
preprocessing compatibility. Training itself uses the separately recorded official
training-code commit `75fbf0183001ed9876c8dbb35de6b68552ee08bd`; the older
inference pin does not contain `train.py` or `configs/`. The official
TRELLIS.2 toolkit must then perform, in order:

1. mesh repair/QC without changing the held-out reference;
2. standardized axis, millimetre scale and unit-box training copy;
3. multi-view rendering plus alpha masks (start with 24 views);
4. O-Voxel/dual-grid preprocessing;
5. shape latent encoding;
6. conditioning-view rendering and metadata construction.

Keep raw, normalized, render, voxel and latent directories separate. Save the
toolkit commit, command line and container digest in the run directory.

## 3. Training stages

Start with **shape flow only** at 512 resolution. Do not
train texture flow from untextured DTU PLY files: synthetic beige renders do not
contain real dental texture supervision.

Use upstream `train.py` and
`configs/gen/slat_flow_img2shape_dit_1_3B_512_bf16.json`. DentalSculptor derives
an immutable candidate config that loads the pinned base checkpoint
`ckpts/slat_flow_img2shape_dit_1_3B_512_bf16` at model revision
`af44b45f2e35a493886929c6d786e563ec68364d`, lowers AdamW to `1e-5`, caps the
first candidate at 20,000 steps, and saves every 1,000 steps. The encoder and
texture stages are not optimized. Exact pins and the derived config are written
into the candidate checkpoint directory for rollback and reproduction.

Only scale from 500 meshes to the full admitted training split if the spike beats
the base model on the untouched validation split. Never tune on official test or
DentalSculptor’s 20-photo clinical holdout.

## 4. Blinded evaluation

Generate base and candidate outputs with identical inputs, seeds and quality.
Randomize their A/B display order. `cases.json` is an array shaped like:

Use separate Modal deployments for the production base and dental candidate;
never change the application endpoint during evaluation. Generate a sealed A/B
bundle with `scripts/blind_model_comparison.py`. Give educators only
`review-cases.json` and the A/B GLBs, never `DO_NOT_SHARE_blinding-key.json`.
After scoring, run `scripts/unblind_model_comparison.py`, followed by
`scripts/evaluate_finetune_candidate.py`. Only a passing report can be registered
and promoted.

Deploy a scale-to-zero candidate without touching the production app:

```powershell
.\scripts\deploy-candidate.ps1 `
  -ModelName your-org/dentalsculptor-trellis2-shape-v1 `
  -ModelRevision FULL_COMMIT_SHA
```

Then create the blinded comparison with the production and candidate synchronous
`generate` endpoint URLs. Both receive identical images, quality and seed. The
script validates each GLB and keeps the A/B key separate from the educator file.

```json
[{"id":"case-001","toothClass":"molar","educatorPreference":"candidate",
  "base":{"validGlb":true,"anatomyScore":0.7},
  "candidate":{"validGlb":true,"anatomyScore":0.9,"protectedRegionScore":0.98}}]
```

Run:

```powershell
python scripts/evaluate_finetune_candidate.py --cases cases.json --output evaluation.json
```

Promotion requires at least 20 held-out cases, at least 60% candidate preference,
no lower valid-GLB rate, mean protected-region score of 0.95, and no material
non-molar regression. The anatomy contract additionally requires landmark error,
ridge/groove continuity and the automatic geometry-gate score for every case;
missing anatomy measurements fail promotion rather than silently passing. Add Chamfer/F-score when a conditioning render has an exact
held-out source mesh; never calculate them against unrelated clinical photos.

`config/anatomy_contract.json` is the machine-readable conditioning, landmark,
loss-weight and promotion contract. Healthy-base training must contain only
healthy meshes. Disease and preparation meshes train the pathology editor as a
separate cohort so an averaged lesion cannot leak into every generated tooth.

## 5. Register, canary, promote and roll back

Upload the candidate to a private immutable Hugging Face revision or a versioned
Modal volume, then register it:

```powershell
python scripts/model_release.py register dental-shape-v1 `
  --repo your-org/dentalsculptor-trellis2-shape-v1 `
  --revision FULL_COMMIT_SHA `
  --manifest D:\dentalsculptor-training\dtu-fdi16-v1\manifest.json `
  --report evaluation.json
python scripts/model_release.py promote dental-shape-v1
```

The command prints `TRELLIS_MODEL_NAME` and `TRELLIS_MODEL_REVISION`. Deploy those
to a separate Modal canary app/label first. Send only internal evaluation traffic
to it. Production promotion is a configuration change followed by deployment;
the base checkpoint remains cached and registered.

Rollback:

```powershell
python scripts/model_release.py rollback
```

Redeploy with the printed last-known-good values. Never delete the candidate or
training evidence during rollback.
