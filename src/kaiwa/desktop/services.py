from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import httpx

AivisOrVoicevox = Literal["aivisspeech", "voicevox"]

ENGINE_PORTS: dict[AivisOrVoicevox, int] = {
    "aivisspeech": 10101,
    "voicevox": 50021,
}

KAIWA_PORT = 8787

VOICEVOX_CANDIDATES = [
    Path.home()
    / "AppData/Local/Microsoft/WinGet/Packages/HiroshibaKazuyuki.VOICEVOX_Microsoft.Winget.Source_8wekyb3d8bbwe/VOICEVOX/vv-engine/run.exe",
]


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _exe_dir() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _resolve_path(path_str: str) -> Path:
    """Absolute path as-is; relative paths are relative to the exe/shell dir."""
    p = Path(path_str)
    if p.is_absolute():
        return p.resolve()
    return (_exe_dir() / p).resolve()


@lru_cache(maxsize=1)
def load_runtime_config() -> dict[str, str]:
    """Sidecar next to Kaiwa.exe (written by scripts/build_desktop.ps1)."""
    path = _exe_dir() / "Kaiwa.runtime.json"
    if not path.is_file():
        return {}
    try:
        # utf-8-sig: PowerShell Set-Content -Encoding UTF8 often writes a BOM.
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if v}
    except Exception:
        pass
    return {}


@lru_cache(maxsize=1)
def resolve_app_root() -> Path:
    """Install / repo root containing static/ (and optional tools/)."""
    cfg = load_runtime_config()
    for key in ("app_root", "repo_root"):
        raw = cfg.get(key)
        if not raw:
            continue
        root = _resolve_path(raw)
        if root.is_dir():
            return root

    env = (os.environ.get("KAIWA_ROOT") or "").strip()
    if env:
        root = Path(env)
        if root.is_dir():
            return root.resolve()

    exe = _exe_dir()
    if (exe / "static").is_dir():
        return exe

    # Source layout: src/kaiwa/desktop/services.py → repo root
    if not _is_frozen():
        return Path(__file__).resolve().parents[3]

    raise FileNotFoundError(
        "Kaiwa app root unknown. Rebuild with scripts/build_desktop.ps1 "
        "or set KAIWA_ROOT / Kaiwa.runtime.json (app_root)."
    )


def resolve_repo_root() -> Path:
    """Alias for resolve_app_root (legacy name used by desktop bootstrap)."""
    return resolve_app_root()


@lru_cache(maxsize=1)
def resolve_api_python() -> Path:
    """Python that can run `python -m kaiwa.app` — never the frozen shell exe."""
    env = (os.environ.get("KAIWA_PYTHON") or "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p.resolve()

    cfg = load_runtime_config()
    if cfg.get("python"):
        p = _resolve_path(cfg["python"])
        if p.is_file():
            return p

    bundled = _exe_dir() / "runtime" / "Scripts" / "python.exe"
    if bundled.is_file():
        return bundled.resolve()

    try:
        root = resolve_app_root()
        venv_py = root / ".venv" / "Scripts" / "python.exe"
        if venv_py.is_file():
            return venv_py.resolve()
    except FileNotFoundError:
        pass

    if not _is_frozen():
        return Path(sys.executable).resolve()

    raise FileNotFoundError(
        "No API Python found. Rebuild with scripts/build_desktop.ps1 "
        "(bundles runtime\\) or set KAIWA_PYTHON."
    )


def _root() -> Path:
    try:
        return resolve_app_root()
    except FileNotFoundError:
        if not _is_frozen():
            return Path(__file__).resolve().parents[3]
        cur = _exe_dir()
        for _ in range(6):
            if (cur / "static").is_dir() or (cur / "tools").is_dir() or (cur / ".venv").is_dir():
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent
        return _exe_dir()


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


def _aivis_candidates() -> list[Path]:
    from kaiwa.bootstrap import aivis_run_candidates_under_install

    root = _root()
    return [
        *aivis_run_candidates_under_install(),
        root / "tools/aivisspeech/engine/Windows-x64/run.exe",
        Path.home() / "AppData/Local/Programs/AivisSpeech/AivisSpeech-Engine/run.exe",
        Path.home() / "AppData/Local/Programs/AivisSpeech/engine/run.exe",
        Path.home() / "AppData/Local/AivisSpeech/engine/run.exe",
        Path("C:/Program Files/AivisSpeech/AivisSpeech-Engine/run.exe"),
        Path("C:/Program Files/AivisSpeech/engine/run.exe"),
        Path("C:/AivisSpeech/engine/run.exe"),
    ]


def find_engine(engine: AivisOrVoicevox) -> Path | None:
    candidates = _aivis_candidates() if engine == "aivisspeech" else VOICEVOX_CANDIDATES
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
        label = "AivisSpeech" if engine == "aivisspeech" else "VOICEVOX"
        raise FileNotFoundError(
            f"{label} TTS engine not found on disk. Relaunch Kaiwa so first-run "
            "setup can install it, or install the engine yourself."
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
            label = "AivisSpeech" if engine == "aivisspeech" else "VOICEVOX"
            raise RuntimeError(
                f"{label} TTS exited early (code {proc.returncode}). "
                "Close and relaunch Kaiwa."
            )
    label = "AivisSpeech" if engine == "aivisspeech" else "VOICEVOX"
    raise TimeoutError(
        f"Timed out waiting for {label} TTS on port {port}. Close and relaunch Kaiwa."
    )


def start_kaiwa(registry: ServiceRegistry) -> None:
    registry.kaiwa.port = KAIWA_PORT
    if kaiwa_already_running():
        registry.kaiwa.started_by_us = False
        registry.kaiwa.proc = None
        return

    python = resolve_api_python()
    root = resolve_app_root()
    child_env = os.environ.copy()
    child_env["KAIWA_ROOT"] = str(root)
    proc = subprocess.Popen(
        [str(python), "-m", "kaiwa.app"],
        cwd=str(root),
        env=child_env,
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
            raise RuntimeError(
                f"Kaiwa exited early (code {proc.returncode}). "
                "Close other copies of Kaiwa, then relaunch."
            )
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


def run_bootstrap(
    *,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
    skip_aivis: bool = False,
) -> None:
    """Run `python -m kaiwa.bootstrap ensure` via API Python; stream JSON progress."""
    python = resolve_api_python()
    root = resolve_app_root()
    cmd = [str(python), "-m", "kaiwa.bootstrap", "ensure"]
    if skip_aivis:
        cmd.append("--skip-aivis")
    child_env = os.environ.copy()
    child_env["KAIWA_ROOT"] = str(root)
    child_env["PYTHONUTF8"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        cmd,
        cwd=str(root),
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_creationflags(),
    )
    assert proc.stdout is not None
    err_chunks: list[str] = []

    def _drain_stderr() -> None:
        if proc.stderr is None:
            return
        for line in proc.stderr:
            err_chunks.append(line)

    err_thread = threading.Thread(target=_drain_stderr, name="kaiwa-boot-err", daemon=True)
    err_thread.start()

    for raw in proc.stdout:
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if on_progress:
            try:
                on_progress(row)
            except Exception:
                pass

    code = proc.wait()
    err_thread.join(timeout=2.0)
    if code != 0:
        detail = "".join(err_chunks).strip() or f"bootstrap exited with code {code}"
        # Prefix so friendly_boot_message can classify; full detail stays in the log.
        raise RuntimeError(f"bootstrap failed: {detail}")
