from __future__ import annotations

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


def engine_default_speaker(settings: Settings, engine: str) -> int:
    eng = normalize_engine(engine, settings.tts_engine)
    if eng == "voicevox":
        return settings.voicevox_speaker_id
    return settings.aivisspeech_speaker_id


def engine_hint(engine: str) -> str:
    eng = normalize_engine(engine)
    if eng == "voicevox":
        return (
            "Start VOICEVOX (port 50021), or run: "
            ".\\.venv\\Scripts\\python.exe scripts\\start_voicevox.py"
        )
    return (
        "Start AivisSpeech (port 10101), or run: "
        ".\\.venv\\Scripts\\python.exe scripts\\start_aivisspeech.py — "
        "or switch TTS engine to VOICEVOX in Settings"
    )


def synthesize(
    settings: Settings,
    text: str,
    *,
    speaker_id: int | None = None,
    engine: str | None = None,
) -> bytes:
    """Return WAV bytes from the selected local TTS engine (VOICEVOX-compatible API)."""
    from kaiwa.text_clean import clean_reply_for_speech

    text = clean_reply_for_speech(text)
    if not text.strip():
        raise TtsError("Nothing left to synthesize after cleaning stage directions")

    eng = normalize_engine(engine, settings.tts_engine)
    speaker = engine_default_speaker(settings, eng) if speaker_id is None else speaker_id
    base = engine_base_url(settings, eng)
    label = ENGINE_LABELS[eng]

    with httpx.Client(timeout=60.0) as client:
        try:
            query = client.post(
                f"{base}/audio_query",
                params={"text": text, "speaker": speaker},
            )
        except httpx.HTTPError as exc:
            raise TtsError(
                f"{label} unreachable at {base}. {engine_hint(eng)}"
            ) from exc
        if query.status_code >= 400:
            raise TtsError(
                f"{label} audio_query failed ({query.status_code}). "
                f"{engine_hint(eng)}. {query.text}"
            )
        try:
            audio = client.post(
                f"{base}/synthesis",
                params={"speaker": speaker},
                json=query.json(),
                headers={"Content-Type": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise TtsError(
                f"{label} synthesis unreachable at {base}. {engine_hint(eng)}"
            ) from exc
        if audio.status_code >= 400:
            raise TtsError(
                f"{label} synthesis failed ({audio.status_code}). "
                f"{engine_hint(eng)}. {audio.text}"
            )
        return audio.content


def list_speakers(settings: Settings, *, engine: str | None = None) -> list[dict]:
    eng = normalize_engine(engine, settings.tts_engine)
    base = engine_base_url(settings, eng)
    label = ENGINE_LABELS[eng]
    with httpx.Client(timeout=15.0) as client:
        try:
            resp = client.get(f"{base}/speakers")
        except httpx.HTTPError as exc:
            raise TtsError(f"{label} unreachable at {base}. {engine_hint(eng)}") from exc
        if resp.status_code >= 400:
            raise TtsError(
                f"{label} /speakers failed ({resp.status_code}). {engine_hint(eng)}"
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
