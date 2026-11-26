[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Model,
    [Parameter(Mandatory = $true)][string]$DatasetDirectory,
    [string]$EnvironmentPath = 'D:\CondaEnvs\myenv',
    [string]$DiffusersSource = 'D:\CondaEnvs\myenv\src\diffusers',
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $EnvironmentPath 'python.exe'
$trainer = Join-Path $DiffusersSource 'examples\text_to_image\train_text_to_image_lora.py'
if (-not (Test-Path -LiteralPath $python)) { throw "Python not found: $python" }
if (-not (Test-Path -LiteralPath $trainer)) {
    throw "Official Diffusers training example not found at $trainer. See docs\windows-training.zh.md."
}
if (-not (Test-Path -LiteralPath $DatasetDirectory -PathType Container)) {
    throw "Dataset directory not found: $DatasetDirectory"
}
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'training_outputs\diffusion-lora' }

$env:HF_HOME = Join-Path $EnvironmentPath 'cache\huggingface'
$env:HF_DATASETS_CACHE = Join-Path $EnvironmentPath 'cache\datasets'
$env:TORCH_HOME = Join-Path $EnvironmentPath 'cache\torch'
$env:PYTHONUTF8 = '1'
New-Item -ItemType Directory -Force -Path $env:HF_HOME, $env:HF_DATASETS_CACHE, $env:TORCH_HOME | Out-Null

& $python -m accelerate.commands.launch $trainer `
    --pretrained_model_name_or_path=$Model `
    --train_data_dir=$DatasetDirectory `
    --caption_column='text' `
    --resolution=512 `
    --train_batch_size=1 `
    --gradient_accumulation_steps=4 `
    --gradient_checkpointing `
    --mixed_precision=fp16 `
    --learning_rate=1e-4 `
    --max_train_steps=2000 `
    --checkpointing_steps=250 `
    --output_dir=$OutputDirectory
if ($LASTEXITCODE -ne 0) { throw "Diffusion LoRA training failed with exit code $LASTEXITCODE" }
