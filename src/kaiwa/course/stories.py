"""Extra listening: a fresh short dialogue built from what the learner already knows.

Comprehension grows with lots of input the learner can almost fully follow.
The units only hold one dialogue each, so this generates more at exactly the
learner's level: learned phrases and words recombined, at most two new words
(glossed). Words still being learned are recycled first, so listening doubles as
review. While one story plays, the next is written and voiced in the background,
so "another" is instant.
"""

from __future__ import annotations

import logging
import random
import re
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from kaiwa import llm, tts
from kaiwa.config import Settings
from kaiwa.course.state import learned_phrase_ids, listening_context, load_state, phrase, state_path

_log = logging.getLogger("kaiwa.course.stories")

STORY_SYSTEM = """\
You write tiny listening exercises for an adult absolute beginner learning Japanese (pre-N5).

Write the requested format so the learner can follow almost completely. Rules:
- dialogue: a natural, everyday conversation between two people (A and B), 4 to 6 lines.
- story: one person (always A) tells a tiny first-person story or describes their day,
  4 to 6 lines. It needs a small turn: a problem, a surprise, a change of plan.
- Each line at most 2 short sentences.
- Grammar: use ONLY sentence patterns that appear in the learner's known phrases. No new verb
  forms (no 〜ましょう, 〜たい, 〜て, plain forms) unless a known phrase already uses them.
  If the learner only knows greetings, the conversation is greetings, thanks, apologies and
  reactions — that is fine and still useful.
- Vocabulary: known phrases and known words only, plus at most 2 new NOUNS that slot into a
  known pattern (e.g. known ねこがすきです → new いぬがすきです). Gloss each new noun where it
  first appears. Question words (どこ, なに, いつ…) count as new unless known.
- Work in as many of the "still learning" words as fit naturally: hearing them in context is
  how they stick.
- Polite です/ます style. Write Japanese in kana only (hiragana + katakana), no kanji.
- "en" is an exact translation of that line: keep negatives negative (わかりません = don't
  understand) and add nothing that isn't in the Japanese. Each person uses phrases the way
  Japanese speakers really do (いってらっしゃい only to someone leaving).
- Make it a tiny situation with a point (a plan, a preference, a small surprise), not a list.
  Don't reuse any of the recent scenes you are given.
- Then 2 comprehension questions in English with 3 short English choices each; exactly one
  correct, answerable only by understanding the Japanese.

Return JSON only:
{
  "scene": "one short English sentence setting the scene",
  "lines": [{"who": "a" | "b", "jp": "kana", "en": "natural English", "gloss": "new word = meaning, or empty"}],
  "questions": [{"q": "...", "choices": ["...", "...", "..."], "answer": 0}]
}
"""

SETTINGS = ["at school", "at a café", "on the weekend", "at home", "meeting a friend", "shopping", "after work",
            "on the train", "at a restaurant", "at the station", "on a rainy day", "at a friend's house",
            "in the morning", "at the park", "on the phone"]
# The model ignores "only known grammar" often enough (いきました, たべました…) that each
# draft is measured: the share of its kana made of known words, phrases, taught grammar
# examples and particles. Below the bar, it's sent back once with the unknown bits named.
# Research puts comfortable listening at ~95% known; particles inflate the measure a little.
COVERAGE_OK = 0.92
PARTICLES = ["ですか", "です", "さん", "じゃないです", "は", "が", "を", "に", "の", "も", "と", "で", "か", "ね", "よ"]
_STRIP = re.compile(r"[、。！？「」\s]")
_KATAKANA = re.compile(r"[゠-ヿ]+")

STORY_SHARE = 0.3   # how often it's a one-person story instead of a conversation
WORDS_SHOWN = 60    # per strength group, so the prompt stays small at any level
PATTERNS_SHOWN = 15
ANCHORS = 3
NAMES = ["アレックス", "ユキ", "ケン", "ハナ", "タロウ", "エミ", "サム", "リサ", "ダイキ", "マヤ"]


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


def coverage(lines: list[str], known: list[str]) -> tuple[float, list[str]]:
    """(share of kana that is known, the unknown leftovers). Katakana names count as known."""
    pieces = sorted({_STRIP.sub("", k) for k in known if k} | set(PARTICLES), key=len, reverse=True)
    total = left = 0
    unknown: list[str] = []
    for line in lines:
        rest = _KATAKANA.sub("", _STRIP.sub("", line))
        total += len(rest)
        for piece in pieces:
            if piece:
                rest = rest.replace(piece, "／")
        bits = [b for b in rest.split("／") if b]
        left += sum(len(b) for b in bits)
        unknown += bits
    return (1 - left / total if total else 0.0), unknown


def _word_list(words: list[dict[str, Any]]) -> str:
    sample = random.sample(words, min(len(words), WORDS_SHOWN))
    return ", ".join(f"{w['jp']} ({w['en']})" for w in sample) or "(none yet)"


def generate(settings: Settings, *, topic_hint: str = "", avoid: list[str] | None = None) -> dict[str, Any] | None:
    """A validated dialogue, or None when nothing is learned yet / the call failed."""
    state = load_state()
    ids = learned_phrase_ids(state)
    if not ids:
        return None
    known = [phrase(i) for i in ids]
    ctx = listening_context(state)
    lines = "\n".join(f"- {p['jp']} ({p['en']})" for p in known if p)
    form = "story" if random.random() < STORY_SHARE else "dialogue"
    recent = ctx["recent"] + list(avoid or [])
    # A few words to hang it on, mostly ones still being learned. Without anchors it
    # circles the newest phrases (every story came out about liking cats).
    pool = ctx["shaky"] or ctx["solid"]
    anchors = random.sample(pool, min(len(pool), ANCHORS))
    patterns = random.sample(ctx["patterns"], min(len(ctx["patterns"]), PATTERNS_SHOWN))
    user = (
        f"Format: {form}\n\n"
        f"Learner's known phrases:\n{lines}\n\n"
        f"Taught sentence patterns (examples): {' / '.join(patterns) or '(only the phrases)'}\n"
        f"Known words, still learning (recycle these): {_word_list(ctx['shaky'])}\n"
        f"Known words, solid: {_word_list(ctx['solid'])}\n\n"
        f"Setting idea: {topic_hint or random.choice(SETTINGS)}.\n"
        f"Build it around these words: {', '.join(w['jp'] for w in anchors) or 'anything known'}. "
        f"Use likes and dislikes (すき/きらい) only if these words call for it.\n"
        f"People: {' and '.join(random.sample(NAMES, 2))}.\n"
        f"Recent scenes (don't repeat): {'; '.join(recent[-12:]) or '(none)'}"
    )
    known_pieces = ([w["jp"] for w in ctx["shaky"] + ctx["solid"]] + [p["jp"] for p in known if p]
                    + ctx["patterns"])
    best: tuple[float, dict[str, Any]] | None = None
    prompt = user
    for _ in range(3):
        data = llm.complete_json(settings, STORY_SYSTEM, prompt)
        if not (data and _valid(data)):
            continue
        glossed = [str(l.get("gloss") or "").split("=")[0].strip() for l in data["lines"]]
        share, unknown = coverage([str(l["jp"]) for l in data["lines"]], known_pieces + glossed)
        if best is None or share > best[0]:
            best = (share, data)
        if share >= COVERAGE_OK:
            break
        # Send it back with what the learner can't know.
        prompt = (f"{user}\n\nYour last draft used words or verb forms the learner hasn't learned: "
                  f"{'、'.join(dict.fromkeys(unknown))}. Rewrite it using only the known material.")
    if best is None:
        return None
    share, data = best
    lines_out = [
        {
            "who": "a" if form == "story" else line["who"],
            "jp": str(line["jp"]).strip(),
            "en": str(line.get("en") or "").strip(),
            "gloss": str(line.get("gloss") or "").strip(),
        }
        for line in data["lines"]
    ]
    return {
        "scene": str(data.get("scene") or "").strip(),
        "form": form,
        "known_share": round(share, 3),
        "lines": lines_out,
        "questions": [_shuffled(q) for q in data["questions"][:3]],
    }


def _shuffled(q: dict[str, Any]) -> dict[str, Any]:
    """Models tend to put the right answer first; shuffle so position gives nothing away."""
    choices = [str(c) for c in q["choices"]]
    right = choices[int(q["answer"])]
    random.shuffle(choices)
    return {"q": str(q.get("q") or ""), "choices": choices, "answer": choices.index(right)}


# ---------- the next story, made while this one plays ----------

_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kaiwa-story")
_lock = threading.Lock()
_next: dict[str, Future] = {}  # profile state file → the story being prepared


def _prepare(settings: Settings, avoid: list[str]) -> dict[str, Any] | None:
    from kaiwa.course.prerender import speaker_for

    data = generate(settings, avoid=avoid)
    if data:
        # Voice it too, so the first play is a cache read.
        try:
            for line in data["lines"]:
                speaker, engine = speaker_for(settings, line["who"])
                tts.synthesize_cached(settings, line["jp"], speaker_id=speaker, engine=engine)
        except Exception as exc:
            _log.info("story prerender stopped: %s", exc)
    return data


def take(settings: Settings) -> dict[str, Any] | None:
    """The prepared story if there is one (else a fresh one), and start on the next."""
    key = str(state_path())
    with _lock:
        pending = _next.pop(key, None)
    data = None
    if pending is not None:
        try:
            data = pending.result(timeout=90)
        except Exception:
            data = None
    if data is None:
        data = generate(settings)
    if data is not None:
        with _lock:
            _next[key] = _pool.submit(_prepare, settings, [data["scene"]])
    return data
