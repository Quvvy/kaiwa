from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import httpx

ENGINE_CANDIDATES = [
    Path.home()
    / "AppData/Local/Microsoft/WinGet/Packages/HiroshibaKazuyuki.VOICEVOX_Microsoft.Winget.Source_8wekyb3d8bbwe/VOICEVOX/vv-engine/run.exe",
]


def find_engine() -> Path | None:
    for path in ENGINE_CANDIDATES:
        if path.exists():
            return path
    return None


def main() -> None:
    base = "http://127.0.0.1:50021"
    try:
        version = httpx.get(f"{base}/version", timeout=2.0).text
        print(f"VOICEVOX already running: {version}")
        return
    except Exception:
        pass

    engine = find_engine()
    if engine is None:
        print("VOICEVOX engine not found. Install with:")
        print("  winget install --id HiroshibaKazuyuki.VOICEVOX")
        raise SystemExit(1)

    print(f"Starting {engine}")
    subprocess.Popen(
        [str(engine)],
        cwd=str(engine.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        time.sleep(1)
        try:
            version = httpx.get(f"{base}/version", timeout=2.0).text
            print(f"VOICEVOX ready: {version}")
            return
        except Exception:
            continue
    print("Timed out waiting for VOICEVOX on port 50021")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
