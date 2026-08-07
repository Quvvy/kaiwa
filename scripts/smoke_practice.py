from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.practice.scoring import score_intelligibility


def main() -> None:
    same = score_intelligibility("こんにちは。", "こんにちは")
    print(f"same -> score={same.score} band={same.band} norm={same.target_norm}")
    assert same.score >= 95, same

    wrong = score_intelligibility("こんにちは。", "さようなら")
    print(f"wrong -> score={wrong.score} band={wrong.band}")
    assert wrong.score < 60, wrong

    kana = score_intelligibility("日本語を勉強しています。", "にほんごをべんきょうしています")
    print(f"kana match -> score={kana.score} band={kana.band}")
    assert kana.score >= 85, kana

    wav = ROOT / "recordings" / "smoke_tts.wav"
    if wav.exists():
        from kaiwa.config import get_settings
        from kaiwa import stt

        settings = get_settings()
        heard = stt.transcribe_file(settings, wav)
        target = "こんにちは。今日は日本語の練習をしましょう。"
        live = score_intelligibility(target, heard)
        print(f"wav heard={heard!r}")
        print(f"wav score={live.score} band={live.band}")
    else:
        print("skip wav STT check (no recordings/smoke_tts.wav)")

    print("smoke_practice ok")


if __name__ == "__main__":
    main()
