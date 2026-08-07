from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from pykakasi import kakasi

_kks = kakasi()
_PUNCT_RE = re.compile(r"[^\w\u3040-\u30ff\u3400-\u9fff]+", re.UNICODE)


@dataclass(frozen=True)
class ScoreResult:
    score: int
    band: str
    target_norm: str
    heard_norm: str
    score_kind: str = "intelligibility"


def _to_hiragana(text: str) -> str:
    parts = _kks.convert(text)
    return "".join(p.get("hira") or p.get("orig", "") for p in parts)


def normalize_for_compare(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.casefold()
    text = _PUNCT_RE.sub("", text)
    text = _to_hiragana(text)
    text = text.replace("ー", "")
    return text.strip()


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def score_intelligibility(target: str, heard: str) -> ScoreResult:
    target_norm = normalize_for_compare(target)
    heard_norm = normalize_for_compare(heard)
    denom = max(len(target_norm), len(heard_norm), 1)
    dist = _levenshtein(target_norm, heard_norm)
    score = int(round(100 * (1 - dist / denom)))
    score = max(0, min(100, score))
    if score >= 85:
        band = "clear"
    elif score >= 60:
        band = "close"
    else:
        band = "unclear"
    return ScoreResult(
        score=score,
        band=band,
        target_norm=target_norm,
        heard_norm=heard_norm,
    )
