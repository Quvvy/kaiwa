# Build the release: KaiwaSetup-<version>.exe (Inno Setup) and
# Kaiwa-<version>-portable.zip, both from the dist\Kaiwa\ tree.
# Usage:
#   .\scripts\build_installer.ps1              # build_desktop.ps1, then package
#   .\scripts\build_installer.ps1 -SkipDesktop # package the existing dist\Kaiwa\

param(
    [switch]$SkipDesktop
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$DistDir = Join-Path $Root "dist\Kaiwa"
$Exe = Join-Path $DistDir "Kaiwa.exe"
$Iss = Join-Path $Root "packaging\kaiwa.iss"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

# One source of truth for the version: src\kaiwa\__init__.py.
$Version = (Select-String -Path (Join-Path $Root "src\kaiwa\__init__.py") -Pattern '__version__ = "([^"]+)"').Matches[0].Groups[1].Value
if (-not $Version) {
    throw "Could not read __version__ from src\kaiwa\__init__.py"
}
$Toml = Get-Content (Join-Path $Root "pyproject.toml") -Raw
$VerInfo = Get-Content (Join-Path $Root "packaging\file_version_info.txt") -Raw
if ($Toml -notmatch "version = `"$([regex]::Escape($Version))`"" -or $VerInfo -notmatch "`"$([regex]::Escape($Version))`"") {
    throw "Version $Version is not the same in pyproject.toml and packaging\file_version_info.txt."
}
$SetupOut = Join-Path $Root "dist\KaiwaSetup-$Version.exe"
$PortableOut = Join-Path $Root "dist\Kaiwa-$Version-portable.zip"
Write-Host "Kaiwa $Version"

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

$Iscc = Find-ISCC
if (-not $Iscc) {
    Write-Host ""
    Write-Host "Inno Setup 6 is required to build the Windows installer (ISCC.exe not found)."
    Write-Host "Download: https://jrsoftware.org/isdl.php"
    Write-Host "Or: winget install --id JRSoftware.InnoSetup -e"
    Write-Host ""
    throw "ISCC.exe not found"
}

if (-not $SkipDesktop) {
    Write-Host "Building the desktop app (release)..."
    & (Join-Path $PSScriptRoot "build_desktop.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "build_desktop.ps1 failed"
    }
}

if (-not (Test-Path $Exe)) {
    throw "Missing $Exe - run .\scripts\build_desktop.ps1 first (or omit -SkipDesktop)."
}
if (-not (Test-Path (Join-Path $DistDir "runtime\python.exe"))) {
    throw "Missing the bundled runtime under dist\Kaiwa\runtime\. Use a release build (not -DevVenv)."
}
$ExeVersion = (Get-Item $Exe).VersionInfo.ProductVersion
if ($ExeVersion -ne $Version) {
    throw "dist\Kaiwa\Kaiwa.exe is version $ExeVersion, expected $Version. Rebuild without -SkipDesktop."
}

Write-Host "Drawing installer images..."
& $VenvPython (Join-Path $Root "packaging\make_wizard_images.py") (Join-Path $Root "build\installer")
if ($LASTEXITCODE -ne 0) {
    throw "make_wizard_images.py failed"
}

Write-Host ("Compiling installer with " + $Iscc)
& $Iscc "/DMyAppVersion=$Version" /Q $Iss
if ($LASTEXITCODE -ne 0) {
    throw ("ISCC failed with exit " + $LASTEXITCODE)
}
if (-not (Test-Path $SetupOut)) {
    throw "Expected installer missing: $SetupOut"
}

Write-Host "Packing the portable zip..."
# Kaiwa.portable next to Kaiwa.exe keeps all data in a Data folder beside it.
$Stage = Join-Path $Root "build\portable"
if (Test-Path $Stage) {
    Remove-Item -Recurse -Force $Stage
}
$StageApp = Join-Path $Stage "Kaiwa"
New-Item -ItemType Directory -Force $Stage | Out-Null
Copy-Item -Recurse $DistDir $StageApp
Copy-Item (Join-Path $Root "LICENSE") $StageApp
Copy-Item (Join-Path $Root "NOTICE.md") $StageApp
$Marker = @"
Kaiwa portable

This file makes Kaiwa keep everything in the Data folder next to Kaiwa.exe:
progress, settings, your DeepSeek key, the speech model and the voice engine.
Copy the whole Kaiwa folder to move it to another PC or a USB drive.

To update: close Kaiwa, then replace everything in this folder except Data.
Delete this file to use the normal per-user data folder (%LocalAppData%\Kaiwa) instead.
"@
[System.IO.File]::WriteAllText((Join-Path $StageApp "Kaiwa.portable"), $Marker, (New-Object System.Text.UTF8Encoding $false))
if (Test-Path $PortableOut) {
    Remove-Item -Force $PortableOut
}
# Windows' own bsdtar (10+) writes zips and is much faster than Compress-Archive
# on big trees. By full path: Git's GNU tar is often first on PATH and can't.
& (Join-Path $env:SystemRoot "System32\tar.exe") -a -c -f $PortableOut -C $Stage Kaiwa
if ($LASTEXITCODE -ne 0) {
    throw "tar failed to write $PortableOut"
}
Remove-Item -Recurse -Force $Stage

$Sums = Join-Path $Root "dist\Kaiwa-$Version-SHA256.txt"
$Lines = foreach ($f in @($SetupOut, $PortableOut)) {
    $h = (Get-FileHash -Algorithm SHA256 $f).Hash.ToLower()
    "$h  $(Split-Path $f -Leaf)"
}
[System.IO.File]::WriteAllText($Sums, (($Lines -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding $false))

Write-Host ""
foreach ($f in @($SetupOut, $PortableOut, $Sums)) {
    Write-Host ("Done: {0}  ({1:N0} MB)" -f $f, ((Get-Item $f).Length / 1MB))
}
Write-Host "Uninstall keeps %LocalAppData%\Kaiwa\ unless the learner chooses to delete it."
