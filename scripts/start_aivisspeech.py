from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import httpx

# Common Windows install / extract locations for AivisSpeech Engine.
ENGINE_CANDIDATES = [
    # Kaiwa local install (scripts/install path)
    Path(__file__).resolve().parents[1] / "tools/aivisspeech/engine/Windows-x64/run.exe",
    Path.home() / "AppData/Local/Programs/AivisSpeech/AivisSpeech-Engine/run.exe",
    Path.home() / "AppData/Local/Programs/AivisSpeech/engine/run.exe",
    Path.home() / "AppData/Local/AivisSpeech/engine/run.exe",
    Path("C:/Program Files/AivisSpeech/AivisSpeech-Engine/run.exe"),
    Path("C:/Program Files/AivisSpeech/engine/run.exe"),
    Path("C:/AivisSpeech/engine/run.exe"),
]


def find_engine() -> Path | None:
    for path in ENGINE_CANDIDATES:
        if path.exists():
            return path
    return None


def main() -> None:
    base = "http://127.0.0.1:10101"
    try:
        version = httpx.get(f"{base}/version", timeout=2.0).text
        print(f"AivisSpeech already running: {version}")
        return
    except Exception:
        pass

    engine = find_engine()
    if engine is None:
        print("AivisSpeech engine not found on disk.")
        print("Install/download from https://aivis-project.com/ and start the app,")
        print("or place the engine so scripts/start_aivisspeech.py can find run.exe.")
        print("Default API: http://127.0.0.1:10101")
        raise SystemExit(1)

    print(f"Starting {engine}")
    subprocess.Popen(
        [str(engine)],
        cwd=str(engine.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(45):
        time.sleep(1)
        try:
            version = httpx.get(f"{base}/version", timeout=2.0).text
            print(f"AivisSpeech ready: {version}")
            return
        except Exception:
            continue
    print("Timed out waiting for AivisSpeech on port 10101")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
