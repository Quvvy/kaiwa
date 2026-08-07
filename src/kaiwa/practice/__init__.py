"""Practice mode: intelligibility scoring (not pitch-accent grading)."""

from kaiwa.practice.scoring import ScoreResult, score_intelligibility
from kaiwa.practice.phrases import PHRASES, next_phrase, phrase_by_id

__all__ = [
    "ScoreResult",
    "score_intelligibility",
    "PHRASES",
    "next_phrase",
    "phrase_by_id",
]
