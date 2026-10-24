"""Desktop shell checks: portable mode, one window at a time, portable updates.

Usage: .venv\\Scripts\\python scripts\\smoke_desktop.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _check(ok: bool, label: str) -> None:
    print(("ok  " if ok else "FAIL") + "  " + label)
    if not ok:
        raise SystemExit(1)


def portable_checks() -> None:
    from kaiwa.desktop import instance

    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "Kaiwa.exe"
        exe.write_bytes(b"")
        saved = {k: os.environ.pop(k, None) for k in ("KAIWA_DATA_DIR", "KAIWA_PORTABLE")}
        real_exe, real_frozen = sys.executable, getattr(sys, "frozen", None)
        sys.executable, sys.frozen = str(exe), True  # type: ignore[attr-defined]
        try:
            _check(instance.apply_portable_mode() is None, "no marker: normal data folder")
            _check("KAIWA_DATA_DIR" not in os.environ, "no marker: KAIWA_DATA_DIR untouched")
            (Path(tmp) / instance.PORTABLE_MARKER).write_text("portable", encoding="utf-8")
            data = instance.apply_portable_mode()
            _check(data == exe.parent / "Data" and data.is_dir(), "marker: Data folder beside Kaiwa.exe")
            _check(os.environ.get("KAIWA_DATA_DIR") == str(data), "marker: children inherit the data folder")

            from kaiwa.secrets_store import user_data_dir

            _check(user_data_dir() == data, "user_data_dir follows portable mode")
        finally:
            sys.executable = real_exe
            if real_frozen is None:
                del sys.frozen  # type: ignore[attr-defined]
            for k, v in saved.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v
    _check(instance.portable_data_dir() is None, "source runs are never portable")


def single_instance_checks() -> None:
    from kaiwa.desktop import instance

    if sys.platform != "win32":
        return
    _check(instance.claim_single_instance(), "first Kaiwa claims the window")
    # A second process sees the mutex, so it would focus this one and exit.
    code = (
        "import sys; sys.path.insert(0, r'%s');"
        "from kaiwa.desktop import instance;"
        "sys.exit(0 if instance.claim_single_instance() else 3)"
    ) % (ROOT / "src")
    second = subprocess.run([sys.executable, "-c", code], check=False)
    _check(second.returncode == 3, "second Kaiwa sees the first and steps aside")


def app_id_checks() -> None:
    from kaiwa.desktop import icons

    import ctypes

    calls: list[str] = []

    class _Shell:
        def SetCurrentProcessExplicitAppUserModelID(self, app_id):  # noqa: N802, ANN001
            calls.append(app_id)

    real_windll = getattr(ctypes, "windll", None)
    ctypes.windll = type("W", (), {"shell32": _Shell()})()  # type: ignore[attr-defined]
    try:
        sys.frozen = True  # type: ignore[attr-defined]
        icons.set_windows_app_id()
        _check(calls == [], "Kaiwa.exe keeps the default identity its shortcuts carry")
        del sys.frozen  # type: ignore[attr-defined]
        icons.set_windows_app_id()
        _check(calls == ["Kaiwa.Desktop"], "source runs still group apart from python.exe")
    finally:
        if real_windll is not None:
            ctypes.windll = real_windll  # type: ignore[attr-defined]


def portable_update_checks() -> None:
    from kaiwa import updates

    opened: list[str] = []
    real = (updates.check_for_updates, os.startfile, updates.sys.platform)
    updates.check_for_updates = lambda force=False: {  # type: ignore[assignment]
        "asset_url": "https://example.invalid/KaiwaSetup-9.0.0.exe",
        "asset_name": "KaiwaSetup-9.0.0.exe",
        "latest_version": "9.0.0",
        "html_url": "https://github.com/Quvvy/kaiwa/releases/tag/v9.0.0",
    }
    os.startfile = opened.append  # type: ignore[assignment]
    updates.sys.platform = "win32"
    os.environ["KAIWA_PORTABLE"] = "1"
    try:
        res = updates.download_and_launch_installer()
        _check(res["ok"] and not res["launched"], "portable: the installer is not run")
        _check(opened == ["https://github.com/Quvvy/kaiwa/releases/tag/v9.0.0"], "portable: the release page opens")
        _check("except Data" in res["detail"], "portable: says to keep the Data folder")
    finally:
        os.environ.pop("KAIWA_PORTABLE", None)
        updates.check_for_updates, os.startfile, updates.sys.platform = real  # type: ignore[assignment]


def main() -> None:
    portable_checks()
    single_instance_checks()
    app_id_checks()
    portable_update_checks()
    print("smoke_desktop: all ok")


if __name__ == "__main__":
    main()
