[CmdletBinding()]
param(
    [ValidateSet('all', 'foodcom', 'food101')]
    [string]$Dataset = 'all'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$raw = Join-Path $root 'data\raw'
New-Item -ItemType Directory -Force -Path $raw | Out-Null

function Get-Archive([string]$Url, [string]$Destination) {
    Write-Host "Downloading to $Destination"
    & curl.exe -L --fail --retry 3 -C - --output $Destination $Url
    if ($LASTEXITCODE -ne 0) { throw "Download failed: $Url" }
}

if ($Dataset -in @('all', 'foodcom')) {
    Get-Archive `
        'https://www.kaggle.com/api/v1/datasets/download/irkaal/foodcom-recipes-and-reviews' `
        (Join-Path $raw 'foodcom-recipes-and-reviews.zip')
}
if ($Dataset -in @('all', 'food101')) {
    Get-Archive `
        'https://data.vision.ee.ethz.ch/cvl/food-101.tar.gz' `
        (Join-Path $raw 'food-101.tar.gz')
}

Write-Host 'Downloads completed. Run the preparation commands documented in docs\windows-training.zh.md.'
