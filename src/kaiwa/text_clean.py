from __future__ import annotations

import re
import unicodedata

# Parenthetical stage directions / acting cues (ASCII + fullwidth).
_PAREN_EMOTE_RE = re.compile(
    r"[\(（]"
    r"[^\)）]{0,80}"
    r"[\)）]"
)
_STAR_EMOTE_RE = re.compile(r"\*[^*\n]{1,60}\*")
_BRACKET_EMOTE_RE = re.compile(r"\[[^\]\n]{1,60}\]")

# Keep short JP particles / known non-emote parens if needed later; for now strip
# any parenthetical that looks like acting (has letters, no digits-only).
_EMOTE_HINT_RE = re.compile(
    r"(smile|laugh|clap|nod|sigh|grin|wink|wave|blush|tear|cry|giggle|"
    r"chuckle|pat|hug|bow|shrug|eyeroll|facepalm|smiles|laughs|claps|"
    r"笑顔|微笑|拍手|うなず|ため息|にこ|ウィンク|涙|泣|笑|抱き|おじぎ|"
    r"くすくす|はは|ふふ|にやり|そわそわ|どきどき)",
    re.IGNORECASE,
)


def _looks_like_emote(inner: str) -> bool:
    text = inner.strip()
    if not text or len(text) > 60:
        return False
    if _EMOTE_HINT_RE.search(text):
        return True
    # Bare stage-direction style: mostly letters/spaces, no sentence particles
    letters = sum(1 for ch in text if ch.isalpha() or "\u3040" <= ch <= "\u30ff")
    if letters < 2:
        return False
    # Don't strip normal JP explanations in parens that look like glosses with は/を/の
    if any(ch in text for ch in "。！？!?、"):
        return False
    # Short English/JP acting words without particles → treat as emote
    if " " in text or text.isascii():
        return True
    # Single JP acting word (笑顔, etc.) already covered; leftover short tokens
    return len(text) <= 8 and not any(ch in text for ch in "はをにがでともへ")


def strip_stage_directions(text: str) -> str:
    """Remove awkward TTS stage directions like (smiles) or *claps*."""
    if not text:
        return text

    def repl_paren(match: re.Match[str]) -> str:
        inner = match.group(0)[1:-1]
        return "" if _looks_like_emote(inner) else match.group(0)

    cleaned = _PAREN_EMOTE_RE.sub(repl_paren, text)
    cleaned = _STAR_EMOTE_RE.sub("", cleaned)

    def repl_bracket(match: re.Match[str]) -> str:
        inner = match.group(0)[1:-1]
        return "" if _looks_like_emote(inner) else match.group(0)

    cleaned = _BRACKET_EMOTE_RE.sub(repl_bracket, cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" *\n+ *", "\n", cleaned)
    return cleaned.strip()


def clean_reply_for_speech(text: str) -> str:
    """Normalize reply text before display + TTS."""
    text = unicodedata.normalize("NFKC", text or "")
    return strip_stage_directions(text)


_TRY_LINE_RE = re.compile(r"^TRY\s*[:：]\s*(.+)$", re.IGNORECASE)


def split_try_phrase(text: str) -> tuple[str, str | None]:
    """Split optional trailing `TRY: …` line from spoken reply.

    Returns (spoken_reply, better_phrase_or_None).
    """
    raw = (text or "").rstrip()
    if not raw:
        return "", None
    lines = raw.split("\n")
    better: str | None = None
    m = _TRY_LINE_RE.match(lines[-1].strip())
    if m:
        phrase = m.group(1).strip()
        if phrase:
            better = phrase[:120]
        lines = lines[:-1]
        while lines and not lines[-1].strip():
            lines.pop()
    spoken = "\n".join(lines).strip()
    return spoken, better
