"""Phase 8.2 Rescue — rewrite the last Kaiwa line one step simpler.

Never invent a learner utterance. The Simpler button is the signal.
"""

from __future__ import annotations

import re

from kaiwa.learner_profile import LearnerProfile, bump_comprehension_struggle
from kaiwa.reply_shape import reply_too_dense, sentence_count

RescueStep = str  # "shorter" | "yes_no" | "ab"

_AB_RE = re.compile(r"それとも|どっち")
_Q_RE = re.compile(r"[？?]")

_STEP_GUIDE = {
    "shorter": "同じ話題で、考えは1つ。短く言い直す。新しい考えは足さない。",
    "yes_no": "同じ話題で、はい／いいえで答えられる短い確認にする。",
    "ab": "同じ話題で、A と B の短い選択肢にする（それとも）。",
}


def looks_like_ab(text: str) -> bool:
    raw = text or ""
    if _AB_RE.search(raw):
        return True
    if raw.count("？") + raw.count("?") >= 2:
        return True
    return False


def looks_like_yes_no(text: str) -> bool:
    """Short single question that is not already A/B or packed."""
    if looks_like_ab(text):
        return False
    if reply_too_dense(text):
        return False
    if not _Q_RE.search(text or ""):
        return False
    if sentence_count(text) > 2:
        return False
    return True


def next_rescue_step(reply: str) -> RescueStep:
    """Target form for this rewrite: packed → shorter → yes/no → A/B."""
    if looks_like_ab(reply):
        return "ab"
    if looks_like_yes_no(reply):
        return "ab"
    if reply_too_dense(reply):
        return "shorter"
    return "yes_no"


def rescue_instruction(original: str, step: str) -> str:
    """Ephemeral LLM instruction — not stored as a user turn."""
    key = (step or "shorter").strip().lower()
    guide = _STEP_GUIDE.get(key, _STEP_GUIDE["shorter"])
    orig = (original or "").strip()
    return (
        f"学習者は直前のKaiwaの発話がわからなかった。"
        f"その発話を一段やさしく書き直す。元: 「{orig}」。"
        f"目標: {key}。{guide}"
        "学習者が何か言った体にしない。モード名は言わない。"
    )


def apply_rescue_signals(profile: LearnerProfile) -> LearnerProfile:
    """Bump comprehension scaffolding without a fake user line or chat_turns++."""
    return bump_comprehension_struggle(profile)
