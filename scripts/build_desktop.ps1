# Build portable Kaiwa.exe + private CPU runtime (no friend .venv required).
# Usage:
#   .\scripts\build_desktop.ps1              # shell + runtime (release)
#   .\scripts\build_desktop.ps1 -DevVenv     # shell only; points at clone .venv

param(
    [switch]$DevVenv
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$VenvPip = Join-Path $Root ".venv\Scripts\pip.exe"
$PyInstaller = Join-Path $Root ".venv\Scripts\pyinstaller.exe"
$Spec = Join-Path $Root "packaging\kaiwa-desktop.spec"
$DistDir = Join-Path $Root "dist\Kaiwa"
$Ico = Join-Path $Root "src\kaiwa\desktop\assets\kaiwa.ico"

if (-not (Test-Path $VenvPython)) {
    throw "Missing venv python. Create .venv and pip install -e `".[desktop,cuda]`""
}
if (-not (Test-Path $Ico)) {
    throw ("Missing icon: " + $Ico)
}

Write-Host "Ensuring desktop + build deps..."
& $VenvPip install -e ".[desktop,desktop-build,cuda]" -q

if (-not (Test-Path $PyInstaller)) {
    throw "pyinstaller not found after install"
}

Write-Host "Running PyInstaller..."
& $PyInstaller --noconfirm --clean $Spec
if ($LASTEXITCODE -ne 0) {
    throw ("PyInstaller failed with exit " + $LASTEXITCODE)
}

if (-not (Test-Path (Join-Path $DistDir "Kaiwa.exe"))) {
    throw "Expected Kaiwa.exe missing under dist\Kaiwa"
}

$RuntimePath = Join-Path $DistDir "Kaiwa.runtime.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false

if ($DevVenv) {
    $RuntimeObj = [ordered]@{
        repo_root = $Root.Path
        python    = $VenvPython
    }
    [System.IO.File]::WriteAllText($RuntimePath, ($RuntimeObj | ConvertTo-Json), $utf8NoBom)
    Write-Host ("Wrote DevVenv " + $RuntimePath)
} else {
    & (Join-Path $PSScriptRoot "build_runtime.ps1") -DistDir $DistDir
    if ($LASTEXITCODE -ne 0) {
        throw "build_runtime.ps1 failed"
    }
}

Write-Host ("Done: " + (Join-Path $DistDir "Kaiwa.exe"))
if (-not $DevVenv) {
    Write-Host "Portable layout: Kaiwa.exe + runtime\ + static\ (relative Kaiwa.runtime.json)."
}
Write-Host "Pin that exe (not python.exe). Unpin any old Python taskbar icon."
