[CmdletBinding()]
param(
    [string]$EnvironmentPath = 'D:\CondaEnvs\myenv',
    [switch]$SkipInstall,
    [switch]$SkipDiffusersExample
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $EnvironmentPath 'python.exe'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python was not found at $python. Create the Conda environment first or pass -EnvironmentPath."
}

Write-Host "Training Python: $python"
& $python --version

if (-not $SkipInstall) {
    & $python -m pip install --upgrade pip
    & $python -m pip install -r (Join-Path $root 'backend\requirements-training.txt')
}

if (-not $SkipDiffusersExample) {
    $diffusersSource = Join-Path $EnvironmentPath 'src\diffusers'
    if (-not (Test-Path -LiteralPath (Join-Path $diffusersSource 'examples\text_to_image\train_text_to_image_lora.py'))) {
        if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
            throw 'Git is required to obtain the official Diffusers LoRA training example.'
        }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $diffusersSource) | Out-Null
        $diffusersVersion = (& $python -c 'import diffusers; print(diffusers.__version__)').Trim()
        & git clone --depth 1 --branch "v$diffusersVersion" https://github.com/huggingface/diffusers.git $diffusersSource
        if ($LASTEXITCODE -ne 0) { throw 'Could not obtain the Diffusers training example.' }
    }
}

$directories = @(
    'data\raw',
    'data\processed',
    'data\training\retriever',
    'data\training\llm',
    'data\training\vlm',
    'training_outputs'
)
foreach ($relative in $directories) {
    New-Item -ItemType Directory -Force -Path (Join-Path $root $relative) | Out-Null
}

$environmentDirectories = @(
    'cache\huggingface',
    'cache\torch',
    'cache\datasets',
    'src'
)
foreach ($relative in $environmentDirectories) {
    New-Item -ItemType Directory -Force -Path (Join-Path $EnvironmentPath $relative) | Out-Null
}

& $python (Join-Path $root 'scripts\check_training_environment.py')
Write-Host 'Training environment preparation completed. Datasets were not downloaded.'
