"""Placement test: find where in the course a learner really is, by testing, not asking.

Three adaptive skills, each estimated on the course scale (0 = below unit 1,
N = units 1..N are within reach), plus a short kana check:

  words      hear a course word, type its meaning (meaning recall: Laufer &
             Goldstein's productive measure, no guessing from options)
  sentences  hear a dialogue line, type what it means (judged by Flash)
  imitate    hear a sentence or two, say it back (elicited imitation: past the
             span you can parrot as raw sound, you can only repeat what you
             parse; items grow from ~9 kana at unit 1 to ~20 at unit 20, as in
             Ortega's 7-19 syllable EI sets, and only a near-exact repeat counts)

Each adaptive skill is a small computerised adaptive test with a Rasch-style
model: an item from unit u is "at" difficulty u, the chance of getting it right
at level L is logistic(SLOPE·(L − u + 0.5)) with a small slip and guess rate,
partial scores count partially, and a posterior over levels 0..20 is updated
after every answer (Bayesian EAP). The next item comes from the unit nearest
the current estimate; a skill stops when the estimate's spread is under
STOP_SD units or after MAX_ITEMS. Course order is the difficulty calibration.
"""

from __future__ import annotations

import math
import random
import re
from typing import Any

from kaiwa import llm
from kaiwa.config import Settings
from kaiwa.course.kana import KANA_LESSONS
from kaiwa.course.units import UNITS

LEVELS = list(range(0, len(UNITS) + 1))
SLOPE = 1.4
SLIP = 0.05      # knows it but misses (typo, misheard)
GUESS = 0.02     # doesn't know it but gets it (recall tasks are hard to guess)
STOP_SD = 1.0
MIN_ITEMS = 4
MAX_ITEMS = 8
SKILLS = ("words", "sentences", "imitate")

# Graduated hints (dynamic assessment): each "don't know" or miss makes the same
# item easier, and an answer after hint N earns HINT_CREDIT[N] of its score
# (partial-credit scoring). Words/sentences: 0 normal, 1 slowed audio, 2 kana
# shown, 3 first letter of the meaning (words only). Imitation: 0, 1 slowed,
# 2 text shown. Hints 0-1 are still "by ear"; from 2 on it's reading.
HINT_CREDIT = (1.0, 0.75, 0.5, 0.25)
HINTS = {"words": 3, "sentences": 2, "imitate": 2}
EAR_HINTS = 1  # the highest hint that still counts as understanding by ear

# Kana groups: lessons are skipped when the learner gets ≥ PASS of a group's sample.
KANA_GROUPS = [
    ("hiragana", [l["id"] for l in KANA_LESSONS if l["script"] == "hiragana" and int(l["id"][1:]) <= 9], 6),
    ("hiragana+", [l["id"] for l in KANA_LESSONS if l["script"] == "hiragana" and int(l["id"][1:]) >= 10], 4),
    ("katakana", [l["id"] for l in KANA_LESSONS if l["script"] == "katakana"], 6),
]
KANA_PASS = 0.85


# ---------- item banks ----------
def imitate_length(unit: int) -> int:
    """Target length (kana) of a unit's imitation item: beyond rote span, more with level."""
    return round(8 + 0.6 * unit)


def _kana_len(text: str) -> int:
    return len(re.sub(r"[、。！？!?「」\s…ー]", "", text))


def _imitate_items(u: int, unit: dict[str, Any]) -> list[dict[str, Any]]:
    """Sentences from the unit, joined in order until each item is long enough."""
    pool = [p for p in unit["phrases"] if "「" not in p["jp"]]
    pool += [line for line in unit["dialogue"]["lines"] if "「" not in line["jp"] and _kana_len(line["jp"]) >= 4]
    want, out = imitate_length(u), []
    for i in range(len(pool)):
        parts = [pool[i]]
        j = i + 1
        while sum(_kana_len(p["jp"]) for p in parts) < want and len(parts) < 3:
            parts.append(pool[j % len(pool)])
            j += 1
        jp = "".join(p["jp"] if p["jp"][-1] in "。？！?!" else p["jp"] + "。" for p in parts)
        out.append({"skill": "imitate", "unit": u, "id": f"{unit['id']}.ei{i}", "jp": jp,
                    "en": " ".join(p["en"] for p in parts)})
    return out


def _bank() -> dict[str, list[dict[str, Any]]]:
    words, sentences, imitate = [], [], []
    for u, unit in enumerate(UNITS, start=1):
        for w in unit.get("words", []):
            words.append({"skill": "words", "unit": u, "id": w["id"], "jp": w["jp"], "en": w["en"]})
        for i, line in enumerate(unit["dialogue"]["lines"]):
            jp = line["jp"]
            if 6 <= len(jp) <= 40:
                sentences.append({"skill": "sentences", "unit": u, "id": f"{unit['id']}.d{i}", "jp": jp, "en": line["en"],
                                  "who": line.get("who", "a")})
        imitate += _imitate_items(u, unit)
    return {"words": words, "sentences": sentences, "imitate": imitate}


BANK = _bank()


def kana_items(rng: random.Random | None = None) -> list[dict[str, Any]]:
    """A fixed-size sample per kana group: see the character, type its romaji."""
    rng = rng or random.Random()
    out = []
    by_id = {l["id"]: l for l in KANA_LESSONS}
    for group, lesson_ids, n in KANA_GROUPS:
        pool = [(ch, ro) for lid in lesson_ids for ch, ro in by_id[lid]["kana"]]
        for ch, ro in rng.sample(pool, min(n, len(pool))):
            out.append({"skill": "kana", "group": group, "char": ch, "ro": ro})
    return out


# ---------- the adaptive estimator ----------
def _p_correct(level: int, unit: int) -> float:
    core = 1.0 / (1.0 + math.exp(-SLOPE * (level - unit + 0.5)))
    return GUESS + (1 - GUESS - SLIP) * core


def posterior(history: list[dict[str, Any]]) -> list[float]:
    """Posterior over levels 0..20 after the answers so far (prior leans gently low)."""
    weights = [math.exp(-0.06 * lv) for lv in LEVELS]  # a beginner app: mild prior toward the start
    for h in history:
        s = max(0.0, min(1.0, float(h["score"])))
        for i, lv in enumerate(LEVELS):
            p = _p_correct(lv, int(h["unit"]))
            weights[i] *= (p ** s) * ((1 - p) ** (1 - s))
    total = sum(weights) or 1.0
    return [w / total for w in weights]


def estimate(history: list[dict[str, Any]]) -> dict[str, float]:
    post = posterior(history)
    mean = sum(lv * p for lv, p in zip(LEVELS, post))
    sd = math.sqrt(sum(((lv - mean) ** 2) * p for lv, p in zip(LEVELS, post)))
    cum, lo, hi = 0.0, LEVELS[0], LEVELS[-1]
    for lv, p in zip(LEVELS, post):
        if cum < 0.1 <= cum + p:
            lo = lv
        if cum < 0.9 <= cum + p:
            hi = lv
        cum += p
    return {"level": round(mean, 2), "sd": round(sd, 2), "low": lo, "high": hi}


def next_item(skill: str, history: list[dict[str, Any]], rng: random.Random | None = None) -> dict[str, Any] | None:
    """The most informative next item for this skill, or None when the skill is pinned down."""
    if skill not in SKILLS:
        raise ValueError(f"unknown skill: {skill}")
    rng = rng or random.Random()
    est = estimate(history)
    asked = {h["id"] for h in history}
    if len(history) >= MAX_ITEMS or (len(history) >= MIN_ITEMS and est["sd"] < STOP_SD):
        return None
    # Below unit 1 after a few misses: nothing more to learn about this skill.
    if len(history) >= MIN_ITEMS and est["high"] <= 0:
        return None
    # Items are most informative where P(correct) ≈ 0.5: one unit above the estimate's floor.
    target = min(len(UNITS), max(1, round(est["level"] + 0.5)))
    pool = [it for it in BANK[skill] if it["id"] not in asked]
    if not pool:
        return None
    best_gap = min(abs(it["unit"] - target) for it in pool)
    near = [it for it in pool if abs(it["unit"] - target) == best_gap]
    return rng.choice(near)


# ---------- judging typed meanings ----------
_STOP = {"a", "an", "the", "to", "is", "are", "it", "i", "you", "of", "it's", "im", "i'm", "be", "do", "and", "or", "in"}


def _content(text: str) -> set[str]:
    words = re.findall(r"[a-z']+", text.lower())
    return {w.rstrip("s") for w in words if w not in _STOP}


def judge_word_locally(expected: str, answer: str) -> float | None:
    """1.0 / 0.0 when the answer clearly matches or clearly misses an English meaning; None when unsure."""
    ans = _content(answer)
    if not ans:
        return 0.0
    options = [o for o in re.split(r"[,;/()]| or ", expected.lower()) if o.strip()]
    for opt in options:
        want = _content(opt)
        if want and (want <= ans or ans <= want):
            return 1.0
    return None


JUDGE_SYSTEM = """\
You mark a Japanese listening test. The learner heard a Japanese word or sentence
and typed what they think it means in English. Compare their answer with the
reference meaning. Spelling mistakes, synonyms, casual wording and missing
politeness are fine; what matters is whether they understood the meaning.

Return JSON only: {"score": 1 | 0.5 | 0}
1 = the meaning is understood. 0.5 = the main idea is there but a key part is wrong
or missing. 0 = wrong, empty, or just a guess at a single word in a sentence.
"""


def judge_meaning(settings: Settings, *, jp: str, expected: str, answer: str, kind: str) -> float:
    if not answer.strip():
        return 0.0
    if kind == "words":
        local = judge_word_locally(expected, answer)
        if local is not None:
            return local
    if not settings.deepseek_api_key:
        local = judge_word_locally(expected, answer)
        return local if local is not None else 0.0
    data = llm.complete_json(settings, JUDGE_SYSTEM, f"Japanese: {jp}\nReference meaning: {expected}\nLearner's answer: {answer}")
    try:
        score = float((data or {}).get("score", 0))
    except (TypeError, ValueError):
        score = 0.0
    return 1.0 if score >= 0.75 else 0.5 if score >= 0.25 else 0.0


# ---------- result ----------
def imitation_credit(similarity: int, kana_band: str | None) -> float:
    """Exact-repetition scoring: near-verbatim 1, most of it 0.5, else 0.

    Whisper turns a similar-sounding attempt into the sentence it expects, so a
    kana-model verdict that the audio sounded different caps the credit at 0.5.
    """
    credit = 1.0 if similarity >= 92 else 0.5 if similarity >= 80 else 0.0
    if kana_band in ("close", "heard"):
        credit = min(credit, 0.5)
    return credit


def kana_result(answers: list[dict[str, Any]]) -> dict[str, Any]:
    """Which kana groups are passed (their lessons can be skipped)."""
    out = {}
    for group, lesson_ids, _ in KANA_GROUPS:
        part = [a for a in answers if a.get("group") == group]
        share = sum(1 for a in part if a.get("correct")) / len(part) if part else 0.0
        out[group] = {"passed": bool(part) and share >= KANA_PASS, "right": sum(1 for a in part if a.get("correct")),
                      "of": len(part), "lessons": lesson_ids}
    return out


def channel_scores(entry: dict[str, Any]) -> tuple[float, float]:
    """(by ear, in kana) for one answered item from its judged score and the hint it took.

    Understood by ear (normal or slowed) also counts as understood in kana; the
    first-letter hint earns half in kana; nothing by ear after the kana is shown.
    """
    judged = float(entry.get("judged", entry.get("score", 0)) or 0)
    hint = int(entry.get("hint", 0) or 0)
    ear = judged if hint <= EAR_HINTS else 0.0
    read = judged if hint <= 2 else judged * 0.5
    return ear, read


def summarize(histories: dict[str, list[dict[str, Any]]], kana: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-skill estimates (combined, by ear, in kana) and the recommended start.

    The adaptive test steers on the combined (partial-credit) score; the start
    is the lower by-ear comprehension estimate, since listening is the goal.
    """
    est = {skill: estimate(histories.get(skill, [])) for skill in SKILLS if histories.get(skill)}
    channels: dict[str, dict[str, Any]] = {}
    reading_only: list[str] = []
    for skill in ("words", "sentences"):
        rows = histories.get(skill) or []
        if not rows:
            continue
        ear = [{"unit": h["unit"], "score": channel_scores(h)[0]} for h in rows]
        read = [{"unit": h["unit"], "score": channel_scores(h)[1]} for h in rows]
        channels[skill] = {"ear": estimate(ear), "read": estimate(read)}
        if skill == "words":
            reading_only += [h["id"] for h in rows if channel_scores(h)[1] >= 0.5 and channel_scores(h)[0] == 0]
    ear_levels = [channels[s]["ear"]["level"] for s in ("words", "sentences") if s in channels]
    known_units = int(math.floor(min(ear_levels))) if ear_levels else 0
    known_units = max(0, min(len(UNITS), known_units))
    read_levels = [channels[s]["read"]["level"] for s in ("words", "sentences") if s in channels]
    gap = round(min(read_levels) - min(ear_levels), 1) if ear_levels and read_levels else 0.0
    return {
        "skills": est,
        "channels": channels,
        "listening_gap": gap,
        "reading_only": reading_only,
        "known_units": known_units,
        "start_unit": min(len(UNITS), known_units + 1),
        "kana": kana_result(kana),
    }


def jlpt_level(units: float) -> str:
    """Rough map from the course scale to the profile's levels (units 1-8 ≈ pre-N5, 9-20 ≈ N5)."""
    return "pre_n5" if units < 8 else "n5" if units < 20 else "n4"
