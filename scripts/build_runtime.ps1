# Bundle a self-contained Python runtime under dist/Kaiwa/runtime.
# Usage:  .\scripts\build_runtime.ps1 [-DistDir path]
# Called by build_desktop.ps1 unless -DevVenv is set.
#
# Uses the official python.org "embeddable" Python (same version as the build
# .venv), so the app runs on PCs without Python installed. A venv would not:
# it points back at the Python it was made from.

param(
    [string]$DistDir = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
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
$SitePackages = Join-Path $RuntimeDir "Lib\site-packages"
$StaticSrc = Join-Path $Root "static"
$StaticDst = Join-Path $DistDir "static"

if (-not (Test-Path (Join-Path $DistDir "Kaiwa.exe"))) {
    throw "Expected Kaiwa.exe under $DistDir - run build_desktop.ps1 first (or PyInstaller)."
}
if (-not (Test-Path $StaticSrc)) {
    throw "Missing static/ at $StaticSrc"
}

# Same version as the build venv, so its wheels (cp3XX) match.
$PyVersion = (& $HostPython -c "import platform; print(platform.python_version())").Trim()
$PyTag = (& $HostPython -c "import sys; print(f'python{sys.version_info[0]}{sys.version_info[1]}')").Trim()
$CacheDir = Join-Path $Root "build\pyembed"
$Zip = Join-Path $CacheDir "python-$PyVersion-embed-amd64.zip"
if (-not (Test-Path $Zip)) {
    New-Item -ItemType Directory -Force $CacheDir | Out-Null
    $Url = "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-embed-amd64.zip"
    Write-Host "Downloading $Url ..."
    Invoke-WebRequest -Uri $Url -OutFile "$Zip.part" -UseBasicParsing
    Move-Item -Force "$Zip.part" $Zip
}

Write-Host "Creating runtime (embeddable Python $PyVersion) at $RuntimeDir ..."
if (Test-Path $RuntimeDir) {
    Remove-Item -Recurse -Force $RuntimeDir
}
Expand-Archive -Path $Zip -DestinationPath $RuntimeDir -Force

$RuntimePython = Join-Path $RuntimeDir "python.exe"
$Sig = Get-AuthenticodeSignature $RuntimePython
if ($Sig.Status -ne "Valid" -or $Sig.SignerCertificate.Subject -notmatch "Python Software Foundation") {
    throw "python.exe in $Zip is not signed by the Python Software Foundation ($($Sig.Status))."
}

# Whisper (ctranslate2) and the kana judge (onnxruntime) need the C++ runtime,
# which a clean Windows install lacks. Ship it app-locally beside python.exe
# (the embeddable zip already does this for vcruntime140.dll).
foreach ($dll in @("msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll")) {
    $src = Join-Path $env:SystemRoot "System32\$dll"
    if (-not (Test-Path $src)) {
        throw "Missing $src - install the Visual C++ Redistributable (x64) on the build PC."
    }
    Copy-Item -Force $src $RuntimeDir
}

# Search path: stdlib zip, the runtime folder, site-packages; `import site`
# so packages' .pth files (e.g. pywin32) are processed.
$Pth = Join-Path $RuntimeDir "$PyTag._pth"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($Pth, "$PyTag.zip`r`n.`r`nLib\site-packages`r`nimport site`r`n", $utf8NoBom)

Write-Host "Installing Kaiwa and its dependencies into the runtime..."
# Base package only - nvidia CUDA wheels are optional [cuda].
& $HostPython -m pip install --target $SitePackages --no-compile --disable-pip-version-check -q "$Root"
if ($LASTEXITCODE -ne 0) {
    throw "pip install kaiwa into runtime failed"
}
# Console-script launchers point at the build machine's Python; nothing uses them.
$BinDir = Join-Path $SitePackages "bin"
if (Test-Path $BinDir) {
    Remove-Item -Recurse -Force $BinDir
}
# Package test suites are never imported by the app.
Get-ChildItem -Path $SitePackages -Directory -Recurse -Filter "tests" |
    Where-Object { $_.FullName -match "\\(numpy|onnxruntime|av|pykakasi|sympy|mpmath|networkx)\\" } |
    Remove-Item -Recurse -Force

Write-Host "Precompiling Python files (faster start; Program Files is read-only)..."
& $RuntimePython -m compileall -q -j 0 $SitePackages | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "compileall reported files it could not compile (usually harmless templates)."
}

Write-Host "Copying static/ ..."
if (Test-Path $StaticDst) {
    Remove-Item -Recurse -Force $StaticDst
}
Copy-Item -Recurse -Force $StaticSrc $StaticDst

Write-Host "Checking the runtime imports..."
$CheckData = Join-Path $env:TEMP "kaiwa-runtime-check"
$saved = @($env:KAIWA_ROOT, $env:KAIWA_DATA_DIR)
$env:KAIWA_ROOT = $DistDir
$env:KAIWA_DATA_DIR = $CheckData
try {
    & $RuntimePython -c "import kaiwa.app, kaiwa.bootstrap, faster_whisper, onnxruntime, fsrs; print('runtime ok')"
    if ($LASTEXITCODE -ne 0) {
        throw "The bundled runtime cannot import Kaiwa."
    }
} finally {
    $env:KAIWA_ROOT, $env:KAIWA_DATA_DIR = $saved
    if (Test-Path $CheckData) { Remove-Item -Recurse -Force $CheckData }
}

& $HostPython (Join-Path $Root "packaging\check_dlls.py") $RuntimeDir (Join-Path $DistDir "_internal")
if ($LASTEXITCODE -ne 0) {
    throw "A bundled module needs a Visual C++ runtime DLL that is not bundled (see above)."
}

$RuntimeObj = [ordered]@{
    app_root = "."
    python   = "runtime\python.exe"
}
$RuntimePath = Join-Path $DistDir "Kaiwa.runtime.json"
[System.IO.File]::WriteAllText($RuntimePath, ($RuntimeObj | ConvertTo-Json), $utf8NoBom)
Write-Host ("Wrote relative " + $RuntimePath)
Write-Host "Runtime bundle ready."
