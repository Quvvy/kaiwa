"""The study-lab branch's logic: content integrity and scheduling. No network."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("KAIWA_DATA_DIR", tempfile.mkdtemp(prefix="kaiwa-lab-smoke-"))

from kaiwa.course import kana_hooks  # noqa: E402
from kaiwa.course import state as cs  # noqa: E402
from kaiwa.course.kana import KANA_LESSONS, KANA_ROMAJI  # noqa: E402


def _check(ok: bool, label: str) -> None:
    line = ("ok  " if ok else "FAIL") + label
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
    if not ok:
        raise SystemExit(f"smoke_lab failed: {label}")


def kana_pictures() -> None:
    base = [c for l in KANA_LESSONS for c, _ in l["kana"] if len(c) == 1 and not (l["id"] in ("h10", "h11", "k6"))]
    _check(not [c for c in base if not kana_hooks.hook_for(c)], "every basic kana has a picture")
    _check(not [c for g in kana_hooks.LOOKALIKES for c in g if c not in KANA_ROMAJI], "look-alike groups are real kana")
    _check("れ" in kana_hooks.alike("ね") and "ね" not in kana_hooks.alike("ね"), "look-alikes exclude the kana itself")
    lesson = cs.public_kana_lesson(KANA_LESSONS[4], cs._empty())
    _check(bool(lesson["kana"][0]["hook"]) and "alike" in lesson["kana"][0], "lesson payload carries pictures and look-alikes")


def main() -> None:
    kana_pictures()
    print("smoke_lab ok")


if __name__ == "__main__":
    main()
