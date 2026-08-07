from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.config import get_settings
from kaiwa import tts


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test local TTS (AivisSpeech or VOICEVOX).")
    parser.add_argument(
        "--engine",
        choices=["aivisspeech", "voicevox"],
        default=None,
        help="Override TTS engine (default: settings TTS_ENGINE)",
    )
    args = parser.parse_args()

    settings = get_settings()
    engine = tts.normalize_engine(args.engine or settings.tts_engine, settings.tts_engine)
    base = tts.engine_base_url(settings, engine)
    speaker = tts.engine_default_speaker(settings, engine)
    label = tts.ENGINE_LABELS[engine]

    out = ROOT / "recordings" / f"smoke_tts_{engine}.wav"
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"{label}={base} speaker={speaker}")
    try:
        speakers = tts.list_speakers(settings, engine=engine)
        print(f"speakers available: {len(speakers)}")
    except Exception as exc:
        print(f"Could not list speakers: {exc}")
        print(tts.engine_hint(engine))
        raise SystemExit(1) from exc

    text = "こんにちは。今日は日本語の練習をしましょう。"
    wav = tts.synthesize(settings, text, speaker_id=speaker, engine=engine)
    out.write_bytes(wav)
    print(f"wrote {out} ({len(wav)} bytes)")


if __name__ == "__main__":
    main()
