"""What Chat shares with the course: the learner's known material in, mistakes out.

In: Chat builds on the same material as talk practice and extra listening (taught
phrases, known words with the shaky ones to recycle, taught sentence patterns), and
in Easy mode a reply that leans on unknown material is rewritten once, measured the
same way (coverage of the reply's kana by known pieces).

Out: each Chat turn is tagged with the same mistake types as the lesson coach and
talk practice and written to the learner log, so every spoken turn feeds one record.
"""

from __future__ import annotations

import random
import re
from typing import Any

from kaiwa.config import Settings
from kaiwa.course.learner_log import MISTAKES_PROMPT, mistakes
from kaiwa.course.state import learned_phrase_ids, listening_context, load_state, phrase

# Easy-mode Chat replies below this share of known kana are rewritten once. Lower
# than talk practice (0.85): Chat lines are short, and its rules allow one new word.
REPLY_OK = 0.7
PHRASES_SHOWN = 40    # most recent taught phrases
SHAKY_SHOWN = 12      # weak words Chat should bring back
SOLID_SHOWN = 40
PATTERNS_SHOWN = 10

# Conversational glue Chat leans on by design: its recast echoes the learner's own
# sentence (ねこがすきなんだね) and short reactions carry no new content. Without
# these, most good replies would be rewritten.
CHAT_GLUE = ["なんだね", "んだね", "なんだ", "いいね", "いい", "そうですか", "そう", "うん", "ええ", "へえ", "わあ",
             "ほんと", "だね", "だよ", "ね", "よ", "な"]

_KANJI = re.compile(r"[一-鿿々〆]")
# English glosses, romaji and digits aren't Japanese the learner has to understand.
_NOT_JP = re.compile(r"\([^)]*\)|（[^）]*）|[A-Za-z0-9][A-Za-z0-9 ,.'!?:;\-/]*")


def context() -> dict[str, Any]:
    """The learner's known material for the Chat prompt, plus pieces for the coverage check.

    Empty lists before any lesson is learned (Chat then keeps to greetings and yes/no).
    """
    state = load_state()
    ids = learned_phrase_ids(state)
    ctx = listening_context(state)
    phrases = [p for p in (phrase(i) for i in ids) if p]
    return {
        "phrases": [{"jp": p["jp"], "en": p["en"]} for p in phrases[-PHRASES_SHOWN:]],
        "shaky": random.sample(ctx["shaky"], min(len(ctx["shaky"]), SHAKY_SHOWN)),
        "solid": random.sample(ctx["solid"], min(len(ctx["solid"]), SOLID_SHOWN)),
        "patterns": random.sample(ctx["patterns"], min(len(ctx["patterns"]), PATTERNS_SHOWN)),
        "words": [w["jp"] for w in ctx["shaky"] + ctx["solid"]],
        "pieces": [w["jp"] for w in ctx["shaky"] + ctx["solid"]] + [p["jp"] for p in phrases] + ctx["patterns"],
    }


def _kana(text: str) -> str:
    """Reply text as the learner hears it: kanji read as hiragana, katakana kept (names pass)."""
    from kaiwa.course.speech_check import _kks

    return "".join(
        (part.get("hira") or part.get("orig", "")) if _KANJI.search(part.get("orig", "")) else part.get("orig", "")
        for part in _kks.convert(text)
    )


def reply_coverage(reply: str, pieces: list[str]) -> tuple[float, list[str]]:
    """(share of the reply's Japanese the learner knows, unknown leftovers)."""
    from kaiwa.course.stories import coverage

    lines = [_kana(line) for line in _NOT_JP.sub(" ", reply).splitlines() if line.strip()]
    if not any(lines):
        return 1.0, []
    share, unknown = coverage(lines, [*pieces, *CHAT_GLUE])
    return share, [u for u in dict.fromkeys(unknown) if len(u) > 1]


TAG_SYSTEM = """\
You check one line an adult absolute beginner (pre-N5) said in a Japanese conversation.
The line came through speech recognition: ignore odd kanji and small transcription noise
and judge what a Japanese listener would have heard. Casual and polite speech are both fine.
Only tag real mistakes; a short or simple answer is not a mistake.
""" + MISTAKES_PROMPT + """
Return JSON only: {"mistakes": [...]}"""


def tag_mistakes(settings: Settings, *, prompt_line: str, said: str) -> list[dict[str, str]] | None:
    """Mistake tags for the learner's Chat line; None when the call failed."""
    from kaiwa import llm

    user = f"The other person said: {prompt_line or '(start of conversation)'}\nThe learner said: {said}"
    data = llm.complete_json(settings, TAG_SYSTEM, user)
    if not isinstance(data, dict):
        return None
    return mistakes(data.get("mistakes"))


def log_turn(settings: Settings, history: list[dict[str, str]], *, log_path: Any = None) -> None:
    """Tag the learner's last Chat line and write it to the learner log (soft-fail).

    `history` ends with the learner's line and the reply to it. Runs off the
    critical path; `log_path` is pinned by the caller so a profile switch mid-call
    can't misfile it.
    """
    from kaiwa.course import learner_log

    if len(history) < 2 or history[-1].get("role") != "assistant" or history[-2].get("role") != "user":
        return
    said = str(history[-2].get("content") or "").strip()
    reply = str(history[-1].get("content") or "").strip()
    prompt_line = next((str(m.get("content") or "") for m in reversed(history[:-2]) if m.get("role") == "assistant"), "")
    if not said:
        return
    course = context()
    pieces = course["pieces"]
    share, unknown = reply_coverage(reply, pieces) if pieces else (None, [])
    # Course words the learner produced themself: what Chat shows they can use.
    said_kana = _kana(said)
    used = sorted({w for w in course["words"] if len(w) > 1 and w in said_kana})
    tags = tag_mistakes(settings, prompt_line=prompt_line, said=said)
    learner_log.log(
        "chat", path=log_path, said=said, prompt=prompt_line, reply=reply,
        reply_known_share=None if share is None else round(share, 2), reply_unknown=unknown[:6],
        used_known=used, mistakes=tags, tagged=tags is not None,
    )
