param(
  [Parameter(Mandatory = $true)][string]$ModelName,
  [Parameter(Mandatory = $true)][string]$ModelRevision,
  [string]$CandidateName = "dental-candidate"
)

$ErrorActionPreference = "Stop"
if ($CandidateName -notmatch '^[a-z0-9-]+$') {
  throw "CandidateName must contain only lowercase letters, digits, and hyphens."
}

$env:MODAL_APP_NAME = "dentalsculptor-$CandidateName"
$env:MODAL_WEB_LABEL_SUFFIX = $CandidateName
$env:TRELLIS_MODEL_NAME = $ModelName
$env:TRELLIS_MODEL_REVISION = $ModelRevision
$env:TRELLIS_DEPLOYMENT_ENV = "development"
$env:TRELLIS_MIN_CONTAINERS = "0"
$env:TRELLIS_MAX_CONTAINERS = "1"

Write-Host "Deploying isolated scale-to-zero candidate app: $env:MODAL_APP_NAME"
$workspacePython = Join-Path $PSScriptRoot "..\..\.tools\modal-venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $workspacePython)) {
  throw "Modal Python environment was not found at $workspacePython"
}
& $workspacePython -m modal deploy -m modal_app.app
