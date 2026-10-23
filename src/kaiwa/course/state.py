"""Course progress + spaced repetition, stored per learner in course_state.json.

Card kinds (id = "<item>:<skill>"):
  phrase  "u1.ohayou:listen" / ":speak"  hear → meaning, English → say it
  word    "u1w.asa:mean"                 see/hear the word → pick its meaning
  kana    "kana.あ:read"                  see the character → pick its sound

Scheduling is a plain Leitner ladder: a good answer moves a card up a box
(longer gap), a miss drops it back to box 1 (tomorrow). Simple, predictable,
and enough for a few hundred phrases.

A unit's steps come from its content (learn, words, grammar, listen, speak), so
units written in the newer template gain steps without resetting older progress.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from kaiwa import jsonio
from kaiwa.course.kana import KANA_LESSONS, KANA_ROMAJI, LESSON_BY_ID, lesson_chars
from kaiwa.course.units import ROMAJI, UNITS

STATE_FILE = "course_state.json"
SKILLS = ("listen", "speak")
STEP_ORDER = ("learn", "words", "grammar", "listen", "speak")
BOX_DAYS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30, 6: 60, 7: 120}
MAX_BOX = max(BOX_DAYS)
MAX_DAYS_KEPT = 400

_PHRASES: dict[str, dict[str, Any]] = {}
_PHRASE_UNIT: dict[str, str] = {}
_WORDS: dict[str, dict[str, Any]] = {}
for _unit in UNITS:
    for _p in _unit["phrases"]:
        _PHRASES[_p["id"]] = {**_p, "ro": ROMAJI.get(_p["id"], "")}
        _PHRASE_UNIT[_p["id"]] = _unit["id"]
    for _w in _unit.get("words", []):
        _WORDS[_w["id"]] = dict(_w)


def state_path() -> Path:
    from kaiwa.profiles import active_profile_dir

    return active_profile_dir() / STATE_FILE


def _today() -> date:
    return date.today()


MAX_QUESTIONS_KEPT = 200

# Daily review budget, in rough "seconds/3" units: a kana or word card takes a
# few seconds, hearing a phrase a little longer, saying one longest. 30 ≈ five
# minutes. Due cards beyond it wait for later days instead of piling up, so a
# missed week never turns into a wall of reviews.
DAILY_REVIEW_BUDGET = 30
CARD_COST = {"kana": 1, "word": 1, "listen": 2, "speak": 3}


def card_cost(kind: str, skill: str) -> int:
    return CARD_COST.get(kind if kind != "phrase" else skill, 2)


def _empty() -> dict[str, Any]:
    return {"version": 1, "units": {}, "cards": {}, "days": [], "kana": {}, "questions": [], "reviewed": {}}


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
    if isinstance(raw.get("kana"), dict):
        state["kana"] = {k: str(v) for k, v in raw["kana"].items() if k in LESSON_BY_ID}
    if isinstance(raw.get("reviewed"), dict):
        state["reviewed"] = {str(k): int(v) for k, v in raw["reviewed"].items() if str(v).isdigit()}
    if isinstance(raw.get("questions"), list):
        state["questions"] = [q for q in raw["questions"] if isinstance(q, dict)][-MAX_QUESTIONS_KEPT:]
    return state


def log_question(question: str, context: dict[str, Any], *, path: Path | None = None) -> None:
    """Keep what the learner asks about: repeated confusion marks a weak spot."""

    def apply(state: dict[str, Any]) -> None:
        state["questions"] = (state["questions"] + [{
            "q": question[:300],
            "screen": str(context.get("screen") or "")[:40],
            "item": str(context.get("jp") or context.get("title") or "")[:120],
            "at": datetime.now(timezone.utc).isoformat(),
        }])[-MAX_QUESTIONS_KEPT:]

    _with_state(apply, path)


def save_state(state: dict[str, Any], path: Path | None = None) -> None:
    jsonio.write_json_atomic(path or state_path(), state)


def phrase(phrase_id: str) -> dict[str, Any] | None:
    p = _PHRASES.get(phrase_id)
    return dict(p) if p else None


def unit_by_id(unit_id: str) -> dict[str, Any] | None:
    return next((u for u in UNITS if u["id"] == unit_id), None)


def unit_steps(unit: dict[str, Any]) -> list[str]:
    """Steps this unit has content for, in lesson order."""
    has = {
        "learn": True,
        "words": bool(unit.get("words")),
        "grammar": bool(unit.get("grammar")),
        "listen": True,
        "speak": True,
    }
    return [s for s in STEP_ORDER if has[s]]


def public_unit(unit: dict[str, Any]) -> dict[str, Any]:
    """Unit content for the client: phrases carry romaji; order index for display."""
    index = next(i for i, u in enumerate(UNITS) if u["id"] == unit["id"])
    return {
        **{k: unit[k] for k in ("id", "title", "title_jp", "goal", "dialogue", "questions", "speak")},
        "words": unit.get("words", []),
        "grammar": unit.get("grammar", []),
        "drill": unit.get("drill", []),
        "steps": unit_steps(unit),
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


def _new_card() -> dict[str, Any]:
    due = (_today() + timedelta(days=BOX_DAYS[1])).isoformat()
    return {"box": 1, "due": due, "reps": 0, "lapses": 0, "last": ""}


def unit_done(state: dict[str, Any], unit: dict[str, Any]) -> bool:
    row = state["units"].get(unit["id"], {})
    return all(row.get(s) for s in unit_steps(unit))


def complete_step(unit_id: str, step: str, *, path: Path | None = None) -> dict[str, Any]:
    """Record a finished lesson step. `learn` and `words` schedule their cards."""
    unit = unit_by_id(unit_id)
    if unit is None:
        raise KeyError(f"unknown unit: {unit_id}")
    if step not in unit_steps(unit):
        raise ValueError(f"unknown step: {step}")

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        row = state["units"].setdefault(unit_id, {})
        row[step] = True
        if step == "learn":
            for p in unit["phrases"]:
                for skill in SKILLS:
                    state["cards"].setdefault(f"{p['id']}:{skill}", _new_card())
        if step == "words":
            for w in unit.get("words", []):
                state["cards"].setdefault(f"{w['id']}:mean", _new_card())
        if unit_done(state, unit):
            row.setdefault("done_at", datetime.now(timezone.utc).isoformat())
        _mark_day(state)
        return row

    return _with_state(apply, path)


def complete_kana(lesson_id: str, *, path: Path | None = None) -> dict[str, Any]:
    """Record a finished kana lesson and schedule a card per character."""
    lesson = LESSON_BY_ID.get(lesson_id)
    if lesson is None:
        raise KeyError(f"unknown kana lesson: {lesson_id}")

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        state["kana"].setdefault(lesson_id, _today().isoformat())
        for ch, _ in lesson["kana"]:
            state["cards"].setdefault(f"kana.{ch}:read", _new_card())
        _mark_day(state)
        return kana_progress(state)

    return _with_state(apply, path)


def _card_kind(card_id: str) -> tuple[str, str, str] | None:
    """(kind, item, skill) for a valid card id, else None."""
    item, _, skill = card_id.partition(":")
    if item in _PHRASES and skill in SKILLS:
        return "phrase", item, skill
    if item in _WORDS and skill == "mean":
        return "word", item, skill
    if item.startswith("kana.") and item[5:] in KANA_ROMAJI and skill == "read":
        return "kana", item[5:], skill
    return None


def grade(card_id: str, good: bool, *, path: Path | None = None) -> dict[str, Any]:
    kind = _card_kind(card_id)
    if kind is None:
        raise KeyError(f"unknown card: {card_id}")

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        today = _today().isoformat()
        spent = state["reviewed"].get(today, 0) + card_cost(kind[0], kind[2])
        state["reviewed"] = {today: spent}  # only today's spend matters
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


def _card_payload(kind: str, item: str) -> dict[str, Any]:
    if kind == "phrase":
        return {"phrase": phrase(item)}
    if kind == "word":
        return {"word": dict(_WORDS[item])}
    return {"kana": {"char": item, "ro": KANA_ROMAJI[item]}}


def due_cards(state: dict[str, Any], *, limit: int = 20, budget: int | None = None) -> list[dict[str, Any]]:
    """Due cards, most-forgotten first (lowest box, then oldest), within `budget` if given.

    A phrase's two sides are never back to back.
    """
    today = _today().isoformat()
    rows = []
    for card_id, card in state["cards"].items():
        kind = _card_kind(card_id)
        if kind is None or str(card.get("due") or "") > today:
            continue
        rows.append((int(card.get("box") or 1), str(card.get("due") or ""), card_id, kind))
    rows.sort(key=lambda r: (r[0], r[1]))
    picked = []
    left = budget
    for row in rows:
        if len(picked) >= limit:
            break
        if left is not None:
            cost = card_cost(row[3][0], row[3][2])
            if cost > left:
                continue
            left -= cost
        picked.append(row)
    ordered: list[tuple] = []
    pending = list(picked)
    while pending:
        last = ordered[-1][3][1] if ordered else None
        idx = next((i for i, r in enumerate(pending) if r[3][1] != last), 0)
        ordered.append(pending.pop(idx))
    return [
        {"card_id": r[2], "kind": r[3][0], "skill": r[3][2], "box": r[0], **_card_payload(r[3][0], r[3][1])}
        for r in ordered
    ]


def todays_reviews(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Today's share of due cards: what fits in the budget left after today's reviews."""
    spent = state["reviewed"].get(_today().isoformat(), 0)
    return due_cards(state, limit=60, budget=max(0, DAILY_REVIEW_BUDGET - spent))


def next_unit(state: dict[str, Any]) -> dict[str, Any] | None:
    for unit in UNITS:
        if not unit_done(state, unit):
            return unit
    return None


def next_kana_lesson(state: dict[str, Any]) -> dict[str, Any] | None:
    for lesson in KANA_LESSONS:
        if lesson["id"] not in state["kana"]:
            return lesson
    return None


def known_chars(state: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for lesson in KANA_LESSONS:
        if lesson["id"] in state["kana"]:
            out |= lesson_chars(lesson)
    return out


def kana_progress(state: dict[str, Any]) -> dict[str, Any]:
    def count(script: str) -> tuple[int, int]:
        lessons = [l for l in KANA_LESSONS if l["script"] == script]
        done = sum(len(l["kana"]) for l in lessons if l["id"] in state["kana"])
        return done, sum(len(l["kana"]) for l in lessons)

    h_done, h_total = count("hiragana")
    k_done, k_total = count("katakana")
    return {
        "lessons_done": len(state["kana"]),
        "lessons_total": len(KANA_LESSONS),
        "hiragana": [h_done, h_total],
        "katakana": [k_done, k_total],
    }


def public_kana_lesson(lesson: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    index = KANA_LESSONS.index(lesson)
    return {
        "id": lesson["id"],
        "number": index + 1,
        "script": lesson["script"],
        "title": lesson["title"],
        "note": lesson["note"],
        "kana": [{"char": ch, "ro": ro} for ch, ro in lesson["kana"]],
        "words": lesson["words"],
        # Earlier characters, so drills can mix new ones with ones you know.
        "known": [{"char": ch, "ro": ro} for l in KANA_LESSONS[:index] for ch, ro in l["kana"]
                  if l["script"] == lesson["script"]],
    }


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
    words = [w for w in _WORDS if f"{w}:mean" in state["cards"]]
    return {
        "phrases_learned": len(learned),
        "phrases_strong": len([p for p in learned if p in strong]),
        "phrases_total": len(_PHRASES),
        "words_learned": len(words),
        "units_done": sum(1 for u in UNITS if unit_done(state, u)),
        "units_total": len(UNITS),
        "streak": streak(state),
        "studied_today": _today().isoformat() in state["days"],
    }


def today_payload(*, path: Path | None = None) -> dict[str, Any]:
    state = load_state(path)
    unit = next_unit(state)
    due = todays_reviews(state)
    all_due = len(due_cards(state, limit=10_000))
    kana = next_kana_lesson(state)
    today = _today().isoformat()
    return {
        "stats": stats(state),
        "review": due,
        "review_total": all_due,
        "unit": public_unit(unit) if unit else None,
        "unit_steps": dict(state["units"].get(unit["id"], {})) if unit else {},
        "kana": public_kana_lesson(kana, state) if kana else None,
        # One kana lesson a day is the plan; more is allowed from the home screen.
        "kana_done_today": today in state["kana"].values(),
        "kana_progress": kana_progress(state),
        "kana_known": "".join(sorted(known_chars(state))),
        "kana_pool": [{"char": ch, "ro": KANA_ROMAJI[ch]} for l in KANA_LESSONS if l["id"] in state["kana"]
                      for ch, _ in l["kana"]],
        "words_pool": [{"jp": w["jp"], "en": w["en"]} for wid, w in _WORDS.items() if f"{wid}:mean" in state["cards"]],
    }


def known_phrases_for_chat(*, limit: int = 40, path: Path | None = None) -> list[dict[str, str]]:
    """What Chat may assume the learner understands (most recent units first)."""
    state = load_state(path)
    ids = learned_phrase_ids(state)[-limit:]
    return [{"jp": _PHRASES[i]["jp"], "en": _PHRASES[i]["en"]} for i in ids]
