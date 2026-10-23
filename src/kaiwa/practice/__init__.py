"""Practice: Chat struggle sittings (Phase 9) plus leftover intelligibility helpers."""

from kaiwa.practice.scoring import ScoreResult, score_intelligibility
from kaiwa.practice.phrases import PHRASES, next_phrase, phrase_by_id
from kaiwa.practice.cards import maybe_write_card, newest_unused, snapshot_signal

__all__ = [
    "ScoreResult",
    "score_intelligibility",
    "PHRASES",
    "next_phrase",
    "phrase_by_id",
    "maybe_write_card",
    "newest_unused",
    "snapshot_signal",
]
