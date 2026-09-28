$ErrorActionPreference = "Stop"
$datasetRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\research\datasets\fdi16-v2")
$archive = Join-Path $datasetRoot "fdi16_dataset.zip"
$log = Join-Path $datasetRoot "ingestion.log"
$expectedSize = 7160405142
$expectedMd5 = "9824c7d342f6f13887084452d2c75c68"
$python = Resolve-Path (Join-Path $PSScriptRoot "..\..\.tools\modal-venv\Scripts\python.exe")

while (-not (Test-Path -LiteralPath $archive) -or (Get-Item -LiteralPath $archive).Length -lt $expectedSize) {
  Start-Sleep -Seconds 60
}
$actualSize = (Get-Item -LiteralPath $archive).Length
if ($actualSize -ne $expectedSize) { throw "FDI-16 file size mismatch: $actualSize" }
$actualMd5 = (Get-FileHash -LiteralPath $archive -Algorithm MD5).Hash.ToLowerInvariant()
if ($actualMd5 -ne $expectedMd5) { throw "FDI-16 checksum mismatch: $actualMd5" }
"[$(Get-Date -Format o)] Checksum verified; extracting 750 meshes" | Add-Content -LiteralPath $log
& $python (Join-Path $PSScriptRoot "extract_fdi16_subset.py") --archive $archive --output (Join-Path $datasetRoot "pilot-750") --maximum 750 2>> $log
if ($LASTEXITCODE -ne 0) { throw "FDI-16 extraction failed; see $log" }
"[$(Get-Date -Format o)] Ingestion complete" | Add-Content -LiteralPath $log
