"""Voice checks: first-run downloads, the move off まお, the Settings list, dialogue casting.

No engine or network needed. Usage: .venv\\Scripts\\python scripts\\smoke_voices.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["KAIWA_DATA_DIR"] = tempfile.mkdtemp(prefix="kaiwa-voices-smoke-")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="kaiwa-voices-appdata-")


def _check(ok: bool, label: str) -> None:
    print(("ok  " if ok else "FAIL") + "  " + label)
    if not ok:
        raise SystemExit(1)


# A fake engine: the speakers AivisSpeech would list.
SPEAKERS = [
    {"name": "まお", "styles": [{"name": "ノーマル", "id": 888753760}]},
    {"name": "コハク", "styles": [{"name": "ノーマル", "id": 1878365376}]},
    {"name": "凛音エル", "styles": [{"name": "ノーマル", "id": 1388823424}]},
    {"name": "ほのか(~現実20代女子AIボイチェン~リアボVC公式モデル)", "styles": [{"name": "ノーマル", "id": 808373280}]},
    {"name": "阿井田 茂", "styles": [{"name": "ノーマル", "id": 1310138976}, {"name": "Mid", "id": 1310138980}]},
    {"name": "らせつん", "styles": [{"name": "標準", "id": 893625024}]},
]


def download_checks() -> None:
    from kaiwa import bootstrap, voices

    _check(set(voices.missing()) == set(voices.MODELS), "a fresh PC is missing every shipped voice")
    got: list[str] = []
    fail = {"6d11c6c2-f4a4-4435-887e-23dd60f8b8dd"}

    def fake_download(url, dest, **kw):  # noqa: ANN001
        uuid = dest.stem
        if uuid in fail:
            raise RuntimeError("network down")
        got.append(kw["label"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"aivmx")

    real = bootstrap._http_download
    bootstrap._http_download = fake_download
    rows: list[dict] = []
    try:
        left = bootstrap.ensure_voices(on_progress=rows.append)
        _check(left == ["にせ"] and len(got) == 3, "voices download into the engine's model folder; a failure doesn't stop the rest")
        _check(all("Downloading voices (" in g for g in got) and rows[-1]["missing"] == ["にせ"], "progress names each voice")
        fail.clear()
        got.clear()
        _check(bootstrap.ensure_voices() == [] and len(got) == 1, "the next launch fetches only what's still missing")
    finally:
        bootstrap._http_download = real
    _check((voices.models_dir() / "f5017410-fbb5-49e1-97cb-e785f42e15f5.aivmx").is_file(),
           "files land as <uuid>.aivmx under %APPDATA%\\AivisSpeech-Engine\\Models")


def default_checks() -> None:
    from kaiwa import bootstrap, prefs, tts, voices
    from kaiwa.config import get_settings

    settings = get_settings()
    _check(prefs.UserPrefs().voicevox_speaker_id == voices.DEFAULT_SPEAKER, "new learners start on 凛音エル")
    real = tts.list_speakers
    p = prefs.load_prefs()
    p.voicevox_speaker_id = voices.OLD_DEFAULT_SPEAKER
    p.tts_engine = "aivisspeech"
    prefs.save_prefs(p)
    try:
        tts.list_speakers = lambda s, engine=None: [x for x in SPEAKERS if x["name"] != "凛音エル"]
        _check(not voices.adopt_new_default(settings) and prefs.load_prefs().voicevox_speaker_id == voices.OLD_DEFAULT_SPEAKER,
               "no switch until 凛音エル is installed")
        tts.list_speakers = lambda s, engine=None: SPEAKERS
        _check(voices.adopt_new_default(settings) and prefs.load_prefs().voicevox_speaker_id == voices.DEFAULT_SPEAKER,
               "someone on the old まお default moves to 凛音エル")
        p = prefs.load_prefs()
        p.voicevox_speaker_id = voices.OLD_DEFAULT_SPEAKER
        prefs.save_prefs(p)
        _check(not voices.adopt_new_default(settings) and prefs.load_prefs().voicevox_speaker_id == voices.OLD_DEFAULT_SPEAKER,
               "picking まお again afterwards sticks (the switch runs once)")
        bootstrap._save_state({"voice_default_v2": False})
        p.voicevox_speaker_id = 893625024
        prefs.save_prefs(p)
        voices.adopt_new_default(settings)
        _check(prefs.load_prefs().voicevox_speaker_id == 893625024, "a voice the learner chose is never changed")
    finally:
        tts.list_speakers = real


def list_and_cast_checks() -> None:
    from fastapi.testclient import TestClient

    from kaiwa import app as app_mod, prefs, tts

    real = tts.list_speakers
    tts.list_speakers = lambda s, engine=None: SPEAKERS
    tts._alt_speaker.clear()
    try:
        p = prefs.load_prefs()
        p.voicevox_speaker_id = 1388823424
        prefs.save_prefs(p)
        data = TestClient(app_mod.app).get("/api/voices").json()
        names = [v["label"] for v in data["voices"]]
        _check(names[0] == "凛音エル — ノーマル" and data["voices"][0]["recommended"], "Kaiwa's voices come first, default on top")
        _check("ほのか — ノーマル" in names, "ほのか gets a short name")
        _check(not any(n.startswith(("まお", "コハク")) for n in names), "the engine's high built-in voices are hidden")
        others = [v["name"] for v in data["voices"] if not v["recommended"]]
        _check("らせつん" in others and all(not v["recommended"] for v in data["voices"][4:]), "other installed voices follow")
        p.voicevox_speaker_id = 888753760
        prefs.save_prefs(p)
        names = [v["label"] for v in TestClient(app_mod.app).get("/api/voices").json()["voices"]]
        _check(any(n.startswith("まお") for n in names), "…unless it's the voice currently selected")

        settings = app_mod.settings
        b = tts.dialogue_speaker(settings, engine="aivisspeech", primary=1388823424, slot=1)
        c = tts.dialogue_speaker(settings, engine="aivisspeech", primary=1388823424, slot=2)
        _check(b == 1310138980 and c == 808373280, "dialogues pair 凛音エル with 阿井田 茂, then ほのか")
        tts._alt_speaker.clear()
        far = tts.dialogue_speaker(settings, engine="aivisspeech", primary=1388823424, slot=4)
        _check(far not in (888753760, 1878365376), "the high voices are never cast, even when the cast runs out")
    finally:
        tts.list_speakers = real
        tts._alt_speaker.clear()


def main() -> None:
    download_checks()
    default_checks()
    list_and_cast_checks()
    print("smoke_voices: all ok")


if __name__ == "__main__":
    main()
