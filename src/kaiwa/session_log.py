from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_session_log(sessions_dir: Path, session_id: str, record: dict[str, Any]) -> None:
    sessions_dir.mkdir(parents=True, exist_ok=True)
    path = sessions_dir / f"{session_id}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
