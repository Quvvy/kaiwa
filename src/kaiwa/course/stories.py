"""Extra listening: a fresh short dialogue built from what the learner already knows.

Comprehension grows with lots of input the learner can almost fully follow.
The units only hold one dialogue each, so this generates more at exactly the
learner's level: learned phrases recombined, at most two new words (glossed).
"""

from __future__ import annotations

import random
from typing import Any

from kaiwa import llm
from kaiwa.config import Settings
from kaiwa.course.state import learned_phrase_ids, load_state, phrase

STORY_SYSTEM = """\
You write tiny listening exercises for an adult absolute beginner learning Japanese (pre-N5).

Write a natural, everyday conversation between two people (A and B) that the learner can
follow almost completely. Rules:
- 4 to 6 lines. Each line at most 2 short sentences.
- Grammar: use ONLY sentence patterns that appear in the learner's known phrases. No new verb
  forms (no 〜ましょう, 〜たい, 〜て, plain forms) unless a known phrase already uses them.
  If the learner only knows greetings, the conversation is greetings, thanks, apologies and
  reactions — that is fine and still useful.
- Vocabulary: known words only, plus at most 2 new NOUNS that slot into a known pattern
  (e.g. known ねこがすきです → new いぬがすきです). Gloss each new noun where it first appears.
  Question words (どこ, なに, いつ…) count as new unless known.
- Polite です/ます style. Write Japanese in kana only (hiragana + katakana), no kanji.
- Make it a tiny situation with a point (a plan, a preference, a small surprise), not a list.
- Then 2 comprehension questions in English with 3 short English choices each; exactly one
  correct, answerable only by understanding the Japanese.

Return JSON only:
{
  "scene": "one short English sentence setting the scene",
  "lines": [{"who": "a" | "b", "jp": "kana", "en": "natural English", "gloss": "new word = meaning, or empty"}],
  "questions": [{"q": "...", "choices": ["...", "...", "..."], "answer": 0}]
}
"""


def _valid(data: dict[str, Any]) -> bool:
    lines = data.get("lines")
    questions = data.get("questions")
    if not isinstance(lines, list) or not 3 <= len(lines) <= 8:
        return False
    for line in lines:
        if not isinstance(line, dict) or not str(line.get("jp") or "").strip() or line.get("who") not in {"a", "b"}:
            return False
    if not isinstance(questions, list) or not questions:
        return False
    for q in questions:
        choices = q.get("choices") if isinstance(q, dict) else None
        if not isinstance(choices, list) or len(choices) < 2:
            return False
        if not isinstance(q.get("answer"), int) or not 0 <= q["answer"] < len(choices):
            return False
    return True


def generate(settings: Settings, *, topic_hint: str = "") -> dict[str, Any] | None:
    """A validated dialogue, or None when nothing is learned yet / the call failed."""
    state = load_state()
    ids = learned_phrase_ids(state)
    if not ids:
        return None
    known = [phrase(i) for i in ids]
    lines = "\n".join(f"- {p['jp']} ({p['en']})" for p in known if p)
    seed = random.choice(["at school", "at a café", "on the weekend", "at home", "meeting a friend", "shopping", "after work"])
    user = (
        f"Learner's known phrases:\n{lines}\n\n"
        f"Setting idea: {topic_hint or seed}. Recent phrases are the priority to recycle: "
        f"{', '.join(p['jp'] for p in known[-6:] if p)}"
    )
    for _ in range(2):
        data = llm.complete_json(settings, STORY_SYSTEM, user)
        if data and _valid(data):
            return {
                "scene": str(data.get("scene") or "").strip(),
                "lines": [
                    {
                        "who": line["who"],
                        "jp": str(line["jp"]).strip(),
                        "en": str(line.get("en") or "").strip(),
                        "gloss": str(line.get("gloss") or "").strip(),
                    }
                    for line in data["lines"]
                ],
                "questions": [_shuffled(q) for q in data["questions"][:3]],
            }
    return None


def _shuffled(q: dict[str, Any]) -> dict[str, Any]:
    """Models tend to put the right answer first; shuffle so position gives nothing away."""
    choices = [str(c) for c in q["choices"]]
    right = choices[int(q["answer"])]
    random.shuffle(choices)
    return {"q": str(q.get("q") or ""), "choices": choices, "answer": choices.index(right)}
