from __future__ import annotations

from typing import Callable

KAIWA_URL = "http://127.0.0.1:8787"


def open_kaiwa_window(*, on_closed: Callable[[], None]) -> None:
    """Block until the window is closed, then call on_closed."""
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError(
            "pywebview is required. Install with: pip install -e \".[desktop]\""
        ) from exc

    closed = {"done": False}

    def _handle_closing() -> bool:
        # True = allow close. Services are stopped by on_closed after window exits.
        return True

    window = webview.create_window(
        "Kaiwa",
        KAIWA_URL,
        width=980,
        height=780,
        min_size=(640, 480),
        text_select=True,
    )
    window.events.closing += _handle_closing

    def _on_closed() -> None:
        if closed["done"]:
            return
        closed["done"] = True
        on_closed()

    window.events.closed += _on_closed
    webview.start()
    # If closed event didn't fire for some backends:
    if not closed["done"]:
        on_closed()
