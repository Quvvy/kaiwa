from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from kaiwa.desktop.icons import set_windows_app_id, window_icon_path
from kaiwa.desktop.lifecycle import Lifecycle
from kaiwa.desktop.ptt import PttController
from kaiwa.desktop.window import KAIWA_URL, error_html, friendly_boot_message, splash_html


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
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "Kaiwa.desktop.log"
    try:
        from kaiwa.secrets_store import user_data_dir

        return user_data_dir() / "Kaiwa.desktop.log"
    except Exception:
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


def main() -> None:
    try:
        import webview
    except ImportError as exc:
        raise SystemExit(
            'Desktop deps missing. Run: .\\.venv\\Scripts\\pip install -e ".[desktop]"'
        ) from exc

    _bootstrap_frozen_paths()
    set_windows_app_id()
    _log("main start")

    lifecycle = Lifecycle()
    ptt = PttController(api_base=KAIWA_URL, log=_log)
    closed = {"done": False}
    boot_started = {"yes": False}
    window_holder: dict = {"win": None}
    status_lock = threading.Lock()

    def on_closed() -> None:
        if closed["done"]:
            return
        closed["done"] = True
        _log("window closed → stop ptt + session")
        try:
            ptt.stop()
        except Exception as exc:
            _log(f"ptt stop error: {exc}")
        try:
            lifecycle.stop_session()
        except Exception as exc:
            _log(f"stop_session error: {exc}")

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

    def boot() -> None:
        _log("boot begin")
        try:
            if lifecycle.session_healthy():
                _log("API already healthy → load UI")
                set_status("Opening Kaiwa…")
                time.sleep(0.2)
                win = window_holder["win"]
                assert win is not None
                win.load_url(KAIWA_URL)
                _log("load_url done (existing API)")
                try:
                    ptt.start()
                except Exception as exc:
                    _log(f"ptt start error: {exc}")
                return

            lifecycle.start_session(on_status=set_status, on_progress=on_boot_progress)
            _log("start_session ok → load UI")
            set_status("Opening window…")
            time.sleep(0.2)
            win = window_holder["win"]
            assert win is not None
            win.load_url(KAIWA_URL)
            _log("load_url done")
            try:
                ptt.start()
            except Exception as exc:
                _log(f"ptt start error: {exc}")
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
    )
    window_holder["win"] = window
    window.events.closed += on_closed
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
