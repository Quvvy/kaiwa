# Build KaiwaSetup-<version>.exe (Inno Setup) over the portable dist\Kaiwa\ tree.
# Usage:
#   .\scripts\build_installer.ps1              # build_desktop.ps1 then ISCC
#   .\scripts\build_installer.ps1 -SkipDesktop # use existing dist\Kaiwa\

param(
    [switch]$SkipDesktop
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$DistDir = Join-Path $Root "dist\Kaiwa"
$Exe = Join-Path $DistDir "Kaiwa.exe"
$Iss = Join-Path $Root "packaging\kaiwa.iss"
$Version = "1.0.0"
$SetupOut = Join-Path $Root "dist\KaiwaSetup-$Version.exe"

function Find-ISCC {
    $cmd = Get-Command ISCC -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        return $cmd.Source
    }
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p)) {
            return $p
        }
    }
    return $null
}

if (-not $SkipDesktop) {
    Write-Host "Building portable desktop (release)..."
    & (Join-Path $PSScriptRoot "build_desktop.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "build_desktop.ps1 failed"
    }
}

if (-not (Test-Path $Exe)) {
    throw "Missing $Exe - run .\scripts\build_desktop.ps1 first (or omit -SkipDesktop)."
}
if (-not (Test-Path (Join-Path $DistDir "runtime\Scripts\python.exe"))) {
    throw "Missing portable runtime under dist\Kaiwa\runtime\. Use a release build (not -DevVenv)."
}
if (-not (Test-Path $Iss)) {
    throw "Missing Inno script: $Iss"
}

$Iscc = Find-ISCC
if (-not $Iscc) {
    Write-Host ""
    Write-Host "Inno Setup 6 is required to build the Windows installer (ISCC.exe not found)."
    Write-Host "Download: https://jrsoftware.org/isdl.php"
    Write-Host "Or: winget install --id JRSoftware.InnoSetup -e"
    Write-Host ""
    throw "ISCC.exe not found"
}

Write-Host ("Compiling installer with " + $Iscc)
& $Iscc $Iss
if ($LASTEXITCODE -ne 0) {
    throw ("ISCC failed with exit " + $LASTEXITCODE)
}

if (-not (Test-Path $SetupOut)) {
    throw "Expected installer missing: $SetupOut"
}

Write-Host ("Done: " + $SetupOut)
Write-Host "Friends: run the Setup.exe, then Start Menu -> Kaiwa. Uninstall keeps %LocalAppData%\Kaiwa\."
