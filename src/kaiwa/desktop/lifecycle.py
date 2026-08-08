from __future__ import annotations

from collections.abc import Callable

from kaiwa.desktop.services import (
    ServiceRegistry,
    kaiwa_already_running,
    read_preferred_tts_engine,
    start_kaiwa,
    start_tts_engine,
    stop_all,
)

StatusFn = Callable[[str], None]


class Lifecycle:
    def __init__(self) -> None:
        self.registry = ServiceRegistry()
        self.running = False

    def session_healthy(self) -> bool:
        """True when the Kaiwa API responds."""
        return kaiwa_already_running()

    def start_session(self, *, on_status: StatusFn | None = None) -> None:
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

        engine = read_preferred_tts_engine()
        try:
            status(f"Starting TTS ({engine})…")
            start_tts_engine(engine, self.registry)
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
