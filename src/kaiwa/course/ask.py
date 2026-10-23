"""The lesson Ask box: short English explanations on demand.

Lessons stay Japanese-first; when the learner is confused they ask, and the
answer is grounded in what's on screen and what the course has taught.
"Break this down" goes to Flash (fast lookups); "why" and typed questions go
to Pro, where grammar accuracy matters more than a second of latency.
"""

from __future__ import annotations

import json
from typing import Any

from kaiwa import llm
from kaiwa.config import Settings

QUICK = {
    "breakdown": "Break this down word by word.",
    "why": "Why is it said this way?",
    "wrong": "What did I get wrong, and how do I fix it?",
}

ASK_SYSTEM = """\
You are the explanation box inside a Japanese course for an adult beginner (pre-N5).
The learner tapped "Ask" because something on screen confused them. They dislike reading
long English, so every word must earn its place: answer the exact question, plainly,
like a sharp tutor sitting next to them. No greetings, no praise, no filler, no "great question".

You get the screen they are on (JSON) and what the course has taught so far.

Return JSON only:
{
  "answer": "the direct answer in 1-3 short sentences of plain English",
  "breakdown": [{"jp": "piece", "en": "meaning or role"}],
  "examples": [{"jp": "short Japanese sentence", "en": "English"}],
  "more": "optional deeper why, at most 80 words; empty string if the answer already covers it",
  "unsure": false
}

Rules:
- breakdown: only when splitting the sentence helps (always for "break this down"); otherwise [].
  Split into words/particles/endings in order; give particles their role (topic, object, question…).
- examples: 0-2, very short, in kana (no kanji), using mostly words the course has taught.
- Write Japanese in kana. Use romaji only if the learner asks how to pronounce something.
- Never use grammar jargon without a 2-3 word gloss (e.g. "particle は (topic marker)").
- If the honest answer is "it's a fixed expression" or "it's a nuance natives feel", say so briefly.
- If you are not confident (rare usage, regional, disputed), set "unsure": true and say so in the answer.
- If the question is not about Japanese, answer in one sentence and steer back.
"""


def _clip(value: Any, limit: int = 1500) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return text[:limit]


def ask(
    settings: Settings,
    *,
    question: str,
    quick: str,
    context: dict[str, Any],
    known: list[dict[str, str]],
) -> dict[str, Any]:
    q = QUICK.get(quick) or question.strip()
    if not q:
        raise ValueError("Type a question first.")
    taught = "; ".join(f"{p['jp']} ({p['en']})" for p in known[-40:]) or "nothing yet (first lesson)"
    user = (
        f"Screen: {_clip(context)}\n"
        f"Taught so far: {taught}\n"
        f"Question: {q}"
    )
    model = settings.deepseek_model if quick == "breakdown" else settings.deepseek_model_pro
    data = llm.complete_json(settings, ASK_SYSTEM, user, model=model)
    if data is None and model != settings.deepseek_model:
        data = llm.complete_json(settings, ASK_SYSTEM, user)  # Pro failed: Flash is better than nothing
    if not data or not str(data.get("answer") or "").strip():
        raise RuntimeError("Couldn't get an answer. Check your connection and try again.")

    def pairs(key: str, limit: int) -> list[dict[str, str]]:
        rows = data.get(key) if isinstance(data.get(key), list) else []
        out = []
        for row in rows[:limit]:
            if isinstance(row, dict) and str(row.get("jp") or "").strip():
                out.append({"jp": str(row["jp"]).strip(), "en": str(row.get("en") or "").strip()})
        return out

    return {
        "question": q,
        "answer": str(data["answer"]).strip(),
        "breakdown": pairs("breakdown", 12),
        "examples": pairs("examples", 2),
        "more": str(data.get("more") or "").strip(),
        "unsure": bool(data.get("unsure")),
    }
