from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from kaiwa.learner_profile import (
    LearnerProfile,
    MAX_NOTES,
    _normalize_tags,
    clamp_level,
    min_level,
    nudge_level,
)
from kaiwa.prefs import UserPrefs
from kaiwa.quiz.items import PLACEMENT_QUESTIONS, question_by_id

PLACEMENT_SIZE = len(PLACEMENT_QUESTIONS)
QUIZ_SIZE = PLACEMENT_SIZE  # alias for existing API imports
SESSION_TTL_SEC = 30 * 60
OTHER_VALUE = "__other__"
MAX_OTHER_TEXT = 120
MAX_NOTE_TEXT = 300

_COMFORT_TO_LEVEL = {
    "barely": "pre_n5",
    "some": "n5",
    "comfortable": "n4",
}

_HELP_TO_LANGUAGE = {
    "more_en": "adaptive",
    "mix": "adaptive",
    "mostly_jp": "immerse",
}


@dataclass
class QuizItemState:
    id: str
    prompt: str
    field: str
    choices: list[dict[str, str]]
    multi: bool = False
    max_select: int = 1
    free_text: bool = False
    allow_other: bool = False
    answered: bool = False
    chosen_index: int | None = None
    chosen_value: str | None = None
    chosen_indices: list[int] = field(default_factory=list)


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
            choices=[{"label": str(c["label"]), "value": str(c["value"])} for c in (q.get("choices") or [])],
            multi=bool(q.get("multi")),
            max_select=max(1, int(q.get("max_select") or (3 if q.get("multi") else 1))),
            free_text=bool(q.get("free_text")),
            allow_other=bool(q.get("allow_other")),
        )
        for q in PLACEMENT_QUESTIONS
    ]
    session = QuizSession(id=uuid.uuid4().hex, items=states)
    _sessions[session.id] = session
    return session


def public_items(session: QuizSession) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in session.items:
        other_index = None
        if row.allow_other:
            for i, c in enumerate(row.choices):
                if c["value"] == OTHER_VALUE:
                    other_index = i
                    break
        out.append(
            {
                "id": row.id,
                "prompt": row.prompt,
                "choices": [c["label"] for c in row.choices],
                "multi": row.multi,
                "max_select": row.max_select,
                "free_text": row.free_text,
                "allow_other": row.allow_other,
                "other_value": OTHER_VALUE if row.allow_other else None,
                "other_index": other_index,
            }
        )
    return out


def _sanitize_other_topic(text: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        raise ValueError("type a short topic for Other")
    if len(cleaned) > MAX_OTHER_TEXT:
        cleaned = cleaned[:MAX_OTHER_TEXT].rstrip()
    # Match tag length used elsewhere
    return cleaned[:40]


def answer_item(
    session: QuizSession,
    item_id: str,
    choice_index: int | None = None,
    choice_indices: list[int] | None = None,
    text: str | None = None,
) -> dict[str, Any]:
    if session.finished:
        raise ValueError("placement already finished")
    row = session.item(item_id)
    if row is None:
        raise KeyError(f"item not in session: {item_id}")
    if row.answered:
        return {
            "chosen_index": row.chosen_index,
            "chosen_indices": list(row.chosen_indices),
            "chosen_value": row.chosen_value,
            "already_answered": True,
        }

    if row.free_text:
        note = " ".join((text or "").strip().split())
        if len(note) > MAX_NOTE_TEXT:
            note = note[:MAX_NOTE_TEXT].rstrip()
        row.answered = True
        row.chosen_index = None
        row.chosen_indices = []
        row.chosen_value = note
        return {
            "chosen_index": None,
            "chosen_indices": [],
            "chosen_value": row.chosen_value,
            "already_answered": False,
        }

    if row.multi:
        indices = list(choice_indices or [])
        if choice_index is not None and not indices:
            indices = [int(choice_index)]
        if not indices:
            raise ValueError("select at least one topic")
        seen: set[int] = set()
        clean: list[int] = []
        for i in indices:
            if i in seen:
                continue
            if i < 0 or i >= len(row.choices):
                raise ValueError("choice_index out of range")
            seen.add(i)
            clean.append(i)
        if len(clean) > row.max_select:
            raise ValueError(f"pick at most {row.max_select}")
        values: list[str] = []
        for i in clean:
            val = row.choices[i]["value"]
            if row.allow_other and val == OTHER_VALUE:
                values.append(_sanitize_other_topic(text or ""))
            else:
                values.append(val)
        row.answered = True
        row.chosen_indices = clean
        row.chosen_index = clean[0]
        row.chosen_value = ",".join(values)
        return {
            "chosen_index": row.chosen_index,
            "chosen_indices": list(row.chosen_indices),
            "chosen_value": row.chosen_value,
            "already_answered": False,
        }

    if choice_index is None:
        raise ValueError("choice_index required")
    if choice_index < 0 or choice_index >= len(row.choices):
        raise ValueError("choice_index out of range")
    row.answered = True
    row.chosen_index = choice_index
    row.chosen_indices = [choice_index]
    row.chosen_value = row.choices[choice_index]["value"]
    return {
        "chosen_index": row.chosen_index,
        "chosen_indices": list(row.chosen_indices),
        "chosen_value": row.chosen_value,
        "already_answered": False,
    }


def _goal_from_pace(overall: str, comprehension: str, pace: str) -> str:
    if pace == "gentle":
        return min_level(overall, comprehension)
    if pace == "stretch":
        return nudge_level(overall, 1)
    return clamp_level(overall)


def _comfort_level(value: str) -> str:
    return _COMFORT_TO_LEVEL.get((value or "").strip().lower(), "pre_n5")


def apply_self_assessment(
    profile: LearnerProfile,
    prefs: UserPrefs,
    answers: dict[str, str],
) -> tuple[LearnerProfile, UserPrefs, dict[str, str]]:
    """Trust self-ratings: set speaking, comprehension, goal, topics, help style."""
    overall = clamp_level(answers.get("overall", "pre_n5"))
    comprehension = clamp_level(answers.get("listening", overall))
    speaking = clamp_level(answers.get("speaking", overall))
    pace = answers.get("pace", "match")
    if pace not in {"gentle", "match", "stretch"}:
        pace = "match"

    kana = (answers.get("kana") or "some").strip().lower()
    reading = (answers.get("reading") or "some").strip().lower()
    grammar = (answers.get("grammar") or "some").strip().lower()
    follow = (answers.get("follow") or "some").strip().lower()
    help_style = (answers.get("help_style") or "mix").strip().lower()
    if help_style not in _HELP_TO_LANGUAGE:
        help_style = "mix"

    # Soft-min comprehension from skill answers (never raise above listening self-rate).
    for skill in (follow, reading, kana, grammar):
        comprehension = min_level(comprehension, _comfort_level(skill))

    goal = _goal_from_pace(overall, comprehension, pace)

    topics_raw = answers.get("topics") or ""
    topics = _normalize_tags(
        [t.strip() for t in topics_raw.split(",") if t.strip() and t.strip() != OTHER_VALUE]
    )

    free_note = " ".join((answers.get("note") or "").strip().split())
    if len(free_note) > MAX_NOTE_TEXT:
        free_note = free_note[:MAX_NOTE_TEXT].rstrip()

    profile.speaking_level = speaking  # type: ignore[assignment]
    profile.comprehension_level = comprehension  # type: ignore[assignment]
    profile.confidence = 0.85
    profile.placement_completed = True
    if topics:
        profile.topic_tags = topics[:8]
        prefs.topic_preferences = list(topics[:8])

    prefs.goal_level = goal  # type: ignore[assignment]
    prefs.language_policy = _HELP_TO_LANGUAGE[help_style]  # type: ignore[assignment]

    completed_at = datetime.now(timezone.utc).isoformat()
    placement: dict[str, Any] = {
        "overall": overall,
        "listening": clamp_level(answers.get("listening", overall)),
        "speaking": speaking,
        "pace": pace,
        "kana": kana,
        "reading": reading,
        "grammar": grammar,
        "follow": follow,
        "topics": topics,
        "help_style": help_style,
        "completed_at": completed_at,
        "chat_turns_at_complete": int(profile.stats.chat_turns),
    }
    if free_note:
        placement["free_note"] = free_note
    profile.placement = placement

    notes = (
        f"Place me: overall={overall}, speaking={speaking}, listening→comp={comprehension}, "
        f"pace={pace}, goal={goal}; kana={kana}, reading={reading}, grammar={grammar}, "
        f"follow={follow}, help={help_style}, topics={', '.join(topics) or '(none)'}."
    )
    if free_note:
        notes = f"{notes} Note: {free_note}"
    profile.notes = notes[:MAX_NOTES]

    summary = {
        "overall": overall,
        "speaking_level": speaking,
        "comprehension_level": comprehension,
        "goal_level": goal,
        "pace": pace,
        "kana": kana,
        "reading": reading,
        "grammar": grammar,
        "follow": follow,
        "help_style": help_style,
        "topics": ",".join(topics),
        "free_note": free_note,
        "language_policy": prefs.language_policy,
        "placement_completed": "true",
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
