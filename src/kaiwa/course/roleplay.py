"""Talk practice: a few spoken turns with a partner in a small scene, at the learner's level.

Speaking grows by using what's known in a real exchange, with one correction at a
time and a partner who keeps the conversation going (output and feedback in
interaction). Each scene has a small goal, the partner speaks only known material
(measured like extra listening), and after each turn the learner gets one fix and a
natural version of what they meant, then the partner answers. A suggested reply is
always one click away, since a pre-N5 learner often can't produce a line unaided.

The server keeps nothing: the client sends the scene and the turns so far each time.
"""

from __future__ import annotations

import random
from typing import Any

from kaiwa import llm
from kaiwa.config import Settings
from kaiwa.course.state import learned_phrase_ids, listening_context, load_state, phrase
from kaiwa.course.stories import NAMES, SETTINGS, coverage

TURNS = 4            # learner turns before the scene wraps up
REPLY_OK = 0.85      # partner lines below this share of known kana are rewritten once
VERDICTS = ("great", "ok", "retry")

KNOWN_RULES = """\
The partner speaks ONLY with the learner's known phrases, known words, taught sentence
patterns, particles and katakana names, plus at most one new noun per line (glossed).
No new verb forms. Polite です/ます style, kana only (no kanji), at most 2 short sentences.
Suggested learner replies follow the same rules, with no new words at all, and use the
learner's own details as their known phrases give them (their name, where they're from).
"""

START_SYSTEM = """\
You set up a tiny spoken role-play for an adult absolute beginner learning Japanese (pre-N5).
The learner plays themself. You choose who the partner is and what the learner wants to do.
The goal must be reachable in 3 or 4 short replies using what the learner knows
(greet, introduce themself, ask or answer about likes, a place, a person, a thing…).

""" + KNOWN_RULES + """
Return JSON only:
{
  "scene": "one short English sentence: where they are and who the partner is",
  "goal": "what the learner should do, in plain English, e.g. 'Greet Ken and find out what food he likes.'",
  "partner": "partner's name in katakana",
  "opener": "the partner's first line in Japanese (kana)",
  "opener_en": "its exact English translation",
  "suggest": "a short reply the learner could give, in kana, using only known material"
}
"""

TURN_SYSTEM = """\
You are both the conversation partner and a warm, precise speaking coach in a tiny role-play
with an adult absolute beginner learning Japanese (pre-N5). The learner's line came through
speech recognition: ignore odd kanji and small transcription noise and judge what a Japanese
listener would have heard.

1. Judge the learner's last line:
   - great: fits and is understood with no effort.
   - ok: understandable and on-topic, with one real mistake worth fixing.
   - retry: not understandable, not Japanese, or doesn't fit at all.
   If they answered in English, verdict is retry.
2. "said_en": what the learner's line means in plain, literal English.
3. "model": a natural version of what they were trying to say (kana, polite), keeping their
   content (their name, food, place…). Same as theirs if it was already natural.
4. "tip": ONE short concrete English tip about the most useful fix; empty if great.
5. "reply": the partner's next line, reacting to what the learner meant (also when it was
   "ok"). If the verdict is retry, the partner politely asks again in simple Japanese
   (e.g. すみません、もういちど、おねがいします。) instead of moving on.
   When the goal is reached or this is the last turn, the partner closes the conversation
   naturally (e.g. じゃあ、また。) and "done" is true.
6. "suggest": a short reply the learner could give next, in kana, using only known
   material. Empty when done.

""" + KNOWN_RULES + """
Return JSON only:
{"verdict": "great"|"ok"|"retry", "said_en": "...", "model": "...", "tip": "...",
 "reply": "...", "reply_en": "exact English translation of reply", "done": false, "suggest": "..."}
"""


def _known(state: dict[str, Any]) -> tuple[str, list[str]]:
    """The learner's known material as a prompt block, and as pieces for the coverage check."""
    ctx = listening_context(state)
    phrases = [phrase(i) for i in learned_phrase_ids(state)]
    words = ctx["shaky"] + ctx["solid"]
    patterns = random.sample(ctx["patterns"], min(len(ctx["patterns"]), 15))
    block = (
        "Learner's known phrases:\n" + "\n".join(f"- {p['jp']} ({p['en']})" for p in phrases if p) + "\n"
        f"Taught sentence patterns (examples): {' / '.join(patterns) or '(only the phrases)'}\n"
        f"Known words: {', '.join(w['jp'] + ' (' + w['en'] + ')' for w in words) or '(none yet)'}"
    )
    pieces = [w["jp"] for w in words] + [p["jp"] for p in phrases if p] + ctx["patterns"]
    return block, pieces


def _s(data: dict[str, Any], key: str) -> str:
    return str(data.get(key) or "").strip()


def start(settings: Settings) -> dict[str, Any] | None:
    """A new scene, or None when nothing is learned yet / the call failed."""
    state = load_state()
    if not learned_phrase_ids(state):
        return None
    block, pieces = _known(state)
    ctx = listening_context(state)
    pool = ctx["shaky"] or ctx["solid"]
    anchors = random.sample(pool, min(len(pool), 2))
    user = (f"{block}\n\nSetting idea: {random.choice(SETTINGS)}. Partner's name idea: {random.choice(NAMES)}.\n"
            f"Try to involve: {', '.join(w['jp'] for w in anchors) or 'anything known'}.")
    best: tuple[float, dict[str, Any]] | None = None
    for _ in range(2):
        data = llm.complete_json(settings, START_SYSTEM, user)
        if not data or not all(_s(data, k) for k in ("scene", "goal", "opener")):
            continue
        share, _unknown = coverage([_s(data, "opener"), _s(data, "suggest")], pieces)
        if best is None or share > best[0]:
            best = (share, data)
        if share >= REPLY_OK:
            break
    if best is None:
        return None
    data = best[1]
    return {
        "scene": _s(data, "scene"), "goal": _s(data, "goal"), "partner": _s(data, "partner") or "ユキ",
        "opener": _s(data, "opener"), "opener_en": _s(data, "opener_en"), "suggest": _s(data, "suggest"),
        "turns": TURNS,
    }


def turn(settings: Settings, *, scene: dict[str, Any], history: list[dict[str, str]], heard: str) -> dict[str, Any] | None:
    """Judge the learner's line and get the partner's answer. None when the call failed."""
    state = load_state()
    block, pieces = _known(state)
    learner_turns = sum(1 for h in history if h.get("who") == "me") + 1
    lines = "\n".join(f"{'Learner' if h.get('who') == 'me' else 'Partner'}: {h.get('jp', '')}" for h in history)
    user = (
        f"{block}\n\nScene: {scene.get('scene', '')}\nLearner's goal: {scene.get('goal', '')}\n"
        f"Partner: {scene.get('partner', '')}\n\nConversation so far:\n{lines}\n"
        f"Learner (speech recognition): {heard}\n\n"
        f"This is learner turn {learner_turns} of {TURNS}."
        + (" It is the last turn: close the conversation." if learner_turns >= TURNS else "")
    )
    best: tuple[float, dict[str, Any]] | None = None
    prompt = user
    for _ in range(2):
        data = llm.complete_json(settings, TURN_SYSTEM, prompt)
        if not data or str(data.get("verdict")) not in VERDICTS or not _s(data, "reply"):
            continue
        share, unknown = coverage([_s(data, "reply"), _s(data, "suggest")], pieces)
        if best is None or share > best[0]:
            best = (share, data)
        if share >= REPLY_OK:
            break
        prompt = (f"{user}\n\nYour reply or suggestion used words or forms the learner hasn't learned:"
                  f"{'、'.join(dict.fromkeys(unknown))}. Answer again using only known material.")
    if best is None:
        return None
    data = best[1]
    done = bool(data.get("done")) or (learner_turns >= TURNS and data["verdict"] != "retry")
    return {
        "verdict": str(data["verdict"]), "heard": heard,
        "said_en": _s(data, "said_en").strip("\"'“”"), "model": _s(data, "model"), "tip": _s(data, "tip"),
        "reply": _s(data, "reply"), "reply_en": _s(data, "reply_en"),
        "done": done, "suggest": "" if done else _s(data, "suggest"),
    }
