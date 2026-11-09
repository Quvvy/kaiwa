"""Prepare mined lines for review: a kana reading, a meaning, a short note, two wrong meanings.

Runs in a background thread so mining never waits on the model. Each pending line
gets one Flash call (one stricter retry); what comes back is checked mechanically
before it's kept. A line that keeps failing is marked "couldn't prepare" after a few
tries and can be retried from the Mined lines page. Without a DeepSeek key nothing
is attempted: lines wait, and start the moment a key is saved.
"""

from __future__ import annotations

import logging
import re
import unicodedata
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from kaiwa import llm
from kaiwa.config import Settings

_log = logging.getLogger("kaiwa.course.mined_enrich")

MAX_ATTEMPTS = 4
MAX_BACKOFF_MIN = 60
PASS_LIMIT = 50

_running = threading.Lock()

_JP = re.compile(r"[぀-ヿ㐀-鿿々〆]")
_KANJI = re.compile(r"[㐀-鿿々〆]")
_LATIN = re.compile(r"[A-Za-zＡ-Ｚａ-ｚ]")

SYSTEM = """\
You prepare a listening card from a line of real Japanese (anime, drama, YouTube) for an
English-speaking learner. They will hear the line and pick its meaning from three options.

"kana": the whole line written in kana as it is actually read here. Katakana words stay katakana;
  every kanji becomes hiragana with the reading that fits this context. Keep the punctuation.
  No kanji, no romaji.
"en": what the line means in natural English, faithful to the Japanese (not to any subtitle),
  under 20 words.
"note": at most 20 words of English on the one or two words or bits of grammar that make this line
  hard. If a target word is given, explain that one. Empty if nothing is worth saying.
"wrong": two wrong meanings with the same shape and length as "en", the kind of thing someone
  would pick if they misheard or didn't know one key word. Plausible, clearly different from "en"
  and from each other.

An English subtitle may be given as a hint. It can be loose, shortened or wrong.

Return JSON only: {"kana": "...", "en": "...", "note": "...", "wrong": ["...", "..."]}
"""

STRICT = ('\n\nCheck before answering: "wrong" has exactly two items, both different from "en" and '
          'from each other; "en" and "wrong" are English only; "kana" has no kanji.')


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def auto_kana(text: str) -> str:
    """Kanji read as hiragana by pykakasi, katakana kept: the fallback reading line."""
    from kaiwa.course.chat_link import _kana

    return _kana(text)


def _plain(text: str) -> str:
    """Hiragana with no punctuation or spaces, for comparing a line with its reading."""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)
    return "".join(c for c in text if not unicodedata.category(c).startswith(("P", "Z", "S")))


def reading_fits(reading: str, text: str) -> bool:
    """The reading keeps every kana of the line, in order, and gives each kanji run some kana.

    A dictionary reader can't check the readings themselves (it reads 今日は as こんにちは),
    so this checks the shape: no dropped or invented words, nothing left in kanji.
    """
    if not reading or _KANJI.search(reading) or _LATIN.search(reading):
        return False
    pattern = []
    for run in re.findall(r"[\u3400-\u9fff々〆]+|.", _plain(text)):
        if _KANJI.match(run):
            pattern.append(f"[\u3040-\u309fー]{{1,{4 * len(run) + 2}}}?")
        else:
            pattern.append(re.escape(run))
    return re.fullmatch("".join(pattern), _plain(reading)) is not None


def _english(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    return text if text and len(text) <= limit and _LATIN.search(text) and not _JP.search(text) else ""


def check(row: dict[str, Any], data: dict[str, Any] | None) -> dict[str, Any] | None:
    """The usable part of a model reply, or None if its meaning or wrong answers don't hold up."""
    if not isinstance(data, dict):
        return None
    en = _english(data.get("en"), 240)
    wrong = [_english(w, 240) for w in (data.get("wrong") or [])] if isinstance(data.get("wrong"), list) else []
    wrong = [w for w in wrong if w]
    if not en or len(wrong) != 2:
        return None
    if len({en.casefold(), wrong[0].casefold(), wrong[1].casefold()}) < 3:
        return None
    note = str(data.get("note") or "").strip()  # may quote the Japanese word it explains
    note = note if len(note) <= 200 else ""
    text = row["text"]
    kana, src = "", "llm"
    if not _KANJI.search(text):
        kana, src = text, "text"
    else:
        raw = str(data.get("kana") or "").strip()
        if reading_fits(raw, text):
            kana = raw
    if not kana:
        kana, src = auto_kana(text), "auto"
    return {"kana": kana[:400], "kana_src": src, "en": en, "note": note[:200], "wrong": wrong}


def enrich(settings: Settings, row: dict[str, Any]) -> dict[str, Any] | None:
    """One prepared card for a row, or None if the model's answers didn't hold up twice."""
    parts = [f"Line: {row['text']}"]
    if row.get("word"):
        parts.append(f"Target word: {row['word']}")
    if row.get("en_sub"):
        parts.append(f"English subtitle (hint only): {row['en_sub']}")
    user = "\n".join(parts)
    for prompt in (user, user + STRICT):
        result = check(row, llm.complete_json(settings, SYSTEM, prompt))
        if result:
            return result
    return None


def backoff(attempts: int) -> timedelta:
    return timedelta(minutes=min(MAX_BACKOFF_MIN, 2 ** attempts))


def _due(row: dict[str, Any], now: datetime) -> bool:
    if row["status"] != "pending":
        return False
    nxt = row.get("next_try") or ""
    try:
        return not nxt or datetime.fromisoformat(nxt) <= now
    except ValueError:
        return True


def run(path: Path | None = None, *, settings: Settings | None = None) -> int:
    """Prepare due lines one by one. Returns how many were tried. One pass at a time."""
    from kaiwa.config import get_settings
    from kaiwa.course import mined_media
    from kaiwa.course import state as course_state

    if not _running.acquire(blocking=False):
        return 0
    tried = 0
    try:
        path = Path(path) if path else course_state.state_path()  # pinned: a profile switch can't redirect writes
        skipped: set[str] = set()
        while tried < PASS_LIMIT:
            current = settings or get_settings()
            if not current.deepseek_api_key:
                break
            st = course_state.load_state(path)
            now = _utcnow()
            row = next((r for r in st["mined"] if r["id"] not in skipped and _due(r, now)), None)
            if row is None:
                break
            skipped.add(row["id"])
            tried += 1
            try:
                result = enrich(current, row)  # no lock held while the model thinks
            except Exception:  # never let one line stop the worker
                _log.exception("preparing mined line %s failed", row["id"])
                result = None
            course_state.store_enrichment(row["id"], row["rev"], result, path=path)
        st = course_state.load_state(path)
        referenced = {r["audio"] for r in st["mined"]} | {r["image"] for r in st["mined"]}
        mined_media.sweep_orphans(mined_media.media_dir(path), referenced - {""})
    finally:
        _running.release()
    return tried


def pending_due(path: Path | None = None) -> bool:
    from kaiwa.course import state as course_state

    now = _utcnow()
    return any(_due(r, now) for r in course_state.load_state(path)["mined"])


def kick(path: Path | None = None) -> bool:
    """Start a background pass if a line is waiting and none is running. Cheap to call often."""
    from kaiwa.config import get_settings
    from kaiwa.course import state as course_state

    if _running.locked() or not get_settings().deepseek_api_key:
        return False
    try:
        path = Path(path) if path else course_state.state_path()
        if not pending_due(path):
            return False
    except Exception:
        return False
    threading.Thread(target=run, kwargs={"path": path}, name="kaiwa-mined-enrich", daemon=True).start()
    return True
