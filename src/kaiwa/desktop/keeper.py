"""Windows: what systemd does on Linux, while phone access is on.

Keeps the PC from idling to sleep on mains power and restarts a dead server. Also
carries requests from outside this process (show the window, quit for an update).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from kaiwa import phone_access

_TICK_S = 1
_CHECK_EVERY_TICKS = 10
_FAILED_CHECKS_LIMIT = 6
_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001


def _hold_awake(hold: bool) -> None:
    """The flag belongs to the calling thread, and clears if that thread ends."""
    try:
        import ctypes

        flags = _ES_CONTINUOUS | (_ES_SYSTEM_REQUIRED if hold else 0)
        ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(flags))
    except Exception:
        pass


class Keeper:
    def __init__(
        self,
        *,
        healthy: Callable[[], bool],
        restart: Callable[[], None],
        show_window: Callable[[], None],
        quit_app: Callable[[], None],
        log: Callable[[str], None],
    ) -> None:
        self._healthy = healthy
        self._restart = restart
        self._show_window = show_window
        self._quit_app = quit_app
        self._log = log
        self._stop = threading.Event()
        self.server_expected = False

    def start(self) -> None:
        threading.Thread(target=self._run, name="kaiwa-keeper", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _check(self, failed: int) -> int:
        enabled = phone_access.is_enabled()
        _hold_awake(enabled and not phone_access.on_battery())
        if not (enabled and self.server_expected):
            return 0
        failed = 0 if self._healthy() else failed + 1
        if failed < _FAILED_CHECKS_LIMIT:
            return failed
        self._log("the server stopped answering; restarting")
        try:
            self._restart()
        except Exception as exc:
            self._log(f"restart failed: {exc}")
        return 0

    def _run(self) -> None:
        ticks = 0
        failed = 0
        while not self._stop.wait(_TICK_S):
            if phone_access.take_signal("show"):
                self._show_window()
            if phone_access.take_signal("quit"):
                self._log("quitting for an update")
                self._quit_app()
                break
            if ticks % _CHECK_EVERY_TICKS == 0:
                failed = self._check(failed)
            ticks += 1
        _hold_awake(False)
