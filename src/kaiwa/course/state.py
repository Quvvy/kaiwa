"""Course progress + spaced repetition, stored per learner in course_state.json.

Card kinds (id = "<item>:<skill>"):
  phrase  "u1.ohayou:listen" / ":speak"  hear → meaning, English → say it
  word    "u1w.asa:mean"                 see/hear the word → pick its meaning
  kana    "kana.あ:read"                  see the character → pick its sound
  grammar "u4g.ga:build"                 English → put the Japanese together (see build.py)

Scheduling is FSRS (see srs.py): each card's memory is modelled and the next
review lands where recall is ~87%. Grades come from how the learner answered,
never from buttons. New and missed cards take short learning steps first; the
day's Recap step gives them their second look.

A unit's steps come from its content (learn, words, grammar, listen, speak), so
units written in the newer template gain steps without resetting older progress.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from kaiwa import jsonio
from kaiwa.course import build, drills, grader, my_phrases, srs
from kaiwa.course.kana import KANA_LESSONS, KANA_ROMAJI, LESSON_BY_ID, lesson_chars
from kaiwa.course.kana_hooks import alike, hook_for
from kaiwa.course.missions import MISSIONS
from kaiwa.course.units import ROMAJI, UNITS

STATE_FILE = "course_state.json"
SKILLS = ("listen", "speak")
STEP_ORDER = ("learn", "words", "grammar", "listen", "speak")
MAX_DAYS_KEPT = 400

_PHRASES: dict[str, dict[str, Any]] = {}  # the course's, plus learners' own as profiles load
_PHRASE_UNIT: dict[str, str] = {}
_WORDS: dict[str, dict[str, Any]] = {}
_WORD_UNIT: dict[str, str] = {}
_GRAMMAR: dict[str, dict[str, Any]] = {}
for _unit in UNITS:
    for _g in _unit.get("grammar", []):
        if build.items_for(_g["id"]):
            _GRAMMAR[_g["id"]] = {"id": _g["id"], "title": _g["title"], "rule": _g.get("rule", ""), "unit": _unit["id"],
                                  "items": build.items_for(_g["id"])}
for _unit in UNITS:
    for _p in _unit["phrases"]:
        _PHRASES[_p["id"]] = {**_p, "ro": ROMAJI.get(_p["id"], "")}
        _PHRASE_UNIT[_p["id"]] = _unit["id"]
    for _w in _unit.get("words", []):
        _WORDS[_w["id"]] = dict(_w)
        _WORD_UNIT[_w["id"]] = _unit["id"]


COURSE_PHRASES = sum(len(_u["phrases"]) for _u in UNITS)


def state_path() -> Path:
    from kaiwa.profiles import active_profile_dir

    return active_profile_dir() / STATE_FILE


def _today() -> date:
    return srs.study_day(srs._now())


MAX_QUESTIONS_KEPT = 200

# Leeches: cards forgotten this many times after being learned get extra help
# (a breakdown and a memory hook) and go back to recognition until stable.
LEECH_LAPSES = 4
LEECH_STABLE_DAYS = 3
# Review log for retention stats: one small row per real review.
LOG_KEPT = 3000
RETUNE_EVERY = 10    # refit the auto-grader every N answers (and after every grade change)
UNDO_KEPT = 20       # answers Ctrl+Z can take back (survives a refresh)
OVERRIDES_KEPT = 500  # "Kaiwa picked X, I chose Y": for tuning the auto-grader later
DAILY_KEPT = 400
RETENTION_DAYS = 30
RETENTION_MIN_REVIEWS = 20

# Daily review budget (see PACES), in rough "seconds/3" units: a kana or word card
# takes a few seconds, hearing a phrase a little longer, saying one longest. 30 ≈
# five minutes. Due cards beyond it wait for later days instead of piling up, so a
# missed week never turns into a wall of reviews.
CARD_COST = {"kana": 1, "word": 1, "listen": 2, "speak": 3, "grammar": 2}


def card_cost(kind: str, skill: str) -> int:
    return CARD_COST.get(kind if kind != "phrase" else skill, 2)


def _empty() -> dict[str, Any]:
    return {"version": 2, "units": {}, "cards": {}, "days": [], "kana": {}, "questions": [], "reviewed": {}, "timing": {}, "log": [],
            "undo": [], "overrides": [], "daily": {}, "seq": 0, "grades": [], "grader": None,
            "checks": {}, "listening": {"recent": [], "total_ms": 0}, "bests": {}, "mine": []}


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
    for key in ("undo", "overrides"):
        if isinstance(raw.get(key), list):
            state[key] = [r for r in raw[key] if isinstance(r, dict)][-(UNDO_KEPT if key == "undo" else OVERRIDES_KEPT):]
    if isinstance(raw.get("daily"), dict):
        state["daily"] = {k: v for k, v in raw["daily"].items() if isinstance(v, dict)}
    state["seq"] = int(raw.get("seq") or 0)
    if isinstance(raw.get("grades"), list):
        state["grades"] = [r for r in raw["grades"] if isinstance(r, dict)][-grader.ROWS_KEPT:]
    if isinstance(raw.get("grader"), dict):
        state["grader"] = raw["grader"]
    if isinstance(raw.get("placement"), dict):
        state["placement"] = raw["placement"]
    if raw.get("pace") in PACES:
        state["pace"] = raw["pace"]
    if isinstance(raw.get("bests"), dict):
        state["bests"] = {str(k): int(v) for k, v in raw["bests"].items() if str(v).isdigit()}
    state["mine"] = my_phrases.clean_kept(raw.get("mine"))
    for row in state["mine"]:
        _PHRASES[row["id"]] = row
    if isinstance(raw.get("listening"), dict):
        lst = raw["listening"]
        state["listening"] = {"recent": [str(s) for s in lst.get("recent") or []][-LISTEN_RECENT_KEPT:],
                              "total_ms": int(lst.get("total_ms") or 0)}
    if isinstance(raw.get("checks"), dict):
        state["checks"] = {k: v for k, v in raw["checks"].items() if isinstance(v, dict)}
    if isinstance(raw.get("log"), list):
        state["log"] = [r for r in raw["log"] if isinstance(r, dict)][-LOG_KEPT:]
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
    _backfill_grammar(state)
    return state


GRAMMAR_BACKFILL_STABILITY = 7.0
GRAMMAR_BACKFILL_SPREAD = 14


def _backfill_grammar(state: dict[str, Any]) -> None:
    """Grammar taught before grammar had reviews joins the schedule, spread over two weeks."""
    today = _today()
    n = 0
    for unit in UNITS:
        if not state["units"].get(unit["id"], {}).get("grammar"):
            continue
        for g in unit.get("grammar", []):
            cid = f"{g['id']}:build"
            if g["id"] in _GRAMMAR and cid not in state["cards"]:
                due = today + timedelta(days=1 + n % GRAMMAR_BACKFILL_SPREAD)
                state["cards"][cid] = srs.placed_card(GRAMMAR_BACKFILL_STABILITY, due)
                n += 1


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
        "build": [{**item, "card_id": f"{g['id']}:build", "point": g["id"]} for g in unit.get("grammar", [])
                  for item in build.items_for(g["id"])],
        # Questions from the units before, mixed into this unit's drill.
        "earlier_drill": [q for u in UNITS[max(0, index - 3):index] for q in u.get("drill", [])],
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


def complete_step(unit_id: str, step: str, *, count: int | None = None, path: Path | None = None) -> dict[str, Any]:
    """Record a finished lesson step. `learn` and `words` schedule their cards.

    `count` is how many of the unit's next words were taught, when they're split
    across days; the words step finishes once all of them have been.
    """
    unit = unit_by_id(unit_id)
    if unit is None:
        raise KeyError(f"unknown unit: {unit_id}")
    if step not in unit_steps(unit):
        raise ValueError(f"unknown step: {step}")

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        before = len(state["cards"])
        row = state["units"].setdefault(unit_id, {})
        fresh = not row.get(step)  # redoing a finished step isn't new work for today's budget
        seen_before = int(row.get("words_seen") or 0)
        row[f"{step}_on"] = _today().isoformat()  # day-two steps wait until after this day
        if step != "words":
            row[step] = True
        if step == "learn":
            for p in unit["phrases"]:
                for skill in SKILLS:
                    state["cards"].setdefault(f"{p['id']}:{skill}", _new_card())
        if step == "words":
            words = unit.get("words", [])
            seen = int(row.get("words_seen") or 0)
            upto = len(words) if count is None else min(len(words), seen + max(0, count))
            for w in words[seen:upto]:
                state["cards"].setdefault(f"{w['id']}:mean", _new_card())
            row["words_seen"] = upto
            row["words"] = upto >= len(words)
        if step == "grammar":
            for g in unit.get("grammar", []):
                if g["id"] in _GRAMMAR:
                    state["cards"].setdefault(f"{g['id']}:build", _new_card())
        if fresh:
            minutes = WORD_MINUTES * (int(row.get("words_seen") or 0) - seen_before) if step == "words" else _step_minutes(step, unit)
            _spend_minutes(state, minutes)
        if unit_done(state, unit):
            row.setdefault("done_at", datetime.now(timezone.utc).isoformat())
        _mark_day(state)
        _count_new(state, before)
        return row

    return _with_state(apply, path)


def _spend_minutes(state: dict[str, Any], minutes: float) -> None:
    """Lesson time used today, so the rest of today's plan fits in what's left."""
    day = state["daily"].setdefault(_today().isoformat(), {"answers": 0, "right": 0, "ms": 0})
    day["lesson_min"] = round(float(day.get("lesson_min") or 0) + minutes, 2)


def _count_new(state: dict[str, Any], before: int) -> None:
    """How many items were taught today, for the end-of-day summary."""
    added = len(state["cards"]) - before
    if added > 0:
        day = state["daily"].setdefault(_today().isoformat(), {"answers": 0, "right": 0, "ms": 0})
        day["new"] = int(day.get("new") or 0) + added


def complete_kana(lesson_id: str, *, path: Path | None = None) -> dict[str, Any]:
    """Record a finished kana lesson and schedule a card per character."""
    lesson = LESSON_BY_ID.get(lesson_id)
    if lesson is None:
        raise KeyError(f"unknown kana lesson: {lesson_id}")

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        if lesson_id not in state["kana"]:
            _spend_minutes(state, _kana_minutes(lesson))
        state["kana"].setdefault(lesson_id, _today().isoformat())
        before = len(state["cards"])
        for ch, _ in lesson["kana"]:
            state["cards"].setdefault(f"kana.{ch}:read", _new_card())
        _mark_day(state)
        _count_new(state, before)
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
    if item in _GRAMMAR and skill == "build":
        return "grammar", item, skill
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
    rating: int | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Apply one answer. The grade is worked out here unless `rating` is given.

    Returns the card, the `rating` used, `intervals` (seconds until the next
    review for each grade, for the grade buttons), `learning` and `again_soon`.
    Everything the answer changes is recorded so `undo` can put it back.
    """
    kind = _card_kind(card_id)
    if kind is None:
        raise KeyError(f"unknown card: {card_id}")
    fmt = fmt or f"{kind[0]}:{kind[2]}"
    outcome = {"correct": correct, "ms": ms, "helped": helped, "guessed": guessed, "band": band, "fmt": fmt}

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        return _apply_grade(state, card_id, kind, outcome, rating)

    return _with_state(apply, path)


def _apply_grade(state: dict[str, Any], card_id: str, kind: tuple, outcome: dict[str, Any], forced: int | None) -> dict[str, Any]:
    existed = card_id in state["cards"]
    card = state["cards"].get(card_id) or _new_card()  # lessons may grade before the step finishes
    before = dict(card) if existed else None
    today = _today().isoformat()
    was_review = not srs.is_learning(card)
    intervals = srs.preview(card)
    times = state["timing"].get(outcome["fmt"], [])
    reps = int(card.get("reps") or 0)
    auto = srs.rating_for(
        correct=outcome["correct"], ms=outcome["ms"], helped=outcome["helped"], guessed=outcome["guessed"],
        band=outcome["band"], reps=reps, times=times, **grader.for_format(state["grader"], outcome["fmt"]),
    )
    rating = forced if forced in (srs.AGAIN, srs.HARD, srs.GOOD, srs.EASY) else auto
    state["seq"] += 1
    entry: dict[str, Any] = {"seq": state["seq"], "card_id": card_id, "before": before, "outcome": outcome,
                             "auto": auto, "rating": rating, "day": today, "cost": 0, "log": None, "time": None}
    # The grader learns from what each answer looked like and which grade stuck.
    state["grades"] = (state["grades"] + [{
        "seq": state["seq"], "fmt": outcome["fmt"], "ratio": srs.speed_ratio(outcome["ms"], times),
        "auto": auto, "final": rating, "correct": bool(outcome["correct"]), "close": outcome["band"] == "close",
        "helped": bool(outcome["helped"]), "guessed": bool(outcome["guessed"]), "seasoned": reps >= srs.EASY_MIN_REPS,
    }])[-grader.ROWS_KEPT:]
    if was_review:
        # Only real reviews spend the daily budget and count toward retention.
        entry["cost"] = card_cost(kind[0], kind[2])
        state["reviewed"] = {today: state["reviewed"].get(today, 0) + entry["cost"]}
        row = {"seq": state["seq"], "d": today, "k": kind[0] if kind[0] != "phrase" else f"phrase:{kind[2]}",
               "ok": rating != srs.AGAIN}
        state["log"] = (state["log"] + [row])[-LOG_KEPT:]
        entry["log"] = state["seq"]
    clean = outcome["correct"] and not (outcome["helped"] or outcome["guessed"]) and forced is None
    srs.record_time(state["timing"], outcome["fmt"], outcome["ms"], clean)
    if clean and outcome["ms"] and outcome["ms"] < srs.TIMING_IGNORE_MS:  # record_time kept it
        entry["time"] = [outcome["fmt"], int(outcome["ms"])]
    day = state["daily"].setdefault(today, {"answers": 0, "right": 0, "ms": 0})
    day["answers"] += 1
    day["right"] += 1 if rating != srs.AGAIN else 0
    day["ms"] += min(int(outcome["ms"] or 0), srs.TIMING_IGNORE_MS)
    if len(state["daily"]) > DAILY_KEPT:
        state["daily"] = dict(sorted(state["daily"].items())[-DAILY_KEPT:])
    if card.get("placed"):
        # First review of something marked known without being taught: a check on its unit.
        entry["check"] = _placement_check(state, kind, rating != srs.AGAIN)
    extras = {k: v for k, v in card.items() if k == "hook"}
    card = {**srs.review(card, rating), **extras}
    state["cards"][card_id] = card
    state["undo"] = (state["undo"] + [entry])[-UNDO_KEPT:]
    if forced is not None or len(state["grades"]) % RETUNE_EVERY == 0:
        state["grader"] = grader.tune(state["grades"])
    _mark_day(state)
    soon = srs.due_at(card) - datetime.now(timezone.utc)
    return {
        **card, "card_id": card_id, "rating": rating, "auto_rating": auto, "intervals": intervals,
        "learning": srs.is_learning(card), "was_review": was_review,
        "seconds": max(0, int(soon.total_seconds())), "again_soon": soon < timedelta(minutes=30),
        "reopened": (entry.get("check") or {}).get("reopened_unit"),
    }


def _undo_entry(state: dict[str, Any], entry: dict[str, Any]) -> None:
    """Put back everything one answer changed."""
    cid = entry["card_id"]
    if entry["before"] is None:
        state["cards"].pop(cid, None)
    else:
        state["cards"][cid] = entry["before"]
    if entry["cost"]:
        day = entry["day"]
        if day in state["reviewed"]:
            state["reviewed"][day] = max(0, state["reviewed"][day] - entry["cost"])
    if entry["log"]:
        state["log"] = [r for r in state["log"] if r.get("seq") != entry["log"]]
    state["grades"] = [r for r in state["grades"] if r.get("seq") != entry["seq"]]
    if entry["time"]:
        fmt, ms = entry["time"]
        times = state["timing"].get(fmt, [])
        for i in range(len(times) - 1, -1, -1):
            if times[i] == ms:
                del times[i]
                break
    check = entry.get("check")
    if check:
        tally = state["checks"].setdefault(check["unit"], {"ok": 0, "miss": 0})
        key = "ok" if check["ok"] else "miss"
        tally[key] = max(0, tally[key] - 1)
        if check.get("row_before") is not None:
            # This answer reopened the unit: take that back too.
            state["units"][check["unit"]] = check["row_before"]
            tally.pop("reopened", None)
    day = state["daily"].get(entry["day"])
    if day:
        day["answers"] = max(0, day["answers"] - 1)
        day["right"] = max(0, day["right"] - (0 if entry.get("rating") == srs.AGAIN else 1))


def undo(*, card_id: str | None = None, path: Path | None = None) -> dict[str, Any] | None:
    """Take back the latest answer (or the latest answer for `card_id`).

    Returns the restored card as a review row, ready to be asked again, or None.
    """

    def apply(state: dict[str, Any]) -> dict[str, Any] | None:
        idx = next((i for i in range(len(state["undo"]) - 1, -1, -1)
                    if card_id is None or state["undo"][i]["card_id"] == card_id), None)
        if idx is None:
            return None
        entry = state["undo"].pop(idx)
        _undo_entry(state, entry)
        cid = entry["card_id"]
        row = _card_row(cid, _card_kind(cid), state["cards"].get(cid) or _new_card())
        return {"card": row, "outcome": entry["outcome"], "auto": entry["auto"]}

    return _with_state(apply, path)


def regrade(card_id: str, rating: int, *, path: Path | None = None) -> dict[str, Any]:
    """The learner picked a different grade: undo their last answer on this card and reapply it."""
    kind = _card_kind(card_id)
    if kind is None:
        raise KeyError(f"unknown card: {card_id}")

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        idx = next((i for i in range(len(state["undo"]) - 1, -1, -1) if state["undo"][i]["card_id"] == card_id), None)
        if idx is None:
            raise KeyError(f"nothing to change for {card_id}")
        entry = state["undo"].pop(idx)
        _undo_entry(state, entry)
        state["overrides"] = (state["overrides"] + [{
            "fmt": entry["outcome"]["fmt"], "ms": entry["outcome"]["ms"], "auto": entry["auto"], "chosen": rating,
            "d": entry["day"],
        }])[-OVERRIDES_KEPT:]
        return _apply_grade(state, card_id, kind, entry["outcome"], rating)

    return _with_state(apply, path)


def _kana_item(char: str, ro: str) -> dict[str, Any]:
    return {"char": char, "ro": ro, "hook": hook_for(char), "alike": alike(char)}


def _card_payload(kind: str, item: str) -> dict[str, Any]:
    if kind == "phrase":
        return {"phrase": phrase(item)}
    if kind == "word":
        return {"word": dict(_WORDS[item])}
    if kind == "grammar":
        return {"grammar": _GRAMMAR[item]}
    return {"kana": _kana_item(item, KANA_ROMAJI[item])}


def answer_format(kind: str, skill: str, card: dict[str, Any]) -> str:
    """How the card is answered: recognise while new, produce once it's known.

    choice   pick from options (new kana and words; every other review of a known word; hearing a phrase)
    produce  say or type the answer (known kana: its sound; known words: the Japanese)
    speak    say the phrase (the speaking side of a phrase)
    """
    if kind == "phrase":
        return "speak" if skill == "speak" else "choice"
    if kind == "grammar":
        return "build"
    if is_leech(card) and srs.stability(card) < LEECH_STABLE_DAYS:
        return "choice"  # a leech goes back to recognition until it holds again
    if not srs.known(card):
        return "choice"
    # Known words take turns: say it, then understand it by ear, so neither skill fades.
    if kind == "word" and int(card.get("reps") or 0) % 2:
        return "choice"
    return "produce"


def is_leech(card: dict[str, Any]) -> bool:
    return int(card.get("lapses") or 0) >= LEECH_LAPSES


def save_hook(card_id: str, hook: dict[str, Any], *, path: Path | None = None) -> None:
    """Keep a leech's memory hook so it's written once, not on every review."""

    def apply(state: dict[str, Any]) -> None:
        if card_id in state["cards"]:
            state["cards"][card_id]["hook"] = hook

    _with_state(apply, path)


def card_item(card_id: str) -> dict[str, Any] | None:
    """What a card is about (for writing its hook): kind, Japanese, meaning or reading."""
    kind = _card_kind(card_id)
    if kind is None:
        return None
    payload = _card_payload(kind[0], kind[1])
    if kind[0] == "kana":
        return {"kind": "kana", "jp": payload["kana"]["char"], "en": payload["kana"]["ro"]}
    if kind[0] == "grammar":
        g = payload["grammar"]
        return {"kind": "grammar", "jp": g["items"][0]["jp"], "en": g["items"][0]["en"], "note": g["rule"]}
    item = payload.get("phrase") or payload.get("word")
    return {"kind": kind[0], "jp": item["jp"], "en": item["en"], "note": item.get("note", "")}


def retention(state: dict[str, Any], *, days: int = RETENTION_DAYS) -> dict[str, Any] | None:
    """Share of real reviews (learned cards) still remembered, overall and by kind.

    None until there are enough reviews to mean something. FSRS aims for 87%.
    """
    since = (_today() - timedelta(days=days)).isoformat()
    rows = [r for r in state["log"] if str(r.get("d")) >= since]
    if len(rows) < RETENTION_MIN_REVIEWS:
        return None
    groups = {"kana": "kana", "word": "words", "phrase:listen": "phrases heard", "phrase:speak": "phrases said", "grammar": "grammar"}
    by_kind = {}
    for key, label in groups.items():
        part = [r for r in rows if r.get("k") == key]
        if len(part) >= 5:
            by_kind[label] = round(100 * sum(1 for r in part if r.get("ok")) / len(part))
    return {
        "percent": round(100 * sum(1 for r in rows if r.get("ok")) / len(rows)),
        "reviews": len(rows),
        "days": days,
        "target": round(100 * srs.SCHEDULER.desired_retention),
        "by_kind": by_kind,
        "leeches": sum(1 for c in state["cards"].values() if is_leech(c)),
    }


def _card_row(card_id: str, kind: tuple[str, str, str], card: dict[str, Any]) -> dict[str, Any]:
    return {
        "card_id": card_id, "kind": kind[0], "skill": kind[2],
        "format": answer_format(kind[0], kind[2], card),
        "stability": round(srs.stability(card), 1),
        "reps": int(card.get("reps") or 0),
        "leech": is_leech(card),
        "hook": card.get("hook"),
        **_card_payload(kind[0], kind[1]),
    }


def _answered_today(card: dict[str, Any]) -> bool:
    last = str(card.get("last") or "")
    return bool(last) and srs.study_day(datetime.fromisoformat(last)).isoformat() == _today().isoformat()


def due_cards(state: dict[str, Any], *, limit: int = 20, budget: int | None = None) -> list[dict[str, Any]]:
    """Due cards, most-forgotten first (lowest box, then oldest), within `budget` if given.

    A phrase's two sides are never back to back. In today's share (`budget` given) a
    phrase comes up on one side per day: hearing おはよう gives away how to say it, so
    the other side waits for a day when it's a real test.
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
    sides_taken: set[str] = set()
    if budget is not None:
        for card_id, card in state["cards"].items():
            kind = _card_kind(card_id)
            if kind and kind[0] == "phrase" and _answered_today(card):
                sides_taken.add(kind[1])
    for row in rows:
        if len(picked) >= limit:
            break
        if budget is not None and row[3][0] == "phrase" and row[3][1] in sides_taken:
            continue
        if left is not None:
            cost = card_cost(row[3][0], row[3][2])
            if cost > left:
                continue
            left -= cost
        if row[3][0] == "phrase":
            sides_taken.add(row[3][1])
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
# How much a day holds, set by the learner. Reviews come first and get their own
# budget (rough "seconds/3" units, see CARD_COST); lessons then fill `lesson_minutes`.
# `minutes` is what scripts/sim_pacing.py measures an average day at, so it's what
# the pace promises. The old fixed plan said 15 and ran 19-27 for most of the course.
PACES: dict[str, dict[str, Any]] = {
    "relaxed": {"label": "Relaxed", "minutes": 14, "lesson_minutes": 6, "reviews": 22, "new_items": 14},
    "regular": {"label": "Regular", "minutes": 18, "lesson_minutes": 11, "reviews": 34, "new_items": 24},
    "intensive": {"label": "Intensive", "minutes": 25, "lesson_minutes": 24, "reviews": 50, "new_items": 50},
}
DEFAULT_PACE = "regular"
# When the due backlog is worth more than two days of reviews, that day is a
# catch-up day: no new material is planned, and the review budget doubles.
CATCH_UP_DAYS = 2
DAY_ONE_STEPS = ("learn", "words")
# Below this share remembered, new material halves until recall recovers: piling
# more on top of what's slipping only makes both worse.
COMEBACK_DAYS = 3
SLOW_DOWN_BELOW = 80
SLOW_DOWN_DAYS = 14
SLOW_DOWN_MIN_REVIEWS = 30
MIN_WORD_BATCH = 5
# Rough minutes a lesson step takes, including its share of the same-day recap.
WORD_MINUTES = 0.3
STEP_MINUTES = {"grammar": 4.0, "listen": 3.5, "speak": 3.5}
REVIEW_SECONDS = {"kana": 4, "word": 5, "listen": 8, "speak": 12, "grammar": 15}


def pace_of(state: dict[str, Any]) -> dict[str, Any]:
    return PACES.get(str(state.get("pace") or ""), PACES[DEFAULT_PACE])


def set_pace(pace: str, *, path: Path | None = None) -> str:
    if pace not in PACES:
        raise ValueError(f"unknown pace: {pace}")

    def apply(state: dict[str, Any]) -> str:
        state["pace"] = pace
        return pace

    return _with_state(apply, path)


def due_cost(state: dict[str, Any]) -> int:
    return sum(card_cost(c["kind"], c["skill"]) for c in due_cards(state, limit=10_000))


def catching_up(state: dict[str, Any]) -> bool:
    return due_cost(state) > pace_of(state)["reviews"] * CATCH_UP_DAYS


def todays_reviews(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Today's share of due cards: what fits in the budget left after today's reviews."""
    spent = state["reviewed"].get(_today().isoformat(), 0)
    # Coming back from a break gets a normal day: a doubled pile is how a break becomes quitting.
    returning = days_away(state) >= COMEBACK_DAYS
    budget = pace_of(state)["reviews"] * (2 if catching_up(state) and not returning else 1)
    return due_cards(state, limit=80, budget=max(0, budget - spent))


def recall_slipping(state: dict[str, Any]) -> int | None:
    """Recent recall as a percent when it's low enough to slow new material, else None."""
    since = (_today() - timedelta(days=SLOW_DOWN_DAYS)).isoformat()
    rows = [r for r in state["log"] if str(r.get("d")) >= since]
    if len(rows) < SLOW_DOWN_MIN_REVIEWS:
        return None
    percent = round(100 * sum(1 for r in rows if r.get("ok")) / len(rows))
    return percent if percent < SLOW_DOWN_BELOW else None


def _words_left(unit: dict[str, Any], row: dict[str, Any]) -> int:
    return 0 if row.get("words") else max(0, len(unit.get("words", [])) - int(row.get("words_seen") or 0))


def _kana_minutes(lesson: dict[str, Any]) -> float:
    return 0.5 * len(lesson["kana"]) + 1 if lesson["kana"] else 2.0


def _step_minutes(step: str, unit: dict[str, Any]) -> float:
    if step == "learn":
        return 0.9 * len(unit["phrases"])
    return STEP_MINUTES.get(step, 3.0)


def _review_minutes(cards: list[dict[str, Any]]) -> float:
    return sum(REVIEW_SECONDS.get(c["skill"] if c["kind"] == "phrase" else c["kind"], 8) for c in cards) / 60


def plan_today(state: dict[str, Any]) -> dict[str, Any]:
    """Which steps today's lesson should run, in order, and why some are held back.

    Rules: reviews first; a unit's day-one steps (phrases, words) and day-two steps
    (grammar, listening, speaking) fall on different days, with sleep in between;
    lessons fill the pace's minutes and new-item cap, and a unit's words split across
    days when they don't fit; kana and the unit take turns going first. On a catch-up
    day only reviews are planned. Nothing here locks anything: the home screen can
    still open any step.
    """
    today = _today()
    iso = today.isoformat()
    yesterday = (today - timedelta(days=1)).isoformat()
    pace = pace_of(state)
    reviews = todays_reviews(state)
    unit = next_unit(state)
    kana = next_kana_lesson(state)
    plan: list[str] = []
    if reviews:
        plan.append("review")
    if catching_up(state):
        if recap_cards(state):
            plan.append("recap")
        return {"plan": plan, "catching_up": True, "day_two_tomorrow": False, "words_today": 0, "pace": _pace_name(state),
                "slipping": None, "minutes": _day_minutes(reviews, state, 0.0)}

    slipping = recall_slipping(state)
    share = 0.5 if slipping is not None else 1.0
    # What's already been done today counts: the plan is worked out again after every step.
    day = state["daily"].get(iso, {})
    spent = float(day.get("lesson_min") or 0)
    minutes_left = pace["lesson_minutes"] * share - spent
    new_left = pace["new_items"] * share - int(day.get("new") or 0)
    started = spent > 0
    row = state["units"].get(unit["id"], {}) if unit else {}
    steps = unit_steps(unit) if unit else []
    day_one = [s for s in steps if s in DAY_ONE_STEPS and not row.get(s)]
    day_two = [s for s in steps if s not in DAY_ONE_STEPS and not row.get(s)]
    day_one_today = any(row.get(f"{s}_on") == iso for s in DAY_ONE_STEPS if s in steps)
    unit_queue = day_one or ([] if day_one_today else day_two)
    day_two_tomorrow = not day_one and bool(day_two) and day_one_today

    planned: list[str] = []
    words_today = 0

    def try_kana() -> None:
        nonlocal minutes_left, new_left
        need = _kana_minutes(kana)
        if (not planned and not started) or (need <= minutes_left and len(kana["kana"]) <= new_left):
            planned.append("kana")
            minutes_left -= need
            new_left -= len(kana["kana"])

    def try_unit() -> None:
        nonlocal minutes_left, new_left, words_today
        for step in unit_queue:
            if step == "words":
                left = _words_left(unit, row)
                fits = int(min(left, max(0.0, minutes_left) / WORD_MINUTES, max(0.0, new_left)))
                if fits < left:
                    fits -= fits % MIN_WORD_BATCH  # whole teach-and-test batches
                if fits < MIN_WORD_BATCH and fits < left:
                    if planned or started:
                        return
                    fits = min(left, MIN_WORD_BATCH)
                planned.append("words")
                words_today = fits
                minutes_left -= fits * WORD_MINUTES
                new_left -= fits
                if fits < left:
                    return
                continue
            need = _step_minutes(step, unit)
            new = len(unit["phrases"]) if step == "learn" else 0
            if (planned or started) and (need > minutes_left or new > new_left):
                return
            planned.append(step)
            minutes_left -= need
            new_left -= new

    kana_wanted = bool(kana) and iso not in state["kana"].values()
    if kana_wanted and yesterday not in state["kana"].values():
        try_kana()
        try_unit()
    else:
        try_unit()
        if kana_wanted:
            try_kana()
    planned.sort(key=lambda s: 0 if s == "kana" else 1)  # kana first: it's what the rest gets read with
    plan.extend(planned)
    if planned or recap_cards(state):
        # After the new material: a second look at today's new and missed cards.
        plan.append("recap")
    used = pace["lesson_minutes"] * share - spent - minutes_left
    return {"plan": plan, "catching_up": False, "day_two_tomorrow": day_two_tomorrow, "words_today": words_today,
            "pace": _pace_name(state), "slipping": slipping, "minutes": _day_minutes(reviews, state, used)}


def _pace_name(state: dict[str, Any]) -> str:
    name = str(state.get("pace") or "")
    return name if name in PACES else DEFAULT_PACE


def _day_minutes(reviews: list[dict[str, Any]], state: dict[str, Any], lessons: float) -> int:
    """About how long the rest of today takes (the home screen's promise)."""
    recap = recap_cards(state)
    return max(1, round(_review_minutes(reviews) + _review_minutes(recap) + lessons))


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
        "kana": [_kana_item(ch, ro) for ch, ro in lesson["kana"]],
        "words": lesson["words"],
        # Earlier characters, so drills can mix new ones with ones you know.
        "known": [_kana_item(ch, ro) for l in KANA_LESSONS[:index] for ch, ro in l["kana"]
                  if l["script"] == lesson["script"]],
    }


REST_EVERY = 7       # studied days in a row that earn a free rest day
REST_MAX = 2         # rest days that can be saved up


def streak_info(state: dict[str, Any]) -> dict[str, int]:
    """Days in a row, where a week of study earns one missed day that doesn't break it.

    A long streak dying over one bad day is the most common reason people quit a
    habit app; a little slack keeps the number a reason to come back, not a threat.
    """
    days = sorted({d for d in state["days"] if d[:4].isdigit()})
    n = rests = 0
    prev: date | None = None
    for raw in days:
        try:
            cur = date.fromisoformat(raw)
        except ValueError:
            continue
        gap = (cur - prev).days - 1 if prev else 0
        if gap <= rests:
            rests -= gap
            n += 1
        else:
            n, rests = 1, 0
        if n % REST_EVERY == 0:
            rests = min(REST_MAX, rests + 1)
        prev = cur
    if prev is None:
        return {"days": 0, "rests": 0}
    # Today isn't over yet: only days fully missed before today count against it.
    missed = (_today() - prev).days - 1
    if missed > rests:
        return {"days": 0, "rests": 0}
    return {"days": n, "rests": rests - max(0, missed)}


def streak(state: dict[str, Any]) -> int:
    return streak_info(state)["days"]


def week_dots(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Monday to Sunday of this week: which days were studied."""
    today = _today()
    monday = today - timedelta(days=today.weekday())
    studied = set(state["days"])
    out = []
    for i in range(7):
        d = monday + timedelta(days=i)
        out.append({"d": d.isoformat(), "label": "MTWTFSS"[i], "on": d.isoformat() in studied, "today": d == today, "future": d > today})
    return out


def days_away(state: dict[str, Any]) -> int:
    """Full days since the last study day (0 when studied today or yesterday)."""
    for raw in reversed(sorted(state["days"])):
        try:
            return max(0, (_today() - date.fromisoformat(raw)).days - 1)
        except ValueError:
            continue
    return 0


def learned_phrase_ids(state: dict[str, Any]) -> list[str]:
    """Phrases the learner has been taught, in course order."""
    seen = {cid.partition(":")[0] for cid in state["cards"]}
    return [pid for pid in _PHRASES if pid in seen]


# Extra listening. Time spent listening is the number that tracks comprehension
# growth, so it's counted; recent scenes are kept so new stories don't repeat them.
LISTEN_RECENT_KEPT = 12
LISTEN_REPORT_MAX_S = 600   # one report can't add more than this


def listening_context(state: dict[str, Any]) -> dict[str, Any]:
    """Learned words split by how well they're held, and the recent story scenes."""
    shaky, solid = [], []
    for wid, w in _WORDS.items():
        card = state["cards"].get(f"{wid}:mean")
        if card is not None:
            (solid if srs.stability(card) >= 7 else shaky).append(w)
    # Example sentences of grammar already taught: their patterns are fair game.
    patterns = [ex["jp"] for u in UNITS if state["units"].get(u["id"], {}).get("grammar")
                for point in u.get("grammar", []) for ex in point["examples"]]
    return {"shaky": shaky, "solid": solid, "patterns": patterns, "recent": list(state["listening"]["recent"])}


def listening_minutes(state: dict[str, Any]) -> dict[str, float]:
    day = state["daily"].get(_today().isoformat(), {})
    return {"today": round(int(day.get("listen_ms") or 0) / 60000, 1),
            "total": round(state["listening"]["total_ms"] / 60000)}


def old_dialogue(state: dict[str, Any]) -> dict[str, Any] | None:
    """A listened-to unit's conversation again, preferring what hasn't been heard lately."""
    units = [u for u in UNITS if state["units"].get(u["id"], {}).get("listen")]
    fresh = [u for u in units if u["dialogue"]["scene"] not in state["listening"]["recent"]]
    if not units:
        return None
    unit = random.choice(fresh or units)
    return {"scene": unit["dialogue"]["scene"], "lines": unit["dialogue"]["lines"], "questions": unit["questions"],
            "form": "dialogue", "replay": True}


def record_listening(seconds: float, *, scene: str = "", path: Path | None = None) -> dict[str, float]:
    ms = int(max(0.0, min(float(seconds), LISTEN_REPORT_MAX_S)) * 1000)

    def apply(state: dict[str, Any]) -> dict[str, float]:
        day = state["daily"].setdefault(_today().isoformat(), {"answers": 0, "right": 0, "ms": 0})
        day["listen_ms"] = int(day.get("listen_ms") or 0) + ms
        state["listening"]["total_ms"] += ms
        if scene:
            recent = [s for s in state["listening"]["recent"] if s != scene] + [scene]
            state["listening"]["recent"] = recent[-LISTEN_RECENT_KEPT:]
        if ms:
            _mark_day(state)
        return listening_minutes(state)

    return _with_state(apply, path)


def record_talk(*, path: Path | None = None) -> int:
    """One spoken turn in talk practice; returns today's count."""

    def apply(state: dict[str, Any]) -> int:
        day = state["daily"].setdefault(_today().isoformat(), {"answers": 0, "right": 0, "ms": 0})
        day["talk"] = int(day.get("talk") or 0) + 1
        _mark_day(state)
        return day["talk"]

    return _with_state(apply, path)


def stats(state: dict[str, Any]) -> dict[str, Any]:
    learned = [p for p in learned_phrase_ids(state) if not p.startswith("my.")]
    strong = {
        cid.partition(":")[0]
        for cid, card in state["cards"].items()
        if srs.stability(card) >= 7
    }
    words = [w for w in _WORDS if f"{w}:mean" in state["cards"]]
    return {
        "phrases_learned": len(learned),
        "phrases_strong": len([p for p in learned if p in strong]),
        "phrases_total": COURSE_PHRASES,
        "words_learned": len(words),
        "units_done": sum(1 for u in UNITS if unit_done(state, u)),
        "units_total": len(UNITS),
        "streak": streak(state),
        "rests": streak_info(state)["rests"],
        "week": week_dots(state),
        "studied_today": _today().isoformat() in state["days"],
        "listening": listening_minutes(state),
        "talk_today": int(state["daily"].get(_today().isoformat(), {}).get("talk") or 0),
    }


def day_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Today so far, in the learner's terms."""
    today = _today().isoformat()
    day = state["daily"].get(today, {})
    answers = int(day.get("answers") or 0)
    finished = [{"id": u["id"], "number": i, "title": u["title"], "goal": u["goal"]}
                for i, u in enumerate(UNITS, start=1)
                if str(state["units"].get(u["id"], {}).get("done_at") or "")[:10] == today
                and not state["units"][u["id"]].get("placed")]
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    due_tomorrow = sum(1 for c in state["cards"].values() if not srs.is_learning(c) and str(c.get("due") or "") <= tomorrow)
    return {
        "answers": answers,
        "right": int(day.get("right") or 0),
        "minutes": round((int(day.get("ms") or 0) + int(day.get("listen_ms") or 0)) / 60000, 1),
        "new": int(day.get("new") or 0),
        "talk": int(day.get("talk") or 0),
        "units_finished": finished,
        "due_tomorrow": due_tomorrow,
    }


def milestones(state: dict[str, Any]) -> list[dict[str, str]]:
    """Real abilities reached, oldest first. Counts things the learner can do, never points."""
    words = sum(1 for w in _WORDS if f"{w}:mean" in state["cards"])
    phrases = len(learned_phrase_ids(state))
    listening = state["listening"]["total_ms"] / 60000
    talk = sum(int(d.get("talk") or 0) for d in state["daily"].values())
    prog = kana_progress(state)
    units = sum(1 for u in UNITS if unit_done(state, u))
    out: list[dict[str, str]] = []

    def add(key: str, reached: bool, text: str) -> None:
        if reached:
            out.append({"id": key, "text": text})

    for n in (10, 25, 50, 100):
        add(f"phrases{n}", phrases >= n, f"{n} phrases you can say.")
    for n in (50, 100, 200, 300):
        add(f"words{n}", words >= n, f"{n} words you know.")
    add("hiragana", prog["hiragana"][0] >= prog["hiragana"][1], "You can read all of hiragana.")
    add("katakana", prog["katakana"][0] >= prog["katakana"][1], "You can read all of katakana.")
    for n in (30, 60, 300, 600):
        add(f"listening{n}", listening >= n, f"{n // 60} hours of listening." if n >= 120 else f"{n} minutes of listening.")
    for n in (25, 100, 500):
        add(f"talk{n}", talk >= n, f"{n} lines spoken in talk practice.")
    for n in (5, 10, 20):
        add(f"units{n}", units >= n, f"{n} units finished." if n < 20 else "The whole course is done.")
    for n in (7, 30, 100):
        add(f"streak{n}", streak(state) >= n, f"{n} days in a row.")
    return out


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
        "kana_pool": [_kana_item(ch, KANA_ROMAJI[ch]) for l in KANA_LESSONS if l["id"] in state["kana"]
                      for ch, _ in l["kana"]],
        "words_pool": [{"jp": w["jp"], "en": w["en"]} for wid, w in _WORDS.items() if f"{wid}:mean" in state["cards"]],
        "phrases_pool": [{"jp": _PHRASES[i]["jp"], "en": _PHRASES[i]["en"]} for i in learned_phrase_ids(state)],
        "recap": recap_cards(state),
        "retention": retention(state),
        "placement": state.get("placement"),
        "placement_checks": placement_checks(state),
        "unit_titles": [u["title"] for u in UNITS],
        "away": days_away(state) if today not in state["days"] else 0,
        "drills": drills.available(state["units"]),
        "bests": state["bests"],
        "day": day_summary(state),
        "milestones": milestones(state),
        "paces": {k: {"label": v["label"], "minutes": v["minutes"]} for k, v in PACES.items()},
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


YOUNG_DAYS = 21  # Anki's line: memory lasting 3 weeks or more is "mature"
INTERVAL_BUCKETS = [(1, "< 1 day"), (3, "1–3 days"), (7, "3–7 days"), (14, "1–2 weeks"), (30, "2–4 weeks"),
                    (90, "1–3 months"), (10_000_000, "3+ months")]


def course_stats(*, path: Path | None = None) -> dict[str, Any]:
    """Everything the stats page shows, from the cards, the review log and daily counts."""
    state = load_state(path)
    today = _today()
    iso = today.isoformat()

    # Coming up: real reviews due on each of the next 30 days (overdue counts as today).
    forecast = [0] * 30
    for card in state["cards"].values():
        if srs.is_learning(card):
            continue
        try:
            offset = (date.fromisoformat(str(card.get("due"))[:10]) - today).days
        except ValueError:
            continue
        if offset < 30:
            forecast[max(0, offset)] += 1

    # Your cards, by kind and stage.
    kinds = {"kana": "Kana", "word": "Words", "phrase": "Phrases", "grammar": "Grammar"}
    stages = {k: {"new": 0, "learning": 0, "young": 0, "mature": 0} for k in kinds}
    intervals = [0] * len(INTERVAL_BUCKETS)
    for cid, card in state["cards"].items():
        kind = _card_kind(cid)
        if kind is None:
            continue
        row = stages[kind[0]]
        if int(card.get("reps") or 0) == 0:
            row["new"] += 1
        elif srs.is_learning(card):
            row["learning"] += 1
        else:
            s = srs.stability(card)
            row["young" if s < YOUNG_DAYS else "mature"] += 1
            intervals[next(i for i, (cap, _) in enumerate(INTERVAL_BUCKETS) if s < cap)] += 1

    # Retention per week for the last 8 weeks (real reviews only).
    weeks = []
    for w in range(7, -1, -1):
        start = (today - timedelta(days=7 * w + 6)).isoformat()
        end = (today - timedelta(days=7 * w)).isoformat()
        rows = [r for r in state["log"] if start <= str(r.get("d")) <= end]
        weeks.append({"end": end, "reviews": len(rows),
                      "percent": round(100 * sum(1 for r in rows if r.get("ok")) / len(rows)) if rows else None})

    day = state["daily"].get(iso, {"answers": 0, "right": 0, "ms": 0})
    activity = []
    for d in range(111, -1, -1):
        key = (today - timedelta(days=d)).isoformat()
        activity.append({"d": key, "answers": state["daily"].get(key, {}).get("answers", 0), "studied": key in state["days"]})

    leeches = []
    for cid, card in state["cards"].items():
        kind = _card_kind(cid)
        if kind and is_leech(card):
            leeches.append({**_card_row(cid, kind, card), "lapses": int(card.get("lapses") or 0)})
    leeches.sort(key=lambda r: -r["lapses"])

    return {
        "today": {"answers": day["answers"], "right": day["right"], "minutes": round(day["ms"] / 60000, 1),
                  "listening": round(int(day.get("listen_ms") or 0) / 60000, 1), "talk": int(day.get("talk") or 0)},
        "listening_total": round(state["listening"]["total_ms"] / 60000),
        "streak": streak(state),
        "forecast": forecast,
        "stages": {kinds[k]: v for k, v in stages.items()},
        "intervals": [{"label": label, "count": n} for (_, label), n in zip(INTERVAL_BUCKETS, intervals)],
        "retention": retention(state),
        "weeks": weeks,
        "activity": activity,
        "leeches": leeches,
        "target": round(100 * srs.SCHEDULER.desired_retention),
        "grading": grader.describe(state["grader"] or grader.tune(state["grades"])),
        "can_do": [u["goal"] for u in UNITS if unit_done(state, u) and not state["units"][u["id"]].get("placed")],
        "milestones": milestones(state),
    }


# Self-correcting placement. Units marked known (by the test, or skipped) aren't
# taken on trust: the first review of each of their cards is a check. When too
# many checks on one unit are missed, that unit's grammar and listening lessons
# come back into the plan, before anything new. Missed word and phrase cards are
# relearned by the scheduler anyway; the lessons bring back what connects them.
REOPEN_MIN_CHECKS = 6     # checks before a unit can be judged
REOPEN_SHARE = 0.35       # share of missed checks that reopens it...
REOPEN_MISSES = 6         # ...or this many misses, however many checks
REOPEN_STEPS = ("grammar", "listen")


def unit_of_card(kind: tuple[str, str, str]) -> str | None:
    if kind[0] == "phrase":
        return _PHRASE_UNIT.get(kind[1])
    if kind[0] == "word":
        return _WORD_UNIT.get(kind[1])
    return None


def _placement_check(state: dict[str, Any], kind: tuple[str, str, str], ok: bool) -> dict[str, Any] | None:
    """Count one check on a placed unit and reopen the unit when it fails. Returns the undo record."""
    uid = unit_of_card(kind)
    row = state["units"].get(uid or "")
    if not uid or not row or not row.get("placed"):
        return None
    tally = state["checks"].setdefault(uid, {"ok": 0, "miss": 0})
    tally["ok" if ok else "miss"] += 1
    record: dict[str, Any] = {"unit": uid, "ok": ok, "row_before": None}
    checked = tally["ok"] + tally["miss"]
    failing = tally["miss"] >= REOPEN_MISSES or (checked >= REOPEN_MIN_CHECKS and tally["miss"] / checked >= REOPEN_SHARE)
    if failing and not tally.get("reopened"):
        unit = unit_by_id(uid)
        record["row_before"] = dict(row)
        for step in REOPEN_STEPS:
            if step in unit_steps(unit):
                row[step] = False
                row.pop(f"{step}_on", None)
        row.pop("done_at", None)
        row["reopened"] = _today().isoformat()
        tally["reopened"] = row["reopened"]
        record["reopened_unit"] = {"id": uid, "number": UNITS.index(unit) + 1, "title": unit["title"],
                                   "missed": tally["miss"], "checked": checked}
    return record


def _unit_card_ids(unit: dict[str, Any]) -> list[str]:
    return [f"{p['id']}:{s}" for p in unit["phrases"] for s in SKILLS] + [f"{w['id']}:mean" for w in unit.get("words", [])]


def placement_checks(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Units marked known without being taught, and how their checks are going."""
    out = []
    for i, unit in enumerate(UNITS, start=1):
        row = state["units"].get(unit["id"], {})
        if not row.get("placed"):
            continue
        tally = state["checks"].get(unit["id"], {})
        pending = sum(1 for c in _unit_card_ids(unit) if (state["cards"].get(c) or {}).get("placed"))
        out.append({"id": unit["id"], "number": i, "title": unit["title"], "ok": tally.get("ok", 0),
                    "miss": tally.get("miss", 0), "reopened": tally.get("reopened"), "pending": pending})
    return out


def _mark_unit_known(state: dict[str, Any], unit: dict[str, Any], place) -> None:
    """Mark a unit done without teaching it; its cards become placed (checked on first review)."""
    earlier = (_today() - timedelta(days=1)).isoformat()
    row = state["units"].setdefault(unit["id"], {})
    for step in unit_steps(unit):
        row.setdefault(step, True)
        row.setdefault(f"{step}_on", earlier)
    row.setdefault("done_at", datetime.now(timezone.utc).isoformat())
    row["placed"] = True
    for cid in _unit_card_ids(unit):
        place(cid)


def skip_unit(unit_id: str, *, path: Path | None = None) -> dict[str, Any]:
    """"I already know this unit": mark it known, with the same checks as a placement.

    Only for a unit that hasn't been started, so nothing learned is overwritten.
    If its checks fail, the unit's lessons come back on their own.
    """
    unit = unit_by_id(unit_id)
    if unit is None:
        raise KeyError(f"unknown unit: {unit_id}")
    today = _today()

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        row = state["units"].get(unit_id, {})
        if any(row.get(s) for s in unit_steps(unit)):
            raise ValueError("This unit is already started.")
        n = 0

        def place(cid: str) -> None:
            nonlocal n
            if cid not in state["cards"]:
                state["cards"][cid] = srs.placed_card(PLACED_STABILITY, today + timedelta(days=1 + n % PLACED_SPREAD_DAYS))
                n += 1

        _mark_unit_known(state, unit, place)
        state["units"][unit_id]["skipped"] = today.isoformat()
        _mark_day(state)
        return {"unit": unit_id, "cards_added": n}

    return _with_state(apply, path)


PLACED_STABILITY = 4.0   # days: soon enough that the first review checks the placement
PLACED_SPREAD_DAYS = 14  # first reviews of placed material spread over two weeks


def apply_placement(result: dict[str, Any], *, path: Path | None = None) -> dict[str, Any]:
    """Mark what the placement test showed as known. Only ever adds: existing cards and
    progress are left alone, so retaking the test can't wipe anything."""
    from kaiwa.course import placement as pl

    known_units = max(0, min(len(UNITS), int(result.get("known_units") or 0)))
    kana = result.get("kana") or {}
    today = _today()
    earlier = (today - timedelta(days=1)).isoformat()  # not "today", so today's plan still offers a kana lesson

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        n = 0

        def place(cid: str) -> None:
            nonlocal n
            if cid not in state["cards"]:
                due = today + timedelta(days=1 + n % PLACED_SPREAD_DAYS)
                state["cards"][cid] = srs.placed_card(PLACED_STABILITY, due)
                n += 1

        for unit in UNITS[:known_units]:
            if not unit_done(state, unit):
                _mark_unit_known(state, unit, place)
        # Words understood once the kana was shown but not by ear: known in writing,
        # not yet by sound. They start as near-due reviews so listening catches up.
        listen_soon = []
        for wid in result.get("reading_only") or []:
            cid = f"{wid}:mean"
            if wid in _WORDS and cid not in state["cards"]:
                state["cards"][cid] = srs.placed_card(1.0, today + timedelta(days=1))
                listen_soon.append(wid)
        skipped = []
        for group in kana.values():
            if group.get("passed"):
                for lid in group.get("lessons", []):
                    if lid not in state["kana"]:
                        state["kana"][lid] = earlier
                        skipped.append(lid)
                        for ch, _ in LESSON_BY_ID[lid]["kana"]:
                            place(f"kana.{ch}:read")
        state["placement"] = {"date": today.isoformat(), "known_units": known_units,
                              "skills": result.get("skills", {}), "channels": result.get("channels", {}),
                              "kana_skipped": skipped, "listen_soon": listen_soon}
        return {"known_units": known_units, "cards_added": n, "kana_skipped": skipped, "listen_soon": listen_soon}

    summary = _with_state(apply, path)

    # The chat side reads the learner profile: set its levels from the measured skills.
    from kaiwa import learner_profile as lp

    skills = result.get("skills") or {}
    channels = result.get("channels") or {}
    ear = [channels[s]["ear"]["level"] for s in ("words", "sentences") if s in channels]
    comp = min(ear or [skills[s]["level"] for s in ("words", "sentences") if s in skills] or [0])
    speak = skills.get("imitate", {}).get("level", comp)
    profile = lp.load_profile()
    lp.apply_manual_override(profile, comprehension_level=pl.jlpt_level(comp), speaking_level=pl.jlpt_level(speak),
                             confidence=0.75)
    profile.placement_completed = True
    profile.placement = {"source": "placement test", "units": round(comp, 1), "date": today.isoformat()}
    lp.save_profile(profile)
    return summary


RECENT_DAYS = 3


def recent_phrases(state: dict[str, Any]) -> list[dict[str, str]]:
    """Phrases taught in the last few days: what Chat should give the learner a chance to use."""
    since = (_today() - timedelta(days=RECENT_DAYS)).isoformat()
    out = []
    for unit in UNITS:
        row = state["units"].get(unit["id"], {})
        if str(row.get("learn_on") or "") >= since and not row.get("placed"):
            out.extend({"jp": p["jp"], "en": p["en"]} for p in unit["phrases"])
    return out[-12:]


def known_phrases_for_chat(*, limit: int = 40, path: Path | None = None) -> list[dict[str, str]]:
    """What Chat may assume the learner understands (most recent units first)."""
    state = load_state(path)
    ids = learned_phrase_ids(state)[-limit:]
    return [{"jp": _PHRASES[i]["jp"], "en": _PHRASES[i]["en"]} for i in ids]


def strength_of(card: dict[str, Any] | None) -> str:
    """A card's memory in plain terms."""
    if not card or srs.is_learning(card):
        return "new"
    s = srs.stability(card)
    return "strong" if s >= YOUNG_DAYS else "growing" if s >= 3 else "new"


def course_map(*, path: Path | None = None) -> dict[str, Any]:
    """Every unit: what it lets you do, and how far along it is."""
    state = load_state(path)
    current = next_unit(state)
    units = []
    for i, unit in enumerate(UNITS, start=1):
        row = state["units"].get(unit["id"], {})
        steps = unit_steps(unit)
        cards = [state["cards"].get(c) for c in _unit_card_ids(unit)]
        started = [c for c in cards if c]
        strong = sum(1 for c in started if strength_of(c) == "strong")
        units.append({
            "id": unit["id"], "number": i, "title": unit["title"], "title_jp": unit["title_jp"], "goal": unit["goal"],
            "status": "done" if unit_done(state, unit) else "current" if current and unit["id"] == current["id"] else "later",
            "steps": sum(1 for s in steps if row.get(s)), "steps_total": len(steps),
            "strength": round(100 * strong / len(cards)) if cards else 0,
            "mission": row.get("mission"), "has_mission": unit["id"] in MISSIONS,
            "placed": bool(row.get("placed")),
        })
    return {"units": units, "kana": kana_progress(state), "kana_lessons": [
        {"id": l["id"], "number": i, "title": l["title"], "script": l["script"], "done": l["id"] in state["kana"],
         "chars": " ".join(c for c, _ in l["kana"])} for i, l in enumerate(KANA_LESSONS, start=1)]}


def kana_lesson_payload(lesson_id: str, *, path: Path | None = None) -> dict[str, Any] | None:
    lesson = LESSON_BY_ID.get(lesson_id)
    return public_kana_lesson(lesson, load_state(path)) if lesson else None


def unit_payload(unit_id: str, *, path: Path | None = None) -> dict[str, Any] | None:
    """A unit opened from the course map, ready for its lesson steps."""
    unit = unit_by_id(unit_id)
    if unit is None:
        return None
    state = load_state(path)
    return {"unit": public_unit(unit), "unit_steps": dict(state["units"].get(unit_id, {}))}


def phrasebook(*, path: Path | None = None) -> dict[str, Any]:
    """Everything learned so far, to look up and hear again."""
    state = load_state(path)
    phrases, words, grammar = [], [], []
    for unit in UNITS:
        for p in unit["phrases"]:
            cards = [state["cards"].get(f"{p['id']}:{s}") for s in SKILLS]
            if any(cards):
                phrases.append({"jp": p["jp"], "en": p["en"], "note": p.get("note", ""), "ro": ROMAJI.get(p["id"], ""),
                                "unit": unit["title"], "strength": strength_of(min((c for c in cards if c), key=srs.stability))})
        for w in unit.get("words", []):
            card = state["cards"].get(f"{w['id']}:mean")
            if card:
                words.append({"jp": w["jp"], "en": w["en"], "ro": w.get("ro", ""), "unit": unit["title"], "strength": strength_of(card)})
        if state["units"].get(unit["id"], {}).get("grammar"):
            for g in unit.get("grammar", []):
                grammar.append({"title": g["title"], "rule": g.get("rule", ""), "explain": g["explain"],
                                "examples": g["examples"], "unit": unit["title"]})
    mine = [{**row, "strength": strength_of(min((c for c in (state["cards"].get(f"{row['id']}:{s}") for s in SKILLS) if c), key=srs.stability, default=None))}
            for row in state["mine"]]
    return {"phrases": phrases, "words": words, "grammar": grammar, "mine": mine}


def keep_my_phrase(jp: str, en: str, note: str = "", *, path: Path | None = None) -> dict[str, Any]:
    """Add the learner's own phrase; it's taught through the day's recap like anything new."""
    jp = jp.strip()
    row = {"id": my_phrases.phrase_id(jp), "jp": jp, "en": en.strip(), "note": note.strip(), "ro": my_phrases.romaji(jp)}

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        if len(state["mine"]) >= my_phrases.MAX_KEPT:
            raise ValueError("Your phrase list is full. Remove one first.")
        if not any(r["id"] == row["id"] for r in state["mine"]):
            state["mine"].append(row)
            _PHRASES[row["id"]] = row
            before = len(state["cards"])
            for skill in SKILLS:
                state["cards"].setdefault(f"{row['id']}:{skill}", _new_card())
            _mark_day(state)
            _count_new(state, before)
        return row

    return _with_state(apply, path)


def remove_my_phrase(phrase_id: str, *, path: Path | None = None) -> bool:
    def apply(state: dict[str, Any]) -> bool:
        kept = [r for r in state["mine"] if r["id"] != phrase_id]
        if len(kept) == len(state["mine"]):
            return False
        state["mine"] = kept
        for skill in SKILLS:
            state["cards"].pop(f"{phrase_id}:{skill}", None)
        return True

    return _with_state(apply, path)


def record_best(key: str, value: int, *, path: Path | None = None) -> dict[str, int]:
    """A drill's score; returns the best so far and whether this beat it."""

    def apply(state: dict[str, Any]) -> dict[str, int]:
        old = int(state["bests"].get(key) or 0)
        state["bests"][key] = max(old, value)
        _mark_day(state)
        return {"best": state["bests"][key], "previous": old}

    return _with_state(apply, path)


def complete_mission(unit_id: str, *, path: Path | None = None) -> str:
    if unit_by_id(unit_id) is None:
        raise KeyError(f"unknown unit: {unit_id}")

    def apply(state: dict[str, Any]) -> str:
        row = state["units"].setdefault(unit_id, {})
        row.setdefault("mission", _today().isoformat())
        _mark_day(state)
        return row["mission"]

    return _with_state(apply, path)
