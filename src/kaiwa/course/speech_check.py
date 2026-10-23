"""Did the learner say it? Kana-normalized comparison of Whisper text vs a target.

Whisper writes kanji (私は猫が好きです); course targets are kana. Both sides go
through pykakasi to hiragana, lose punctuation and long-vowel marks, then get
an edit-distance score. This measures "a Japanese ear heard roughly this", not
pronunciation quality.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from pykakasi import kakasi

_kks = kakasi()
_PUNCT_RE = re.compile(r"[^\w぀-ヿ㐀-鿿]+", re.UNICODE)

GOOD = 90
CLOSE = 60

_DIGITS = ["", "いち", "に", "さん", "よん", "ご", "ろく", "なな", "はち", "きゅう"]
_HUNDREDS = {1: "ひゃく", 3: "さんびゃく", 6: "ろっぴゃく", 8: "はっぴゃく"}
_THOUSANDS = {1: "せん", 3: "さんぜん", 8: "はっせん"}
_HOURS = {4: "よじ", 7: "しちじ", 9: "くじ"}
_NUM_RE = re.compile(r"(\d+)(時)?")


def _number_kana(n: int) -> str:
    """Kana reading for 0–99999 (Whisper writes times and prices as digits)."""
    if n == 0:
        return "ぜろ"
    out = ""
    man, n = divmod(n, 10000)
    if man:
        out += _number_kana(man) + "まん"
    th, n = divmod(n, 1000)
    if th:
        out += _THOUSANDS.get(th, _DIGITS[th] + "せん")
    hu, n = divmod(n, 100)
    if hu:
        out += _HUNDREDS.get(hu, _DIGITS[hu] + "ひゃく")
    te, n = divmod(n, 10)
    if te:
        out += ("" if te == 1 else _DIGITS[te]) + "じゅう"
    return out + _DIGITS[n]


def _digits_to_kana(text: str) -> str:
    def sub(m: re.Match[str]) -> str:
        n = int(m.group(1))
        if m.group(2):
            return _HOURS.get(n, _number_kana(n) + "じ")
        return _number_kana(n)

    return _NUM_RE.sub(sub, text)


@lru_cache(maxsize=2048)
def to_hiragana(text: str) -> str:
    text = _digits_to_kana(text or "")
    return "".join(p.get("hira") or p.get("orig", "") for p in _kks.convert(text))


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").casefold()
    text = _PUNCT_RE.sub("", text)
    text = to_hiragana(text)
    return text.replace("ー", "").strip()


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a or not b:
        return len(a) or len(b)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def similarity(target: str, heard: str) -> int:
    t, h = normalize(target), normalize(heard)
    if not t and not h:
        return 0
    return max(0, round(100 * (1 - _levenshtein(t, h) / max(len(t), len(h), 1))))


def pattern_matches(pattern: str, heard: str) -> bool:
    """`*` = any run of sounds (or none). Pieces are kana-normalized, in order."""
    heard_n = normalize(heard)
    if not heard_n:
        return False
    body = ".*".join(re.escape(normalize(piece)) for piece in pattern.split("*"))
    return re.search(body, heard_n) is not None


@dataclass(frozen=True)
class Check:
    score: int
    band: str  # good | close | off
    heard: str
    heard_kana: str


def check_phrase(target: str, heard: str, accept: list[str] | None = None) -> Check:
    """Score a say-it-back attempt against a phrase (plus accepted variants)."""
    best = similarity(target, heard)
    for alt in accept or []:
        if "*" in alt:
            if pattern_matches(alt, heard):
                best = max(best, GOOD)
        else:
            best = max(best, similarity(alt, heard))
    band = "good" if best >= GOOD else "close" if best >= CLOSE else "off"
    return Check(score=best, band=band, heard=heard, heard_kana=normalize(heard))


def matches_any(patterns: list[str], heard: str) -> bool:
    for pat in patterns:
        if "*" in pat:
            if pattern_matches(pat, heard):
                return True
        elif similarity(pat, heard) >= GOOD:
            return True
    return False
