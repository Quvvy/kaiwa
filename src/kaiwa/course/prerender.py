"""Render every lesson line to the disk TTS cache in the background.

Lesson text is fixed, so after one pass (a few minutes, once per voice) every
"play" in Learn is a file read instead of a synthesis.
"""

from __future__ import annotations

import logging
import threading

from kaiwa import tts
from kaiwa.config import Settings
from kaiwa.course.units import UNITS
from kaiwa.prefs import load_prefs

_log = logging.getLogger("kaiwa.course.prerender")

SLOW_SPEED = 0.75
_running = threading.Lock()


def speaker_for(settings: Settings, voice: str) -> tuple[int, str]:
    """(speaker id, engine) for lesson voice "a" (your chosen voice) or "b" (the other speaker)."""
    prefs = load_prefs()
    speaker = prefs.voicevox_speaker_id
    if voice == "b":
        speaker = tts.alternate_speaker(settings, engine=prefs.tts_engine, primary=speaker)
    return speaker, prefs.tts_engine


def lesson_lines() -> list[tuple[str, str, float | None]]:
    """(text, voice, speed) for everything Learn plays, in course order."""
    lines: list[tuple[str, str, float | None]] = []
    for unit in UNITS:
        for phrase in unit["phrases"]:
            lines.append((phrase["jp"], "a", None))
        for line in unit["dialogue"]["lines"]:
            lines.append((line["jp"], "b" if line.get("who") == "b" else "a", None))
        for task in unit["speak"]:
            lines.append((task["say"], "a", None))
        # Slow versions last: they are only played on request.
    for unit in UNITS:
        for phrase in unit["phrases"]:
            lines.append((phrase["jp"], "a", SLOW_SPEED))
    seen: set[tuple[str, str, float | None]] = set()
    return [x for x in lines if not (x in seen or seen.add(x))]


def run(settings: Settings) -> None:
    """Render missing lines. Safe to call repeatedly; only one pass runs at a time."""
    if not _running.acquire(blocking=False):
        return
    try:
        done = 0
        for text, voice, speed in lesson_lines():
            speaker, engine = speaker_for(settings, voice)
            if tts.is_cached(settings, text, speaker_id=speaker, engine=engine, speed=speed):
                continue
            try:
                tts.synthesize_cached(settings, text, speaker_id=speaker, engine=engine, speed=speed)
                done += 1
            except Exception as exc:
                _log.info("prerender stopped: %s", exc)
                return
        if done:
            _log.info("prerendered %d lesson lines", done)
    finally:
        _running.release()


def start(settings: Settings) -> None:
    threading.Thread(target=run, args=(settings,), name="kaiwa-tts-prerender", daemon=True).start()
