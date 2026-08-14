"""After-chat leftovers (Phase 8.7 / decision #112).

Deterministic learner-line chunks from a hydrated thread. Optional Flash
“you could have said” is soft-fail and never written into live Chat.
"""

from __future__ import annotations

from typing import Any

from kaiwa.config import Settings
from kaiwa.learner_memory import _extract_json

CHUNK_MAX = 80
CHUNK_LIMIT = 5
ALT_LIMIT = 3

ALTERNATIVES_SYSTEM = """\
You suggest natural Japanese the learner could have said in a finished chat.
Reply with JSON only (no markdown):
{"alternatives": ["", ""]}
Rules:
- 1 to 3 short Japanese phrases (spoken, not textbook).
- Same meaning as the learner lines; slightly more natural is OK.
- No stars, scores, or rankings.
- Do not say wrong / incorrect / TRY: / 間違い.
- No English unless a proper noun needs it.
- Empty array if nothing useful.
"""


def leftover_chunks(
    messages: list[dict[str, str]],
    *,
    limit: int = CHUNK_LIMIT,
    clip: int = CHUNK_MAX,
) -> list[str]:
    """Unique recent user lines, chronological, capped."""
    cap = max(0, int(limit))
    width = max(1, int(clip))
    seen: set[str] = set()
    picked: list[str] = []
    for message in reversed(messages or []):
        if (message.get("role") or "") != "user":
            continue
        text = str(message.get("content") or "").strip()[:width]
        if not text or text in seen:
            continue
        seen.add(text)
        picked.append(text)
        if len(picked) >= cap:
            break
    picked.reverse()
    return picked


def parse_alternatives(raw_text: str, *, limit: int = ALT_LIMIT) -> list[str]:
    """Parse Flash JSON. Junk / TRY: / empty → []."""
    data = _extract_json(raw_text)
    if not data:
        return []
    items = data.get("alternatives")
    if not isinstance(items, list):
        return []
    out: list[str] = []
    cap = max(0, int(limit))
    for item in items:
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("phrase") or "").strip()
        else:
            text = str(item or "").strip()
        text = text.lstrip("*-• \t").strip()
        lower = text.lower()
        if not text or lower.startswith("try:") or "間違い" in text:
            continue
        out.append(text[:CHUNK_MAX])
        if len(out) >= cap:
            break
    return out


def last_assistant_line(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages or []):
        if (message.get("role") or "") != "assistant":
            continue
        text = str(message.get("content") or "").strip()
        if text:
            return text
    return ""


def suggest_alternatives(
    settings: Settings,
    chunks: list[str],
    *,
    last_assistant: str = "",
    client: Any = None,
) -> list[str]:
    """Flash 1–3 alternatives. Soft-fail → []. Never raises to the caller."""
    if not chunks or not (settings.deepseek_api_key or "").strip():
        return []
    from openai import OpenAI

    from kaiwa.llm import _completion

    lines = "\n".join(f"- {c}" for c in chunks)
    last = (last_assistant or "").strip()
    user = "Learner said:\n" + lines
    if last:
        user += "\nKaiwa's last line: " + last
    try:
        used = client or OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=12.0,
        )
        raw = _completion(
            settings,
            ALTERNATIVES_SYSTEM,
            [{"role": "user", "content": user}],
            client=used,
            model=settings.deepseek_model,
        )
        return parse_alternatives(raw)
    except Exception:
        return []
