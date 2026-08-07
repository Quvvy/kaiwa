from __future__ import annotations

import queue
import threading
import time

from kaiwa.desktop.lifecycle import Lifecycle
from kaiwa.desktop.window import open_kaiwa_window

# Windows often activates the tray icon (default menu item = Open) when the
# webview closes / loses focus. Ignore those for a short window.
_REOPEN_COOLDOWN_S = 2.5


def _make_icon():
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, size - 5, size - 5), fill=(32, 140, 140, 255))
    draw.ellipse((18, 18, size - 19, size - 19), fill=(240, 248, 248, 255))
    return img


def _drain_opens(commands: queue.Queue[str]) -> str | None:
    """Drop queued Open commands. Return Quit if seen (re-queue for main loop)."""
    quit_seen = False
    while True:
        try:
            cmd = commands.get_nowait()
        except queue.Empty:
            break
        if cmd == "quit":
            quit_seen = True
        # drop "open" and anything else unexpected
    if quit_seen:
        commands.put("quit")
        return "quit"
    return None


def main() -> None:
    try:
        import pystray
        from pystray import MenuItem as Item
    except ImportError as exc:
        raise SystemExit(
            'Desktop deps missing. Run: .\\.venv\\Scripts\\pip install -e ".[desktop]"'
        ) from exc

    lifecycle = Lifecycle()
    commands: queue.Queue[str] = queue.Queue()
    icon_holder: dict = {"icon": None}
    last_closed_at = 0.0

    def request_open(icon=None, item=None) -> None:
        # Ignore Open while a session is up, and ignore the post-close tray bounce.
        if lifecycle.running:
            return
        if time.monotonic() - last_closed_at < _REOPEN_COOLDOWN_S:
            return
        commands.put("open")

    def request_quit(icon=None, item=None) -> None:
        commands.put("quit")

    menu = pystray.Menu(
        Item("Open Kaiwa", request_open, default=True),
        Item("Quit", request_quit),
    )
    icon = pystray.Icon("kaiwa", _make_icon(), "Kaiwa", menu)
    icon_holder["icon"] = icon

    tray_thread = threading.Thread(target=icon.run, name="kaiwa-tray", daemon=True)
    tray_thread.start()

    opening = False
    while True:
        cmd = commands.get()
        if cmd == "quit":
            try:
                lifecycle.stop_session()
            except Exception:
                pass
            try:
                icon.stop()
            except Exception:
                pass
            break
        if cmd == "open":
            if opening or lifecycle.running:
                continue
            if time.monotonic() - last_closed_at < _REOPEN_COOLDOWN_S:
                continue
            opening = True
            try:
                lifecycle.start_session()
                # webview must run on this (main) thread on Windows
                open_kaiwa_window(on_closed=lifecycle.stop_session)
            except Exception as exc:
                try:
                    lifecycle.stop_session()
                except Exception:
                    pass
                try:
                    icon.notify(str(exc)[:200], "Kaiwa")
                except Exception:
                    print(f"Kaiwa open failed: {exc}")
            finally:
                last_closed_at = time.monotonic()
                # Let focus settle, then drop Open events fired by the close.
                time.sleep(0.35)
                _drain_opens(commands)
                opening = False


if __name__ == "__main__":
    main()
