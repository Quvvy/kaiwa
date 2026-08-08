# Bundle a private CPU Python runtime under dist/Kaiwa/runtime (no developer .venv).
# Usage:  .\scripts\build_runtime.ps1 [-DistDir path]
# Called by build_desktop.ps1 unless -DevVenv is set.

param(
    [string]$DistDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not $DistDir) {
    $DistDir = Join-Path $Root "dist\Kaiwa"
}
$DistDir = (Resolve-Path $DistDir).Path

$HostPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $HostPython)) {
    throw "Missing build venv python at $HostPython"
}

$RuntimeDir = Join-Path $DistDir "runtime"
$StaticSrc = Join-Path $Root "static"
$StaticDst = Join-Path $DistDir "static"

if (-not (Test-Path (Join-Path $DistDir "Kaiwa.exe"))) {
    throw "Expected Kaiwa.exe under $DistDir - run build_desktop.ps1 first (or PyInstaller)."
}
if (-not (Test-Path $StaticSrc)) {
    throw "Missing static/ at $StaticSrc"
}

Write-Host "Creating private runtime venv at $RuntimeDir ..."
if (Test-Path $RuntimeDir) {
    Remove-Item -Recurse -Force $RuntimeDir
}
& $HostPython -m venv $RuntimeDir
if ($LASTEXITCODE -ne 0) {
    throw "python -m venv failed"
}

$RuntimePython = Join-Path $RuntimeDir "Scripts\python.exe"
$RuntimePip = Join-Path $RuntimeDir "Scripts\pip.exe"
if (-not (Test-Path $RuntimePython)) {
    throw "Runtime python missing after venv create"
}

Write-Host "Installing Kaiwa (CPU deps, non-editable) into runtime..."
& $RuntimePython -m pip install --upgrade pip -q
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
# Base package only - nvidia CUDA wheels are optional [cuda], deferred to Phase 6.6.
& $RuntimePip install "$Root" -q
if ($LASTEXITCODE -ne 0) {
    throw "pip install kaiwa into runtime failed"
}

Write-Host "Copying static/ ..."
if (Test-Path $StaticDst) {
    Remove-Item -Recurse -Force $StaticDst
}
Copy-Item -Recurse -Force $StaticSrc $StaticDst

$RuntimeObj = [ordered]@{
    app_root = "."
    python   = "runtime\Scripts\python.exe"
}
$RuntimePath = Join-Path $DistDir "Kaiwa.runtime.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($RuntimePath, ($RuntimeObj | ConvertTo-Json), $utf8NoBom)
Write-Host ("Wrote relative " + $RuntimePath)
Write-Host "Runtime bundle ready."
