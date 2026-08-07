"""Prompt strings and legacy exports.

Prefer kaiwa.persona.build_tutor_system_prompt for chat.
"""

from kaiwa.persona import (
    BASE_RULES,
    build_practice_tip_system_prompt,
    build_tutor_system_prompt,
)
from kaiwa.prefs import UserPrefs, default_prefs

# Backward-compatible default tutor prompt (patient + gentle).
TUTOR_SYSTEM_PROMPT = build_tutor_system_prompt(default_prefs())

PRACTICE_TIP_PROMPT = build_practice_tip_system_prompt(default_prefs())

__all__ = [
    "BASE_RULES",
    "TUTOR_SYSTEM_PROMPT",
    "PRACTICE_TIP_PROMPT",
    "build_tutor_system_prompt",
    "build_practice_tip_system_prompt",
    "UserPrefs",
]
