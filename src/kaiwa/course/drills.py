"""Fluency drills: known material, faster.

Nation's four strands give a course four equal jobs: input, output, language study,
and fluency. Kaiwa had the first three. Numbers are the clearest case of the gap:
someone can "know" さんびゃく and still lose a price said at normal speed in a shop.
Items are generated and judged here, no LLM, so these work offline.
"""

from __future__ import annotations

import random
from typing import Any

from kaiwa.course.speech_check import _HOURS, _number_kana

ITEMS_PER_ROUND = 10


def price_item(level: int, rng: random.Random) -> dict[str, str]:
    if level <= 1:
        n = rng.randrange(1, 10) * 100
    elif level == 2:
        n = rng.randrange(1, 100) * 100
    else:
        n = rng.randrange(1, 1000) * 100
    return {"say": _number_kana(n) + "えん", "answer": str(n), "show": f"¥{n:,}"}


def time_item(level: int, rng: random.Random) -> dict[str, str]:
    hour = rng.randrange(1, 13)
    half = level >= 2 and rng.random() < 0.5
    spoken = _HOURS.get(hour, _number_kana(hour) + "じ") + ("はん" if half else "")
    return {"say": spoken + "です", "answer": f"{hour}:{'30' if half else '00'}", "show": f"{hour}:{'30' if half else '00'}"}


def round_items(kind: str, level: int = 1, *, seed: int | None = None) -> list[dict[str, str]]:
    """A round without repeats (as far as the level has enough different items)."""
    rng = random.Random(seed)
    make = {"price": price_item, "time": time_item}[kind]
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for _ in range(ITEMS_PER_ROUND * 8):
        item = make(level, rng)
        if item["answer"] not in seen or len(seen) >= (9 if kind == "price" and level == 1 else 12):
            seen.add(item["answer"])
            out.append(item)
        if len(out) == ITEMS_PER_ROUND:
            break
    return out


def available(unit_steps_done: dict[str, Any]) -> dict[str, bool]:
    """Which drills the learner has been taught enough for."""
    return {"time": bool(unit_steps_done.get("u8", {}).get("learn")), "price": bool(unit_steps_done.get("u11", {}).get("learn"))}
