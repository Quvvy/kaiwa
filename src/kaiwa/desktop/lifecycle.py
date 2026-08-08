from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kaiwa.desktop.services import (
    ServiceRegistry,
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
            status(f"Starting TTS ({engine})…")
            start_tts_engine(
                engine,
                self.registry,
                exe_path=aivis if engine == "aivisspeech" else None,
            )
            status("Starting Kaiwa…")
            start_kaiwa(self.registry)
        except Exception:
            stop_all(self.registry)
            self.running = False
            raise
        self.running = True

    def stop_session(self) -> None:
        stop_all(self.registry)
        self.running = False
