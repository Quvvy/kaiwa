"""Decks brought in from Anki (Kaishi 1.5k first): their sentence rows, media and import job.

Rows live in their own file per profile (<profile>/imported/<deck>.json), not in course_state.json,
which is rewritten on every answer; cards (the memory) live with the other cards in course state.
Each row is a sentence card like a mined line: the recorded sentence, a kana line from the deck's
own furigana, its meaning, two wrong meanings taken from other sentences of the deck (no model
needed), and the word it teaches with its reading, meaning, audio, note and picture.
"""

from __future__ import annotations

import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from kaiwa import jsonio
from kaiwa.course import mined_media

DIRNAME = "imported"
MEDIA_DIRNAME = "imported_media"
LABELS = {"kaishi": "Kaishi 1.5k"}


def deck_dir(profile_dir: Path) -> Path:
    return Path(profile_dir) / DIRNAME


def media_dir(profile_dir: Path) -> Path:
    path = Path(profile_dir) / MEDIA_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def media_url(name: str) -> str | None:
    return f"/api/course/imported/media/{name}" if name else None


def _file(profile_dir: Path, deck: str) -> Path:
    return deck_dir(profile_dir) / f"{deck}.json"


# ——— rows, cached by file time (they're read on every state load) ———

_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def load(profile_dir: Path, deck: str) -> dict[str, Any] | None:
    path = _file(profile_dir, deck)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    hit = _cache.get(str(path))
    if hit and hit[0] == mtime:
        return hit[1]
    data = jsonio.read_json_dict(path)
    if not data or not isinstance(data.get("rows"), list):
        return None
    data["rows"] = [r for r in data["rows"] if isinstance(r, dict) and isinstance(r.get("id"), str) and r.get("text")]
    _cache[str(path)] = (mtime, data)
    return data


def save(profile_dir: Path, deck: str, data: dict[str, Any]) -> None:
    deck_dir(profile_dir).mkdir(parents=True, exist_ok=True)
    jsonio.write_json_atomic(_file(profile_dir, deck), data)
    _cache.pop(str(_file(profile_dir, deck)), None)


def all_rows(profile_dir: Path) -> dict[str, dict[str, Any]]:
    """Every imported row by id, across decks."""
    out: dict[str, dict[str, Any]] = {}
    for deck in LABELS:
        data = load(profile_dir, deck)
        for row in (data or {}).get("rows", []):
            out[row["id"]] = row
    return out


def public_row(row: dict[str, Any]) -> dict[str, Any]:
    """What a card needs: the same shape as a mined line, plus the word it teaches."""
    deck = row["id"].split(".", 1)[0]
    return {
        "id": row["id"], "text": row["text"], "kana": row.get("kana", ""), "en": row.get("en", ""), "note": "",
        "wrong": row.get("wrong", []), "word": row.get("word", ""), "word_reading": row.get("word_reading", ""),
        "word_meaning": row.get("word_meaning", ""), "notes": row.get("notes", ""),
        "source": {"kind": "anki", "title": f"{LABELS.get(deck, deck)} · #{row.get('order', 0) + 1}", "start_ms": None},
        "audio_url": media_url(row.get("audio", "")), "word_audio_url": media_url(row.get("word_audio", "")),
        "image_url": media_url(row.get("image", "")), "deck_label": LABELS.get(deck, deck),
    }


# ——— building rows ———

def pick_wrong(rows: list[dict[str, Any]]) -> None:
    """Two wrong meanings per row: other sentences' meanings of about the same length.
    Deterministic, so a re-import gives the same options."""
    order = sorted(range(len(rows)), key=lambda i: (len(rows[i]["en"]), rows[i]["en"]))
    where = {i: pos for pos, i in enumerate(order)}
    for i, row in enumerate(rows):
        mine = row["en"].casefold()
        picked: list[str] = []
        seen = {mine}
        pos = where[i]
        for step in range(1, len(order)):
            for cand in (pos + step, pos - step):
                if 0 <= cand < len(order):
                    en = rows[order[cand]]["en"]
                    if en and en.casefold() not in seen:
                        picked.append(en)
                        seen.add(en.casefold())
                if len(picked) == 2:
                    break
            if len(picked) == 2:
                break
        row["wrong"] = picked


def _copy_media(src_dir: Path, dst_dir: Path, name: str) -> str:
    """Copy one file from Anki's media folder (if it's a known audio/image type and size)."""
    if not name or "/" in name or "\\" in name:
        return ""
    src = src_dir / name
    try:
        safe = mined_media.safe_name(name)
        size = src.stat().st_size
    except (mined_media.MediaError, OSError):
        return ""
    limit = mined_media.MAX_AUDIO_BYTES if mined_media.kind_of(name) == "audio" else mined_media.MAX_IMAGE_BYTES
    if not size or size > limit:
        return ""
    dst = dst_dir / safe
    if not dst.exists() or dst.stat().st_size != size:
        tmp = dst.with_suffix(dst.suffix + ".part")
        shutil.copyfile(src, tmp)
        os.replace(tmp, dst)
    return safe


def build_rows(deck: str, read: dict[str, Any], src_media: Path, dst_media: Path,
               progress: Callable[[int, int], None] | None = None) -> list[dict[str, Any]]:
    """Rows to keep from what anki_import.read_deck returned, with their media copied over."""
    rows = []
    total = len(read["rows"])
    for n, r in enumerate(read["rows"]):
        rows.append({
            "id": f"{deck}.{r['anki_nid']}", "order": r["order"], "anki_nid": r["anki_nid"],
            "text": r["text"], "word": r["word"], "kana": r["kana"], "en": r["en"],
            "word_reading": r["word_reading"], "word_meaning": r["word_meaning"], "notes": r["notes"],
            "audio": _copy_media(src_media, dst_media, r["sentence_audio"]),
            "word_audio": _copy_media(src_media, dst_media, r["word_audio"]),
            "image": _copy_media(src_media, dst_media, r["picture"]),
            "frequency": r["frequency"], "anki": r["anki"],
        })
        if progress and (n % 25 == 0 or n == total - 1):
            progress(n + 1, total)
    pick_wrong(rows)
    return rows


# ——— the import job (one at a time; the page polls its progress) ———

_job_lock = threading.Lock()
job: dict[str, Any] = {"running": False, "done": 0, "total": 0, "stage": "", "error": "", "result": None}


def start(run: Callable[[Callable[[str, int, int], None]], dict[str, Any]]) -> bool:
    """Run `run(report)` in the background; False if an import is already going."""
    if not _job_lock.acquire(blocking=False):
        return False
    job.update({"running": True, "done": 0, "total": 0, "stage": "Reading Anki…", "error": "", "result": None,
                "started": datetime.now(timezone.utc).isoformat(timespec="seconds")})

    def report(stage: str, done: int, total: int) -> None:
        job.update({"stage": stage, "done": done, "total": total})

    def work() -> None:
        try:
            job["result"] = run(report)
        except Exception as exc:  # shown on the page
            job["error"] = str(exc) or exc.__class__.__name__
        finally:
            job["running"] = False
            job["stage"] = "Done" if not job["error"] else "Failed"
            _job_lock.release()

    threading.Thread(target=work, name="kaiwa-anki-import", daemon=True).start()
    return True
