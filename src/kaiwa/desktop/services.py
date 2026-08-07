from __future__ import annotations

import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import httpx

ROOT = Path(__file__).resolve().parents[3]  # src/kaiwa/desktop -> repo root

AivisOrVoicevox = Literal["aivisspeech", "voicevox"]

AIVIS_CANDIDATES = [
    ROOT / "tools/aivisspeech/engine/Windows-x64/run.exe",
    Path.home() / "AppData/Local/Programs/AivisSpeech/AivisSpeech-Engine/run.exe",
    Path.home() / "AppData/Local/Programs/AivisSpeech/engine/run.exe",
    Path.home() / "AppData/Local/AivisSpeech/engine/run.exe",
    Path("C:/Program Files/AivisSpeech/AivisSpeech-Engine/run.exe"),
    Path("C:/Program Files/AivisSpeech/engine/run.exe"),
    Path("C:/AivisSpeech/engine/run.exe"),
]

VOICEVOX_CANDIDATES = [
    Path.home()
    / "AppData/Local/Microsoft/WinGet/Packages/HiroshibaKazuyuki.VOICEVOX_Microsoft.Winget.Source_8wekyb3d8bbwe/VOICEVOX/vv-engine/run.exe",
]

ENGINE_PORTS: dict[AivisOrVoicevox, int] = {
    "aivisspeech": 10101,
    "voicevox": 50021,
}

KAIWA_PORT = 8787


@dataclass
class ManagedProcess:
    name: str
    proc: subprocess.Popen | None = None
    started_by_us: bool = False
    port: int | None = None


@dataclass
class ServiceRegistry:
    tts: ManagedProcess = field(default_factory=lambda: ManagedProcess("tts"))
    kaiwa: ManagedProcess = field(default_factory=lambda: ManagedProcess("kaiwa", port=KAIWA_PORT))


def _creationflags() -> int:
    if sys.platform == "win32":
        # New process group so we can taskkill /T; hide console for python child.
        flags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return flags
    return 0


def port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        r = httpx.get(url, timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False


def find_engine(engine: AivisOrVoicevox) -> Path | None:
    candidates = AIVIS_CANDIDATES if engine == "aivisspeech" else VOICEVOX_CANDIDATES
    for path in candidates:
        if path.exists():
            return path
    return None


def engine_base_url(engine: AivisOrVoicevox) -> str:
    return f"http://127.0.0.1:{ENGINE_PORTS[engine]}"


def engine_already_running(engine: AivisOrVoicevox) -> bool:
    return http_ok(f"{engine_base_url(engine)}/version", timeout=1.5)


def kaiwa_already_running() -> bool:
    return http_ok(f"http://127.0.0.1:{KAIWA_PORT}/api/health", timeout=1.5)


def read_preferred_tts_engine() -> AivisOrVoicevox:
    """Read active profile prefs without loading Whisper/FastAPI stack if possible."""
    try:
        from kaiwa.prefs import load_prefs

        prefs = load_prefs()
        eng = (prefs.tts_engine or "aivisspeech").strip().lower()
        if eng in {"aivisspeech", "voicevox"}:
            return eng  # type: ignore[return-value]
    except Exception:
        pass
    return "aivisspeech"


def start_tts_engine(engine: AivisOrVoicevox, registry: ServiceRegistry) -> None:
    port = ENGINE_PORTS[engine]
    registry.tts.name = engine
    registry.tts.port = port

    if engine_already_running(engine):
        registry.tts.started_by_us = False
        registry.tts.proc = None
        return

    exe = find_engine(engine)
    if exe is None:
        raise FileNotFoundError(
            f"{engine} engine not found on disk. Install it, then retry Open."
        )

    proc = subprocess.Popen(
        [str(exe)],
        cwd=str(exe.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_creationflags(),
    )
    registry.tts.proc = proc
    registry.tts.started_by_us = True

    url = f"{engine_base_url(engine)}/version"
    for _ in range(45):
        time.sleep(1)
        if http_ok(url):
            return
        if proc.poll() is not None:
            raise RuntimeError(f"{engine} exited early (code {proc.returncode})")
    raise TimeoutError(f"Timed out waiting for {engine} on port {port}")


def start_kaiwa(registry: ServiceRegistry) -> None:
    registry.kaiwa.port = KAIWA_PORT
    if kaiwa_already_running():
        registry.kaiwa.started_by_us = False
        registry.kaiwa.proc = None
        return

    python = sys.executable
    proc = subprocess.Popen(
        [python, "-m", "kaiwa.app"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_creationflags(),
    )
    registry.kaiwa.proc = proc
    registry.kaiwa.started_by_us = True

    url = f"http://127.0.0.1:{KAIWA_PORT}/api/health"
    for _ in range(90):
        time.sleep(1)
        if http_ok(url):
            return
        if proc.poll() is not None:
            raise RuntimeError(f"Kaiwa exited early (code {proc.returncode})")
    raise TimeoutError("Timed out waiting for Kaiwa on port 8787")


def _terminate_pid(pid: int) -> None:
    if pid <= 0:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            import os
            import signal

            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


def stop_managed(mp: ManagedProcess) -> None:
    if not mp.started_by_us:
        mp.proc = None
        return
    if mp.proc is not None and mp.proc.poll() is None:
        _terminate_pid(mp.proc.pid)
    mp.proc = None
    mp.started_by_us = False


def stop_all(registry: ServiceRegistry) -> None:
    stop_managed(registry.kaiwa)
    stop_managed(registry.tts)
