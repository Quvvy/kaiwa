from __future__ import annotations

"""Thin CLI wrappers — shared logic lives in kaiwa.desktop.services."""

from kaiwa.desktop.services import engine_already_running, find_engine, start_tts_engine, ServiceRegistry


def main() -> None:
    engine = "voicevox"
    if engine_already_running(engine):
        from kaiwa.desktop.services import engine_base_url
        import httpx

        version = httpx.get(f"{engine_base_url(engine)}/version", timeout=2.0).text
        print(f"VOICEVOX already running: {version}")
        return

    if find_engine(engine) is None:
        print("VOICEVOX engine not found. Install with:")
        print("  winget install --id HiroshibaKazuyuki.VOICEVOX")
        raise SystemExit(1)

    reg = ServiceRegistry()
    try:
        start_tts_engine(engine, reg)
        print("VOICEVOX ready")
    except Exception as exc:
        print(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
