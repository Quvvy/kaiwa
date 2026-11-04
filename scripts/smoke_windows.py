"""Phone access on real Windows: the registry, power and tray parts other smokes fake.

Usage: python scripts/smoke_windows.py [dist\\Kaiwa]  (the path also checks the built app)
Restores what it changes.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["KAIWA_DATA_DIR"] = tempfile.mkdtemp(prefix="kaiwa-windows-smoke-")

import winreg  # noqa: E402

from kaiwa import phone_access  # noqa: E402
from kaiwa.desktop import keeper  # noqa: E402
from kaiwa.desktop.tray import Tray  # noqa: E402


def _check(ok: bool, label: str) -> None:
    print(("ok    " if ok else "FAIL  ") + label, flush=True)
    if not ok:
        raise SystemExit(f"smoke_windows failed: {label}")


def _run_value() -> str | None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, phone_access.RUN_KEY) as key:
        try:
            return winreg.QueryValueEx(key, phone_access.RUN_VALUE)[0]
        except FileNotFoundError:
            return None


before = _run_value()
os.environ["KAIWA_DESKTOP_CMD"] = r'"C:\Test\Kaiwa.exe" --background'
try:
    _check(phone_access._set_autostart(True) and _run_value() == os.environ["KAIWA_DESKTOP_CMD"], "startup entry written")
    _check(phone_access._set_autostart(False) is False and _run_value() is None, "startup entry removed")
finally:
    if before is not None:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, phone_access.RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, phone_access.RUN_VALUE, 0, winreg.REG_SZ, before)

power = phone_access._power_status()
_check(power is not None, f"power status reads {power}")
print(f"      on_battery={phone_access.on_battery()} has_battery={phone_access.has_battery()}", flush=True)

keeper._hold_awake(True)
keeper._hold_awake(False)
_check(True, "keep-awake call runs")

problems: list[str] = []
tray = Tray(on_open=lambda: None, on_quit=lambda: None, log=problems.append)
tray.start()
time.sleep(1)
tray.stop()
_check(not problems, f"tray starts and stops {problems}")

if len(sys.argv) > 1:
    internal = Path(sys.argv[1]) / "_internal"
    _check((internal / "PIL").is_dir(), "the built app includes Pillow for the tray")
    _check((Path(sys.argv[1]) / "runtime" / "Lib" / "site-packages" / "segno").is_dir(), "the runtime includes segno for QR codes")
    _check((Path(sys.argv[1]) / "static" / "phone.js").is_file(), "the built app includes the phone pages")
print("smoke_windows ok")
