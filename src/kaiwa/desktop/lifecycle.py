from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from kaiwa.desktop.services import (
    ServiceRegistry,
    engine_already_running,
    kaiwa_already_running,
    read_preferred_tts_engine,
    run_bootstrap,
    start_kaiwa,
    start_tts_engine,
    stop_all,
)

StatusFn = Callable[[str], None]
ProgressFn = Callable[[dict[str, Any]], None]


class Lifecycle:
    def __init__(self) -> None:
        self.registry = ServiceRegistry()
        self.running = False
        self.tts_error = ""

    def session_healthy(self) -> bool:
        """True when the Kaiwa API responds."""
        return kaiwa_already_running()

    def start_session(
        self,
        *,
        on_status: StatusFn | None = None,
        on_progress: ProgressFn | None = None,
    ) -> None:
        if self.running:
            if self.session_healthy():
                return
            self.stop_session()

        def status(msg: str) -> None:
            if on_status:
                try:
                    on_status(msg)
                except Exception:
                    pass

        def progress(row: dict[str, Any]) -> None:
            if on_progress:
                try:
                    on_progress(row)
                except Exception:
                    pass
            label = str(row.get("label") or "").strip()
            pct = row.get("pct")
            if label and pct is not None:
                try:
                    status(f"{label} ({int(pct)}%)")
                except (TypeError, ValueError):
                    status(label)
            elif label:
                status(label)

        try:
            status("Preparing models…")
            aivis = run_bootstrap(on_progress=progress)
            engine = read_preferred_tts_engine()
            status("Starting Kaiwa…")
            # The API is up in ~2 s; the voice engine takes 15-25 s. Open the window
            # as soon as the API answers and let the engine finish in the background:
            # the page shows "Voice engine starting…" until it's ready.
            tts_booting = not engine_already_running(engine)

            def tts_job() -> None:
                try:
                    start_tts_engine(
                        engine,
                        self.registry,
                        exe_path=aivis if engine == "aivisspeech" else None,
                    )
                except BaseException as exc:  # the page reports the engine as down
                    self.tts_error = str(exc)

            threading.Thread(target=tts_job, name="kaiwa-tts-start", daemon=True).start()
            start_kaiwa(self.registry, tts_booting=tts_booting)
        except Exception:
            stop_all(self.registry)
            self.running = False
            raise
        self.running = True

    def stop_session(self) -> None:
        stop_all(self.registry)
        self.running = False
