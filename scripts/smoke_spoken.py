"""Kanji spellings sent to the voice engine (course.spoken).

Offline: lookups work per sentence and leave unknown text alone, and every course
sentence is either spelled or listed in KEEP_KANA (so a new line can't slip in
with the engine's guess at its accent).
With a voice engine running (AivisSpeech :10101, VOICEVOX :50021): every spelling
reads with the same sounds as its kana line, so a spelling can only change pitch,
never what the learner hears. Engines that aren't running are skipped.
`--accents` also lists the lines whose pitch the spelling changes.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("KAIWA_DATA_DIR", tempfile.mkdtemp(prefix="kaiwa-spoken-smoke-"))

from kaiwa.course.spoken import KEEP_KANA, SPELLING, course_sentences, for_speech  # noqa: E402

ENGINES = {"AivisSpeech": "http://127.0.0.1:10101", "VOICEVOX": "http://127.0.0.1:50021"}
# Kana lines the engine itself misreads (は as わ, の＋う as a long お); the kanji
# spelling's sounds are the right ones.
KANA_MISREAD = {"はなし", "はは", "ははです", "ははのしゃしんです", "これは、ははのしゃしんです",
                "ははは、げんきですか", "ははは、せんせいです", "はち", "えきのうしろで、まっています"}


def _check(ok: bool, label: str) -> None:
    print(("ok  " if ok else "FAIL") + label)
    if not ok:
        raise SystemExit(f"smoke_spoken failed: {label}")


def offline() -> None:
    _check(for_speech("あしたは、あめです。") == "明日は、雨です。", "a known line gets its spelling")
    _check(for_speech("はい。たのしみです！あめですから、うちにいます。") == "はい。楽しみです！雨ですから、うちにいます。",
           "each sentence of a longer clip is looked up")
    _check(for_speech("こんにちは！") == "こんにちは！", "a line with no spelling is left alone")
    _check(for_speech("今日は雨ですね。") == "今日は雨ですね。", "text already in kanji is left alone")
    _check(all(k != v for k, v in SPELLING.items()), "every entry changes something")
    _check(not any(ch in "。！？" for k in SPELLING for ch in k), "keys carry no sentence-ending punctuation")
    sentences = course_sentences()
    missing = [s for s in sentences if s not in SPELLING and s not in KEEP_KANA]
    for s in missing[:10]:
        print(f"     no spelling decision: {s}")
    _check(not missing, f"every course sentence ({len(sentences)}) is spelled or kept in kana"
           + (f": {len(missing)} new, add each to SPELLING or KEEP_KANA in course/spoken.py" if missing else ""))
    known = set(sentences)
    stale = [k for k in [*SPELLING, *KEEP_KANA] if k not in known]
    for s in stale[:10]:
        print(f"     no longer in the course: {s}")
    _check(not stale, "no spelling entry is left over from removed content")
    _check(not set(SPELLING) & KEEP_KANA, "no sentence is both spelled and kept in kana")


def _engine_up(base: str) -> int | None:
    try:
        speakers = json.load(urllib.request.urlopen(f"{base}/speakers", timeout=3))
        return int(speakers[0]["styles"][0]["id"])
    except Exception:
        return None


def _phrases(base: str, text: str, speaker: int) -> list[dict]:
    q = urllib.parse.urlencode({"text": text + "。", "speaker": speaker})
    req = urllib.request.Request(f"{base}/accent_phrases?{q}", method="POST")
    return json.load(urllib.request.urlopen(req, timeout=30))


def _sounds(aps: list[dict]) -> str:
    """Sounds, with a long vowel written either way (セイ/セエ, ボウ/ボオ) counted the same."""
    out, prev = [], ""
    for ap in aps:
        for m in ap["moras"]:
            t = m["text"]
            if (prev == "e" and t in ("イ", "エ")) or (prev == "o" and t in ("ウ", "オ")):
                t = "ー"
            out.append(t)
            prev = str(m.get("vowel") or "").lower()
    return "".join(out)


def _shape(aps: list[dict]) -> str:
    return " ".join("".join(m["text"] for m in ap["moras"]) + f"[{ap['accent']}]" for ap in aps)


def with_engine(name: str, base: str, show_accents: bool) -> None:
    speaker = _engine_up(base)
    if speaker is None:
        print(f"skip {name} isn't running at {base}, so its readings weren't checked")
        return
    wrong = []
    for kana, kanji in SPELLING.items():
        a, b = _phrases(base, kana, speaker), _phrases(base, kanji, speaker)
        if _sounds(a) != _sounds(b) and kana not in KANA_MISREAD:
            wrong.append(f"{kana} → {kanji}: {_sounds(a)} vs {_sounds(b)}")
        elif show_accents and _shape(a) != _shape(b):
            print(f"     {kanji}: {_shape(a)} → {_shape(b)}")
    for row in wrong:
        print("     " + row)
    _check(not wrong, f"{name}: all {len(SPELLING)} spellings read with the same sounds as their kana")


if __name__ == "__main__":
    offline()
    for engine_name, engine_base in ENGINES.items():
        with_engine(engine_name, engine_base, "--accents" in sys.argv)
