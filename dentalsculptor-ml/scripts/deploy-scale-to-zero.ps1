# Scale TRELLIS to zero idle GPUs (no min_containers burn).
# Usage: .\dentalsculptor-ml\scripts\deploy-scale-to-zero.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location (Join-Path $repoRoot "dentalsculptor-ml")

Write-Host "Deploying dentalsculptor with min_containers=0 (scale to zero when idle)..." -ForegroundColor Yellow

$env:PYTHONIOENCODING = "utf-8"
$env:TRELLIS_GPU = "1"
$env:TRELLIS_RESEARCH_WARM_POOL = "false"
$env:TRELLIS_MIN_CONTAINERS = "0"
$env:TRELLIS_ENABLE_WARMUP = "true"
$env:TRELLIS_ASYNC_S3_ENABLED = "true"
$env:TRELLIS_DEPLOYMENT_ENV = "development"
$env:TRELLIS_MODAL_GPU = "A100"

python -m modal deploy -m modal_app.app
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Scale-to-zero active. Session warmup via POST ...--warm-gpu.modal.run (202)." -ForegroundColor Green
Write-Host "First preview after idle: ~2-5 min cold load; subsequent previews ~10-60s while container stays up." -ForegroundColor Green
