"""The learner log: what happened in each activity, for building a model of this learner.

One JSON line per event in the active profile's folder, so every learner's log is
their own. It records what a tutor would want to know and nothing else: answers
and mistakes (with a type), what was heard vs. meant, listening behaviour (replays,
peeks, missed questions), help used, hesitation, and when and how long sessions are.
No audio, nothing unrelated to learning.

Writing never fails loudly: a log problem must not break a lesson. Old lines are
rotated out (one previous file kept) so the log stays small.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_log = logging.getLogger("kaiwa.course.learner_log")

LOG_FILE = "learner_log.jsonl"
MAX_BYTES = 8 * 1024 * 1024   # rotate past this; with one old file kept, ~16 MB at most
SESSION_GAP_S = 30 * 60        # a pause this long starts a new session
MAX_TEXT = 300                 # any one text field is cut to this

# Mistake types the coach tags; anything else becomes "other".
MISTAKE_TYPES = ("particle", "verb_form", "word_choice", "politeness", "word_order",
                 "missing_word", "pronunciation", "english", "off_topic", "other")

# Events the page may send itself (everything else is logged by the server where it happens).
CLIENT_KINDS = frozenset({"open", "listen", "talk_end", "talk_hint", "hint", "skip", "lesson_step"})

_lock = threading.Lock()
_last: dict[str, tuple[float, int]] = {}  # log path → (time of last event, session number)


def log_path() -> Path:
    from kaiwa.profiles import active_profile_dir

    return active_profile_dir() / LOG_FILE


def _clean(value: Any, depth: int = 0) -> Any:
    if isinstance(value, str):
        return value[:MAX_TEXT]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if depth > 3:
        return None
    if isinstance(value, dict):
        return {str(k)[:40]: _clean(v, depth + 1) for k, v in list(value.items())[:40]}
    if isinstance(value, (list, tuple)):
        return [_clean(v, depth + 1) for v in list(value)[:40]]
    return str(value)[:MAX_TEXT]


def _session(path: Path, now: float) -> int:
    """Session number for this event: continues the last one unless there was a long pause."""
    key = str(path)
    if key not in _last:
        _last[key] = _last_session_on_disk(path)
    at, n = _last[key]
    if now - at > SESSION_GAP_S:
        n += 1
    _last[key] = (now, n)
    return n


def _last_session_on_disk(path: Path) -> tuple[float, int]:
    """(time, session) of the last event written, so a restart mid-session continues it."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 4096))
            tail = fh.read().decode("utf-8", errors="ignore").strip().splitlines()
        row = json.loads(tail[-1])
        return datetime.fromisoformat(row["t"]).timestamp(), int(row.get("s") or 0)
    except (OSError, ValueError, IndexError, KeyError, TypeError):
        return 0.0, 0


def log(kind: str, *, path: Path | None = None, **data: Any) -> None:
    """Append one event. Never raises."""
    try:
        path = path or log_path()
        now = datetime.now().astimezone()
        with _lock:
            row = {"t": now.astimezone(timezone.utc).isoformat(timespec="seconds"), "hour": now.hour,
                   "dow": now.weekday(), "s": _session(path, now.timestamp()), "kind": kind,
                   **{k: _clean(v) for k, v in data.items() if v not in (None, "", [], {})}}
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.stat().st_size > MAX_BYTES:
                path.replace(path.with_suffix(".1.jsonl"))
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001 - the log must never break a lesson
        _log.info("learner log write failed: %s", exc)


def read(*, path: Path | None = None, kinds: set[str] | None = None) -> list[dict[str, Any]]:
    """Every event (oldest first, the rotated file included), optionally of some kinds only."""
    path = path or log_path()
    rows: list[dict[str, Any]] = []
    for p in (path.with_suffix(".1.jsonl"), path):
        try:
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(row, dict) and (kinds is None or row.get("kind") in kinds):
                        rows.append(row)
        except OSError:
            continue
    return rows


def mistakes(raw: Any) -> list[dict[str, str]]:
    """Normalize the coach's mistake tags: [{"type": one of MISTAKE_TYPES, "detail": "..."}]."""
    out = []
    for m in raw if isinstance(raw, list) else []:
        if isinstance(m, dict):
            kind = str(m.get("type") or "other").strip().lower().replace(" ", "_")
            out.append({"type": kind if kind in MISTAKE_TYPES else "other", "detail": str(m.get("detail") or "")[:120]})
    return out[:4]


MISTAKES_PROMPT = """\
Also return "mistakes": every real mistake in the learner's line (empty list if none), each
{"type": one of particle | verb_form | word_choice | politeness | word_order | missing_word |
pronunciation | english | off_topic | other, "detail": "short, specific, e.g. を instead of が with すき"}.
Tag everything you notice here even though the tip names only one."""
