"""Learn tab: clustered Chat lines, or canned starters if none are eligible."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from kaiwa.practice.cards import (
    SPEAKABLE_AGAIN,
    SPEAKABLE_ETTO,
    display_line,
    is_practice_worthy,
    is_recast_family_line,
    load_cards,
    practice_worthy_line,
)

LINES_CAP = 5
LEARN_PREFIX = "learn:"
_LETTER_RE = re.compile(r"[A-Za-z\u3040-\u30ff\u3400-\u9fff]")
SKIP_LINES = frozenset({SPEAKABLE_ETTO, SPEAKABLE_AGAIN})

STARTER_CARDS: list[dict[str, str]] = [
    {
        "id": "learn:suki",
        "learner_line": "",
        "tutor_reply": "コーヒーが好き？",
        "speakable": "コーヒーが好きです。",
    },
    {
        "id": "learn:iku",
        "learner_line": "",
        "tutor_reply": "学校、行く？",
        "speakable": "学校に行きます。",
    },
    {
        "id": "learn:wakaranai",
        "learner_line": "",
        "tutor_reply": "わからない時は、そう言っていいよ。",
        "speakable": "わかりません。",
    },
]


def is_learn_id(card_id: str | None) -> bool:
    return str(card_id or "").startswith(LEARN_PREFIX)


def starter_card_by_id(card_id: str | None) -> dict[str, Any] | None:
    cid = str(card_id or "")
    if not cid:
        return None
    for card in STARTER_CARDS:
        if card["id"] == cid:
            return dict(card)
    return None


def skip_learn_line(line: str | None) -> bool:
    raw = (line or "").strip()
    if not raw or raw in SKIP_LINES:
        return True
    if _LETTER_RE.search(raw) is None:
        return True
    return not practice_worthy_line(raw)


def resolve_card(
    card_id: str | None,
    *,
    cards_path: Path | None = None,
) -> dict[str, Any] | None:
    """Chat snapshot, else a Learn starter. Not 9.8 survival fallbacks."""
    cid = str(card_id or "")
    if not cid:
        return None
    for card in load_cards(cards_path):
        if str(card.get("id") or "") == cid:
            return card
    return starter_card_by_id(cid)


def _public_line(card: dict[str, Any], speakable: str) -> dict[str, str]:
    return {"speakable": speakable, "card_id": str(card.get("id") or "")}


def cluster_chat_lines(
    cards: list[dict[str, Any]] | None = None,
    *,
    path: Path | None = None,
) -> list[dict[str, str]]:
    """Recurring speakable first. Cap LINES_CAP. No tags."""
    rows = cards if cards is not None else load_cards(path)
    groups: dict[str, dict[str, Any]] = {}
    for card in rows:
        line = display_line(card)
        if skip_learn_line(line) or not is_practice_worthy(card):
            continue
        ts = str(card.get("ts") or "")
        stored = bool(str(card.get("speakable") or "").strip())
        prev = groups.get(line)
        if prev is None:
            groups[line] = {
                "count": 1,
                "card": card,
                "ts": ts,
                "stored": stored,
            }
            continue
        prev["count"] = int(prev["count"]) + 1
        take = False
        if ts > str(prev["ts"]):
            take = True
        elif ts == str(prev["ts"]):
            if stored and not prev["stored"]:
                take = True
            elif stored == prev["stored"]:
                take = True
        if take:
            prev["card"] = card
            prev["ts"] = ts
            prev["stored"] = stored
    ranked = sorted(
        groups.items(),
        key=lambda item: (
            is_recast_family_line(item[0]),
            int(item[1]["count"]),
            str(item[1]["ts"]),
        ),
        reverse=True,
    )
    out: list[dict[str, str]] = []
    for line, group in ranked:
        card = group["card"]
        if not isinstance(card, dict):
            continue
        out.append(_public_line(card, line))
        if len(out) >= LINES_CAP:
            break
    return out


def today_payload(*, cards_path: Path | None = None) -> dict[str, Any]:
    clustered = cluster_chat_lines(path=cards_path)
    if clustered:
        return {"source": "chat", "lines": clustered}
    return {
        "source": "starter",
        "lines": [
            _public_line(card, str(card.get("speakable") or ""))
            for card in STARTER_CARDS
        ],
    }
