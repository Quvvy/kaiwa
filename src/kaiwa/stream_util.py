"""Helpers for streaming Chat replies (sentence boundaries)."""

from __future__ import annotations

import re

# Sentence / line boundaries for TTS chunking (JP + EN).
_SENTENCE_END_RE = re.compile(r"[。！？!?\n]")


class SentenceBuffer:
    """Accumulate streamed text and emit complete sentences."""

    def __init__(self) -> None:
        self._buf = ""

    def push(self, text: str) -> list[str]:
        if not text:
            return []
        self._buf += text
        out: list[str] = []
        while True:
            match = _SENTENCE_END_RE.search(self._buf)
            if not match:
                break
            end = match.end()
            piece = self._buf[:end].strip()
            self._buf = self._buf[end:]
            if piece:
                out.append(piece)
        return out

    def flush(self) -> str | None:
        piece = self._buf.strip()
        self._buf = ""
        return piece or None
