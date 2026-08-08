"""Resolve bundled Kaiwa icon assets for the desktop window."""

from __future__ import annotations

import sys
from pathlib import Path

# Distinct from python.exe so Windows taskbar uses our window icon.
_WINDOWS_APP_ID = "Kaiwa.Desktop"


def _assets_dir() -> Path:
    """Source install: package assets/. Frozen: PyInstaller desktop_assets/."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / "desktop_assets"
        if bundled.is_dir():
            return bundled
    return Path(__file__).resolve().parent / "assets"


def asset_path(name: str) -> Path:
    path = _assets_dir() / name
    if not path.is_file():
        raise FileNotFoundError(f"Kaiwa icon missing: {path}")
    return path


def set_windows_app_id(app_id: str = _WINDOWS_APP_ID) -> None:
    """Tell Windows this process is Kaiwa, not python.exe (taskbar grouping)."""
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def window_icon_path() -> Path | None:
    """Absolute path to .ico for title bar / taskbar (from kaiwa-full-icon)."""
    ico = _assets_dir() / "kaiwa.ico"
    if ico.is_file():
        return ico.resolve()
    return None
