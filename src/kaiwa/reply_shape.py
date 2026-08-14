"""Pre-N5 reply-shape checks (Phase 8.1). Surface heuristics, not a parser.

High-load constructions (ば-conditionals / たら / なら) are too heavy at this
pitch — not a forever grammar ban. Extra ideas (3+ sentences or a second-claim
connective) are the main density signal. Two short pieces can still be one
thought: こんにちは！元気？
"""

from __future__ import annotations

import re
from typing import Any

# Same boundaries as stream_util.SentenceBuffer.
_SENTENCE_END_RE = re.compile(r"[。！？!?\n]")
# 話せば / すれば / 行けば / 食べれば / なければ — not bare ば (こんばんは).
_HIGH_LOAD_BA_RE = re.compile(r"[れけせえべ]ば")
_TARA_RE = re.compile(r"たら")
_NARA_RE = re.compile(r"なら(?!ない)")
_OPEN_PIVOT_RE = re.compile(r"どうした|何をしました|予定")
_CONNECTIVE_RE = re.compile(r"(でも|だけど|それから|そして)")
_JP_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
# Function bigrams that would make "reuse" always true.
_STOP_BIGRAMS = {
    "です",
    "ます",
    "した",
    "ない",
    "から",
    "って",
    "んだ",
    "よね",
    "かな",
    "まし",
    "せん",
    "たい",
    "この",
    "その",
    "あの",
    "これ",
    "それ",
    "あれ",
    "さん",
    "して",
    "いる",
    "うん",
    "はい",
    "ええ",
    "けど",
}


def sentence_pieces(text: str) -> list[str]:
    buf = (text or "").strip()
    if not buf:
        return []
    pieces: list[str] = []
    while True:
        match = _SENTENCE_END_RE.search(buf)
        if not match:
            break
        piece = buf[: match.end()].strip()
        buf = buf[match.end() :]
        if piece:
            pieces.append(piece)
    rem = buf.strip()
    if rem:
        pieces.append(rem)
    return pieces


def sentence_count(text: str) -> int:
    return len(sentence_pieces(text))


def has_high_load(text: str) -> bool:
    """True if a high-load construction is present (log field: conditional)."""
    raw = text or ""
    if _HIGH_LOAD_BA_RE.search(raw):
        return True
    if _TARA_RE.search(raw):
        return True
    if _NARA_RE.search(raw):
        return True
    return False


def has_open_question(text: str) -> bool:
    return bool(_OPEN_PIVOT_RE.search(text or ""))


def has_extra_idea(text: str) -> bool:
    """Second idea: 3+ sentence pieces, or a contrast/addition connective."""
    if sentence_count(text) >= 3:
        return True
    return bool(_CONNECTIVE_RE.search(text or ""))


def reply_too_dense(text: str) -> bool:
    return has_extra_idea(text) or has_high_load(text) or has_open_question(text)


def _jp_bigrams(text: str) -> set[str]:
    chars = _JP_CHAR_RE.findall(text or "")
    grams = {"".join(chars[i : i + 2]) for i in range(len(chars) - 1)}
    return {g for g in grams if g not in _STOP_BIGRAMS}


def reused_user_vocab(user_text: str, reply: str) -> bool:
    user_grams = _jp_bigrams(user_text)
    if not user_grams:
        return False
    return bool(user_grams & _jp_bigrams(reply))


def analyze_reply_shape(
    *,
    reply: str,
    user_text: str,
    locked: bool,
    retry: bool,
) -> dict[str, Any]:
    """Silent JSONL metric — not shown in the Chat UI."""
    return {
        "locked": bool(locked),
        "sentence_count": sentence_count(reply),
        "conditional": has_high_load(reply),
        "open_question": has_open_question(reply),
        "reused_user_vocab": reused_user_vocab(user_text, reply),
        "retry": bool(retry),
        "extra_idea": has_extra_idea(reply),
    }
