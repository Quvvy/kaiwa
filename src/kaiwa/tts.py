from __future__ import annotations

import hashlib
import os
import socket
import threading
import time
from collections import OrderedDict
from urllib.parse import urlparse
from typing import Any, Literal

import httpx

from kaiwa.config import Settings

TtsEngine = Literal["aivisspeech", "voicevox"]
VALID_ENGINES = {"aivisspeech", "voicevox"}

ENGINE_LABELS = {
    "aivisspeech": "AivisSpeech",
    "voicevox": "VOICEVOX",
}


class TtsError(RuntimeError):
    pass


# Back-compat alias
VoicevoxError = TtsError


def normalize_engine(engine: str | None, default: str = "aivisspeech") -> TtsEngine:
    value = (engine or default).strip().lower()
    if value not in VALID_ENGINES:
        return "aivisspeech"  # type: ignore[return-value]
    return value  # type: ignore[return-value]


def engine_base_url(settings: Settings, engine: str) -> str:
    eng = normalize_engine(engine, settings.tts_engine)
    if eng == "voicevox":
        return settings.voicevox_base_url
    return settings.aivisspeech_base_url


# The desktop app opens its window before the voice engine finishes loading
# (AivisSpeech takes 15-25 s). It sets KAIWA_TTS_BOOTING=1 for this process when
# it launched the engine itself; until the deadline, a missing engine means
# "still starting", and voice calls wait for it instead of failing.
BOOT_GRACE_S = 90.0
_boot_deadline = time.monotonic() + BOOT_GRACE_S if os.environ.get("KAIWA_TTS_BOOTING") == "1" else 0.0


def _port_open(base: str) -> bool:
    """Socket probe: a closed port on Windows takes ~2 s to refuse over HTTP."""
    parsed = urlparse(base)
    try:
        with socket.create_connection((parsed.hostname or "127.0.0.1", parsed.port or 80), timeout=0.15):
            return True
    except OSError:
        return False


_seen_up: set[str] = set()


def _engine_up(settings: Settings, eng: str) -> bool:
    base = engine_base_url(settings, eng)
    if not _port_open(base):
        return False
    if eng in _seen_up:
        return True  # busy synthesizing can make /version slow; the port is enough now
    try:
        ok = httpx.get(f"{base}/version", timeout=1.0).status_code < 500
    except httpx.HTTPError:
        return False
    if ok:
        _seen_up.add(eng)
    return ok


def engine_state(settings: Settings, engine: str | None = None) -> str:
    """"ready", "starting" (desktop app is still launching it) or "down"."""
    global _boot_deadline
    eng = normalize_engine(engine, settings.tts_engine)
    if _engine_up(settings, eng):
        _boot_deadline = 0.0  # seen up once: later failures are real failures
        return "ready"
    return "starting" if time.monotonic() < _boot_deadline else "down"


def wait_while_starting(settings: Settings, engine: str | None = None) -> None:
    """Block (up to the boot deadline) while the engine is still starting."""
    while engine_state(settings, engine) == "starting":
        time.sleep(0.3)


def engine_default_speaker(settings: Settings, engine: str) -> int:
    eng = normalize_engine(engine, settings.tts_engine)
    if eng == "voicevox":
        return settings.voicevox_speaker_id
    return settings.aivisspeech_speaker_id


def engine_hint(engine: str) -> str:
    """User-facing next step when the voice engine isn't answering."""
    other = "AivisSpeech" if normalize_engine(engine) == "voicevox" else "VOICEVOX"
    return f"Restart Kaiwa to start it again, or switch to {other} in Settings → Speech."


def synthesize(
    settings: Settings,
    text: str,
    *,
    speaker_id: int | None = None,
    engine: str | None = None,
    speed: float | None = None,
) -> bytes:
    """Return WAV bytes from the selected local TTS engine (VOICEVOX-compatible API).

    `speed` scales speaking rate (1.0 normal; ~0.75 for a slow learner replay).
    """
    from kaiwa.text_clean import clean_reply_for_speech

    text = clean_reply_for_speech(text)
    if not text.strip():
        raise TtsError("Nothing left to synthesize after cleaning stage directions")

    eng = normalize_engine(engine, settings.tts_engine)
    speaker = engine_default_speaker(settings, eng) if speaker_id is None else speaker_id
    base = engine_base_url(settings, eng)
    label = ENGINE_LABELS[eng]
    if _boot_deadline:
        wait_while_starting(settings, eng)
    if not _port_open(base):
        raise TtsError(f"The {label} voice engine isn't running. {engine_hint(eng)}")

    with httpx.Client(timeout=60.0) as client:
        try:
            query = client.post(
                f"{base}/audio_query",
                params={"text": text, "speaker": speaker},
            )
        except httpx.HTTPError as exc:
            raise TtsError(
                f"The {label} voice engine isn't running. {engine_hint(eng)}"
            ) from exc
        if query.status_code >= 400:
            raise TtsError(
                f"The {label} voice engine couldn't read this text (error {query.status_code}). "
                f"{engine_hint(eng)}"
            )
        audio_query = query.json()
        if speed and isinstance(audio_query, dict):
            audio_query["speedScale"] = float(speed)
        try:
            audio = client.post(
                f"{base}/synthesis",
                params={"speaker": speaker},
                json=audio_query,
                headers={"Content-Type": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise TtsError(
                f"The {label} voice engine stopped responding. {engine_hint(eng)}"
            ) from exc
        if audio.status_code >= 400:
            raise TtsError(
                f"The {label} voice engine couldn't make audio (error {audio.status_code}). "
                f"{engine_hint(eng)}"
            )
        return audio.content


def list_speakers(settings: Settings, *, engine: str | None = None) -> list[dict]:
    eng = normalize_engine(engine, settings.tts_engine)
    base = engine_base_url(settings, eng)
    label = ENGINE_LABELS[eng]
    if _boot_deadline:
        wait_while_starting(settings, eng)
    if not _port_open(base):
        raise TtsError(f"The {label} voice engine isn't running. {engine_hint(eng)}")
    with httpx.Client(timeout=15.0) as client:
        try:
            resp = client.get(f"{base}/speakers")
        except httpx.HTTPError as exc:
            raise TtsError(f"The {label} voice engine isn't running. {engine_hint(eng)}") from exc
        if resp.status_code >= 400:
            raise TtsError(
                f"The {label} voice engine couldn't list its voices (error {resp.status_code}). {engine_hint(eng)}"
            )
        return resp.json()


def flatten_speaker_styles(speakers: list[dict]) -> list[dict[str, Any]]:
    """VOICEVOX-compatible /speakers → flat list of {id, name, style, label}."""
    out: list[dict[str, Any]] = []
    for character in speakers:
        name = str(character.get("name") or "Unknown")
        for style in character.get("styles") or []:
            style_id = style.get("id")
            if style_id is None:
                continue
            style_name = str(style.get("name") or "Normal")
            out.append(
                {
                    "id": int(style_id),
                    "name": name,
                    "style": style_name,
                    "label": f"{name} — {style_name}",
                }
            )
    out.sort(key=lambda row: (row["name"].lower(), row["id"]))
    return out


def resolve_speaker_id(
    settings: Settings,
    *,
    engine: str,
    preferred_id: int,
) -> int:
    """Prefer preferred_id if present for this engine; else engine default."""
    try:
        voices = flatten_speaker_styles(list_speakers(settings, engine=engine))
    except Exception:
        return preferred_id
    ids = {int(v["id"]) for v in voices}
    if preferred_id in ids:
        return preferred_id
    default = engine_default_speaker(settings, engine)
    if default in ids:
        return default
    return int(voices[0]["id"]) if voices else preferred_id


_CACHE_MAX = 300
_cache: OrderedDict[tuple, bytes] = OrderedDict()
_cache_lock = threading.Lock()
_alt_speaker: dict[tuple[str, int], int] = {}


def _disk_path(key: tuple):
    from kaiwa.secrets_store import user_data_dir

    engine, speaker_id, text, speed = key
    folder = f"{engine}_{speaker_id}_{speed or 1}"
    name = hashlib.sha1(text.encode("utf-8")).hexdigest()[:20] + ".wav"
    return user_data_dir() / "tts_cache" / folder / name


def is_cached(settings: Settings, text: str, *, speaker_id: int | None, engine: str | None, speed: float | None = None) -> bool:
    key = (normalize_engine(engine, settings.tts_engine), speaker_id, text, speed)
    with _cache_lock:
        if key in _cache:
            return True
    return _disk_path(key).is_file()


def synthesize_cached(
    settings: Settings,
    text: str,
    *,
    speaker_id: int | None = None,
    engine: str | None = None,
    speed: float | None = None,
) -> bytes:
    """synthesize() behind an in-memory LRU and a disk cache.

    Lesson lines never change, so once rendered they are read from disk instead
    of costing ~0.8 s of synthesis each time the app starts.
    """
    key = (normalize_engine(engine, settings.tts_engine), speaker_id, text, speed)
    with _cache_lock:
        hit = _cache.get(key)
        if hit is not None:
            _cache.move_to_end(key)
            return hit
    path = _disk_path(key)
    try:
        wav = path.read_bytes()
    except OSError:
        wav = synthesize(settings, text, speaker_id=speaker_id, engine=engine, speed=speed)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(wav)
            tmp.replace(path)
        except OSError:
            pass
    with _cache_lock:
        _cache[key] = wav
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
    return wav


def alternate_speaker(settings: Settings, *, engine: str, primary: int) -> int:
    """A second voice for dialogues: another character if possible, else another style."""
    eng = normalize_engine(engine, settings.tts_engine)
    key = (eng, primary)
    if key in _alt_speaker:
        return _alt_speaker[key]
    try:
        voices = flatten_speaker_styles(list_speakers(settings, engine=eng))
    except Exception:
        return primary
    primary_name = next((v["name"] for v in voices if v["id"] == primary), None)
    other = next((v for v in voices if v["name"] != primary_name), None)
    other = other or next((v for v in voices if v["id"] != primary), None)
    _alt_speaker[key] = int(other["id"]) if other else primary
    return _alt_speaker[key]
