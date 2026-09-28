$ErrorActionPreference = "Stop"
$datasetRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\research\datasets\fdi16-v2")
$archive = Join-Path $datasetRoot "fdi16_dataset.zip"
$log = Join-Path $datasetRoot "ingestion.log"
$expectedMd5 = "9824c7d342f6f13887084452d2c75c68"
$python = Resolve-Path (Join-Path $PSScriptRoot "..\..\.tools\modal-venv\Scripts\python.exe")

"[$(Get-Date -Format o)] Resuming official FDI-16 download" | Add-Content -LiteralPath $log
& $python (Join-Path $PSScriptRoot "resumable_download.py") --url "https://ndownloader.figshare.com/files/44571158" --destination $archive --expected-size 7160405142 --log $log 2>> $log
if ($LASTEXITCODE -ne 0) { throw "FDI-16 download failed; see $log" }

$actualMd5 = (Get-FileHash -LiteralPath $archive -Algorithm MD5).Hash.ToLowerInvariant()
if ($actualMd5 -ne $expectedMd5) { throw "FDI-16 checksum mismatch: $actualMd5" }
"[$(Get-Date -Format o)] Checksum verified; extracting 750 meshes" | Add-Content -LiteralPath $log

& $python (Join-Path $PSScriptRoot "extract_fdi16_subset.py") --archive $archive --output (Join-Path $datasetRoot "pilot-750") --maximum 750 2>> $log
if ($LASTEXITCODE -ne 0) { throw "FDI-16 extraction failed; see $log" }
"[$(Get-Date -Format o)] Ingestion complete" | Add-Content -LiteralPath $log
