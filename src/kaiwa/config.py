from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
# Project .env wins over any machine-wide DEEPSEEK_API_KEY.
load_dotenv(ROOT / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    deepseek_model_pro: str
    deepseek_thinking: str
    tts_engine: str
    voicevox_base_url: str
    voicevox_speaker_id: int
    aivisspeech_base_url: str
    aivisspeech_speaker_id: int
    whisper_model: str
    whisper_device: str
    whisper_compute_type: str
    host: str
    port: int
    sessions_dir: Path


def get_settings() -> Settings:
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is missing. Copy .env.example to .env and set your key.")

    tts_engine = os.getenv("TTS_ENGINE", "aivisspeech").strip().lower()
    if tts_engine not in {"aivisspeech", "voicevox"}:
        tts_engine = "aivisspeech"

    return Settings(
        deepseek_api_key=key,
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        deepseek_model_pro=os.getenv("DEEPSEEK_MODEL_PRO", "deepseek-v4-pro"),
        deepseek_thinking=os.getenv("DEEPSEEK_THINKING", "disabled").strip().lower(),
        tts_engine=tts_engine,
        voicevox_base_url=os.getenv("VOICEVOX_BASE_URL", "http://127.0.0.1:50021").rstrip("/"),
        voicevox_speaker_id=int(os.getenv("VOICEVOX_SPEAKER_ID", "3")),
        aivisspeech_base_url=os.getenv("AIVISSPEECH_BASE_URL", "http://127.0.0.1:10101").rstrip("/"),
        aivisspeech_speaker_id=int(os.getenv("AIVISSPEECH_SPEAKER_ID", "888753760")),
        whisper_model=os.getenv("WHISPER_MODEL", "large-v3-turbo"),
        whisper_device=os.getenv("WHISPER_DEVICE", "cuda"),
        whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "float16"),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8787")),
        sessions_dir=ROOT / "sessions",
    )
