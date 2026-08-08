"""Practice mode: intelligibility scoring (shadowing warm-up)."""

from kaiwa.practice.scoring import ScoreResult, score_intelligibility
from kaiwa.practice.phrases import PHRASES, next_phrase, phrase_by_id

__all__ = [
    "ScoreResult",
    "score_intelligibility",
    "PHRASES",
    "next_phrase",
    "phrase_by_id",
]
