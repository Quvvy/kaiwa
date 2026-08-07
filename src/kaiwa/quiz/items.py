from __future__ import annotations

from typing import Any

LEVEL_CHOICES: list[dict[str, str]] = [
    {"label": "Just starting", "value": "pre_n5"},
    {"label": "Can handle basics", "value": "n5"},
    {"label": "Getting comfortable", "value": "n4"},
]

# Self-assessment onboarding — no right/wrong, no Japanese audio.
PLACEMENT_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "overall",
        "prompt": "What stage of Japanese do you consider yourself at?",
        "field": "overall",
        "choices": LEVEL_CHOICES,
    },
    {
        "id": "listening",
        "prompt": "How's your listening right now?",
        "field": "comprehension",
        "choices": LEVEL_CHOICES,
    },
    {
        "id": "speaking",
        "prompt": "How's your speaking right now?",
        "field": "speaking",
        "choices": LEVEL_CHOICES,
    },
    {
        "id": "pace",
        "prompt": "How hard should Kaiwa aim in chat?",
        "field": "pace",
        "choices": [
            {"label": "Keep it gentle", "value": "gentle"},
            {"label": "Match me", "value": "match"},
            {"label": "Stretch a bit", "value": "stretch"},
        ],
    },
]


def question_by_id(question_id: str) -> dict[str, Any] | None:
    for question in PLACEMENT_QUESTIONS:
        if question["id"] == question_id:
            return question
    return None
