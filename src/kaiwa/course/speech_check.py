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
from difflib import SequenceMatcher
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


_VOWEL_OF: dict[str, str] = {}
for _vowel, _row in (
    ("あ", "あかがさざただなはばぱまやらわぁゃゎ"),
    ("い", "いきぎしじちぢにひびぴみりぃ"),
    ("う", "うくぐすずつづぬふぶぷむゆるぅゅ"),
    ("え", "えけげせぜてでねへべぺめれぇ"),
    ("お", "おこごそぞとどのほぼぽもよろをぉょ"),
):
    for _ch in _row:
        _VOWEL_OF[_ch] = _vowel


def vowel_of(ch: str) -> str:
    """The vowel a hiragana ends in (か → あ, しょ's ょ → お), or "" for ん, っ and the rest."""
    return _VOWEL_OF.get(ch, "")


def _long_vowels(text: str) -> str:
    """ー as the vowel it stretches: こーひー → こおひい, びーる → びいる.

    It used to be dropped, which made ビール (beer) and ビル (building) the same
    answer. Spelled out, a long vowel is one more sound, like がっこう's う.
    """
    out: list[str] = []
    for ch in text:
        if ch == "ー":
            ch = vowel_of(out[-1]) if out else ""
        out.append(ch)
    return "".join(out)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").casefold()
    text = _PUNCT_RE.sub("", text)
    text = to_hiragana(text)
    return _long_vowels(text).strip()


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


def _written_parts(target: str) -> list[tuple[str, int]]:
    """The target as written, cut into pieces, each with how many compared sounds it holds."""
    parts: list[tuple[str, int]] = []
    for piece in re.split(r"(\d+時?)", target):
        if _NUM_RE.fullmatch(piece):
            parts.append((piece, len(normalize(piece))))
            continue
        for seg in _kks.convert(piece):
            orig = seg.get("orig", "")
            if orig == seg.get("hira") or orig == seg.get("kana"):
                parts.extend((ch, len(normalize(ch))) for ch in orig)  # kana: mark sound by sound
            elif orig:
                parts.append((orig, len(normalize(seg.get("hira") or orig))))  # kanji: all or nothing
    return parts


def spot_differences(target: str, heard: str) -> list[dict[str, object]]:
    """The target as written (コーヒー stays コーヒー), in runs, each marked heard or not.

    Showing exactly which sounds went missing tells the learner what to listen for
    next time, where a score only tells them it wasn't right.
    """
    t, h = normalize(target), normalize(heard)
    if not t:
        return []
    heard_at = [False] * len(t)
    for block in SequenceMatcher(None, t, h, autojunk=False).get_matching_blocks():
        for i in range(block.a, block.a + block.size):
            heard_at[i] = True
    parts = _written_parts(target)
    if sum(n for _, n in parts) != len(t):  # couldn't line them up: show the compared sounds
        parts = [(ch, 1) for ch in t]
    runs: list[dict[str, object]] = []
    at = 0
    for text, n in parts:
        # ー takes after the sound it lengthens; punctuation has no sound to miss.
        ok = all(heard_at[at:at + n]) if n else (bool(runs[-1]["ok"]) if runs and text == "ー" else True)
        at += n
        if runs and runs[-1]["ok"] == ok:
            runs[-1]["text"] = str(runs[-1]["text"]) + text
        else:
            runs.append({"text": text, "ok": ok})
    return runs
