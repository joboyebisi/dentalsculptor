# TRELLIS Modal benchmark runbook

No production GPU has been selected yet. Selection requires the fixed
ten-image dental validation set and a complete matrix.

## Validation input

Place exactly ten representative `.jpg`, `.png` or `.webp` files in:

```text
research/validation/trellis-teeth/
```

Include anterior teeth, premolars, molars, imperfect backgrounds, reflective
enamel and partial occlusion. Do not duplicate one image to satisfy the count.

## Deployed development endpoints

The development apps scale to zero and do not have an idle warm pool:

- H100: `https://dentalsculptor--generate-speed-dev.modal.run`
- A100 40 GB: `https://dentalsculptor--generate-speed-a100-dev.modal.run`
- L40S: `https://dentalsculptor--generate-speed-l40s-dev.modal.run`

## Run the matrix

From `dentalsculptor-ml` in PowerShell:

```powershell
$env:MODAL_WEBHOOK_SECRET = "<same value as dentalsculptor-webhook>"

python .\scripts\benchmark_trellis_modal.py `
  --images ..\research\validation\trellis-teeth `
  --endpoint H100=https://dentalsculptor--generate-speed-dev.modal.run `
  --endpoint A100-40GB=https://dentalsculptor--generate-speed-a100-dev.modal.run `
  --endpoint L40S=https://dentalsculptor--generate-speed-l40s-dev.modal.run `
  --gpu-hourly-rate H100=3.9492 `
  --gpu-hourly-rate A100-40GB=2.0988 `
  --gpu-hourly-rate L40S=1.9512 `
  --output ..\docs\benchmarks\trellis-modal-matrix
```

Rates above are the hourly equivalents of Modal's published per-second prices
retrieved on 2026-08-19. Verify current rates at
`https://modal.com/pricing` before a later run.

The command writes JSON observations and a Markdown summary. A first request is
only counted as cold when the worker reports `coldContainer=true`; the script
does not manufacture cold/warm labels.

## Enable asynchronous private S3 results

Do not enable the feature until the private bucket and Modal AWS secret exist.
Apply the Prisma migration first, then set:

```text
TRELLIS_ASYNC_S3_ENABLED=true        # Modal deployment
MODAL_ASYNC_S3_ENABLED=true          # Next.js
MODAL_GENERATE_ASYNC_URL=https://<generate-job-endpoint>
STORAGE_BACKEND=s3
```

Create the `dentalsculptor-aws` Modal secret with `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AWS_REGION` and `AWS_S3_BUCKET`. The bucket must keep
Block Public Access enabled. Modal uploads use no public ACL and request
SSE-S3 encryption.

## Edit pilot benchmark (skeleton)

After Modal deploy succeeds, see:

- Smoke test checklist: `docs/benchmarks/CUSP_FRACTURE_SMOKE_TEST.md`
- Edit probe script: `dentalsculptor-ml/scripts/benchmark_edit_pilot.py`

```powershell
$env:MODAL_WEBHOOK_SECRET = "<secret>"
python .\scripts\benchmark_edit_pilot.py `
  --source-image ..\research\validation\trellis-teeth\images\12-upper-molar-three-roots-a.png `
  --edited-image <path-to-ai-edited-png> `
  --endpoint https://dentalsculptor--edit.modal.run `
  --job-status-url https://dentalsculptor--job-status.modal.run `
  --operation remove `
  --output ..\docs\benchmarks\edit-pilot-runs
```

Full six-case automated gate (mask + 2D + accept) is not scripted yet — use the smoke checklist in the app UI first.
