"""One Kaiwa window at a time, and portable mode (data next to Kaiwa.exe)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# The installer checks this name (AppMutex in packaging/kaiwa.iss) so it can ask
# the learner to close Kaiwa before updating or uninstalling.
MUTEX_NAME = "KaiwaDesktopSingleInstance"
PORTABLE_MARKER = "Kaiwa.portable"
PORTABLE_DATA = "Data"

_ERROR_ALREADY_EXISTS = 183
_SW_RESTORE = 9
_mutex = None  # held for the life of the process


def portable_data_dir() -> Path | None:
    """`<exe dir>/Data` when Kaiwa.exe sits next to a Kaiwa.portable marker."""
    if not getattr(sys, "frozen", False):
        return None
    exe_dir = Path(sys.executable).resolve().parent
    if not (exe_dir / PORTABLE_MARKER).is_file():
        return None
    return exe_dir / PORTABLE_DATA


def apply_portable_mode() -> Path | None:
    """Keep progress, models and the voice engine inside the portable folder.

    Set before anything reads user_data_dir(); the API and bootstrap processes
    inherit it. KAIWA_DATA_DIR set by hand still wins.
    """
    data = portable_data_dir()
    if data is None:
        return None
    os.environ["KAIWA_PORTABLE"] = "1"
    if not (os.environ.get("KAIWA_DATA_DIR") or "").strip():
        data.mkdir(parents=True, exist_ok=True)
        os.environ["KAIWA_DATA_DIR"] = str(data)
    return data


def claim_single_instance() -> bool:
    """True if this is the only Kaiwa window; otherwise bring the open one forward."""
    if sys.platform != "win32":
        return True
    global _mutex
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        _mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if not _mutex or kernel32.GetLastError() != _ERROR_ALREADY_EXISTS:
            return True
    except Exception:
        return True
    _focus_existing_window()
    return False


def _focus_existing_window() -> None:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        found: list[int] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def visit(hwnd, _lparam):  # noqa: ANN001
            if not user32.IsWindowVisible(hwnd):
                return True
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 256)
            cls = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls, 256)
            # pywebview's window is a WinForms form titled "Kaiwa"; this skips
            # Explorer showing a folder of the same name.
            if title.value == "Kaiwa" and cls.value.startswith("WindowsForms"):
                found.append(hwnd)
                return False
            return True

        user32.EnumWindows(visit, 0)
        if not found:
            return
        hwnd = found[0]
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, _SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
