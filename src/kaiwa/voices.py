"""The AivisSpeech voices Kaiwa ships with: clear to a beginner and not high-pitched.

AivisSpeech comes with one voice, まお, which is high (median pitch ~430 Hz) and
grating over a long session. Kaiwa downloads these from AivisHub on first run instead
(bootstrap.ensure_voices), into the engine's own model folder.

Chosen by measuring every candidate on the same course words and sentences:
median pitch, and the kana error rate of the acoustic kana model (no dictionary to
fill in a lost sound, so it tracks how clearly a voice articulates).

    voice        pitch   kana error   first sound right
    にせ         182 Hz   0.33         84%
    凛音エル     282 Hz   0.35         84%   default
    阿井田 茂    162 Hz   0.36         90%   male, dialogues
    ほのか       239 Hz   0.46         66%   lowest female
    まお         430 Hz   0.52         60%   AivisSpeech's built-in voice
    (花音, まい, みちのくあいり, 天深シノ, わかな, らせつん, 桜音, コハク:
     294-432 Hz, 0.53-0.80; none clearer than まお)
"""

from __future__ import annotations

import os
from pathlib import Path

# AivisHub model UUID → voice name, in order of use.
MODELS: dict[str, str] = {
    "f5017410-fbb5-49e1-97cb-e785f42e15f5": "凛音エル",
    "47e53151-a378-46f3-abee-ce13aa07feb1": "阿井田 茂",
    "59f96896-64d2-4378-830a-4d5feb3d81aa": "ほのか",
    "6d11c6c2-f4a4-4435-887e-23dd60f8b8dd": "にせ",
}
DOWNLOAD_URL = "https://api.aivis-project.com/v1/aivm-models/{uuid}/download?model_type=AIVMX"

DEFAULT_SPEAKER = 1388823424      # 凛音エル / ノーマル
OLD_DEFAULT_SPEAKER = 888753760   # まお / ノーマル, the default before 2.0.1

# Style ids of the shipped voices, for the Settings voice list.
RECOMMENDED = {
    1388823424: "凛音エル",
    808373280: "ほのか",
    1310138976: "阿井田 茂",
    1937616896: "にせ",
}


# AivisSpeech's built-in voices, both ~430 Hz. The engine won't uninstall them, so
# Kaiwa keeps them out of its voice list and dialogues instead.
HIDDEN_NAMES = {"まお", "コハク"}


def models_dir() -> Path:
    """Where AivisSpeech Engine loads voice models from (%APPDATA%\\AivisSpeech-Engine\\Models)."""
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "AivisSpeech-Engine" / "Models"


def missing() -> dict[str, str]:
    """Shipped voices not in the engine's model folder yet."""
    folder = models_dir()
    return {uuid: name for uuid, name in MODELS.items() if not (folder / f"{uuid}.aivmx").is_file()}


def adopt_new_default(settings) -> bool:  # noqa: ANN001
    """Once: move a learner still on the old default (まお) to 凛音エル when it's installed.

    Someone who picked まお on purpose after this ran keeps it. Returns True when
    the voice changed (the caller re-renders lesson audio).
    """
    from kaiwa import bootstrap, tts
    from kaiwa.prefs import load_prefs, save_prefs

    if bootstrap._load_state().get("voice_default_v2"):
        return False
    prefs = load_prefs()
    if tts.normalize_engine(prefs.tts_engine, settings.tts_engine) != "aivisspeech":
        return False
    try:
        ids = {int(v["id"]) for v in tts.flatten_speaker_styles(tts.list_speakers(settings, engine="aivisspeech"))}
    except Exception:
        return False
    if DEFAULT_SPEAKER not in ids:
        return False  # not downloaded yet: try again next launch
    changed = prefs.voicevox_speaker_id == OLD_DEFAULT_SPEAKER
    if changed:
        prefs.voicevox_speaker_id = DEFAULT_SPEAKER
        save_prefs(prefs)
    bootstrap._save_state({"voice_default_v2": True})
    return changed
