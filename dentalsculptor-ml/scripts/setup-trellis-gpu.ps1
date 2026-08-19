# DentalSculptor - wire HuggingFace token to Modal and deploy TRELLIS GPU
# Usage (from repo root):
#   1. Complete Hugging Face steps in docs/TRELLIS_GPU_SETUP.md
#   2. Add HF_TOKEN=hf_... to dentalsculptor-app\.env  (Ctrl+S to save!)
#   3. .\dentalsculptor-ml\scripts\setup-trellis-gpu.ps1

$ErrorActionPreference = "Stop"

function Invoke-External {
    param([scriptblock]$Command)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Command
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    return $code
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$envFile = Join-Path $repoRoot "dentalsculptor-app\.env"

if (-not (Test-Path $envFile)) {
    Write-Error "Missing $envFile - create it or run from DentalSculptor repo."
}

$hfToken = $null
Get-Content $envFile -Encoding UTF8 | ForEach-Object {
    if ($_ -match '^\s*HF_TOKEN=(.+)$') {
        $hfToken = $matches[1].Trim().Trim('"').Trim("'")
    }
}

if (-not $hfToken -or $hfToken -eq "" -or $hfToken -like "*your_token*") {
    Write-Host ""
    Write-Host "HF_TOKEN not set in $envFile" -ForegroundColor Red
    Write-Host "Add: HF_TOKEN=hf_xxxxxxxx then save the file (Ctrl+S)" -ForegroundColor Yellow
    exit 1
}

Write-Host "Checking Hugging Face token..." -ForegroundColor Cyan
$null = Invoke-External { python -m pip install huggingface_hub -q 2>&1 | Out-Null }
$verifyScript = Join-Path $PSScriptRoot "verify_hf_token.py"
& python $verifyScript
$verifyCode = $LASTEXITCODE
if ($verifyCode -ne 0) {
    Write-Host ""
    Write-Host "HF token check failed. Common fixes:" -ForegroundColor Yellow
    Write-Host "  1. Create a new Read token: https://huggingface.co/settings/tokens" -ForegroundColor Yellow
    Write-Host "  2. Paste into .env as HF_TOKEN=hf_... (no quotes, no spaces)" -ForegroundColor Yellow
    Write-Host "  3. Save .env with Ctrl+S and run this script again" -ForegroundColor Yellow
    exit 1
}

Write-Host "Creating Modal secret huggingface..." -ForegroundColor Cyan
& python (Join-Path $PSScriptRoot "create_modal_hf_secret.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Create secret manually: https://modal.com/secrets/dentalsculptor/main/create?secret_name=huggingface" -ForegroundColor Yellow
    Write-Host "Key: HF_TOKEN  Value: (same as in .env)" -ForegroundColor Yellow
    exit 1
}
Write-Host "Modal secret huggingface ready." -ForegroundColor Green

Write-Host "Deploying Modal with TRELLIS_GPU=1 (first run: 20-40 min image build)..." -ForegroundColor Cyan
$env:PYTHONIOENCODING = "utf-8"
$env:TRELLIS_GPU = "1"
Set-Location (Join-Path $repoRoot "dentalsculptor-ml")
$deployCode = Invoke-External { python -m modal deploy -m modal_app.app }

if ($deployCode -eq 0) {
    Write-Host ""
    Write-Host "Done. Restart npm run dev in dentalsculptor-app." -ForegroundColor Green
    Write-Host "Generate URL: https://dentalsculptor--generate.modal.run" -ForegroundColor Green
    Write-Host "Success check: response source should be modal-trellis2-gpu" -ForegroundColor Green
} else {
    exit $deployCode
}
