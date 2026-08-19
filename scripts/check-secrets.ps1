# Scan tracked and staged files for likely secrets before commit.
param(
    [switch]$StagedOnly
)

$ErrorActionPreference = "Stop"

$patterns = @(
    'sk_test_[A-Za-z0-9]+',
    'sk_live_[A-Za-z0-9]+',
    'pk_test_[A-Za-z0-9]+',
    'AKIA[0-9A-Z]{16}',
    'hf_[A-Za-z0-9]{20,}',
    'as-[A-Za-z0-9]+',
    'ak-[A-Za-z0-9]+',
    'postgresql://[^:]+:[^@]+@',
    'RESEARCH_GENERATION_ACCESS_CODE=[^#\r\n]+'
)

$files = if ($StagedOnly) {
    git diff --cached --name-only --diff-filter=ACM
} else {
    git ls-files
}

$hits = @()
foreach ($file in $files) {
    if (-not (Test-Path $file)) { continue }
    if ($file -match '(^|/)\.env($|\.)') { continue }
    if ($file -match '\.env\.example$') { continue }
    if ($file -match 'check-secrets\.ps1$') { continue }
    $content = Get-Content $file -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }
    foreach ($pattern in $patterns) {
        if ($content -match $pattern) {
            $hits += [pscustomobject]@{ File = $file; Pattern = $pattern }
        }
    }
}

if ($hits.Count -gt 0) {
    Write-Host "Potential secrets detected:" -ForegroundColor Red
    $hits | Format-Table -AutoSize
    exit 1
}

Write-Host "No likely secrets found in scanned files." -ForegroundColor Green
