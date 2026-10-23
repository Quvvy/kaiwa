"""Crash-safe JSON state files (prefs, profile, memory, registries).

Writes go to a temp file in the same folder, then ``os.replace`` swaps it in,
so a reader never sees a half-written file. A file that still fails to parse
is moved aside (``*.corrupt-<stamp>``) instead of being silently replaced by
defaults on the next save.

``STATE_LOCK`` serializes load→modify→save across request handlers and the
background chat sidework thread. It is re-entrant; never hold it across an
LLM call.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

STATE_LOCK = threading.RLock()

# Windows: antivirus / indexers can briefly hold a file open.
_RETRIES = 8
_RETRY_SLEEP = 0.05


def write_json_atomic(path: Path, data: Any, *, ensure_ascii: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=ensure_ascii, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        for attempt in range(_RETRIES):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == _RETRIES - 1:
                    raise
                time.sleep(_RETRY_SLEEP * (attempt + 1))
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def quarantine(path: Path, reason: str) -> Path | None:
    """Move an unreadable state file aside so defaults can't overwrite it."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(f"{path.name}.corrupt-{stamp}")
    try:
        os.replace(path, dest)
    except OSError as exc:
        _log.error("could not quarantine %s (%s): %s", path, reason, exc)
        return None
    _log.warning("quarantined unreadable %s → %s (%s)", path.name, dest.name, reason)
    return dest


def read_json_dict(path: Path) -> dict[str, Any] | None:
    """Parsed object, or None if missing / corrupt (corrupt files are quarantined).

    Transient OS errors are retried and then raised: returning defaults there
    would let the caller's next save wipe a perfectly good file.
    """
    if not path.exists():
        return None
    for attempt in range(_RETRIES):
        try:
            text = path.read_text(encoding="utf-8")
            break
        except FileNotFoundError:
            return None
        except OSError:
            if attempt == _RETRIES - 1:
                raise
            time.sleep(_RETRY_SLEEP * (attempt + 1))
    try:
        raw = json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        quarantine(path, f"invalid JSON: {exc}")
        return None
    if not isinstance(raw, dict):
        quarantine(path, f"expected an object, got {type(raw).__name__}")
        return None
    return raw
