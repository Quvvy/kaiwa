"""Mined lines: sentences the learner caught in real shows, kept as Listen → meaning cards.

This module is pure (no course state): it turns what a mining tool sends into Kaiwa's
own capture shape, cleans stored rows, and answers the AnkiConnect-shaped questions
(notesInfo, findNotes) about them. state.py owns the rows; ankiconnect.py speaks the
protocol; mined_media.py keeps the clips; mined_enrich.py prepares each card.

The capture shape is what a future Tsugi "mine" button will post directly:
    {text, word, en_sub, audio: [{filename, data}], image: [{filename, data}],
     audio_refs, image_refs, source: {kind, title, url, episode, start_ms, end_ms}, tags}
"""

from __future__ import annotations

import hashlib
import html
import re
from typing import Any

MAX_KEPT = 3000
MAX_TEXT = 200
DECK = "Kaiwa"
MODEL = "Kaiwa Mining"
FIELDS = ("Sentence", "Word", "Translation", "Audio", "Image", "Source", "URL")
STATUSES = ("pending", "ready", "failed")

JP_RE = re.compile(r"[぀-ヿ㐀-鿿々〆ｦ-ﾟ]")
_CJK_RE = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uff00-\uffef]")  # incl. 。、「」 and full-width marks
_SOUND_RE = re.compile(r"\[sound:([^\]]+)\]")
_IMG_RE = re.compile(r"""<img\b[^>]*?\bsrc\s*=\s*["']?([^"'\s>]+)["']?[^>]*>""", re.I)
_BOLD_RE = re.compile(r"<(b|strong)\b[^>]*>(.*?)</\1\s*>", re.I | re.S)
_BREAK_RE = re.compile(r"<\s*(br|/div|/p|div|p)\b[^>]*>", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_STAMP_RE = re.compile(r"\((?:(\d+):)?(\d{1,2}):(\d{2})(?:\.\d+)?\)\s*$")
# asbplayer's own form: "Title (00h01m06.0s)"
_HMS_RE = re.compile(r"\((\d+)h(\d+)m(\d+)(?:\.\d+)?s\)\s*$")
# What's left of a subtitle file name: ".srt", YouTube's ".ytsrv3", " - 日本語 (自動生成)"
_TRACK_EXT_RE = re.compile(r"\.(srt|ass|ssa|vtt|ytsrv3|ttml|json3|sup)\s*$", re.I)
_YT_TRACK_RE = re.compile(r"\s*-\s*日本語(?:\s*\(自動生成\))?\s*$")


def normalize_key(text: str) -> str:
    """What makes two mined lines "the same line" (spacing, punctuation, script ignored)."""
    from kaiwa.course.speech_check import normalize

    return normalize(text)


def row_id(key: str) -> str:
    return "mined." + hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def _join_lines(lines: list[str]) -> str:
    out = ""
    for line in (l.strip() for l in lines):
        if not line:
            continue
        if out and not (_CJK_RE.match(out[-1]) and _CJK_RE.match(line[0])):
            out += " "
        out += line
    return out


def strip_html(value: Any) -> tuple[str, list[str], list[str], list[str]]:
    """(plain text, bold words, [sound:] names, <img> names) from an Anki field value."""
    raw = str(value or "")
    sounds = _SOUND_RE.findall(raw)
    images = _IMG_RE.findall(raw)
    bold = [_TAG_RE.sub("", html.unescape(m[1])).strip() for m in _BOLD_RE.findall(raw)]
    text = _SOUND_RE.sub("", raw)
    text = _IMG_RE.sub("", text)
    text = _BREAK_RE.sub("\n", text)
    text = html.unescape(_TAG_RE.sub("", text))
    lines = [re.sub(r"\s+", " ", line) for line in text.splitlines()]
    return _join_lines(lines), [b for b in bold if b], sounds, images


def _media_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = [value]
    return [m for m in value if isinstance(m, dict)] if isinstance(value, list) else []


def _field(fields: dict[str, Any], name: str) -> Any:
    for key, value in fields.items():
        if str(key).strip().casefold() == name.casefold():
            return value
    return None


def _parse_source(text: str) -> tuple[str, int | None]:
    """Split the time off a source ("Title (12:34)", "Title (00h12m34.0s)") and tidy the title."""
    start_ms = None
    m = _HMS_RE.search(text) or _STAMP_RE.search(text)
    if m:
        h, mm, ss = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
        start_ms = ((h * 60 + mm) * 60 + ss) * 1000
        text = text[: m.start()]
    text = _TRACK_EXT_RE.sub("", text.strip())
    return _YT_TRACK_RE.sub("", text).strip(), start_ms


def note_to_capture(note: dict[str, Any]) -> dict[str, Any]:
    """An AnkiConnect note (any field names, any deck/model) → Kaiwa's capture shape."""
    fields = note.get("fields") if isinstance(note.get("fields"), dict) else {}
    sentence = _field(fields, "Sentence")
    if sentence is None:
        sentence = next((v for v in fields.values() if JP_RE.search(strip_html(v)[0])), "")
    text, bold, sounds, images = strip_html(sentence)
    word = strip_html(_field(fields, "Word"))[0] or (bold[0] if bold else "")
    en_sub = strip_html(_field(fields, "Translation"))[0]
    title, start_ms = _parse_source(strip_html(_field(fields, "Source"))[0])
    url = strip_html(_field(fields, "URL"))[0]
    for value in fields.values():
        _, _, s, i = strip_html(value)
        sounds += s
        images += i
    return {
        "text": text,
        "word": word[:40],
        "en_sub": en_sub[:300],
        "audio": _media_list(note.get("audio")),
        "image": _media_list(note.get("picture")),
        "audio_refs": list(dict.fromkeys(sounds)),
        "image_refs": list(dict.fromkeys(images)),
        "source": {"kind": "asbplayer", "title": title[:200], "url": url[:500], "episode": "",
                   "start_ms": start_ms, "end_ms": None},
        "tags": [str(t)[:40] for t in (note.get("tags") or []) if str(t).strip()][:20],
    }


def validate_capture(capture: dict[str, Any]) -> None:
    """AnkiConnect-style errors for a line Kaiwa can't make a card from."""
    text = capture.get("text") or ""
    if not JP_RE.search(text):
        raise ValueError("cannot create note because it is empty (no Japanese line)")
    if len(text) > MAX_TEXT:
        raise ValueError(f"line too long for one card (over {MAX_TEXT} characters)")


def _str(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def clean_row(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    text = _str(raw.get("text"), MAX_TEXT)
    rid = str(raw.get("id") or "")
    if not text or not rid.startswith("mined."):
        return None
    src = raw.get("source") if isinstance(raw.get("source"), dict) else {}
    wrong = [str(w).strip() for w in (raw.get("wrong") or []) if str(w).strip()][:2]
    status = raw.get("status") if raw.get("status") in STATUSES else "pending"
    if status == "ready" and not (raw.get("en") and len(wrong) == 2 and raw.get("kana")):
        status = "pending"
    try:
        note_id = int(raw.get("note_id") or 0)
    except (TypeError, ValueError):
        note_id = 0

    def _int(v: Any) -> int | None:
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    return {
        "id": rid, "note_id": note_id, "key": _str(raw.get("key"), 400) or normalize_key(text), "text": text,
        "word": _str(raw.get("word"), 40), "en_sub": _str(raw.get("en_sub"), 300),
        "kana": _str(raw.get("kana"), 400), "kana_src": _str(raw.get("kana_src"), 8),
        "en": _str(raw.get("en"), 240), "note": _str(raw.get("note"), 200), "wrong": wrong,
        "source": {"kind": _str(src.get("kind"), 20), "title": _str(src.get("title"), 200),
                   "url": _str(src.get("url"), 500), "episode": _str(src.get("episode"), 20),
                   "start_ms": _int(src.get("start_ms")), "end_ms": _int(src.get("end_ms"))},
        "audio": _str(raw.get("audio"), 80), "audio_ms": _int(raw.get("audio_ms")) or 0,
        "image": _str(raw.get("image"), 80),
        "tags": [str(t)[:40] for t in (raw.get("tags") or []) if str(t).strip()][:20],
        "status": status, "attempts": _int(raw.get("attempts")) or 0, "next_try": _str(raw.get("next_try"), 40),
        "error": _str(raw.get("error"), 200), "rev": _int(raw.get("rev")) or 1,
        "added_at": _str(raw.get("added_at"), 40), "updated_at": _str(raw.get("updated_at"), 40),
    }


def clean_rows(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out, seen_ids, seen_keys = [], set(), set()
    for item in raw:
        row = clean_row(item)
        if row and row["id"] not in seen_ids and row["key"] not in seen_keys:
            seen_ids.add(row["id"])
            seen_keys.add(row["key"])
            out.append(row)
    return out[-MAX_KEPT:]


def media_url(name: str) -> str | None:
    return f"/api/course/mined/media/{name}" if name else None


def public_row(row: dict[str, Any]) -> dict[str, Any]:
    """What the page needs for a card or a list entry (no retry bookkeeping)."""
    return {
        "id": row["id"], "text": row["text"], "kana": row["kana"], "en": row["en"], "note": row["note"],
        "wrong": row["wrong"], "word": row["word"], "source": row["source"], "status": row["status"],
        "audio_url": media_url(row["audio"]), "image_url": media_url(row["image"]), "added_at": row["added_at"],
    }


def note_info(row: dict[str, Any]) -> dict[str, Any]:
    """The row as AnkiConnect's notesInfo would describe a note."""
    src = row["source"]
    title = src.get("title") or ""
    if src.get("start_ms") is not None:
        s = src["start_ms"] // 1000
        title = f"{title} ({s // 60}:{s % 60:02d})".strip()
    values = {
        "Sentence": row["text"], "Word": row["word"], "Translation": row["en_sub"] or row["en"],
        "Audio": f"[sound:{row['audio']}]" if row["audio"] else "",
        "Image": f'<img src="{row["image"]}">' if row["image"] else "",
        "Source": title, "URL": src.get("url") or "",
    }
    return {"noteId": row["note_id"], "modelName": MODEL, "tags": row["tags"], "cards": [row["note_id"]],
            "mod": _mod_seconds(row), "fields": {f: {"value": values[f], "order": i} for i, f in enumerate(FIELDS)}}


def _mod_seconds(row: dict[str, Any]) -> int:
    from datetime import datetime

    try:
        return int(datetime.fromisoformat(row["updated_at"] or row["added_at"]).timestamp())
    except ValueError:
        return 0


def match_query(rows: list[dict[str, Any]], query: str) -> list[int]:
    """Note ids for an Anki search. Only what mining tools ask: added:N, nid:, deck:, note:, words."""
    from datetime import datetime, timedelta, timezone

    picked = list(rows)
    for term in re.findall(r'"[^"]*"|\S+', query or ""):
        term = term.strip('"')
        low = term.casefold()
        if not term or term == "*" or low.startswith(("deck:", "note:", "is:", "-is:")):
            continue
        if low.startswith("added:"):
            try:
                days = max(1, int(low[6:]))
            except ValueError:
                continue
            since = datetime.now(timezone.utc) - timedelta(days=days)
            picked = [r for r in picked if r["added_at"] and datetime.fromisoformat(r["added_at"]) >= since]
        elif low.startswith(("nid:", "cid:")):
            ids = {int(x) for x in low[4:].split(",") if x.strip().isdigit()}
            picked = [r for r in picked if r["note_id"] in ids]
        else:
            needle = term.split(":", 1)[1] if ":" in term else term
            needle = needle.strip("*")
            picked = [r for r in picked if needle in r["text"] or needle.casefold() in r["en"].casefold()]
    return [r["note_id"] for r in picked]
