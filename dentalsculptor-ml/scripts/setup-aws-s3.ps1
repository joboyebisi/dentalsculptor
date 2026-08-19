# Create DentalSculptor S3 bucket (private, encrypted, CORS, jobs lifecycle).
# Run AFTER creating the IAM user + access key in AWS Console.
#
# Usage:
#   aws configure --profile dentalsculptor
#   $env:AWS_PROFILE = "dentalsculptor"
#   powershell -ExecutionPolicy Bypass -File .\dentalsculptor-ml\scripts\setup-aws-s3.ps1 `
#     -BucketName "dentalsculptor-assets-prod-YOUR-SUFFIX" `
#     -Region "eu-west-1" `
#     -AppOrigin "https://your-app.vercel.app"

param(
    [Parameter(Mandatory = $true)]
    [string]$BucketName,

    [string]$Region = "eu-west-1",

    [string]$AppOrigin = "http://localhost:3000"
)

$ErrorActionPreference = "Stop"

function Require-AwsCli {
    aws --version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "AWS CLI is not installed." }
}

function Test-BucketExists {
    param([string]$Name)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        aws s3api head-bucket --bucket $Name 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Write-JsonTempFile {
    param([object]$Object)
    $path = [System.IO.Path]::GetTempFileName()
    $Object | ConvertTo-Json -Depth 8 | Set-Content -Path $path -Encoding utf8
    return $path
}

Require-AwsCli

Write-Host "Checking caller identity..."
aws sts get-caller-identity

if ($LASTEXITCODE -ne 0) { throw "AWS credentials are not configured for this profile." }

if (Test-BucketExists -Name $BucketName) {
    Write-Host "Bucket already exists: $BucketName"
} else {
    Write-Host "Creating bucket $BucketName in $Region..."
    if ($Region -eq "us-east-1") {
        aws s3api create-bucket --bucket $BucketName --region $Region
    } else {
        aws s3api create-bucket `
            --bucket $BucketName `
            --region $Region `
            --create-bucket-configuration LocationConstraint=$Region
    }
    if ($LASTEXITCODE -ne 0) { throw "Failed to create bucket." }
}

Write-Host "Blocking public access..."
aws s3api put-public-access-block `
    --bucket $BucketName `
    --public-access-block-configuration `
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

Write-Host "Enabling default encryption (SSE-S3)..."
$encryptionPath = Write-JsonTempFile @{
    Rules = @(
        @{
            ApplyServerSideEncryptionByDefault = @{ SSEAlgorithm = "AES256" }
            BucketKeyEnabled                   = $true
        }
    )
}
try {
    aws s3api put-bucket-encryption `
        --bucket $BucketName `
        --server-side-encryption-configuration "file://$($encryptionPath -replace '\\', '/')"
} finally {
    Remove-Item $encryptionPath -ErrorAction SilentlyContinue
}

Write-Host "Setting CORS..."
$corsPath = Write-JsonTempFile @{
    CORSRules = @(
        @{
            AllowedHeaders = @("*")
            AllowedMethods = @("GET", "PUT", "HEAD")
            AllowedOrigins = @("http://localhost:3000", $AppOrigin)
            ExposeHeaders  = @("ETag")
            MaxAgeSeconds  = 3600
        }
    )
}
try {
    aws s3api put-bucket-cors `
        --bucket $BucketName `
        --cors-configuration "file://$($corsPath -replace '\\', '/')"
} finally {
    Remove-Item $corsPath -ErrorAction SilentlyContinue
}

Write-Host "Adding lifecycle rule for jobs/ prefix (30 days)..."
$lifecyclePath = Write-JsonTempFile @{
    Rules = @(
        @{
            ID     = "expire-modal-jobs"
            Status = "Enabled"
            Filter = @{ Prefix = "jobs/" }
            Expiration = @{ Days = 30 }
        }
    )
}
try {
    aws s3api put-bucket-lifecycle-configuration `
        --bucket $BucketName `
        --lifecycle-configuration "file://$($lifecyclePath -replace '\\', '/')"
} finally {
    Remove-Item $lifecyclePath -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Done. Bucket: s3://$BucketName"
Write-Host "Add to dentalsculptor-app/.env and Vercel:"
Write-Host "  AWS_REGION=$Region"
Write-Host "  AWS_S3_BUCKET=$BucketName"
Write-Host "  STORAGE_BACKEND=s3"
