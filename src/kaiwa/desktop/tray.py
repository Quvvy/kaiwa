"""Windows: the tray icon that stays while Kaiwa runs with its window closed."""

from __future__ import annotations

import threading
from collections.abc import Callable

from kaiwa.desktop.icons import asset_path


class Tray:
    def __init__(self, *, on_open: Callable[[], None], on_quit: Callable[[], None], log: Callable[[str], None]) -> None:
        self._on_open = on_open
        self._on_quit = on_quit
        self._log = log
        self._icon = None

    def start(self) -> None:
        if self._icon is not None:
            return
        try:
            import pystray
            from PIL import Image

            self._icon = pystray.Icon(
                "Kaiwa",
                Image.open(asset_path("kaiwa.ico")),
                "Kaiwa: running for your phone",
                menu=pystray.Menu(
                    pystray.MenuItem("Open Kaiwa", lambda: self._on_open(), default=True),
                    pystray.MenuItem("Quit Kaiwa", lambda: self._on_quit()),
                ),
            )
            threading.Thread(target=self._icon.run, name="kaiwa-tray", daemon=True).start()
        except Exception as exc:
            self._icon = None
            self._log(f"tray start error: {exc}")

    def stop(self) -> None:
        icon, self._icon = self._icon, None
        if icon is None:
            return
        try:
            icon.stop()
        except Exception as exc:
            self._log(f"tray stop error: {exc}")
