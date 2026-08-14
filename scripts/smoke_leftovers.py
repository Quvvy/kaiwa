from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.leftovers import leftover_chunks, parse_alternatives
from kaiwa.session_store import append_record, create_session, hydrate


def _check(ok: bool, label: str) -> None:
    status = "ok  " if ok else "FAIL"
    line = status + label
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    if not ok:
        raise SystemExit(f"smoke_leftovers failed: {label}")


def main() -> None:
    import tempfile

    _check(leftover_chunks([]) == [], "empty messages → no chunks")
    _check(leftover_chunks([{"role": "assistant", "content": "猫好き？"}]) == [], "assistant-only → no chunks")
    _check(
        leftover_chunks([{"role": "user", "content": "   "}]) == [],
        "blank user → no chunks",
    )

    messages = [
        {"role": "user", "content": "こんにちは"},
        {"role": "assistant", "content": "元気？"},
        {"role": "user", "content": "猫好きです"},
        {"role": "assistant", "content": "そうなんだ。猫好き？"},
        {"role": "user", "content": "猫好きです"},
        {"role": "user", "content": "白"},
    ]
    chunks = leftover_chunks(messages)
    _check(chunks == ["こんにちは", "猫好きです", "白"], "unique recent user lines chronological")

    many = [{"role": "user", "content": f"line{i}"} for i in range(8)]
    capped = leftover_chunks(many)
    _check(len(capped) == 5, "cap 5")
    _check(capped == ["line3", "line4", "line5", "line6", "line7"], "most recent five")

    long = "あ" * 120
    _check(len(leftover_chunks([{"role": "user", "content": long}])[0]) == 80, "clip 80")

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        meta = create_session(root, "alice")
        append_record(
            root,
            meta.id,
            {
                "ts": "2026-08-13T00:00:00+00:00",
                "mode": "chat",
                "transcript": "犬も好き",
                "reply": "犬、好き？",
            },
            profile_id="alice",
            bump_turns=True,
            title_hint="犬も好き",
        )
        append_record(
            root,
            meta.id,
            {
                "ts": "2026-08-13T00:00:01+00:00",
                "mode": "chat",
                "rescue": True,
                "transcript": "",
                "reply": "犬？猫？",
            },
            profile_id="alice",
            bump_turns=False,
        )
        append_record(
            root,
            meta.id,
            {
                "ts": "2026-08-13T00:00:02+00:00",
                "mode": "practice",
                "target": "犬も好き",
            },
            profile_id="alice",
            bump_turns=False,
        )
        hydrated = hydrate(root, meta.id)
        from_file = leftover_chunks(hydrated)
        _check(from_file == ["犬も好き"], "hydrate skips practice; rescue is not a user line")

    _check(
        parse_alternatives('{"alternatives": ["猫が好きです", "猫、好き。"]}'),
        "parse two alternatives",
    )
    parsed = parse_alternatives(
        '```json\n{"alternatives": [{"text": "犬が好き"}, "TRY: だめ", "白猫が好き"]}\n```'
    )
    _check(parsed == ["犬が好き", "白猫が好き"], "skip TRY: and unwrap json fence")
    _check(parse_alternatives("not json") == [], "junk → empty")
    _check(parse_alternatives('{"alternatives": "nope"}') == [], "non-list → empty")
    _check(
        parse_alternatives('{"alternatives": ["a", "b", "c", "d"]}') == ["a", "b", "c"],
        "cap 3 alternatives",
    )

    print("smoke_leftovers ok")


if __name__ == "__main__":
    main()
