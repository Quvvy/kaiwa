# Build thin Kaiwa.exe (window + webview). API stays in .venv.
# Usage:  .\scripts\build_desktop.ps1

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
    throw "Missing venv python. Create .venv and pip install -e .[desktop]"
}
if (-not (Test-Path $Ico)) {
    throw ("Missing icon: " + $Ico)
}

Write-Host "Ensuring desktop + build deps..."
& $VenvPip install -e ".[desktop,desktop-build]" -q

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

$RuntimeObj = [ordered]@{
    repo_root = $Root.Path
    python    = $VenvPython
}
$RuntimePath = Join-Path $DistDir "Kaiwa.runtime.json"
# No BOM — frozen Kaiwa.json.loads must read this (utf-8-sig also accepted).
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($RuntimePath, ($RuntimeObj | ConvertTo-Json), $utf8NoBom)
Write-Host ("Wrote " + $RuntimePath)
Write-Host ("Done: " + (Join-Path $DistDir "Kaiwa.exe"))
Write-Host "Pin that exe (not python.exe). Unpin any old Python taskbar icon."
