[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [ValidateRange(1, 65535)]
    [int]$Port = 8000,
    [switch]$Reload
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$backendDirectory = Join-Path $repoRoot "backend"
$pythonExecutable = Join-Path $backendDirectory ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
    throw "Backend virtual environment not found at '$pythonExecutable'. Create it from the repository root with: py -3 -m venv backend\.venv"
}

$uvicornArguments = @(
    "-m", "uvicorn", "app.main:app",
    "--host", $HostAddress,
    "--port", $Port.ToString()
)

if ($Reload) {
    $uvicornArguments += "--reload"
}

Push-Location $backendDirectory
try {
    & $pythonExecutable @uvicornArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Backend exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
