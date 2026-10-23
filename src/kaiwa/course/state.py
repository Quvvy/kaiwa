"""Course progress + spaced repetition, stored per learner in course_state.json.

Card kinds (id = "<item>:<skill>"):
  phrase  "u1.ohayou:listen" / ":speak"  hear → meaning, English → say it
  word    "u1w.asa:mean"                 see/hear the word → pick its meaning
  kana    "kana.あ:read"                  see the character → pick its sound

Scheduling is FSRS (see srs.py): each card's memory is modelled and the next
review lands where recall is ~90%. Grades come from how the learner answered,
never from buttons. New and missed cards take short learning steps first; the
day's Recap step gives them their second look.

A unit's steps come from its content (learn, words, grammar, listen, speak), so
units written in the newer template gain steps without resetting older progress.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from kaiwa import jsonio
from kaiwa.course import srs
from kaiwa.course.kana import KANA_LESSONS, KANA_ROMAJI, LESSON_BY_ID, lesson_chars
from kaiwa.course.units import ROMAJI, UNITS

STATE_FILE = "course_state.json"
SKILLS = ("listen", "speak")
STEP_ORDER = ("learn", "words", "grammar", "listen", "speak")
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
    return {"version": 2, "units": {}, "cards": {}, "days": [], "kana": {}, "questions": [], "reviewed": {}, "timing": {}}


def load_state(path: Path | None = None) -> dict[str, Any]:
    raw = jsonio.read_json_dict(path or state_path())
    if raw is None:
        return _empty()
    state = _empty()
    if isinstance(raw.get("units"), dict):
        state["units"] = raw["units"]
    if isinstance(raw.get("cards"), dict):
        # Leitner cards from before FSRS convert here, keeping their progress.
        state["cards"] = {k: srs.ensure(v) for k, v in raw["cards"].items() if isinstance(v, dict)}
    if isinstance(raw.get("timing"), dict):
        state["timing"] = {str(k): [int(x) for x in v if str(x).isdigit()] for k, v in raw["timing"].items() if isinstance(v, list)}
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
    return srs.new_card()


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
        row[f"{step}_on"] = _today().isoformat()  # day-two steps wait until after this day
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


def grade(
    card_id: str,
    *,
    correct: bool,
    ms: int | None = None,
    helped: bool = False,
    guessed: bool = False,
    band: str = "",
    fmt: str = "",
    path: Path | None = None,
) -> dict[str, Any]:
    """Apply one answer. The FSRS grade is worked out here (srs.rating_for).

    Returns the card plus `rating` and `again_soon` (due within the session:
    the client shows it again a few cards later).
    """
    kind = _card_kind(card_id)
    if kind is None:
        raise KeyError(f"unknown card: {card_id}")
    fmt = fmt or f"{kind[0]}:{kind[2]}"

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        card = state["cards"].get(card_id) or _new_card()  # lessons may grade before the step finishes
        if not srs.is_learning(card):
            # Only real reviews spend the daily budget; learning steps are part of the lesson.
            today = _today().isoformat()
            spent = state["reviewed"].get(today, 0) + card_cost(kind[0], kind[2])
            state["reviewed"] = {today: spent}
        rating = srs.rating_for(
            correct=correct, ms=ms, helped=helped, guessed=guessed, band=band,
            reps=int(card.get("reps") or 0), times=state["timing"].get(fmt, []),
        )
        srs.record_time(state["timing"], fmt, ms, correct and not (helped or guessed))
        card = srs.review(card, rating)
        state["cards"][card_id] = card
        _mark_day(state)
        soon = srs.due_at(card) - datetime.now(timezone.utc) < timedelta(minutes=30)
        return {**card, "rating": rating, "again_soon": soon}

    return _with_state(apply, path)


def _card_payload(kind: str, item: str) -> dict[str, Any]:
    if kind == "phrase":
        return {"phrase": phrase(item)}
    if kind == "word":
        return {"word": dict(_WORDS[item])}
    return {"kana": {"char": item, "ro": KANA_ROMAJI[item]}}


def answer_format(kind: str, skill: str, card: dict[str, Any]) -> str:
    """How the card is answered: recognise while new, produce once it's known.

    choice   pick from options (new kana and words; hearing a phrase)
    produce  say or type the answer (known kana: its sound; known words: the Japanese)
    speak    say the phrase (the speaking side of a phrase)
    """
    if kind == "phrase":
        return "speak" if skill == "speak" else "choice"
    return "produce" if srs.known(card) else "choice"


def _card_row(card_id: str, kind: tuple[str, str, str], card: dict[str, Any]) -> dict[str, Any]:
    return {
        "card_id": card_id, "kind": kind[0], "skill": kind[2],
        "format": answer_format(kind[0], kind[2], card),
        "stability": round(srs.stability(card), 1),
        **_card_payload(kind[0], kind[1]),
    }


def due_cards(state: dict[str, Any], *, limit: int = 20, budget: int | None = None) -> list[dict[str, Any]]:
    """Due cards, most-forgotten first (lowest box, then oldest), within `budget` if given.

    A phrase's two sides are never back to back.
    """
    today = _today().isoformat()
    rows = []
    for card_id, card in state["cards"].items():
        kind = _card_kind(card_id)
        if kind is None or srs.is_learning(card) or str(card.get("due") or "") > today:
            continue
        # Weakest memories first (lowest stability), then the most overdue.
        rows.append((srs.stability(card), str(card.get("due") or ""), card_id, kind))
    rows.sort(key=lambda r: (r[0], r[1]))
    if budget is not None:
        # Take turns between kana, words and phrases so one kind never fills the day.
        lanes: dict[str, list[tuple]] = {}
        for row in rows:
            lanes.setdefault(row[3][0], []).append(row)
        mixed: list[tuple] = []
        while any(lanes.values()):
            for lane in lanes.values():
                if lane:
                    mixed.append(lane.pop(0))
        rows = mixed
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
    return [_card_row(r[2], r[3], state["cards"][r[2]]) for r in ordered]


RECAP_LIMIT = 40


def recap_cards(state: dict[str, Any]) -> list[dict[str, Any]]:
    """New and just-missed cards in their short learning steps: today's second look."""
    today = _today().isoformat()
    rows = []
    for card_id, card in state["cards"].items():
        kind = _card_kind(card_id)
        if kind and srs.is_learning(card) and str(card.get("due") or "") <= today:
            rows.append((srs.due_at(card), card_id, kind))
    rows.sort(key=lambda r: r[0])
    return [_card_row(r[1], r[2], state["cards"][r[1]]) for r in rows[:RECAP_LIMIT]]


# ---------- pacing ----------
# New review cards a day can add. A unit's day one is 22-26 (6 phrases, 16-20
# words) and day two adds none, so this averages ~16 a day. Kana lessons of up
# to 6-10 characters fit beside a day one; longer ones alternate with units.
NEW_ITEMS_PER_DAY = 32
# When the due backlog is worth more than two days of reviews, that day is a
# catch-up day: no new material is planned, and the review budget doubles.
CATCH_UP_COST = DAILY_REVIEW_BUDGET * 2
DAY_ONE_STEPS = ("learn", "words")


def due_cost(state: dict[str, Any]) -> int:
    return sum(card_cost(c["kind"], c["skill"]) for c in due_cards(state, limit=10_000))


def catching_up(state: dict[str, Any]) -> bool:
    return due_cost(state) > CATCH_UP_COST


def todays_reviews(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Today's share of due cards: what fits in the budget left after today's reviews."""
    spent = state["reviewed"].get(_today().isoformat(), 0)
    budget = DAILY_REVIEW_BUDGET * (2 if catching_up(state) else 1)
    return due_cards(state, limit=80, budget=max(0, budget - spent))


def _new_items(unit: dict[str, Any], step: str) -> int:
    return {"learn": len(unit["phrases"]), "words": len(unit.get("words", []))}.get(step, 0)


def plan_today(state: dict[str, Any]) -> dict[str, Any]:
    """Which steps today's lesson should run, in order, and why some are held back.

    Rules: reviews first; a unit's day-one steps (phrases, words) and day-two
    steps (grammar, listening, speaking) fall on different days; new items stay
    under NEW_ITEMS_PER_DAY, alternating with the kana lesson when both don't fit;
    on a catch-up day only reviews are planned. Nothing here locks anything: the
    home screen can still open any step.
    """
    today = _today()
    iso = today.isoformat()
    yesterday = (today - timedelta(days=1)).isoformat()
    unit = next_unit(state)
    kana = next_kana_lesson(state)
    plan: list[str] = []
    if todays_reviews(state):
        plan.append("review")
    if catching_up(state):
        if recap_cards(state):
            plan.append("recap")
        return {"plan": plan, "catching_up": True, "day_two_tomorrow": False}

    kana_wanted = bool(kana) and iso not in state["kana"].values()
    kana_new = len(kana["kana"]) if kana else 0
    row = state["units"].get(unit["id"], {}) if unit else {}
    steps = unit_steps(unit) if unit else []
    day_one = [s for s in steps if s in DAY_ONE_STEPS and not row.get(s)]
    day_two = [s for s in steps if s not in DAY_ONE_STEPS and not row.get(s)]
    day_one_today = any(row.get(f"{s}_on") == iso for s in DAY_ONE_STEPS if s in steps)
    unit_new = sum(_new_items(unit, s) for s in day_one) if unit else 0

    unit_plan: list[str] = []
    day_two_tomorrow = False
    if day_one:
        unit_plan = day_one
    elif day_two and not day_one_today:
        unit_plan = day_two
    elif day_two:
        day_two_tomorrow = True

    if kana_wanted and unit_plan and unit_new and kana_new + unit_new > NEW_ITEMS_PER_DAY:
        # Both don't fit: alternate, starting with whichever didn't happen yesterday.
        if yesterday in state["kana"].values():
            kana_wanted = False
        else:
            unit_plan = []
    if kana_wanted:
        plan.append("kana")
    plan.extend(unit_plan)
    if unit_plan or kana_wanted or recap_cards(state):
        # After the new material: a second look at today's new and missed cards.
        plan.append("recap")
    return {"plan": plan, "catching_up": False, "day_two_tomorrow": day_two_tomorrow}


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
        if srs.stability(card) >= 7
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
        "phrases_pool": [{"jp": _PHRASES[i]["jp"], "en": _PHRASES[i]["en"]} for i in learned_phrase_ids(state)],
        "recap": recap_cards(state),
        **plan_today(state),
    }


def word_targets(card_ids: list[str]) -> list[dict[str, str]]:
    """Word cards → {card_id, jp, en} (other ids are ignored)."""
    out = []
    for card_id in card_ids:
        kind = _card_kind(card_id)
        if kind and kind[0] == "word":
            w = _WORDS[kind[1]]
            out.append({"card_id": card_id, "jp": w["jp"], "en": w["en"]})
    return out


def known_vocab(*, path: Path | None = None) -> tuple[list[str], list[str]]:
    """(learned words, learned phrases) in Japanese, for generating practice."""
    state = load_state(path)
    words = [w["jp"] for wid, w in _WORDS.items() if f"{wid}:mean" in state["cards"]]
    phrases = [_PHRASES[p]["jp"] for p in learned_phrase_ids(state)]
    return words, phrases


def known_phrases_for_chat(*, limit: int = 40, path: Path | None = None) -> list[dict[str, str]]:
    """What Chat may assume the learner understands (most recent units first)."""
    state = load_state(path)
    ids = learned_phrase_ids(state)[-limit:]
    return [{"jp": _PHRASES[i]["jp"], "en": _PHRASES[i]["en"]} for i in ids]
