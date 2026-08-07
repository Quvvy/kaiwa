from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from kaiwa.learner_profile import (
    LearnerProfile,
    clamp_level,
    min_level,
    nudge_level,
)
from kaiwa.prefs import UserPrefs
from kaiwa.quiz.items import PLACEMENT_QUESTIONS, question_by_id

PLACEMENT_SIZE = len(PLACEMENT_QUESTIONS)
QUIZ_SIZE = PLACEMENT_SIZE  # alias for existing API imports
SESSION_TTL_SEC = 30 * 60


@dataclass
class QuizItemState:
    id: str
    prompt: str
    field: str
    choices: list[dict[str, str]]
    answered: bool = False
    chosen_index: int | None = None
    chosen_value: str | None = None


@dataclass
class QuizSession:
    id: str
    items: list[QuizItemState]
    created_at: float = field(default_factory=time.time)
    finished: bool = False

    def item(self, item_id: str) -> QuizItemState | None:
        for row in self.items:
            if row.id == item_id:
                return row
        return None

    def answers(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for row in self.items:
            if row.answered and row.chosen_value is not None:
                out[row.id] = row.chosen_value
        return out


_sessions: dict[str, QuizSession] = {}


def _purge_stale(now: float | None = None) -> None:
    now = time.time() if now is None else now
    dead = [sid for sid, sess in _sessions.items() if now - sess.created_at > SESSION_TTL_SEC]
    for sid in dead:
        _sessions.pop(sid, None)


def get_session(session_id: str) -> QuizSession | None:
    _purge_stale()
    return _sessions.get(session_id)


def discard_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def start_quiz_session(
    prefs: UserPrefs | None = None,
    profile: LearnerProfile | None = None,
) -> QuizSession:
    """Start a fixed self-assessment questionnaire (prefs/profile unused; kept for call sites)."""
    del prefs, profile
    _purge_stale()
    states = [
        QuizItemState(
            id=str(q["id"]),
            prompt=str(q["prompt"]),
            field=str(q["field"]),
            choices=[{"label": str(c["label"]), "value": str(c["value"])} for c in q["choices"]],
        )
        for q in PLACEMENT_QUESTIONS
    ]
    session = QuizSession(id=uuid.uuid4().hex, items=states)
    _sessions[session.id] = session
    return session


def public_items(session: QuizSession) -> list[dict[str, Any]]:
    return [
        {
            "id": row.id,
            "prompt": row.prompt,
            "choices": [c["label"] for c in row.choices],
        }
        for row in session.items
    ]


def answer_item(session: QuizSession, item_id: str, choice_index: int) -> dict[str, Any]:
    if session.finished:
        raise ValueError("placement already finished")
    row = session.item(item_id)
    if row is None:
        raise KeyError(f"item not in session: {item_id}")
    if row.answered:
        return {
            "chosen_index": row.chosen_index,
            "chosen_value": row.chosen_value,
            "already_answered": True,
        }
    if choice_index < 0 or choice_index >= len(row.choices):
        raise ValueError("choice_index out of range")
    row.answered = True
    row.chosen_index = choice_index
    row.chosen_value = row.choices[choice_index]["value"]
    return {
        "chosen_index": row.chosen_index,
        "chosen_value": row.chosen_value,
        "already_answered": False,
    }


def _goal_from_pace(overall: str, comprehension: str, pace: str) -> str:
    if pace == "gentle":
        return min_level(overall, comprehension)
    if pace == "stretch":
        return nudge_level(overall, 1)
    return clamp_level(overall)


def apply_self_assessment(
    profile: LearnerProfile,
    prefs: UserPrefs,
    answers: dict[str, str],
) -> tuple[LearnerProfile, UserPrefs, dict[str, str]]:
    """Trust self-ratings: set speaking, comprehension, goal. Returns profile, prefs, summary."""
    overall = clamp_level(answers.get("overall", "pre_n5"))
    comprehension = clamp_level(answers.get("listening", overall))
    speaking = clamp_level(answers.get("speaking", overall))
    pace = answers.get("pace", "match")
    if pace not in {"gentle", "match", "stretch"}:
        pace = "match"
    goal = _goal_from_pace(overall, comprehension, pace)

    profile.speaking_level = speaking  # type: ignore[assignment]
    profile.comprehension_level = comprehension  # type: ignore[assignment]
    profile.confidence = 0.7
    profile.notes = (
        f"Self-assessment: overall={overall}, speaking={speaking}, "
        f"listening={comprehension}, pace={pace}, goal={goal}."
    )[:400]

    prefs.goal_level = goal  # type: ignore[assignment]

    summary = {
        "overall": overall,
        "speaking_level": speaking,
        "comprehension_level": comprehension,
        "goal_level": goal,
        "pace": pace,
    }
    return profile, prefs, summary


# Back-compat name used nowhere after rewrite; keep if anything still imports it.
def apply_quiz_to_profile(
    profile: LearnerProfile,
    prefs: UserPrefs,
    answers: dict[str, str],
) -> tuple[LearnerProfile, UserPrefs, dict[str, str]]:
    return apply_self_assessment(profile, prefs, answers)


def question_prompt(question_id: str) -> str:
    bank = question_by_id(question_id)
    if bank is None:
        raise KeyError(question_id)
    return str(bank["prompt"])
