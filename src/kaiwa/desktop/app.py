from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from kaiwa.desktop.icons import set_windows_app_id, window_icon_path
from kaiwa.desktop.keeper import Keeper
from kaiwa.desktop.instance import apply_portable_mode, claim_single_instance
from kaiwa.desktop.lifecycle import Lifecycle
from kaiwa.desktop.ptt import PttController
from kaiwa.desktop.tray import Tray
from kaiwa.desktop.window import KAIWA_URL, error_html, friendly_boot_message, splash_html
from kaiwa import phone_access

SERVICE_WAIT_S = 120


def _bootstrap_frozen_paths() -> None:
    """Point kaiwa.config.ROOT at the install/app root when running as Kaiwa.exe."""
    if not getattr(sys, "frozen", False):
        return
    try:
        from kaiwa.desktop.services import resolve_app_root
        import kaiwa.config as cfg

        cfg.ROOT = resolve_app_root()
    except Exception:
        pass


def _log_path() -> Path:
    """Always prefer AppData — Program Files next to Kaiwa.exe is not writable."""
    try:
        from kaiwa.secrets_store import user_data_dir

        return user_data_dir() / "Kaiwa.desktop.log"
    except Exception:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent / "Kaiwa.desktop.log"
        return Path.cwd() / "Kaiwa.desktop.log"


def _log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}\n"
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    try:
        print(f"Kaiwa: {msg}", flush=True)
    except Exception:
        pass


def _windows_is_shutting_down() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.user32.GetSystemMetrics(0x2000))  # SM_SHUTTINGDOWN
    except Exception:
        return False


def _stop_on_signals(on_closed) -> None:  # noqa: ANN001
    """Linux: shut the API and voice engine down on SIGTERM/SIGHUP/SIGINT (logout, kill).

    The GUI loop doesn't run Python signal handlers promptly, so the C-level handler
    writes to a wakeup socket and a watcher thread does the cleanup.
    """
    if sys.platform == "win32":
        return
    import os
    import signal
    import socket

    reader, writer = socket.socketpair()
    writer.setblocking(False)
    signal.set_wakeup_fd(writer.fileno())
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(sig, lambda *_: None)

    def watch() -> None:
        sig = reader.recv(1)
        _log(f"signal {sig[0] if sig else '?'} → shutting down")
        on_closed()
        os._exit(0)

    threading.Thread(target=watch, name="kaiwa-signals", daemon=True).start()
    _stop_on_signals.keep = (reader, writer)  # type: ignore[attr-defined]


def main() -> None:
    try:
        import webview
    except ImportError as exc:
        raise SystemExit(
            'Desktop deps missing. Run: .\\.venv\\Scripts\\pip install -e ".[desktop]"'
            if sys.platform == "win32"
            else 'Desktop deps missing. Run: .venv/bin/pip install -e ".[desktop]"'
        ) from exc

    portable = apply_portable_mode()
    if not claim_single_instance():
        # Kaiwa is already open (e.g. clicked again on the taskbar): the open
        # window was brought forward instead of starting a second copy.
        return
    _bootstrap_frozen_paths()
    set_windows_app_id()
    _log(f"log file: {_log_path()}")
    _log("main start" + (f" (portable, data in {portable})" if portable else ""))

    lifecycle = Lifecycle()
    ptt = PttController(api_base=KAIWA_URL, log=_log)
    windows = sys.platform == "win32"
    # Started with Windows for phone access: run without showing anything.
    hidden = {"yes": windows and "--background" in sys.argv}
    quitting = {"yes": False}
    for name in ("show", "quit"):
        phone_access.take_signal(name)  # left over from a crash
    closed = {"done": False}
    boot_started = {"yes": False}
    window_holder: dict = {"win": None}
    status_lock = threading.Lock()

    def on_closed() -> None:
        if closed["done"]:
            return
        closed["done"] = True
        _log("window closed → stop ptt + session")
        keeper.stop()
        tray.stop()
        try:
            ptt.stop()
        except Exception as exc:
            _log(f"ptt stop error: {exc}")
        try:
            lifecycle.stop_session()
        except Exception as exc:
            _log(f"stop_session error: {exc}")
        try:
            phone_access.after_window_closed()
        except Exception as exc:
            _log(f"phone service hand-over error: {exc}")

    def start_ptt() -> None:
        """Only with the window showing: a key held with Kaiwa "closed" mustn't record."""
        if hidden["yes"]:
            return
        try:
            ptt.start()
        except Exception as exc:
            _log(f"ptt start error: {exc}")

    def show_window() -> None:
        win = window_holder.get("win")
        if win is None or closed["done"]:
            return
        hidden["yes"] = False
        try:
            win.show()
        except Exception as exc:
            _log(f"show window error: {exc}")
        start_ptt()

    def quit_app() -> None:
        quitting["yes"] = True
        win = window_holder.get("win")
        if win is None:
            return
        threading.Thread(target=win.destroy, name="kaiwa-quit", daemon=True).start()

    def on_closing():  # noqa: ANN202
        """Windows, phone access on: closing the window leaves Kaiwa running in the tray."""
        if not windows or quitting["yes"] or _windows_is_shutting_down() or not phone_access.is_enabled():
            return None
        _log("window closed → still running for the phone")
        hidden["yes"] = True
        tray.start()
        ptt.stop()
        win = window_holder["win"]
        # Not from inside this event: pywebview's window thread is busy running it.
        threading.Thread(target=win.hide, name="kaiwa-hide", daemon=True).start()
        return False

    def restart_server() -> None:
        lifecycle.start_session(on_status=_log)
        win = window_holder.get("win")
        if win is not None:
            win.load_url(KAIWA_URL)

    tray = Tray(on_open=show_window, on_quit=quit_app, log=_log)
    keeper = Keeper(
        healthy=lifecycle.session_healthy,
        restart=restart_server,
        show_window=show_window,
        quit_app=quit_app,
        log=_log,
    )

    def set_status(msg: str, pct: int | None = None) -> None:
        """Update splash text without evaluate_js (avoids Edge thread deadlocks)."""
        _log(f"status: {msg}" + (f" ({pct}%)" if pct is not None else ""))
        win = window_holder.get("win")
        if win is None or closed["done"]:
            return

        def _apply() -> None:
            with status_lock:
                if closed["done"]:
                    return
                try:
                    win.load_html(splash_html(msg, pct=pct))
                except Exception as exc:
                    _log(f"load_html status failed: {exc}")

        threading.Thread(target=_apply, name="kaiwa-status", daemon=True).start()

    def on_boot_progress(row: dict) -> None:
        label = str(row.get("label") or "").strip() or "Preparing…"
        pct_raw = row.get("pct")
        pct: int | None
        try:
            pct = int(pct_raw) if pct_raw is not None else None
        except (TypeError, ValueError):
            pct = None
        set_status(label, pct)

    def show_error(exc: BaseException) -> None:
        friendly = friendly_boot_message(exc)
        _log(f"error: {exc!r}")
        _log(f"error (friendly): {friendly}")
        win = window_holder.get("win")
        if win is None:
            return
        try:
            win.load_html(error_html(friendly))
        except Exception as e2:
            _log(f"load_html error page failed: {e2}")

    def attach_to_service() -> None:
        """With phone access on, the service owns the server: wait for it rather than
        start a second one on the same port."""
        if not (phone_access.is_enabled() and phone_access.service_supported()):
            return
        if lifecycle.session_healthy():
            return
        set_status("Starting Kaiwa…")
        if not phone_access.start_service():
            _log("couldn't start the phone service; starting Kaiwa directly")
            return
        deadline = time.monotonic() + SERVICE_WAIT_S
        while time.monotonic() < deadline:
            if lifecycle.session_healthy():
                return
            time.sleep(0.5)
        raise RuntimeError(
            "Kaiwa's background service didn't start. "
            "Details: journalctl --user -u kaiwa-phone"
        )

    def boot() -> None:
        _log("boot begin")
        try:
            attach_to_service()
            if lifecycle.session_healthy():
                _log("API already healthy → load UI")
                set_status("Opening Kaiwa…")
                time.sleep(0.2)
                win = window_holder["win"]
                assert win is not None
                win.load_url(KAIWA_URL)
                _log("load_url done (existing API)")
                keeper.server_expected = True
                start_ptt()
                return

            lifecycle.start_session(on_status=set_status, on_progress=on_boot_progress)
            _log("start_session ok → load UI")
            set_status("Opening window…")
            time.sleep(0.2)
            win = window_holder["win"]
            assert win is not None
            win.load_url(KAIWA_URL)
            _log("load_url done")
            keeper.server_expected = True
            start_ptt()
        except Exception as exc:
            _log(f"boot failed: {exc!r}")
            try:
                lifecycle.stop_session()
            except Exception:
                pass
            show_error(exc)

    def start_boot() -> None:
        if boot_started["yes"] or closed["done"]:
            return
        boot_started["yes"] = True
        _log("scheduling boot thread")
        threading.Thread(target=boot, name="kaiwa-boot", daemon=True).start()

    window = webview.create_window(
        "Kaiwa",
        html=splash_html("Starting…"),
        width=980,
        height=780,
        min_size=(640, 480),
        text_select=True,
        background_color="#12141a",
        hidden=hidden["yes"],
    )
    window_holder["win"] = window
    window.events.closed += on_closed
    if windows:
        window.events.closing += on_closing
        keeper.start()
        if hidden["yes"]:
            tray.start()
    _stop_on_signals(on_closed)
    window.events.shown += start_boot
    window.events.loaded += start_boot

    icon = window_icon_path()
    _log("webview.start")
    # Also pass boot to start() as a third trigger (some backends skip shown).
    if icon is not None:
        webview.start(start_boot, icon=str(icon))
    else:
        webview.start(start_boot)

    if not closed["done"]:
        on_closed()
    _log("main exit")


if __name__ == "__main__":
    main()
