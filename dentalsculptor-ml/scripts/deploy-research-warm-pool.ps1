# Enable one always-warm TRELLIS GPU for research / educator sessions.
# Usage (from repo root):
#   .\dentalsculptor-ml\scripts\deploy-research-warm-pool.ps1
#   .\dentalsculptor-ml\scripts\deploy-research-warm-pool.ps1 -Gpu L40S
#
# Turn off when not testing (stops idle GPU charges):
#   .\dentalsculptor-ml\scripts\deploy-scale-to-zero.ps1

param(
    [ValidateSet("H100", "A100", "L40S", "A100-80GB")]
    [string]$Gpu = "H100"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location (Join-Path $repoRoot "dentalsculptor-ml")

$hourly = switch ($Gpu) {
    "H100" { 3.95 }
    "A100" { 2.10 }
    "A100-80GB" { 2.10 }
    "L40S" { 1.95 }
}

Write-Host ""
Write-Host "Research warm pool — cost estimate (Modal list rates, Aug 2026)" -ForegroundColor Cyan
Write-Host "  GPU: $Gpu at ~`$$hourly/hour while min_containers=1"
Write-Host "  8-hour test day:  ~`$$([math]::Round($hourly * 8, 2))"
Write-Host "  24/7 month:       ~`$$([math]::Round($hourly * 24 * 30, 0))  (turn off when not testing!)"
Write-Host ""
Write-Host "Deploying dentalsculptor with 1 warm container + model warmup..." -ForegroundColor Yellow

$env:PYTHONIOENCODING = "utf-8"
$env:TRELLIS_GPU = "1"
$env:TRELLIS_RESEARCH_WARM_POOL = "true"
$env:TRELLIS_MIN_CONTAINERS = "1"
$env:TRELLIS_ENABLE_WARMUP = "true"
$env:TRELLIS_ASYNC_S3_ENABLED = "true"
$env:TRELLIS_MODAL_GPU = $Gpu
$env:TRELLIS_SCALEDOWN_WINDOW = "3600"

python -m modal deploy -m modal_app.app
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Warm pool active on production app: dentalsculptor" -ForegroundColor Green
Write-Host "First preview after deploy may still take 2-5 min (container boot + load)." -ForegroundColor Green
Write-Host "Subsequent previews target ~10-60s on $Gpu." -ForegroundColor Green
Write-Host "When sessions end, run: .\dentalsculptor-ml\scripts\deploy-scale-to-zero.ps1" -ForegroundColor Yellow
