"""Durable Chat session records (Phase 8.3 / decision #110).

JSONL stays append-only under the global sessions dir. A sidecar meta.json
binds each file to a profile. RAM `_sessions` hydrates from JSONL on miss.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kaiwa.persona import PROMPT_REVISION
from kaiwa.session_log import append_session_log

TITLE_MAX = 80
LEGACY_PROFILE = "legacy"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def jsonl_path(sessions_dir: Path, session_id: str) -> Path:
    return sessions_dir / f"{session_id}.jsonl"


def meta_path(sessions_dir: Path, session_id: str) -> Path:
    return sessions_dir / f"{session_id}.meta.json"


@dataclass
class SessionMeta:
    id: str
    profile_id: str
    started: str
    updated: str
    turn_count: int = 0
    title: str = ""
    prompt_revision: int = PROMPT_REVISION
    replay_of: str = ""
    replay_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def meta_from_dict(raw: dict[str, Any], *, session_id: str) -> SessionMeta:
    now = _now_iso()
    try:
        turns = max(0, int(raw.get("turn_count", 0) or 0))
    except (TypeError, ValueError):
        turns = 0
    try:
        rev = int(raw.get("prompt_revision", 0) or 0)
    except (TypeError, ValueError):
        rev = 0
    return SessionMeta(
        id=str(raw.get("id") or session_id).strip() or session_id,
        profile_id=str(raw.get("profile_id") or "").strip(),
        started=str(raw.get("started") or now),
        updated=str(raw.get("updated") or now),
        turn_count=turns,
        title=str(raw.get("title") or "")[:TITLE_MAX],
        prompt_revision=rev,
        replay_of=str(raw.get("replay_of") or "").strip(),
        replay_questions=_questions_from_raw(raw.get("replay_questions")),
    )


def _questions_from_raw(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def assistant_questions(messages: list[dict[str, str]]) -> list[str]:
    """Non-empty assistant lines in order (hydrate already applies rescue)."""
    out: list[str] = []
    for message in messages:
        if (message.get("role") or "") != "assistant":
            continue
        text = str(message.get("content") or "").strip()
        if text:
            out.append(text)
    return out


def replay_title(parent_title: str) -> str:
    base = (parent_title or "").strip() or "Untitled chat"
    if base.startswith("Again:"):
        return base[:TITLE_MAX]
    return ("Again: " + base)[:TITLE_MAX]


def questions_for_replay(sessions_dir: Path, session_id: str) -> list[str]:
    """Prefer stored list so a child is not re-parsed into ack+question soup."""
    meta = load_meta(sessions_dir, session_id)
    if meta is not None and meta.replay_questions:
        return list(meta.replay_questions)
    return assistant_questions(hydrate(sessions_dir, session_id))


def replay_remaining(
    questions: list[str], history: list[dict[str, str]]
) -> list[str]:
    """Questions still to ask, including the current one until the learner answers it."""
    n_user = 0
    for message in history:
        if (message.get("role") or "") != "user":
            continue
        if str(message.get("content") or "").strip():
            n_user += 1
    if n_user >= len(questions):
        return []
    return list(questions[n_user:])


def create_replay_session(
    sessions_dir: Path,
    profile_id: str,
    *,
    parent_id: str,
    questions: list[str],
    parent_title: str = "",
) -> SessionMeta:
    meta = create_session(sessions_dir, profile_id)
    meta.replay_of = (parent_id or "").strip()
    meta.replay_questions = [q for q in questions if str(q).strip()]
    meta.title = replay_title(parent_title)
    save_meta(sessions_dir, meta)
    return meta


def load_meta(sessions_dir: Path, session_id: str) -> SessionMeta | None:
    path = meta_path(sessions_dir, session_id)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    return meta_from_dict(raw, session_id=session_id)


def save_meta(sessions_dir: Path, meta: SessionMeta) -> None:
    sessions_dir.mkdir(parents=True, exist_ok=True)
    path = meta_path(sessions_dir, meta.id)
    path.write_text(json.dumps(meta.to_dict(), indent=2) + "\n", encoding="utf-8")


def iter_jsonl(sessions_dir: Path, session_id: str) -> list[dict[str, Any]]:
    path = jsonl_path(sessions_dir, session_id)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict):
            rows.append(raw)
    return rows


def hydrate(sessions_dir: Path, session_id: str) -> list[dict[str, str]]:
    """Rebuild Chat messages. Skip practice/placement. Rescue replaces last assistant."""
    messages: list[dict[str, str]] = []
    for record in iter_jsonl(sessions_dir, session_id):
        mode = str(record.get("mode") or "chat").strip().lower()
        if mode in {"practice", "placement"}:
            continue
        if record.get("rescue"):
            reply = str(record.get("reply") or "").strip()
            if not reply:
                continue
            if messages and messages[-1].get("role") == "assistant":
                messages[-1] = {"role": "assistant", "content": reply}
            else:
                messages.append({"role": "assistant", "content": reply})
            continue
        transcript = str(record.get("transcript") or "").strip()
        reply = str(record.get("reply") or "").strip()
        if transcript:
            messages.append({"role": "user", "content": transcript})
        if reply:
            messages.append({"role": "assistant", "content": reply})
    return messages


def _title_from_records(records: list[dict[str, Any]]) -> str:
    for record in records:
        if record.get("rescue"):
            continue
        if str(record.get("mode") or "chat").strip().lower() != "chat":
            continue
        text = str(record.get("transcript") or "").strip()
        if text:
            return text[:TITLE_MAX]
    return ""


def _chat_turns(records: list[dict[str, Any]]) -> int:
    n = 0
    for record in records:
        if record.get("rescue"):
            continue
        if str(record.get("mode") or "chat").strip().lower() != "chat":
            continue
        if str(record.get("transcript") or "").strip() or str(record.get("reply") or "").strip():
            n += 1
    return n


def _first_ts(records: list[dict[str, Any]]) -> str:
    for record in records:
        ts = str(record.get("ts") or "").strip()
        if ts:
            return ts
    return _now_iso()


def _last_ts(records: list[dict[str, Any]]) -> str:
    ts = ""
    for record in records:
        value = str(record.get("ts") or "").strip()
        if value:
            ts = value
    return ts or _now_iso()


def attach_legacy(
    sessions_dir: Path,
    session_id: str,
    profile_id: str,
) -> SessionMeta:
    """Write meta for a JSONL that has none. Never split mixed files."""
    records = iter_jsonl(sessions_dir, session_id)
    inferred = ""
    for record in records:
        pid = str(record.get("profile_id") or "").strip()
        if pid:
            inferred = pid
            break
    pid = inferred or (profile_id or "").strip() or LEGACY_PROFILE
    started = _first_ts(records)
    meta = SessionMeta(
        id=session_id,
        profile_id=pid,
        started=started,
        updated=_last_ts(records),
        turn_count=_chat_turns(records),
        title=_title_from_records(records),
        prompt_revision=0,
    )
    save_meta(sessions_dir, meta)
    return meta


def ensure_meta(
    sessions_dir: Path,
    session_id: str,
    profile_id: str,
) -> SessionMeta:
    meta = load_meta(sessions_dir, session_id)
    if meta is not None:
        if not meta.profile_id:
            meta.profile_id = (profile_id or "").strip() or LEGACY_PROFILE
            save_meta(sessions_dir, meta)
        return meta
    if jsonl_path(sessions_dir, session_id).is_file():
        return attach_legacy(sessions_dir, session_id, profile_id)
    now = _now_iso()
    meta = SessionMeta(
        id=session_id,
        profile_id=(profile_id or "").strip() or LEGACY_PROFILE,
        started=now,
        updated=now,
        turn_count=0,
        title="",
        prompt_revision=PROMPT_REVISION,
    )
    sessions_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path(sessions_dir, session_id).touch()
    save_meta(sessions_dir, meta)
    return meta


def create_session(
    sessions_dir: Path,
    profile_id: str,
    *,
    session_id: str | None = None,
) -> SessionMeta:
    sid = (session_id or "").strip() or uuid.uuid4().hex
    now = _now_iso()
    meta = SessionMeta(
        id=sid,
        profile_id=(profile_id or "").strip() or LEGACY_PROFILE,
        started=now,
        updated=now,
        turn_count=0,
        title="",
        prompt_revision=PROMPT_REVISION,
    )
    sessions_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path(sessions_dir, sid).touch()
    save_meta(sessions_dir, meta)
    return meta


def session_exists(sessions_dir: Path, session_id: str) -> bool:
    return jsonl_path(sessions_dir, session_id).is_file() or meta_path(
        sessions_dir, session_id
    ).is_file()


def other_named_profile(meta: SessionMeta, active_id: str, known_ids: set[str]) -> bool:
    pid = (meta.profile_id or "").strip()
    if not pid or pid == LEGACY_PROFILE:
        return False
    if pid == active_id:
        return False
    return pid in known_ids


def revision_stale(meta: SessionMeta) -> bool:
    return int(meta.prompt_revision or 0) < int(PROMPT_REVISION)


def list_session_ids(sessions_dir: Path) -> list[str]:
    if not sessions_dir.is_dir():
        return []
    ids: set[str] = set()
    for path in sessions_dir.glob("*.jsonl"):
        ids.add(path.stem)
    for path in sessions_dir.glob("*.meta.json"):
        name = path.name[: -len(".meta.json")]
        if name:
            ids.add(name)
    return sorted(ids)


def list_sessions(
    sessions_dir: Path,
    profile_id: str,
    *,
    attach_unbound: bool = True,
) -> list[SessionMeta]:
    """Metas for this profile. Unbound legacy files attach on first list."""
    pid = (profile_id or "").strip()
    out: list[SessionMeta] = []
    for sid in list_session_ids(sessions_dir):
        meta = load_meta(sessions_dir, sid)
        if meta is None:
            if attach_unbound:
                meta = attach_legacy(sessions_dir, sid, pid)
            else:
                continue
        elif not meta.profile_id and attach_unbound:
            meta.profile_id = pid or LEGACY_PROFILE
            save_meta(sessions_dir, meta)
        if meta.profile_id == pid or (
            pid and meta.profile_id == LEGACY_PROFILE and attach_unbound
        ):
            if meta.profile_id == LEGACY_PROFILE and pid:
                meta.profile_id = pid
                save_meta(sessions_dir, meta)
            out.append(meta)
    out.sort(key=lambda m: m.updated, reverse=True)
    return out


def append_record(
    sessions_dir: Path,
    session_id: str,
    record: dict[str, Any],
    *,
    profile_id: str,
    bump_turns: bool = False,
    title_hint: str = "",
) -> SessionMeta:
    payload = dict(record)
    payload["profile_id"] = profile_id
    append_session_log(sessions_dir, session_id, payload)
    meta = ensure_meta(sessions_dir, session_id, profile_id)
    if not meta.profile_id or meta.profile_id == LEGACY_PROFILE:
        meta.profile_id = profile_id or meta.profile_id
    meta.updated = str(payload.get("ts") or _now_iso())
    if bump_turns:
        meta.turn_count = max(0, int(meta.turn_count)) + 1
        hint = (title_hint or "").strip()
        if hint and not meta.title:
            meta.title = hint[:TITLE_MAX]
    save_meta(sessions_dir, meta)
    return meta


def ensure_ram(
    sessions: dict[str, list[dict[str, str]]],
    sessions_dir: Path,
    session_id: str,
) -> list[dict[str, str]]:
    if session_id in sessions:
        return sessions[session_id]
    history = hydrate(sessions_dir, session_id)
    sessions[session_id] = history
    return history
