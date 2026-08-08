"""In-memory PTT background-turn events, status toasts, and desktop heartbeat."""

from __future__ import annotations

import itertools
import threading
import time
from typing import Any

_lock = threading.Lock()
_next_id = itertools.count(1)
_events: list[dict[str, Any]] = []
_MAX = 40

_registered_session_id: str = ""
_bind_capture: bool = False
_last_heartbeat_monotonic: float = 0.0
# Desktop hook considered alive if heartbeat within this window.
_HEARTBEAT_TTL_SEC = 5.0


def register_session(session_id: str) -> None:
    global _registered_session_id
    with _lock:
        _registered_session_id = (session_id or "").strip()


def registered_session() -> str:
    with _lock:
        return _registered_session_id


def set_bind_capture(active: bool) -> None:
    global _bind_capture
    with _lock:
        _bind_capture = bool(active)


def bind_capture_active() -> bool:
    with _lock:
        return _bind_capture


def heartbeat() -> None:
    global _last_heartbeat_monotonic
    with _lock:
        _last_heartbeat_monotonic = time.monotonic()


def hook_alive() -> bool:
    with _lock:
        if _last_heartbeat_monotonic <= 0:
            return False
        return (time.monotonic() - _last_heartbeat_monotonic) <= _HEARTBEAT_TTL_SEC


def push_event(
    *,
    user_text: str,
    reply_text: str,
    better_phrase: str | None = None,
    session_id: str = "",
) -> int:
    with _lock:
        eid = next(_next_id)
        _events.append(
            {
                "id": eid,
                "type": "turn",
                "session_id": session_id,
                "user_text": user_text,
                "reply_text": reply_text,
                "better_phrase": better_phrase or "",
            }
        )
        if len(_events) > _MAX:
            del _events[: len(_events) - _MAX]
        return eid


def push_status(message: str, *, level: str = "info") -> int:
    with _lock:
        eid = next(_next_id)
        _events.append(
            {
                "id": eid,
                "type": "status",
                "level": (level or "info").strip().lower() or "info",
                "message": (message or "").strip(),
            }
        )
        if len(_events) > _MAX:
            del _events[: len(_events) - _MAX]
        return eid


def events_after(after_id: int = 0) -> list[dict[str, Any]]:
    with _lock:
        return [dict(e) for e in _events if int(e["id"]) > after_id]
