from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from kaiwa.config import ROOT

CorrectionStyle = Literal["gentle", "critique"]
LanguagePolicy = Literal["immerse", "adaptive"]
SpeechRegister = Literal["formal", "casual"]
GoalLevel = Literal["pre_n5", "n5", "n4"]
ModelRouting = Literal["flash_only", "auto"]
TtsEngine = Literal["aivisspeech", "voicevox"]

PREFS_PATH = ROOT / "data" / "user_prefs.json"  # legacy flat path (migration only)
EXAMPLE_PREFS_PATH = ROOT / "data" / "user_prefs.example.json"

VALID_CORRECTION = {"gentle", "critique"}
VALID_LANGUAGE_POLICY = {"immerse", "adaptive"}
VALID_SPEECH_REGISTER = {"formal", "casual"}
VALID_GOAL_LEVEL = {"pre_n5", "n5", "n4"}
VALID_MODEL_ROUTING = {"flash_only", "auto"}
VALID_TTS_ENGINE = {"aivisspeech", "voicevox"}
MAX_TOPIC_PREFS = 8
MAX_TOPIC_LEN = 40


@dataclass
class UserPrefs:
    correction_style: CorrectionStyle = "gentle"
    personality_id: str = "patient_tutor"
    personality_custom: str = ""
    max_sentences: int = 3
    language_policy: LanguagePolicy = "adaptive"
    speech_register: SpeechRegister = "casual"
    naturalness_tips: bool = True
    help_language: str = "en"
    tts_engine: TtsEngine = "aivisspeech"
    voicevox_speaker_id: int = 888753760
    goal_level: GoalLevel = "pre_n5"
    topic_preferences: list[str] = field(default_factory=list)
    model_routing: ModelRouting = "auto"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_prefs() -> UserPrefs:
    return UserPrefs()


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _normalize_topics(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        items = [p.strip() for p in raw.split(",")]
    elif isinstance(raw, list):
        items = [str(p).strip() for p in raw]
    else:
        raise ValueError("topic_preferences must be a list of strings")
    out: list[str] = []
    for item in items:
        if not item:
            continue
        if len(item) > MAX_TOPIC_LEN:
            raise ValueError(f"topic preference too long (max {MAX_TOPIC_LEN})")
        if item not in out:
            out.append(item)
        if len(out) >= MAX_TOPIC_PREFS:
            break
    return out


def validate_prefs_dict(raw: dict[str, Any]) -> UserPrefs:
    # Import here to avoid circular import at module load.
    from kaiwa.persona import valid_personality_ids

    style = str(raw.get("correction_style", "gentle")).strip().lower()
    if style not in VALID_CORRECTION:
        raise ValueError("correction_style must be 'gentle' or 'critique'")

    personality_id = str(raw.get("personality_id", "patient_tutor")).strip()
    allowed = valid_personality_ids()
    if personality_id not in allowed:
        raise ValueError(
            "personality_id must be a built-in id, a user_ preset id, or 'custom'"
        )

    custom = str(raw.get("personality_custom", "") or "")
    if len(custom) > 2000:
        raise ValueError("personality_custom is too long (max 2000 chars)")

    max_sentences = int(raw.get("max_sentences", 3))
    if max_sentences < 1 or max_sentences > 6:
        raise ValueError("max_sentences must be between 1 and 6")

    language_policy = str(raw.get("language_policy", "adaptive")).strip().lower()
    if language_policy not in VALID_LANGUAGE_POLICY:
        raise ValueError("language_policy must be 'immerse' or 'adaptive'")

    speech_register = str(raw.get("speech_register", "casual")).strip().lower()
    if speech_register not in VALID_SPEECH_REGISTER:
        raise ValueError("speech_register must be 'formal' or 'casual'")

    naturalness_tips = _as_bool(raw.get("naturalness_tips", True), True)

    help_language = str(raw.get("help_language", "en") or "en").strip().lower() or "en"
    if len(help_language) > 16:
        raise ValueError("help_language is too long")

    try:
        voicevox_speaker_id = int(raw.get("voicevox_speaker_id", 888753760))
    except (TypeError, ValueError) as exc:
        raise ValueError("voicevox_speaker_id must be an integer") from exc
    if voicevox_speaker_id < 0:
        raise ValueError("voicevox_speaker_id must be >= 0")

    tts_engine = str(raw.get("tts_engine", "aivisspeech")).strip().lower()
    if tts_engine not in VALID_TTS_ENGINE:
        raise ValueError("tts_engine must be 'aivisspeech' or 'voicevox'")

    goal_level = str(raw.get("goal_level", "pre_n5")).strip().lower()
    if goal_level not in VALID_GOAL_LEVEL:
        raise ValueError("goal_level must be 'pre_n5', 'n5', or 'n4'")

    topic_preferences = _normalize_topics(raw.get("topic_preferences", []))

    model_routing = str(raw.get("model_routing", "auto")).strip().lower()
    if model_routing not in VALID_MODEL_ROUTING:
        raise ValueError("model_routing must be 'flash_only' or 'auto'")

    return UserPrefs(
        correction_style=style,  # type: ignore[arg-type]
        personality_id=personality_id,
        personality_custom=custom.strip(),
        max_sentences=max_sentences,
        language_policy=language_policy,  # type: ignore[arg-type]
        speech_register=speech_register,  # type: ignore[arg-type]
        naturalness_tips=naturalness_tips,
        help_language=help_language,
        tts_engine=tts_engine,  # type: ignore[arg-type]
        voicevox_speaker_id=voicevox_speaker_id,
        goal_level=goal_level,  # type: ignore[arg-type]
        topic_preferences=topic_preferences,
        model_routing=model_routing,  # type: ignore[arg-type]
    )


def load_prefs(path: Path | None = None) -> UserPrefs:
    from kaiwa.profiles import prefs_path as active_prefs_path

    prefs_file = path or active_prefs_path()
    if not prefs_file.exists():
        return default_prefs()
    try:
        raw = json.loads(prefs_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return default_prefs()
    if not isinstance(raw, dict):
        return default_prefs()
    try:
        return validate_prefs_dict(raw)
    except (ValueError, TypeError):
        return default_prefs()


def save_prefs(prefs: UserPrefs, path: Path | None = None) -> UserPrefs:
    from kaiwa.profiles import prefs_path as active_prefs_path

    prefs_file = path or active_prefs_path()
    prefs_file.parent.mkdir(parents=True, exist_ok=True)
    prefs_file.write_text(
        json.dumps(prefs.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return prefs
