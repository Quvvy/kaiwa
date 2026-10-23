"""Ephemeral Practice sitting — not a Chat session, not in the Chats drawer."""

from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kaiwa import jsonio
from kaiwa import profiles
from kaiwa.practice.cards import (
    SPEAKABLE_AGAIN,
    SPEAKABLE_ETTO,
    display_line,
    newest_unused,
    practice_worthy_line,
    why_line,
)
from kaiwa.practice.learn import resolve_card

STATE_FILE = "practice_state.json"
MAX_LEARNER_TURNS = 2
SITTING_MINUTES = 2
LINES_CAP = 5
FALLBACK_PREFIX = "fallback:"
FALLBACK_CARDS: list[dict[str, str]] = [
    {
        "id": "fallback:suki",
        "learner_line": "",
        "tutor_reply": "コーヒーが好き？",
        "speakable": "コーヒーが好きです。",
    },
    {
        "id": "fallback:again",
        "learner_line": "",
        "tutor_reply": "もう一回言うね。",
        "speakable": "もう一回お願いします",
    },
    {
        "id": "fallback:etto",
        "learner_line": "",
        "tutor_reply": "ゆっくりでいいよ。",
        "speakable": "えっと…",
    },
]

_lock = threading.Lock()
_ram: dict[str, dict[str, Any]] = {}


def state_path(profile_dir: Path | None = None) -> Path:
    return (profile_dir or profiles.active_profile_dir()) / STATE_FILE


def default_state() -> dict[str, Any]:
    return {"used_card_ids": [], "sitting": None, "pending_elicit": ""}


def load_state(path: Path | None = None) -> dict[str, Any]:
    file = path or state_path()
    if not file.is_file():
        return default_state()
    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default_state()
    if not isinstance(raw, dict):
        return default_state()
    used = raw.get("used_card_ids") or []
    if not isinstance(used, list):
        used = []
    sitting = raw.get("sitting")
    if sitting is not None and not isinstance(sitting, dict):
        sitting = None
    elicit = raw.get("pending_elicit")
    if not isinstance(elicit, str):
        elicit = ""
    return {
        "used_card_ids": [str(i) for i in used if i],
        "sitting": sitting,
        "pending_elicit": elicit.strip(),
    }


def save_state(state: dict[str, Any], *, path: Path | None = None) -> None:
    file = path or state_path()
    payload = {
        "used_card_ids": list(state.get("used_card_ids") or []),
        "sitting": state.get("sitting"),
        "pending_elicit": str(state.get("pending_elicit") or "").strip(),
    }
    jsonio.write_json_atomic(file, payload)


def _profile_key() -> str:
    return profiles.active_profile_id()


def _sitting_from_ram_or_disk(path: Path | None = None) -> dict[str, Any] | None:
    key = _profile_key()
    sitting = _ram.get(key)
    if isinstance(sitting, dict) and sitting.get("id"):
        return sitting
    state = load_state(path)
    sitting = state.get("sitting")
    if isinstance(sitting, dict) and sitting.get("id"):
        _ram[key] = sitting
        return sitting
    return None


def active_sitting(path: Path | None = None) -> dict[str, Any] | None:
    with _lock:
        return _sitting_from_ram_or_disk(path)


def public_sitting(sitting: dict[str, Any] | None) -> dict[str, Any] | None:
    if not sitting:
        return None
    card = sitting.get("card") if isinstance(sitting.get("card"), dict) else {}
    return {
        "id": sitting.get("id"),
        "card_id": sitting.get("card_id"),
        "speakable": display_line(card),
        "learner_turns": int(sitting.get("learner_turns") or 0),
        "max_turns": MAX_LEARNER_TURNS,
        "done": bool(sitting.get("done")),
        "messages": list(sitting.get("messages") or []),
        "why": why_line(card),
    }


def sitting_speakable(sitting: dict[str, Any] | None) -> str:
    if not sitting:
        return ""
    card = sitting.get("card") if isinstance(sitting.get("card"), dict) else {}
    return display_line(card)


def is_fallback_id(card_id: str | None) -> bool:
    return str(card_id or "").startswith(FALLBACK_PREFIX)


def next_fallback_card(used_ids: list[str] | None) -> dict[str, Any]:
    """Canned sitting when no unused Chat card. Recycles fallbacks only."""
    used = [str(i) for i in (used_ids or []) if i]
    used_set = set(used)
    for card in FALLBACK_CARDS:
        if card["id"] not in used_set:
            return dict(card)
    fallback_ids = [card["id"] for card in FALLBACK_CARDS]
    last = ""
    for item in reversed(used):
        if item in fallback_ids:
            last = item
            break
    if not last:
        return dict(FALLBACK_CARDS[0])
    idx = fallback_ids.index(last)
    return dict(FALLBACK_CARDS[(idx + 1) % len(FALLBACK_CARDS)])


def pick_today_card(
    *,
    used_ids: list[str] | None,
    cards_path: Path | None = None,
) -> tuple[dict[str, Any], bool]:
    """Chat snapshot if unused; else canned fallback. Second value is fallback."""
    chat = newest_unused(used_ids=used_ids, path=cards_path)
    if chat:
        return chat, False
    return next_fallback_card(used_ids), True


def _card_by_id(card_id: str, *, cards_path: Path | None = None) -> dict[str, Any] | None:
    cid = str(card_id or "")
    if not cid:
        return None
    card = resolve_card(cid, cards_path=cards_path)
    if card:
        return card
    for row in FALLBACK_CARDS:
        if row["id"] == cid:
            return dict(row)
    return None


def recent_practiced_lines(
    used_ids: list[str] | None,
    *,
    cards_path: Path | None = None,
) -> list[dict[str, str]]:
    """Newest finished sittings first. Speakable only. Cap LINES_CAP."""
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for card_id in reversed([str(i) for i in (used_ids or []) if i]):
        card = _card_by_id(card_id, cards_path=cards_path)
        line = display_line(card)
        if not line or line in seen or not practice_worthy_line(line):
            continue
        seen.add(line)
        out.append({"speakable": line})
        if len(out) >= LINES_CAP:
            break
    return out


def today_payload(
    *,
    cards_path: Path | None = None,
    state_path_override: Path | None = None,
) -> dict[str, Any]:
    state = load_state(state_path_override)
    sitting = active_sitting(state_path_override)
    lines = recent_practiced_lines(
        state.get("used_card_ids"),
        cards_path=cards_path,
    )
    if sitting:
        return {
            "available": True,
            "minutes": SITTING_MINUTES,
            "card_id": sitting.get("card_id"),
            "sitting": public_sitting(sitting),
            "fallback": is_fallback_id(str(sitting.get("card_id") or "")),
            "lines": lines,
        }
    card, fallback = pick_today_card(
        used_ids=state.get("used_card_ids"),
        cards_path=cards_path,
    )
    return {
        "available": True,
        "minutes": SITTING_MINUTES,
        "card_id": card.get("id"),
        "sitting": None,
        "fallback": fallback,
        "lines": lines,
    }


def new_sitting(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": uuid.uuid4().hex,
        "card_id": str(card.get("id") or ""),
        "card": {
            "id": card.get("id"),
            "signal": card.get("signal"),
            "help_type": card.get("help_type"),
            "learner_line": card.get("learner_line") or "",
            "tutor_reply": card.get("tutor_reply") or "",
            "speakable": card.get("speakable"),
            "prior_user": card.get("prior_user") or "",
            "prior_assistant": card.get("prior_assistant") or "",
        },
        "messages": [],
        "learner_turns": 0,
        "done": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def remaining_learner_turns(sitting: dict[str, Any]) -> int:
    used = int(sitting.get("learner_turns") or 0)
    return max(0, MAX_LEARNER_TURNS - used)


def start_sitting(
    *,
    card_id: str | None = None,
    cards_path: Path | None = None,
    state_path_override: Path | None = None,
) -> dict[str, Any]:
    """Begin a sitting. Optional card_id is a Chat snapshot or Learn starter.

    Practice Start (no card_id) resumes an in-progress sitting.
    Learn tap (explicit card_id) replaces it so the tap matches the UI.
    """
    with _lock:
        state = load_state(state_path_override)
        existing = _ram.get(_profile_key()) or state.get("sitting")
        chosen = str(card_id or "").strip()
        if isinstance(existing, dict) and existing.get("id") and not existing.get("done"):
            existing_id = str(existing.get("card_id") or "")
            if not chosen or chosen == existing_id:
                _ram[_profile_key()] = existing
                return existing
            state["sitting"] = None
            _ram.pop(_profile_key(), None)
        if isinstance(existing, dict) and existing.get("done"):
            done_id = str(existing.get("card_id") or "")
            used = list(state.get("used_card_ids") or [])
            if done_id and done_id not in used:
                used.append(done_id)
            state["used_card_ids"] = used
            state["sitting"] = None
            _ram.pop(_profile_key(), None)
            save_state(state, path=state_path_override)
        chosen = str(card_id or "").strip()
        if chosen:
            card = resolve_card(chosen, cards_path=cards_path)
            if not card:
                raise LookupError("unknown practice card")
        else:
            card, _fallback = pick_today_card(
                used_ids=state.get("used_card_ids"),
                cards_path=cards_path,
            )
        sitting = new_sitting(card)
        _ram[_profile_key()] = sitting
        state["sitting"] = sitting
        save_state(state, path=state_path_override)
        return sitting


def persist_sitting(
    sitting: dict[str, Any],
    *,
    state_path_override: Path | None = None,
) -> None:
    with _lock:
        _ram[_profile_key()] = sitting
        state = load_state(state_path_override)
        state["sitting"] = sitting
        save_state(state, path=state_path_override)


def append_learner_turn(sitting: dict[str, Any], text: str) -> dict[str, Any]:
    sitting.setdefault("messages", []).append(
        {"role": "user", "content": (text or "").strip()}
    )
    sitting["learner_turns"] = int(sitting.get("learner_turns") or 0) + 1
    if int(sitting["learner_turns"]) >= MAX_LEARNER_TURNS:
        sitting["done"] = True
    return sitting


def append_tutor_turn(sitting: dict[str, Any], text: str) -> dict[str, Any]:
    sitting.setdefault("messages", []).append(
        {"role": "assistant", "content": (text or "").strip()}
    )
    return sitting


def sitting_hit_speakable(sitting: dict[str, Any] | None) -> bool:
    """True if a learner turn overlaps the speakable (not うん)."""
    if not sitting:
        return False
    target = sitting_speakable(sitting)
    compact_t = re.sub(r"[\s。．.、,！!？?…・]+", "", target)
    runs = re.findall(r"[\u3040-\u30ff\u3400-\u9fff]{2,}", target)
    needles = [item for item in runs if item] or ([compact_t] if len(compact_t) >= 2 else [])
    if not needles:
        return False
    for message in sitting.get("messages") or []:
        if message.get("role") != "user":
            continue
        text = str(message.get("content") or "")
        if any(needle in text for needle in needles):
            return True
    return False


def peek_pending_elicit(path: Path | None = None) -> str:
    return str(load_state(path).get("pending_elicit") or "").strip()


def consume_pending_elicit(path: Path | None = None) -> str:
    with _lock:
        state = load_state(path)
        line = str(state.get("pending_elicit") or "").strip()
        if line:
            state["pending_elicit"] = ""
            save_state(state, path=path)
        return line


def finish_sitting(
    *,
    mark_used: bool | None = None,
    state_path_override: Path | None = None,
) -> dict[str, Any]:
    """Clear the active sitting. Marks used if they produced the line (or forced)."""
    with _lock:
        state = load_state(state_path_override)
        sitting = _ram.get(_profile_key()) or state.get("sitting")
        if not isinstance(sitting, dict):
            sitting = None
        turns = int((sitting or {}).get("learner_turns") or 0)
        card_id = str((sitting or {}).get("card_id") or "")
        speakable = sitting_speakable(sitting) if sitting else ""
        hit = sitting_hit_speakable(sitting)
        if mark_used is not None:
            should_mark = mark_used
        else:
            should_mark = hit
        if should_mark and card_id:
            used = list(state.get("used_card_ids") or [])
            if card_id not in used:
                used.append(card_id)
            state["used_card_ids"] = used
        survival = speakable in {SPEAKABLE_ETTO, SPEAKABLE_AGAIN}
        if should_mark and speakable and not survival:
            state["pending_elicit"] = speakable
        state["sitting"] = None
        save_state(state, path=state_path_override)
        _ram.pop(_profile_key(), None)
        return {
            "done": True,
            "marked_used": bool(should_mark and card_id),
            "card_id": card_id or None,
            "pending_elicit": str(state.get("pending_elicit") or ""),
            "speakable": speakable,
        }


def require_active(path: Path | None = None) -> dict[str, Any]:
    sitting = active_sitting(path)
    if not sitting or sitting.get("done"):
        raise LookupError("no active practice sitting")
    return sitting
