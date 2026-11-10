"""Read an Anki collection on this computer, without ever changing it.

The collection (and its write-ahead log) is copied to a temporary folder first, so Anki can stay
open and its file is never touched. Field roles (sentence, meaning, audio, …) are found by name,
so any sentence deck with ordinary field names imports; Kaishi 1.5k matches exactly.

What comes out per note is plain data: the sentence with its target word, a kana reading from the
deck's own furigana (no model needed), meanings, notes, media file names, and Anki's own FSRS
memory for the card (stability, difficulty, last review) so Kaiwa can carry it over.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from kaiwa.course.mined import strip_html

# Field roles, by the names decks commonly use (case and spacing ignored), first match wins.
ROLES: dict[str, tuple[str, ...]] = {
    "sentence": ("sentence", "expression", "sentencejp", "japanesesentence", "example", "examplesentence"),
    "sentence_meaning": ("sentencemeaning", "sentenceenglish", "sentencetranslation", "englishsentence", "translation"),
    "sentence_furigana": ("sentencefurigana", "sentencereading", "sentencekana"),
    "sentence_audio": ("sentenceaudio", "audiosentence", "sentencesound"),
    "word": ("word", "vocab", "vocabulary", "target", "targetword", "kanji"),
    "word_reading": ("wordreading", "reading", "vocabreading", "kana"),
    "word_meaning": ("wordmeaning", "meaning", "vocabmeaning", "definition", "english"),
    "word_furigana": ("wordfurigana", "vocabfurigana"),
    "word_audio": ("wordaudio", "vocabaudio", "audio", "sound"),
    "notes": ("notes", "note", "hint", "extra"),
    "picture": ("picture", "image", "screenshot", "pic"),
    "frequency": ("frequency", "freq", "rank"),
}

_FURI_RE = re.compile(r"\s*([^\s\[\]]+?)\[([^\]]*)\]")
_KANJI_RE = re.compile(r"[㐀-鿿々〆]")
_SOUND_RE = re.compile(r"\[sound:([^\]]+)\]")
_IMG_RE = re.compile(r"""<img\b[^>]*?\bsrc\s*=\s*["']?([^"'\s>]+)""", re.I)


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def detect_fields(names: list[str]) -> dict[str, int]:
    """role → field index, for the roles this note type has."""
    keys = [_key(n) for n in names]
    out: dict[str, int] = {}
    used: set[int] = set()
    for role, wants in ROLES.items():
        for want in wants:
            if want in keys and keys.index(want) not in used:
                out[role] = keys.index(want)
                used.add(out[role])
                break
    return out


def furigana_to_kana(text: str) -> str:
    """Anki furigana ("<b>私[わたし]</b>は アン です") → the line in kana ("わたしはアンです")."""
    plain = strip_html(text)[0]

    def swap(m: re.Match[str]) -> str:
        base, reading = m.group(1), m.group(2)
        # "お茶[ちゃ]": only the kanji part is replaced by the reading; leading kana stay.
        lead = re.match(r"^[^㐀-鿿々〆]*", base).group(0)
        return lead + reading

    kana = _FURI_RE.sub(swap, plain)
    return re.sub(r"\s+", "", kana)


_JP_CHAR = re.compile("[\u3040-\u30ff\u3400-\u9fff\u3005\u3006\u30fc]")
_WORD_CHAR = re.compile("[A-Za-z0-9\u3040-\u30ff\u3400-\u9fff\u3005\u3006\u30fc]")


def mostly_japanese(text: str) -> bool:
    """At least half the letters are Japanese (a sentence, not a deck's welcome note)."""
    letters = _WORD_CHAR.findall(text or "")
    return bool(letters) and len(_JP_CHAR.findall(text)) * 2 >= len(letters)


def _plain(value: str, limit: int) -> str:
    text = strip_html(value)[0]
    return html.unescape(text).strip()[:limit]


# ——— finding and opening collections ———

def anki_roots() -> list[Path]:
    home = Path.home()
    roots = [home / ".local/share/Anki2", home / "Library/Application Support/Anki2"]
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        roots.insert(0, Path(os.environ["APPDATA"]) / "Anki2")
    flat = os.environ.get("XDG_DATA_HOME")
    if flat:
        roots.insert(0, Path(flat) / "Anki2")
    return roots


def find_collections(roots: list[Path] | None = None) -> list[dict[str, Any]]:
    """Every Anki profile's collection on this computer: [{profile, path, modified}]."""
    out = []
    for root in roots or anki_roots():
        if not root.is_dir():
            continue
        for coll in sorted(root.glob("*/collection.anki2")):
            out.append({"profile": coll.parent.name, "path": str(coll),
                        "modified": datetime.fromtimestamp(coll.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")})
    return out


def is_collection_path(path: str, roots: list[Path] | None = None) -> bool:
    """Only real collections under Anki's own folders may be opened (no arbitrary files)."""
    try:
        p = Path(path).resolve()
    except OSError:
        return False
    return p.name == "collection.anki2" and p.is_file() and any(
        r.is_dir() and p.is_relative_to(r.resolve()) for r in (roots or anki_roots()))


def _unicase(a: str, b: str) -> int:
    a, b = a.lower(), b.lower()
    return (a > b) - (a < b)


@contextmanager
def open_copy(path: str | Path) -> Iterator[sqlite3.Connection]:
    """A read-only connection to a temporary copy of the collection (Anki may stay open)."""
    src = Path(path)
    with tempfile.TemporaryDirectory(prefix="kaiwa-anki-") as tmp:
        dst = Path(tmp) / "collection.anki2"
        shutil.copy2(src, dst)
        for suffix in ("-wal", "-shm"):
            side = src.with_name(src.name + suffix)
            if side.exists():
                shutil.copy2(side, dst.with_name(dst.name + suffix))
        db = sqlite3.connect(dst)
        db.create_collation("unicase", _unicase)
        try:
            yield db
        finally:
            db.close()


def media_dir(path: str | Path) -> Path:
    return Path(path).with_name("collection.media")


# ——— decks ———

def _decks(db: sqlite3.Connection) -> dict[int, str]:
    return {int(i): str(n).replace("\x1f", "::") for i, n in db.execute("select id, name from decks")}


def _fields_of(db: sqlite3.Connection, ntid: int) -> list[str]:
    return [r[0] for r in db.execute("select name from fields where ntid=? order by ord", (ntid,))]


def list_decks(path: str | Path) -> list[dict[str, Any]]:
    """Decks with sentence notes Kaiwa can use: name, counts, and which fields were recognised."""
    out = []
    with open_copy(path) as db:
        names = _decks(db)
        rows = db.execute(
            "select c.did, n.mid, count(*), sum(c.reps > 0), sum(c.type = 0), sum(c.queue = -1) "
            "from cards c join notes n on n.id = c.nid group by c.did, n.mid").fetchall()
        types = {int(i): n for i, n in db.execute("select id, name from notetypes")}
        for did, mid, total, studied, new, suspended in rows:
            roles = detect_fields(_fields_of(db, mid))
            if "sentence" not in roles or not ({"sentence_meaning", "word_meaning"} & roles.keys()):
                continue
            out.append({"id": int(did), "name": names.get(did, str(did)), "note_type": types.get(mid, ""), "notetype_id": int(mid),
                        "total": total, "studied": studied or 0, "new": new or 0, "suspended": suspended or 0,
                        "roles": sorted(roles)})
    return sorted(out, key=lambda d: -d["total"])


def _fsrs_state(data: str, ivl: int, factor: int) -> tuple[float | None, float | None]:
    try:
        d = json.loads(data or "{}")
    except ValueError:
        d = {}
    if isinstance(d, dict) and isinstance(d.get("s"), (int, float)):
        return float(d["s"]), float(d.get("d") or 5.0)
    if ivl > 0:
        # Older (SM-2) cards: the interval is a fair stand-in for stability; ease → difficulty.
        return float(ivl), max(1.0, min(10.0, 11 - (factor or 2500) / 300))
    return None, None


def read_deck(path: str | Path, deck_id: int) -> dict[str, Any]:
    """Every note in a deck, as plain rows, plus the deck's name."""
    rows = []
    with open_copy(path) as db:
        name = _decks(db).get(deck_id, str(deck_id))
        last_review = {int(cid): int(ms) for cid, ms in db.execute(
            "select cid, max(id) from revlog where cid in (select id from cards where did=?) group by cid", (deck_id,))}
        reviews = db.execute("select count(*) from revlog where cid in (select id from cards where did=?)", (deck_id,)).fetchone()[0]
        fields_cache: dict[int, dict[str, int]] = {}
        for nid, mid, flds, cid, ctype, queue, ivl, factor, reps, lapses, data, cdue in db.execute(
                "select n.id, n.mid, n.flds, c.id, c.type, c.queue, c.ivl, c.factor, c.reps, c.lapses, c.data, c.due "
                "from cards c join notes n on n.id = c.nid where c.did=? order by c.type = 0, c.due, c.id", (deck_id,)):
            if mid not in fields_cache:
                fields_cache[mid] = detect_fields(_fields_of(db, mid))
            roles = fields_cache[mid]
            parts = flds.split("\x1f")
            get = lambda role: parts[roles[role]] if role in roles and roles[role] < len(parts) else ""  # noqa: E731
            text, bold, _s, _i = strip_html(get("sentence"))
            if not mostly_japanese(text):
                continue  # an intro or info note, not a sentence
            word = strip_html(get("word"))[0] or (bold[0] if bold else "")
            furi = get("sentence_furigana")
            kana = furigana_to_kana(furi) if furi else ""
            if kana and _KANJI_RE.search(kana):
                kana = ""
            stab, diff = _fsrs_state(data, ivl, factor) if ctype != 0 else (None, None)
            lrt = last_review.get(int(cid))
            try:
                lrt_json = json.loads(data or "{}").get("lrt")
            except (ValueError, AttributeError):
                lrt_json = None
            when = (datetime.fromtimestamp(lrt / 1000, timezone.utc) if lrt
                    else datetime.fromtimestamp(lrt_json, timezone.utc) if isinstance(lrt_json, (int, float)) else None)
            freq = strip_html(get("frequency"))[0]
            rows.append({
                "anki_nid": int(nid), "anki_cid": int(cid), "order": len(rows),
                "text": text[:200], "word": word[:40], "kana": kana[:400],
                "en": _plain(get("sentence_meaning") or get("word_meaning"), 240),
                "word_reading": _plain(get("word_reading"), 60) or (furigana_to_kana(get("word_furigana")) if get("word_furigana") else ""),
                "word_meaning": _plain(get("word_meaning"), 200),
                "notes": _plain(get("notes"), 300),
                "sentence_audio": next(iter(_SOUND_RE.findall(get("sentence_audio"))), ""),
                "word_audio": next(iter(_SOUND_RE.findall(get("word_audio"))), ""),
                "picture": next(iter(_IMG_RE.findall(get("picture"))), ""),
                "frequency": int(freq) if freq.isdigit() else None,
                "anki": {"type": int(ctype), "suspended": queue == -1, "reps": int(reps), "lapses": int(lapses),
                         "stability": stab, "difficulty": diff,
                         "last_review": when.isoformat(timespec="seconds") if when else None},
            })
    return {"name": name, "rows": rows, "reviews": reviews}
