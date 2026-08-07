from __future__ import annotations

from kaiwa.desktop.services import ServiceRegistry, read_preferred_tts_engine, start_kaiwa, start_tts_engine, stop_all


class Lifecycle:
    def __init__(self) -> None:
        self.registry = ServiceRegistry()
        self.running = False

    def start_session(self) -> None:
        if self.running:
            return
        engine = read_preferred_tts_engine()
        try:
            start_tts_engine(engine, self.registry)
            start_kaiwa(self.registry)
        except Exception:
            stop_all(self.registry)
            self.running = False
            raise
        self.running = True

    def stop_session(self) -> None:
        if not self.running and not self.registry.kaiwa.started_by_us and not self.registry.tts.started_by_us:
            # Still clear any we marked
            stop_all(self.registry)
            self.running = False
            return
        stop_all(self.registry)
        self.running = False
