"""Render every lesson line to the disk TTS cache in the background.

Lesson text is fixed, so after one pass (a few minutes, once per voice) every
"play" in Learn is a file read instead of a synthesis.
"""

from __future__ import annotations

import logging
import threading

from kaiwa import tts
from kaiwa.config import Settings
from kaiwa.course.kana import KANA_LESSONS
from kaiwa.course.units import UNITS
from kaiwa.prefs import load_prefs

_log = logging.getLogger("kaiwa.course.prerender")

SLOW_SPEED = 0.75
_running = threading.Lock()


VOICE_SLOTS = "abcd"


def speaker_for(settings: Settings, voice: str) -> tuple[int, str]:
    """(speaker id, engine) for a dialogue voice: "a" is your chosen voice, "b"–"d" the others."""
    prefs = load_prefs()
    speaker = prefs.voicevox_speaker_id
    slot = VOICE_SLOTS.find(voice)
    if slot > 0:
        speaker = tts.dialogue_speaker(settings, engine=prefs.tts_engine, primary=speaker, slot=slot)
    return speaker, prefs.tts_engine


def lesson_lines(*, everything: bool = False) -> list[tuple[str, str, float | None]]:
    """(text, voice, speed) Learn will play soon, in course order.

    Everything up to one lesson past where the learner is: what's learned (it
    comes back in reviews), the current unit and kana lesson, and the next of
    each. Finishing a step moves the window on. `everything` lists the whole course.
    """
    from kaiwa.course import state as course_state

    unit_limit, kana_limit = len(UNITS), len(KANA_LESSONS)
    if not everything:
        st = course_state.load_state()
        nxt = course_state.next_unit(st)
        unit_limit = (UNITS.index(nxt) + 2) if nxt else len(UNITS)
        nk = course_state.next_kana_lesson(st)
        kana_limit = (KANA_LESSONS.index(nk) + 2) if nk else len(KANA_LESSONS)
    units = UNITS[:unit_limit]
    lines: list[tuple[str, str, float | None]] = []
    for lesson in KANA_LESSONS[:kana_limit]:
        for ch, _ in lesson["kana"]:
            lines.append((ch, "a", None))
        for word in lesson["words"]:
            lines.append((word["jp"], "a", None))
    for unit in units:
        for phrase in unit["phrases"]:
            lines.append((phrase["jp"], "a", None))
        for word in unit.get("words", []):
            lines.append((word["jp"], "a", None))
        for point in unit.get("grammar", []):
            for ex in point["examples"]:
                lines.append((ex["jp"], "a", None))
        for line in unit["dialogue"]["lines"]:
            who = line.get("who")
            lines.append((line["jp"], who if who in VOICE_SLOTS else "a", None))
        for task in unit["speak"]:
            lines.append((task["say"], "a", None))
        # Slow versions last: they are only played on request.
    for unit in units:
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
