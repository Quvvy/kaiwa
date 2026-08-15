from __future__ import annotations

from typing import Any

LEVEL_CHOICES: list[dict[str, str]] = [
    {"label": "Just starting", "value": "pre_n5"},
    {"label": "Can handle basics", "value": "n5"},
    {"label": "Getting comfortable", "value": "n4"},
]

COMFORT_CHOICES: list[dict[str, str]] = [
    {"label": "Barely / not yet", "value": "barely"},
    {"label": "Some — with effort", "value": "some"},
    {"label": "Mostly comfortable", "value": "comfortable"},
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
    {
        "id": "kana",
        "prompt": "How comfortable are you with hiragana and katakana?",
        "field": "kana",
        "choices": COMFORT_CHOICES,
    },
    {
        "id": "reading",
        "prompt": "Can you read simple Japanese sentences (with furigana / kana OK)?",
        "field": "reading",
        "choices": COMFORT_CHOICES,
    },
    {
        "id": "grammar",
        "prompt": "How are particles and basic grammar for you?",
        "field": "grammar",
        "choices": COMFORT_CHOICES,
    },
    {
        "id": "follow",
        "prompt": "How much slow, clear spoken Japanese can you follow?",
        "field": "follow",
        "choices": [
            {"label": "Only a few words", "value": "barely"},
            {"label": "Short simple sentences", "value": "some"},
            {"label": "Most of a slow chat turn", "value": "comfortable"},
        ],
    },
    {
        "id": "topics",
        "prompt": "What do you want to talk about? (pick up to 3)",
        "field": "topics",
        "multi": True,
        "max_select": 3,
        "allow_other": True,
        "choices": [
            {"label": "Daily life", "value": "daily life"},
            {"label": "Food & travel", "value": "food travel"},
            {"label": "Hobbies & games", "value": "hobbies"},
            {"label": "Work / school", "value": "work school"},
            {"label": "Anime / culture", "value": "anime culture"},
            {"label": "Just chatting", "value": "casual chat"},
            {"label": "Other…", "value": "__other__"},
        ],
    },
    {
        "id": "help_style",
        "prompt": "When you’re stuck, how should Kaiwa help?",
        "field": "help_style",
        "choices": [
            {"label": "More English is fine", "value": "more_en"},
            {"label": "Mix — JP first, English if needed", "value": "mix"},
            {"label": "Stay in Japanese as much as possible", "value": "mostly_jp"},
        ],
    },
    {
        "id": "note",
        "prompt": "Anything else Kaiwa should know? (optional)",
        "field": "note",
        "free_text": True,
        "choices": [],
        "placeholder": "Optional — anything helpful for Kaiwa…",
        "hint": "Optional — leave blank to skip.",
        "max_length": 300,
    },
    {
        "id": "preferred_name",
        "prompt": "What should Kaiwa call you?",
        "field": "preferred_name",
        "free_text": True,
        "choices": [],
        "placeholder": "Eli / イーライ",
        "hint": "Optional — name as you want it said. Add a reading if useful.",
        "max_length": 40,
    },
]


def question_by_id(question_id: str) -> dict[str, Any] | None:
    for question in PLACEMENT_QUESTIONS:
        if question["id"] == question_id:
            return question
    return None
