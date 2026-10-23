"""Judge a spoken answer in a lesson's Speak step.

The learner answers one of Kaiwa's questions with what the unit taught. A
pattern match says "probably fine", but only a reader catches を/が slips or
a reply that doesn't answer the question — so Flash judges every attempt and
the pattern result is the fallback when the call fails.
"""

from __future__ import annotations

from typing import Any

from kaiwa import llm
from kaiwa.config import Settings
from kaiwa.course.speech_check import matches_any

VERDICTS = ("great", "ok", "retry")

COACH_SYSTEM = """\
You are a warm, precise Japanese speaking coach for an adult absolute beginner (pre-N5).
The learner just answered a line spoken by a Japanese conversation partner. Their answer
came through speech recognition, so ignore odd kanji choices and small transcription noise;
judge what a Japanese listener would have heard and understood.

Return JSON only:
{
  "verdict": "great" | "ok" | "retry",
  "said_en": "what the learner's reply means in plain English, literally — so they can see what they actually said",
  "model": "a natural reply in Japanese, in kana (no kanji), polite です/ます style, as close as possible to what the learner tried to say; keep their content (their name, food, place…)",
  "tip": "one short, concrete English tip about the single most useful fix — or an empty string if verdict is great"
}

Verdicts:
- great: a fitting reply a Japanese listener understands with no effort. Minor recognition noise is fine.
- ok: understandable and on-topic, but with one real mistake worth fixing (wrong particle such as を for が with すき, wrong verb form, missing です/ます where needed, a word that doesn't fit).
- retry: not understandable, not Japanese, or doesn't answer the line at all.

Rules: never explain grammar terms longer than a few words. Never pile on several corrections — pick one.
If the learner answered in English, verdict is retry and the tip tells them how to say it in Japanese.
"""


def judge(
    settings: Settings,
    *,
    task: dict[str, Any],
    heard: str,
) -> dict[str, Any]:
    matched = matches_any(task.get("expect") or [], heard)
    user = (
        f"Partner said: {task['say']}\n"
        f"Situation (what the learner was asked to do): {task['situation']}\n"
        f"A model answer: {task['hint']}\n"
        f"Learner said (speech recognition): {heard}\n"
        f"Simple pattern check passed: {'yes' if matched else 'no'}"
    )
    data = llm.complete_json(settings, COACH_SYSTEM, user) if settings.deepseek_api_key else None
    if data and str(data.get("verdict")) in VERDICTS:
        return {
            "verdict": str(data["verdict"]),
            "said_en": str(data.get("said_en") or "").strip().strip("\"'“”"),
            "model": str(data.get("model") or task["hint"]).strip(),
            "tip": str(data.get("tip") or "").strip(),
            "heard": heard,
            "coached": True,
        }
    return {
        "verdict": "great" if matched else "retry",
        "said_en": "",
        "model": task["hint"],
        "tip": "" if matched else "Try the model answer — tap it to hear it first.",
        "heard": heard,
        "coached": False,
    }
