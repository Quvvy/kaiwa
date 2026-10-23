from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.practice.scoring import score_intelligibility


def _out(line: str) -> None:
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()


def main() -> None:
    same = score_intelligibility("こんにちは。", "こんにちは")
    _out(f"same -> score={same.score} band={same.band} norm={same.target_norm}")
    assert same.score >= 95, same

    wrong = score_intelligibility("こんにちは。", "さようなら")
    _out(f"wrong -> score={wrong.score} band={wrong.band}")
    assert wrong.score < 60, wrong

    kana = score_intelligibility("日本語を勉強しています。", "にほんごをべんきょうしています")
    _out(f"kana match -> score={kana.score} band={kana.band}")
    assert kana.score >= 85, kana

    _out("skip wav STT check (offline smoke is scoring only; live Whisper is smoke_stt.py)")

    _out("smoke_practice ok")


if __name__ == "__main__":
    main()
