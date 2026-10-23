"""Review words inside short sentences instead of as isolated cards.

At the start of a review, due word cards are bundled into a few short spoken
sentences built only from what the learner knows. The learner hears one and
picks its meaning; the answer grades every word card the sentence covers.
If generation fails or a sentence doesn't check out, the plain word cards stay.

The model drifts into untaught words (さむい, いそがしい…), so every sentence is
checked mechanically: strip the known words, phrases and basic particles, and
anything left that isn't a katakana name means it's rejected.
"""

from __future__ import annotations

import random
import re
from typing import Any

from kaiwa import llm
from kaiwa.config import Settings

SYSTEM = """\
You write listening practice for an adult beginner (pre-N5) learning Japanese.
Write up to 4 very short sentences that together use as many of the target words as
possible. Each sentence uses one target word, or two only when they genuinely belong
together. Natural beats coverage: skip a target rather than force it.

Use ONLY the known words, the known phrases, katakana names (ユキ, アレックス) and these
grammar bits: です, ですか, は, の, も, ね, よ, か, さん. No other words at all, not even
common ones. Kana only, no kanji, no romaji. At most 16 kana.

Every sentence must be something a person would really say: a greeting with a name or
title, a short reply, a self-introduction.
Bad (unnatural): あさとひるです。 いまはあしたですか。 わたしはひとです。
Good: せんせい、おはようございます。 ユキさんはともだちです。 あしたもがっこうですか。

For each sentence give its English meaning and two wrong meanings that a learner who
misheard or forgot the target word might pick (same shape, different key word).

Return JSON only:
{"items": [{"targets": ["target word exactly as given"], "jp": "...", "en": "...", "wrong": ["...", "..."]}]}
"""

GRAMMAR = ["ですか", "です", "さん", "は", "の", "も", "ね", "よ", "か"]
_KANA_ONLY = re.compile(r"^[ぁ-ゟ゠-ヿ、。！？ー\s]+$")
_PUNCT = re.compile(r"[、。！？\s]")
_KATAKANA = re.compile(r"[゠-ヿ]+")


def only_known(jp: str, vocab: list[str]) -> bool:
    """True if `jp` is made of known pieces (longest first), particles and katakana names."""
    rest = _KATAKANA.sub("", _PUNCT.sub("", jp))
    pieces = sorted({_PUNCT.sub("", v) for v in vocab if v} | set(GRAMMAR), key=len, reverse=True)
    for piece in pieces:
        if piece:
            rest = rest.replace(piece, "")
    return rest == ""


def contains_word(jp: str, word: str, vocab: list[str]) -> bool:
    """`word` appears on its own, not just inside a longer known item (いま in ございます)."""
    rest = jp
    for longer in sorted({v for v in vocab if word in v and v != word}, key=len, reverse=True):
        rest = rest.replace(longer, "／")
    return word in rest


def generate(
    settings: Settings,
    *,
    targets: list[dict[str, str]],
    known_words: list[str],
    known_phrases: list[str],
) -> list[dict[str, Any]]:
    """[{jp, en, choices, answer, card_ids, words}] for as many targets as could be covered."""
    if not settings.deepseek_api_key or len(targets) < 2:
        return []
    listed = ", ".join(f"{t['jp']} ({t['en']})" for t in targets[:8])
    user = (
        f"Target words: {listed}\n"
        f"Known words: {', '.join(known_words[:80])}\n"
        f"Known phrases: {' / '.join(known_phrases[:30])}"
    )
    data = llm.complete_json(settings, SYSTEM, user)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    # Phrases count piece by piece too (じゃあ、また → じゃあ, また).
    vocab = list(known_words) + [part for p in known_phrases for part in [p, *re.split(r"[、。]", p)]]
    by_jp = {t["jp"]: t for t in targets}
    out: list[dict[str, Any]] = []
    used: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        jp = str(item.get("jp") or "").strip()
        en = str(item.get("en") or "").strip()
        wrong = [str(w).strip() for w in (item.get("wrong") or []) if str(w).strip()][:2]
        hits = [by_jp[w] for w in item.get("targets") or []
                if w in by_jp and w not in used and contains_word(jp, w, vocab)]
        if not (jp and en and len(wrong) == 2 and hits and _KANA_ONLY.match(jp) and len(jp) <= 24):
            continue
        if len({en, *wrong}) < 3 or not only_known(jp, vocab):
            continue
        used.update(t["jp"] for t in hits)
        choices = [en, *wrong]
        random.shuffle(choices)
        out.append({
            "jp": jp,
            "en": en,
            "choices": choices,
            "answer": choices.index(en),
            "card_ids": [t["card_id"] for t in hits],
            "words": [{"jp": t["jp"], "en": t["en"]} for t in hits],
        })
    return out
