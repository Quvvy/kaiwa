"""The learner's own phrases: "how do I say what I actually want to say?"

Words about your own life are the ones you'll really use and the ones that stick.
A learner writes what they want to say, Flash gives the simplest natural Japanese for
it, and if they keep it, it becomes normal cards alongside the course's phrases.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from kaiwa import llm
from kaiwa.config import Settings

MAX_KEPT = 200
NOT_KANA = re.compile(r"[A-Za-z0-9Ａ-Ｚａ-ｚ０-９一-鿿]")
MAX_LEN = 40

SYSTEM = """\
An adult beginner (pre-N5) learning spoken Japanese wants to be able to say something about their own life.
Give the simplest natural way a beginner could actually say it out loud: polite です/ます style, one short
sentence, under 25 kana, written in kana only (hiragana, with katakana for foreign words and names).
Never use kanji or Latin letters: IT is アイティー, 5 is ご.
Prefer patterns from the known phrases when they fit. Don't add anything they didn't ask to say.
If they wrote Japanese, correct it only if needed.

"en": what your Japanese says, in plain English.
"note": at most 12 words of English on how it's built or when to use it. Empty if nothing useful.

Return JSON only: {"jp": "...", "en": "...", "note": "..."}
"""


def suggest(settings: Settings, text: str, known: list[dict[str, str]]) -> dict[str, str] | None:
    if not settings.deepseek_api_key:
        return None
    sample = "\n".join(f"- {p['jp']} ({p['en']})" for p in known[-25:])
    user = f"Known phrases:\n{sample or '(none yet)'}\n\nThey want to say: {text}"
    for prompt in (user, user + "\n\nWrite the Japanese entirely in kana: no kanji, no Latin letters, no digits."):
        data = llm.complete_json(settings, SYSTEM, prompt)
        jp = str((data or {}).get("jp") or "").strip()
        if jp and len(jp) <= MAX_LEN and not NOT_KANA.search(jp):
            return {"jp": jp, "en": str(data.get("en") or text).strip(), "note": str(data.get("note") or "").strip()}
    return None


def phrase_id(jp: str) -> str:
    return "my." + hashlib.sha1(jp.encode("utf-8")).hexdigest()[:10]


def romaji(jp: str) -> str:
    from kaiwa.course.speech_check import _kks

    return " ".join(p.get("hepburn", "") for p in _kks.convert(jp) if p.get("hepburn", "").strip()).strip()


def clean_kept(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out = []
    for row in raw[:MAX_KEPT]:
        if isinstance(row, dict) and str(row.get("id", "")).startswith("my.") and row.get("jp"):
            out.append({"id": str(row["id"]), "jp": str(row["jp"]), "en": str(row.get("en") or ""),
                        "note": str(row.get("note") or ""), "ro": str(row.get("ro") or "")})
    return out
