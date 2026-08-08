# -*- mode: python ; coding: utf-8 -*-
"""Thin Kaiwa desktop shell (window + webview). API/Whisper stay in the venv."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

SPECDIR = Path(SPECPATH).resolve()
ROOT = SPECDIR.parent
ASSETS = ROOT / "src" / "kaiwa" / "desktop" / "assets"
ICON = ASSETS / "kaiwa.ico"
VERSION = SPECDIR / "file_version_info.txt"
ENTRY = SPECDIR / "kaiwa_desktop_entry.py"

datas = [(str(ASSETS), "desktop_assets")]
binaries = []
hiddenimports = [
    "kaiwa.desktop",
    "kaiwa.desktop.app",
    "kaiwa.desktop.window",
    "kaiwa.desktop.icons",
    "kaiwa.desktop.lifecycle",
    "kaiwa.desktop.services",
    "kaiwa.prefs",
    "kaiwa.config",
    "clr",
]

# pywebview + pythonnet need their package data
for pkg in ("webview", "pythonnet", "clr_loader"):
    try:
        pkg_datas, pkg_bins, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_bins
        hiddenimports += pkg_hidden
    except Exception:
        pass

excludes = [
    "torch",
    "torchaudio",
    "torchvision",
    "faster_whisper",
    "ctranslate2",
    "onnxruntime",
    "tensorflow",
    "tensorboard",
    "nvidia",
    "cuda",
    "av",
    "matplotlib",
    "scipy",
    "pandas",
    "sklearn",
    "cv2",
    "IPython",
    "jupyter",
    "notebook",
    "pystray",
    "PIL",
]

a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Kaiwa",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.is_file() else None,
    version=str(VERSION) if VERSION.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Kaiwa",
)
