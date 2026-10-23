"""Memory hooks for leeches: cards the learner keeps forgetting.

More of the same review doesn't fix a leech; a new way in does. Flash writes a
short hook (a sound-alike, a picture to imagine, or how the parts build the
meaning) plus a word-by-word breakdown. It's written once and kept on the card.
"""

from __future__ import annotations

from typing import Any

from kaiwa import llm
from kaiwa.config import Settings

SYSTEM = """\
You help an adult beginner (pre-N5) remember a Japanese item they keep forgetting.
Write ONE memory hook in plain English, at most 25 words: a sound-alike in English,
a vivid image to picture, or how the pieces build the meaning. Concrete beats clever.
For a single kana, the hook links its shape to its sound.
Also split the item into its parts with a short meaning or role for each
(skip this for a single kana: return []).

Return JSON only:
{"hook": "...", "parts": [{"jp": "...", "en": "..."}]}
"""


def write_hook(settings: Settings, item: dict[str, Any]) -> dict[str, Any] | None:
    if not settings.deepseek_api_key:
        return None
    what = "kana character" if item["kind"] == "kana" else item["kind"]
    user = (
        f"Item ({what}): {item['jp']}\n"
        f"{'Reading' if item['kind'] == 'kana' else 'Meaning'}: {item['en']}\n"
        + (f"Course note: {item['note']}\n" if item.get("note") else "")
    )
    data = llm.complete_json(settings, SYSTEM, user)
    if not data or not str(data.get("hook") or "").strip():
        return None
    parts = []
    for row in (data.get("parts") or [])[:8]:
        if isinstance(row, dict) and str(row.get("jp") or "").strip():
            parts.append({"jp": str(row["jp"]).strip(), "en": str(row.get("en") or "").strip()})
    return {"hook": str(data["hook"]).strip(), "parts": parts}
