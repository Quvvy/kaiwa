"""Keep the voice engine running.

AivisSpeech has been seen to crash mid-session and stay down, which leaves a
listening app silent until Kaiwa is restarted. The desktop shell starts the
engine once at launch; this watches it from the API server and starts it again
when it stops answering, with a cooldown and an hourly cap so a broken install
doesn't relaunch forever. The page can also ask for a restart ("Restart voice").

A relaunched engine is a child of the API process, so closing Kaiwa (which ends
the API's process tree) closes it too.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from typing import Any

_log = logging.getLogger("kaiwa.engine_watchdog")

FIRST_CHECK_S = 60      # leave the launch-time start to the desktop shell
CHECK_EVERY_S = 10
COOLDOWN_S = 45         # between automatic restarts
MAX_PER_HOUR = 5
READY_TIMEOUT_S = 60

_lock = threading.Lock()
_status: dict[str, Any] = {"state": "unknown", "engine": "", "restarts": 0, "error": ""}
_history: list[float] = []   # times of automatic restarts
_last_try = 0.0
_started = False


def _engine() -> str:
    from kaiwa.prefs import load_prefs

    eng = (load_prefs().tts_engine or "aivisspeech").strip().lower()
    return eng if eng in ("aivisspeech", "voicevox") else "aivisspeech"


def status() -> dict[str, Any]:
    from kaiwa.desktop import services

    eng = _engine()
    if _status["state"] != "restarting":
        _status["state"] = "up" if services.engine_already_running(eng) else "down"  # type: ignore[arg-type]
    _status["engine"] = eng
    return dict(_status)


def restart(*, manual: bool = False) -> dict[str, Any]:
    """Start the engine if it isn't answering. Returns the status afterwards. Never raises."""
    global _last_try
    from kaiwa.desktop import services

    eng = _engine()
    if not _lock.acquire(blocking=False):
        return dict(_status)  # a restart is already under way
    try:
        if services.engine_already_running(eng):  # type: ignore[arg-type]
            _status.update(state="up", engine=eng, error="")
            return dict(_status)
        now = time.time()
        if not manual:
            _history[:] = [t for t in _history if now - t < 3600]
            if now - _last_try < COOLDOWN_S or len(_history) >= MAX_PER_HOUR:
                return dict(_status)
            _history.append(now)
        _last_try = now
        exe = services.find_engine(eng)  # type: ignore[arg-type]
        if exe is None:
            _status.update(state="missing", engine=eng, error="The voice engine isn't installed. Relaunch Kaiwa to set it up.")
            return dict(_status)
        _status.update(state="restarting", engine=eng, error="")
        _log.info("voice engine down; starting %s", exe)
        try:
            subprocess.Popen([str(exe)], cwd=str(exe.parent), stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, creationflags=services._creationflags())
        except OSError as exc:
            _status.update(state="down", error=f"Couldn't start the voice engine: {exc}")
            return dict(_status)
        deadline = time.time() + READY_TIMEOUT_S
        while time.time() < deadline:
            time.sleep(0.5)
            if services.engine_already_running(eng):  # type: ignore[arg-type]
                _status["restarts"] += 1
                _status.update(state="up", error="")
                _rewarm()
                return dict(_status)
        _status.update(state="down", error="The voice engine didn't come back. Restart Kaiwa.")
        return dict(_status)
    except Exception as exc:  # noqa: BLE001 - the watchdog must never take the API down
        _status.update(state="down", error=str(exc))
        return dict(_status)
    finally:
        _lock.release()


def _rewarm() -> None:
    """A fresh engine's first synthesis is slow; pay it now, and refill the lesson cache."""
    try:
        from kaiwa import tts
        from kaiwa.config import get_settings
        from kaiwa.course import prerender
        from kaiwa.prefs import load_prefs

        settings = get_settings()
        prefs = load_prefs()
        tts.synthesize(settings, "こんにちは。", speaker_id=prefs.voicevox_speaker_id, engine=prefs.tts_engine)
        prerender.start(settings)
    except Exception as exc:  # noqa: BLE001
        _log.info("rewarm after restart failed: %s", exc)


def _loop() -> None:
    time.sleep(FIRST_CHECK_S)
    while True:
        try:
            if status()["state"] == "down":
                restart()
        except Exception as exc:  # noqa: BLE001
            _log.info("watchdog check failed: %s", exc)
        time.sleep(CHECK_EVERY_S)


def start() -> None:
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=_loop, name="kaiwa-tts-watchdog", daemon=True).start()
