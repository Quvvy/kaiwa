"""Kaiwa with no window, for the phone-access service (see kaiwa.phone_access).

Same start-up as the desktop app; the window, when opened, just attaches to it.
"""

from __future__ import annotations

import signal
import sys
import time

from kaiwa.desktop.lifecycle import Lifecycle

_CHECK_EVERY_S = 10
_FAILED_CHECKS_LIMIT = 6


def _log(msg: str) -> None:
    print(f"Kaiwa: {msg}", flush=True)


def main() -> None:
    lifecycle = Lifecycle()

    def stop(*_: object) -> None:
        _log("stopping")
        lifecycle.stop_session()
        sys.exit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    lifecycle.start_session(on_status=_log)
    _log("ready")

    # Exit on a dead server and systemd starts everything again (Restart=on-failure).
    failed = 0
    while True:
        time.sleep(_CHECK_EVERY_S)
        api = lifecycle.registry.kaiwa.proc
        failed = 0 if lifecycle.session_healthy() else failed + 1
        if (api is not None and api.poll() is not None) or failed >= _FAILED_CHECKS_LIMIT:
            _log("the server stopped answering; restarting")
            lifecycle.stop_session()
            sys.exit(1)


if __name__ == "__main__":
    main()
