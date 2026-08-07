from __future__ import annotations

"""Thin CLI wrappers — shared logic lives in kaiwa.desktop.services."""

from kaiwa.desktop.services import engine_already_running, find_engine, start_tts_engine, ServiceRegistry


def main() -> None:
    import sys

    engine = "aivisspeech"
    if engine_already_running(engine):
        from kaiwa.desktop.services import engine_base_url
        import httpx

        version = httpx.get(f"{engine_base_url(engine)}/version", timeout=2.0).text
        print(f"AivisSpeech already running: {version}")
        return

    if find_engine(engine) is None:
        print("AivisSpeech engine not found on disk.")
        print("Install/download from https://aivis-project.com/ and start the app,")
        print("or place the engine so scripts/start_aivisspeech.py can find run.exe.")
        print("Default API: http://127.0.0.1:10101")
        raise SystemExit(1)

    reg = ServiceRegistry()
    try:
        start_tts_engine(engine, reg)
        print("AivisSpeech ready")
    except Exception as exc:
        print(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
