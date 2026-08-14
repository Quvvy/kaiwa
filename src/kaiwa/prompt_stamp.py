"""AppData stamp for tutor PROMPT_REVISION (decision #115).

The assembled system prompt is never stored on a profile. A newer revision
clears in-memory chat threads so old Kaiwa style cannot outvote the new prompt.
Does not touch learner memory, prefs, or placement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kaiwa.persona import PROMPT_REVISION
from kaiwa.secrets_store import user_data_dir

STAMP_FILENAME = "prompt_revision.json"

# Set at API startup: True if this process rotated the stamp and cleared sessions.
chat_reset_this_process = False


def stamp_path() -> Path:
    return user_data_dir() / STAMP_FILENAME


def stored_revision() -> int:
    path = stamp_path()
    if not path.is_file():
        return 0
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return 0
    if not isinstance(raw, dict):
        return 0
    try:
        return max(0, int(raw.get("revision", 0) or 0))
    except (TypeError, ValueError):
        return 0


def write_revision(revision: int) -> None:
    path = stamp_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"revision": int(revision)}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def apply_on_startup(sessions: dict[str, Any]) -> bool:
    """If code revision > stored, clear RAM chats and stamp. Returns chat_reset.

    JSONL catalog is kept (8.3). The UI mints a new durable session per profile.
    """
    global chat_reset_this_process
    stored = stored_revision()
    if PROMPT_REVISION > stored:
        sessions.clear()
        write_revision(PROMPT_REVISION)
        chat_reset_this_process = True
        return True
    chat_reset_this_process = False
    return False
