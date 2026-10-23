"""Course progress + spaced repetition, stored per learner in course_state.json.

Every taught phrase becomes two cards:
  listen — hear the Japanese, recall the meaning (comprehension)
  speak  — see the English, say the Japanese (production)

Scheduling is a plain Leitner ladder: a good answer moves a card up a box
(longer gap), a miss drops it back to box 1 (tomorrow). Simple, predictable,
and enough for a few hundred phrases.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from kaiwa import jsonio
from kaiwa.course.units import ROMAJI, UNITS

STATE_FILE = "course_state.json"
SKILLS = ("listen", "speak")
STEPS = ("learn", "listen", "speak")
BOX_DAYS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30, 6: 60, 7: 120}
MAX_BOX = max(BOX_DAYS)
MAX_DAYS_KEPT = 400

_PHRASES: dict[str, dict[str, Any]] = {}
_PHRASE_UNIT: dict[str, str] = {}
for _unit in UNITS:
    for _p in _unit["phrases"]:
        _PHRASES[_p["id"]] = {**_p, "ro": ROMAJI.get(_p["id"], "")}
        _PHRASE_UNIT[_p["id"]] = _unit["id"]


def state_path() -> Path:
    from kaiwa.profiles import active_profile_dir

    return active_profile_dir() / STATE_FILE


def _today() -> date:
    return date.today()


def _empty() -> dict[str, Any]:
    return {"version": 1, "units": {}, "cards": {}, "days": []}


def load_state(path: Path | None = None) -> dict[str, Any]:
    raw = jsonio.read_json_dict(path or state_path())
    if raw is None:
        return _empty()
    state = _empty()
    if isinstance(raw.get("units"), dict):
        state["units"] = raw["units"]
    if isinstance(raw.get("cards"), dict):
        state["cards"] = {k: v for k, v in raw["cards"].items() if isinstance(v, dict)}
    if isinstance(raw.get("days"), list):
        state["days"] = [str(d) for d in raw["days"]][-MAX_DAYS_KEPT:]
    return state


def save_state(state: dict[str, Any], path: Path | None = None) -> None:
    jsonio.write_json_atomic(path or state_path(), state)


def phrase(phrase_id: str) -> dict[str, Any] | None:
    p = _PHRASES.get(phrase_id)
    return dict(p) if p else None


def unit_by_id(unit_id: str) -> dict[str, Any] | None:
    return next((u for u in UNITS if u["id"] == unit_id), None)


def public_unit(unit: dict[str, Any]) -> dict[str, Any]:
    """Unit content for the client: phrases carry romaji; order index for display."""
    index = next(i for i, u in enumerate(UNITS) if u["id"] == unit["id"])
    return {
        **{k: unit[k] for k in ("id", "title", "title_jp", "goal", "dialogue", "questions", "speak")},
        "number": index + 1,
        "phrases": [phrase(p["id"]) for p in unit["phrases"]],
    }


def _mark_day(state: dict[str, Any]) -> None:
    today = _today().isoformat()
    if today not in state["days"]:
        state["days"] = (state["days"] + [today])[-MAX_DAYS_KEPT:]


def _with_state(fn, path: Path | None = None):
    with jsonio.STATE_LOCK:
        state = load_state(path)
        result = fn(state)
        save_state(state, path)
        return result


def complete_step(unit_id: str, step: str, *, path: Path | None = None) -> dict[str, Any]:
    """Record a finished lesson step. Finishing `learn` schedules the unit's cards."""
    if step not in STEPS:
        raise ValueError(f"unknown step: {step}")
    unit = unit_by_id(unit_id)
    if unit is None:
        raise KeyError(f"unknown unit: {unit_id}")

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        row = state["units"].setdefault(unit_id, {})
        row[step] = True
        if step == "learn":
            due = (_today() + timedelta(days=BOX_DAYS[1])).isoformat()
            for p in unit["phrases"]:
                for skill in SKILLS:
                    state["cards"].setdefault(
                        f"{p['id']}:{skill}",
                        {"box": 1, "due": due, "reps": 0, "lapses": 0, "last": ""},
                    )
        if all(row.get(s) for s in STEPS) and not row.get("done_at"):
            row["done_at"] = datetime.now(timezone.utc).isoformat()
        _mark_day(state)
        return row

    return _with_state(apply, path)


def grade(card_id: str, good: bool, *, path: Path | None = None) -> dict[str, Any]:
    phrase_id, _, skill = card_id.partition(":")
    if phrase_id not in _PHRASES or skill not in SKILLS:
        raise KeyError(f"unknown card: {card_id}")

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        card = state["cards"].setdefault(
            card_id, {"box": 1, "due": "", "reps": 0, "lapses": 0, "last": ""}
        )
        box = int(card.get("box") or 1)
        if good:
            box = min(MAX_BOX, box + 1)
        else:
            box = 1
            card["lapses"] = int(card.get("lapses") or 0) + 1
        card["box"] = box
        card["reps"] = int(card.get("reps") or 0) + 1
        card["due"] = (_today() + timedelta(days=BOX_DAYS[box])).isoformat()
        card["last"] = datetime.now(timezone.utc).isoformat()
        _mark_day(state)
        return dict(card)

    return _with_state(apply, path)


def due_cards(state: dict[str, Any], *, limit: int = 20) -> list[dict[str, Any]]:
    """Cards due today or earlier, oldest first; a phrase's two sides never adjacent."""
    today = _today().isoformat()
    rows = []
    for card_id, card in state["cards"].items():
        phrase_id, _, skill = card_id.partition(":")
        p = _PHRASES.get(phrase_id)
        if not p or skill not in SKILLS or str(card.get("due") or "") > today:
            continue
        rows.append((str(card.get("due") or ""), int(card.get("box") or 1), card_id, skill, p))
    rows.sort(key=lambda r: (r[0], r[1]))
    picked = rows[:limit]
    ordered: list[tuple] = []
    pending = list(picked)
    while pending:
        last = ordered[-1][4]["id"] if ordered else None
        idx = next((i for i, r in enumerate(pending) if r[4]["id"] != last), 0)
        ordered.append(pending.pop(idx))
    return [{"card_id": r[2], "skill": r[3], "box": r[1], "phrase": phrase(r[4]["id"])} for r in ordered]


def next_unit(state: dict[str, Any]) -> dict[str, Any] | None:
    for unit in UNITS:
        if not state["units"].get(unit["id"], {}).get("done_at"):
            return unit
    return None


def streak(state: dict[str, Any]) -> int:
    days = set(state["days"])
    cur = _today()
    if cur.isoformat() not in days:
        cur -= timedelta(days=1)
    n = 0
    while cur.isoformat() in days:
        n += 1
        cur -= timedelta(days=1)
    return n


def learned_phrase_ids(state: dict[str, Any]) -> list[str]:
    """Phrases the learner has been taught, in course order."""
    seen = {cid.partition(":")[0] for cid in state["cards"]}
    return [pid for pid in _PHRASES if pid in seen]


def stats(state: dict[str, Any]) -> dict[str, Any]:
    learned = learned_phrase_ids(state)
    strong = {
        cid.partition(":")[0]
        for cid, card in state["cards"].items()
        if int(card.get("box") or 1) >= 3
    }
    return {
        "phrases_learned": len(learned),
        "phrases_strong": len([p for p in learned if p in strong]),
        "phrases_total": len(_PHRASES),
        "units_done": sum(1 for u in UNITS if state["units"].get(u["id"], {}).get("done_at")),
        "units_total": len(UNITS),
        "streak": streak(state),
        "studied_today": _today().isoformat() in state["days"],
    }


def today_payload(*, review_limit: int = 20, path: Path | None = None) -> dict[str, Any]:
    state = load_state(path)
    unit = next_unit(state)
    due = due_cards(state, limit=review_limit)
    all_due = len(due_cards(state, limit=10_000))
    return {
        "stats": stats(state),
        "review": due,
        "review_total": all_due,
        "unit": public_unit(unit) if unit else None,
        "unit_steps": dict(state["units"].get(unit["id"], {})) if unit else {},
    }


def known_phrases_for_chat(*, limit: int = 40, path: Path | None = None) -> list[dict[str, str]]:
    """What Chat may assume the learner understands (most recent units first)."""
    state = load_state(path)
    ids = learned_phrase_ids(state)[-limit:]
    return [{"jp": _PHRASES[i]["jp"], "en": _PHRASES[i]["en"]} for i in ids]
