from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from kaiwa.config import Settings
from kaiwa.prefs import UserPrefs

LearnerLevel = Literal["pre_n5", "n5", "n4"]
LEVEL_ORDER = ("pre_n5", "n5", "n4")
VALID_LEVELS = set(LEVEL_ORDER)

MAX_PRACTICE_SCORES = 20
MAX_TOPIC_TAGS = 8
MAX_NOTES = 500
ASSESS_EVERY_N_TURNS = 8
PLACEMENT_PROTECT_TURNS = 15


@dataclass
class ProfileStats:
    chat_turns: int = 0
    practice_scores: list[int] = field(default_factory=list)
    struggle_streak: int = 0
    flow_streak: int = 0
    last_assess_turn: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LearnerProfile:
    speaking_level: LearnerLevel = "pre_n5"
    comprehension_level: LearnerLevel = "pre_n5"
    confidence: float = 0.35
    topic_tags: list[str] = field(default_factory=list)
    notes: str = ""
    stats: ProfileStats = field(default_factory=ProfileStats)
    updated_at: str = ""
    # Fresh create/reset: False. Missing on load → grandfather True (see profile_from_dict).
    placement_completed: bool = False
    placement: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaking_level": self.speaking_level,
            "comprehension_level": self.comprehension_level,
            "confidence": round(float(self.confidence), 3),
            "topic_tags": list(self.topic_tags),
            "notes": self.notes,
            "stats": self.stats.to_dict(),
            "updated_at": self.updated_at,
            "placement_completed": bool(self.placement_completed),
            "placement": dict(self.placement) if self.placement else {},
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_profile() -> LearnerProfile:
    """Fresh profile defaults — Place me not done yet."""
    return LearnerProfile(updated_at=_now_iso(), placement_completed=False, placement={})


def placement_levels_locked(profile: LearnerProfile) -> bool:
    """True while we should not nudge levels after a fresh Place me."""
    if not profile.placement_completed:
        return False
    if profile.confidence < 0.8:
        return False
    baseline = 0
    raw = profile.placement.get("chat_turns_at_complete") if isinstance(profile.placement, dict) else None
    try:
        baseline = max(0, int(raw or 0))
    except (TypeError, ValueError):
        baseline = 0
    return (profile.stats.chat_turns - baseline) < PLACEMENT_PROTECT_TURNS

def level_index(level: str) -> int:
    try:
        return LEVEL_ORDER.index(level)  # type: ignore[arg-type]
    except ValueError:
        return 0


def clamp_level(level: str) -> LearnerLevel:
    if level in VALID_LEVELS:
        return level  # type: ignore[return-value]
    return "pre_n5"


def min_level(a: str, b: str) -> LearnerLevel:
    return LEVEL_ORDER[min(level_index(a), level_index(b))]  # type: ignore[return-value]


def nudge_level(level: str, delta: int) -> LearnerLevel:
    idx = max(0, min(len(LEVEL_ORDER) - 1, level_index(level) + delta))
    return LEVEL_ORDER[idx]  # type: ignore[return-value]


def effective_speech_level(prefs: UserPrefs, profile: LearnerProfile) -> LearnerLevel:
    """Pitch Kaiwa speech near min(goal, comprehension), floored at pre_n5."""
    return min_level(prefs.goal_level, profile.comprehension_level)


def _normalize_tags(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        items = [p.strip() for p in raw.split(",")]
    elif isinstance(raw, list):
        items = [str(p).strip() for p in raw]
    else:
        return []
    out: list[str] = []
    for item in items:
        if not item:
            continue
        item = item[:40]
        if item not in out:
            out.append(item)
        if len(out) >= MAX_TOPIC_TAGS:
            break
    return out


def _parse_stats(raw: Any) -> ProfileStats:
    if not isinstance(raw, dict):
        return ProfileStats()
    scores_raw = raw.get("practice_scores", [])
    scores: list[int] = []
    if isinstance(scores_raw, list):
        for s in scores_raw[-MAX_PRACTICE_SCORES:]:
            try:
                scores.append(max(0, min(100, int(s))))
            except (TypeError, ValueError):
                continue
    try:
        chat_turns = max(0, int(raw.get("chat_turns", 0)))
    except (TypeError, ValueError):
        chat_turns = 0
    try:
        struggle = max(0, int(raw.get("struggle_streak", 0)))
    except (TypeError, ValueError):
        struggle = 0
    try:
        flow = max(0, int(raw.get("flow_streak", 0)))
    except (TypeError, ValueError):
        flow = 0
    try:
        last_assess = max(0, int(raw.get("last_assess_turn", 0)))
    except (TypeError, ValueError):
        last_assess = 0
    return ProfileStats(
        chat_turns=chat_turns,
        practice_scores=scores,
        struggle_streak=struggle,
        flow_streak=flow,
        last_assess_turn=last_assess,
    )


def _parse_placement(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key, val in raw.items():
        k = str(key)[:40]
        if isinstance(val, (str, int, float, bool)):
            out[k] = val if not isinstance(val, str) else val[:120]
        elif isinstance(val, list):
            out[k] = [str(x)[:40] for x in val[:MAX_TOPIC_TAGS] if str(x).strip()]
    return out


def profile_from_dict(raw: dict[str, Any]) -> LearnerProfile:
    try:
        confidence = float(raw.get("confidence", 0.35))
    except (TypeError, ValueError):
        confidence = 0.35
    confidence = max(0.0, min(1.0, confidence))
    notes = str(raw.get("notes", "") or "")[:MAX_NOTES]
    # Grandfather existing profiles that predate the flag.
    if "placement_completed" in raw:
        placement_completed = bool(raw.get("placement_completed"))
    else:
        placement_completed = True
    return LearnerProfile(
        speaking_level=clamp_level(str(raw.get("speaking_level", "pre_n5"))),
        comprehension_level=clamp_level(str(raw.get("comprehension_level", "pre_n5"))),
        confidence=confidence,
        topic_tags=_normalize_tags(raw.get("topic_tags", [])),
        notes=notes,
        stats=_parse_stats(raw.get("stats")),
        updated_at=str(raw.get("updated_at") or _now_iso()),
        placement_completed=placement_completed,
        placement=_parse_placement(raw.get("placement")),
    )


def load_profile(path: Path | None = None) -> LearnerProfile:
    from kaiwa.profiles import learner_profile_path

    profile_file = path or learner_profile_path()
    if not profile_file.exists():
        return default_profile()
    try:
        raw = json.loads(profile_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return default_profile()
    if not isinstance(raw, dict):
        return default_profile()
    try:
        return profile_from_dict(raw)
    except (ValueError, TypeError):
        return default_profile()


def save_profile(profile: LearnerProfile, path: Path | None = None) -> LearnerProfile:
    from kaiwa.profiles import learner_profile_path

    profile_file = path or learner_profile_path()
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    profile.updated_at = _now_iso()
    profile_file.write_text(
        json.dumps(profile.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return profile


def reset_profile(path: Path | None = None) -> LearnerProfile:
    profile = default_profile()
    return save_profile(profile, path)


def apply_manual_override(
    profile: LearnerProfile,
    *,
    speaking_level: str | None = None,
    comprehension_level: str | None = None,
    topic_tags: list[str] | None = None,
    notes: str | None = None,
    confidence: float | None = None,
) -> LearnerProfile:
    if speaking_level is not None:
        profile.speaking_level = clamp_level(speaking_level)
    if comprehension_level is not None:
        profile.comprehension_level = clamp_level(comprehension_level)
    if topic_tags is not None:
        profile.topic_tags = _normalize_tags(topic_tags)
    if notes is not None:
        profile.notes = str(notes)[:MAX_NOTES]
    if confidence is not None:
        profile.confidence = max(0.0, min(1.0, float(confidence)))
    return profile


def apply_chat_signals(
    profile: LearnerProfile,
    learner_state: str,
    transcript: str,
) -> LearnerProfile:
    profile.stats.chat_turns += 1
    state = (learner_state or "flowing").strip().lower()
    # Pending placement: track streaks only — do not invent a level.
    # Fresh placement: protect levels for PLACEMENT_PROTECT_TURNS.
    lock_levels = (not profile.placement_completed) or placement_levels_locked(profile)

    if state in {"struggling", "help_request"}:
        profile.stats.struggle_streak += 1
        profile.stats.flow_streak = 0
        if profile.stats.struggle_streak >= 3:
            if not lock_levels and profile.stats.struggle_streak == 3:
                profile.speaking_level = nudge_level(profile.speaking_level, -1)
                profile.comprehension_level = nudge_level(profile.comprehension_level, -1)
            if not lock_levels:
                profile.confidence = max(0.15, profile.confidence - 0.05)
    else:
        profile.stats.flow_streak += 1
        profile.stats.struggle_streak = 0
        if profile.stats.flow_streak >= 5:
            if not lock_levels and profile.stats.flow_streak == 5:
                profile.speaking_level = nudge_level(profile.speaking_level, 1)
            if not lock_levels:
                profile.confidence = min(0.85, profile.confidence + 0.03)

    jp_chars = len(re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", transcript or ""))
    if jp_chars >= 20 and state == "flowing" and not lock_levels:
        profile.confidence = min(0.9, profile.confidence + 0.01)

    return profile


def apply_practice_score(profile: LearnerProfile, score: int, band: str) -> LearnerProfile:
    score = max(0, min(100, int(score)))
    scores = list(profile.stats.practice_scores)
    scores.append(score)
    profile.stats.practice_scores = scores[-MAX_PRACTICE_SCORES:]

    lock_levels = (not profile.placement_completed) or placement_levels_locked(profile)
    mean = sum(profile.stats.practice_scores) / len(profile.stats.practice_scores)
    if not lock_levels:
        if mean >= 85 and len(profile.stats.practice_scores) >= 3:
            profile.speaking_level = nudge_level(profile.speaking_level, 1)
            profile.confidence = min(0.9, profile.confidence + 0.04)
        elif mean < 50 and len(profile.stats.practice_scores) >= 3:
            profile.speaking_level = nudge_level(profile.speaking_level, -1)
            profile.confidence = max(0.15, profile.confidence - 0.04)

    if band == "unclear" and profile.placement_completed and not placement_levels_locked(profile):
        profile.confidence = max(0.15, profile.confidence - 0.02)
    elif band == "clear" and profile.placement_completed and not placement_levels_locked(profile):
        profile.confidence = min(0.9, profile.confidence + 0.01)

    return profile


def should_assess(profile: LearnerProfile, prefs: UserPrefs) -> bool:
    if prefs.model_routing == "flash_only":
        # Still allow assess on Flash — routing only gates Pro for chat replies.
        pass
    if not profile.placement_completed:
        return False
    if placement_levels_locked(profile):
        return False
    if profile.confidence < 0.5:
        return True
    turns = profile.stats.chat_turns
    if turns > 0 and (turns - profile.stats.last_assess_turn) >= ASSESS_EVERY_N_TURNS:
        return True
    if profile.stats.struggle_streak >= 3:
        return True
    return False


ASSESS_SYSTEM = """\
You estimate a Japanese learner's level from one utterance and light context.
Reply with JSON only (no markdown):
{
  "speaking_level": "pre_n5"|"n5"|"n4",
  "comprehension_level": "pre_n5"|"n5"|"n4",
  "topic_tags": ["optional","short","tags"],
  "notes": "one short English sentence",
  "confidence": 0.0-1.0
}
Be conservative. Prefer pre_n5 when unsure. Do not invent advanced ability.
"""


def _extract_json(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        raw = json.loads(text)
        return raw if isinstance(raw, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            raw = json.loads(match.group(0))
            return raw if isinstance(raw, dict) else None
        except json.JSONDecodeError:
            return None


def merge_assess_result(profile: LearnerProfile, data: dict[str, Any]) -> LearnerProfile:
    """Merge assess JSON conservatively (at most one band jump per skill)."""
    if "speaking_level" in data:
        target = clamp_level(str(data["speaking_level"]))
        cur = level_index(profile.speaking_level)
        tgt = level_index(target)
        if abs(tgt - cur) <= 1:
            profile.speaking_level = target
        else:
            profile.speaking_level = nudge_level(profile.speaking_level, 1 if tgt > cur else -1)

    if "comprehension_level" in data:
        target = clamp_level(str(data["comprehension_level"]))
        cur = level_index(profile.comprehension_level)
        tgt = level_index(target)
        if abs(tgt - cur) <= 1:
            profile.comprehension_level = target
        else:
            profile.comprehension_level = nudge_level(
                profile.comprehension_level, 1 if tgt > cur else -1
            )

    if "topic_tags" in data:
        tags = _normalize_tags(data.get("topic_tags"))
        if tags:
            merged = list(profile.topic_tags)
            for tag in tags:
                if tag not in merged:
                    merged.append(tag)
            profile.topic_tags = merged[:MAX_TOPIC_TAGS]

    if "notes" in data and str(data.get("notes") or "").strip():
        profile.notes = str(data["notes"]).strip()[:MAX_NOTES]

    if "confidence" in data:
        try:
            c = float(data["confidence"])
            profile.confidence = max(0.2, min(0.95, (profile.confidence + c) / 2))
        except (TypeError, ValueError):
            pass

    profile.stats.last_assess_turn = profile.stats.chat_turns
    return profile


def run_assess(
    settings: Settings,
    profile: LearnerProfile,
    *,
    transcript: str,
    learner_state: str,
    prefs: UserPrefs,
    client: Any = None,
) -> LearnerProfile:
    """Occasional Flash JSON assess. Fails soft on errors."""
    from kaiwa.llm import _completion

    placement_hint = ""
    if profile.placement_completed and isinstance(profile.placement, dict) and profile.placement:
        placement_hint = (
            "Respect recent Place-me self-ratings unless this utterance clearly contradicts them.\n"
            f"placement: {json.dumps(profile.placement, ensure_ascii=False)[:400]}\n"
        )
    user = (
        f"goal_level: {prefs.goal_level}\n"
        f"learner_state: {learner_state}\n"
        f"current_speaking: {profile.speaking_level}\n"
        f"current_comprehension: {profile.comprehension_level}\n"
        f"{placement_hint}"
        f"utterance: {transcript}\n"
        f"recent_practice_scores: {profile.stats.practice_scores[-5:]}\n"
    )
    try:
        raw_text = _completion(
            settings,
            ASSESS_SYSTEM,
            [{"role": "user", "content": user}],
            client=client,
            model=settings.deepseek_model,
        )
        data = _extract_json(raw_text)
        if data:
            profile = merge_assess_result(profile, data)
        else:
            profile.stats.last_assess_turn = profile.stats.chat_turns
    except Exception:
        profile.stats.last_assess_turn = profile.stats.chat_turns
    return profile


def maybe_run_assess(
    settings: Settings,
    profile: LearnerProfile,
    *,
    transcript: str,
    learner_state: str,
    prefs: UserPrefs,
    client: Any = None,
) -> LearnerProfile:
    if not should_assess(profile, prefs):
        return profile
    return run_assess(
        settings,
        profile,
        transcript=transcript,
        learner_state=learner_state,
        prefs=prefs,
        client=client,
    )


def needs_pro_routing(
    prefs: UserPrefs,
    profile: LearnerProfile,
    learner_state: str,
) -> bool:
    if prefs.model_routing != "auto":
        return False
    state = (learner_state or "").strip().lower()
    if state in {"struggling", "help_request"}:
        return True
    if prefs.correction_style == "critique" and profile.stats.struggle_streak >= 2:
        return True
    return False
