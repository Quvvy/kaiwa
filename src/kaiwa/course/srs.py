"""Spaced repetition on FSRS, with grades worked out from how the learner answered.

FSRS models each card's memory (stability: how long it lasts; difficulty: how
hard it is for this learner) and schedules the next review for ~90% recall.
New and missed cards go through short learning steps (1 and 10 minutes), which
is what gives a new item its second look the same day.

Nobody presses Again/Hard/Good/Easy. `rating_for` derives the grade from what
happened: wrong → Again; right but slow (against the learner's own usual speed
for that kind of card), helped, guessed, or "close" on a speech check → Hard;
right at normal speed → Good; right and much faster than usual on a card with a
track record → Easy.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from statistics import median
from typing import Any

from fsrs import Card, Rating, Scheduler, State

SCHEDULER = Scheduler(
    desired_retention=0.9,
    learning_steps=(timedelta(minutes=1), timedelta(minutes=10)),
    relearning_steps=(timedelta(minutes=10),),
    # No random spread: the interval shown on each grade button is exactly what
    # that grade gives (with fuzz, Hard could land after Good). One learner's
    # cards bunching on a day is handled by the daily review budget anyway.
    enable_fuzzing=False,
)

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
TIMING_KEPT = 40          # recent answer times kept per answer format
TIMING_MIN_SAMPLES = 8    # until then, speed doesn't change the grade
TIMING_IGNORE_MS = 30_000  # longer than this: probably looked away, ignore speed
EASY_MIN_REPS = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def new_card() -> dict[str, Any]:
    """A card that has never been reviewed: due now, in the first learning step."""
    return _store(Card(due=_now()), reps=0, lapses=0)


def _store(card: Card, *, reps: int, lapses: int) -> dict[str, Any]:
    due_local = card.due.astimezone().date().isoformat()
    return {
        "fsrs": card.to_dict(),
        "due": due_local,  # local date: what "due today" is decided on
        "reps": reps,
        "lapses": lapses,
        "last": card.last_review.isoformat() if card.last_review else "",
    }


def from_legacy(old: dict[str, Any]) -> dict[str, Any]:
    """Convert a Leitner card ({box, due, reps, lapses}) without losing its progress.

    Box N meant "remembered for about BOX_DAYS[N] days", which is what FSRS calls
    stability. Difficulty starts at the middle and rises a little per past lapse.
    """
    box_days = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30, 6: 60, 7: 120}
    box = int(old.get("box") or 1)
    reps = int(old.get("reps") or 0)
    lapses = int(old.get("lapses") or 0)
    if reps == 0:
        return {**new_card(), "reps": 0, "lapses": lapses}
    try:
        due_day = date.fromisoformat(str(old.get("due"))[:10])
    except ValueError:
        due_day = date.today()
    due = datetime.combine(due_day, time(4, 0)).astimezone().astimezone(timezone.utc)
    stability = float(box_days.get(box, 1))
    card = Card(
        state=State.Review,
        stability=stability,
        difficulty=min(10.0, 5.0 + 0.5 * lapses),
        due=due,
        last_review=due - timedelta(days=stability),
    )
    return _store(card, reps=reps, lapses=lapses)


def placed_card(stability_days: float, due_day: date) -> dict[str, Any]:
    """A card the placement test showed the learner already knows: a short review
    memory, so the first review soon confirms it (or catches an overestimate)."""
    due = datetime.combine(due_day, time(4, 0)).astimezone().astimezone(timezone.utc)
    card = Card(state=State.Review, stability=float(stability_days), difficulty=5.0,
                due=due, last_review=due - timedelta(days=stability_days))
    return {**_store(card, reps=1, lapses=0), "placed": True}


def ensure(card: dict[str, Any]) -> dict[str, Any]:
    """Cards saved before FSRS get converted on first touch."""
    return card if isinstance(card.get("fsrs"), dict) else from_legacy(card)


def _card(stored: dict[str, Any]) -> Card:
    return Card.from_dict(ensure(stored)["fsrs"])


def review(stored: dict[str, Any], rating: int, *, now: datetime | None = None) -> dict[str, Any]:
    stored = ensure(stored)
    card, _log = SCHEDULER.review_card(_card(stored), Rating(rating), now or _now())
    reps = int(stored.get("reps") or 0) + 1
    lapses = int(stored.get("lapses") or 0) + (1 if rating == AGAIN and stored["fsrs"].get("state") == State.Review.value else 0)
    return _store(card, reps=reps, lapses=lapses)


def preview(stored: dict[str, Any], *, now: datetime | None = None) -> dict[int, int]:
    """Seconds until the next review for each possible grade (shown on the grade buttons)."""
    now = now or _now()
    card = _card(stored)
    out = {}
    for rating in (AGAIN, HARD, GOOD, EASY):
        nxt, _log = SCHEDULER.review_card(Card.from_dict(card.to_dict()), Rating(rating), now)
        out[rating] = max(0, int((nxt.due - now).total_seconds()))
    return out


def is_learning(stored: dict[str, Any]) -> bool:
    """New, or in a short learning/relearning step (minutes, not days)."""
    return ensure(stored)["fsrs"].get("state") != State.Review.value


def stability(stored: dict[str, Any]) -> float:
    return float(ensure(stored)["fsrs"].get("stability") or 0.0)


def due_at(stored: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(ensure(stored)["fsrs"]["due"])


def known(stored: dict[str, Any]) -> bool:
    """Past the learning steps and reviewed a couple of times: ready to be produced, not just recognised."""
    stored = ensure(stored)
    return not is_learning(stored) and int(stored.get("reps") or 0) >= 2


def speed_ratio(ms: int | None, times: list[int]) -> float | None:
    """This answer's time as a multiple of the learner's usual for the format, or None."""
    if not ms or ms >= TIMING_IGNORE_MS or len(times) < TIMING_MIN_SAMPLES:
        return None
    return round(ms / max(1.0, median(times)), 3)


def rating_for(
    *,
    correct: bool,
    ms: int | None,
    helped: bool,
    guessed: bool,
    band: str,
    reps: int,
    times: list[int],
    hard_ratio: float = 2.0,
    easy_ratio: float = 0.6,
    close_grade: int = HARD,
    helped_grade: int = HARD,
) -> int:
    """Again / Hard / Good / Easy from what happened, never asked of the learner.

    The ratios and what "close" / "helped" mean come from grader.tune (the
    learner's own corrections); the defaults are the starting point.
    """
    if not correct or band == "off":
        return AGAIN
    if guessed:
        return HARD
    flagged = (band == "close" and close_grade == HARD) or (helped and helped_grade == HARD)
    if flagged:
        return HARD
    ratio = speed_ratio(ms, times)
    if ratio is not None:
        if ratio > hard_ratio:
            return HARD
        if ratio < easy_ratio and reps >= EASY_MIN_REPS and band != "close" and not helped:
            return EASY
    return GOOD


def record_time(timing: dict[str, list[int]], fmt: str, ms: int | None, correct: bool) -> None:
    """Keep recent answer times per format (only clean right answers), for rating_for."""
    if not correct or not ms or ms >= TIMING_IGNORE_MS:
        return
    timing[fmt] = (timing.get(fmt, []) + [int(ms)])[-TIMING_KEPT:]
