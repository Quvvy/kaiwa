"""The study-lab branch's logic: content integrity and scheduling. No network."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("KAIWA_DATA_DIR", tempfile.mkdtemp(prefix="kaiwa-lab-smoke-"))

from datetime import datetime, timedelta, timezone  # noqa: E402

from kaiwa.course import kana_hooks, srs  # noqa: E402
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


def due_card(days_overdue: int = 1) -> dict:
    due = srs._now() - timedelta(days=days_overdue)
    return srs.placed_card(5.0, due.date())


def day_boundary() -> None:
    late = datetime(2027, 3, 2, 1, 30).astimezone()
    _check(srs.study_day(late).isoformat() == "2027-03-01", "1:30 a.m. belongs to the evening before")
    morning = datetime(2027, 3, 2, 8, 0).astimezone()
    _check(srs.study_day(morning).isoformat() == "2027-03-02", "8 a.m. is the new day")


def one_side_per_day() -> None:
    state = cs._empty()
    state["cards"]["u1.ohayou:listen"] = due_card()
    state["cards"]["u1.ohayou:speak"] = due_card()
    state["cards"]["u1.sumimasen:speak"] = due_card()
    today_ids = [c["card_id"] for c in cs.todays_reviews(state)]
    _check(sum(i.startswith("u1.ohayou") for i in today_ids) == 1, "a phrase comes up on one side per day")
    _check("u1.sumimasen:speak" in today_ids, "other phrases are unaffected")
    _check(len(cs.due_cards(state, limit=100)) == 3, "the held-back side still counts as due")
    side = next(i for i in today_ids if i.startswith("u1.ohayou"))
    cs._apply_grade(state, side, cs._card_kind(side), {"correct": True, "ms": None, "helped": False, "guessed": False, "band": "", "fmt": "x"}, None)
    after = [c["card_id"] for c in cs.todays_reviews(state)]
    _check(not any(i.startswith("u1.ohayou") for i in after), "the other side stays away after one was answered today")


def pacing_plans() -> None:
    state = cs._empty()
    p = cs.plan_today(state)
    _check(p["plan"][0] == "kana" and "learn" in p["plan"] and p["plan"][-1] == "recap", "day one has kana, phrases and a recap")
    _check(p["minutes"] >= 1, "the plan says how long today takes")
    relaxed = {**cs._empty(), "pace": "relaxed"}
    pr = cs.plan_today(relaxed)
    intense = {**cs._empty(), "pace": "intensive"}
    pi = cs.plan_today(intense)
    _check(pi["words_today"] == 20 and "words" in pi["plan"], "intensive takes all of a unit's words in a day")
    _check("words" not in pr["plan"] or pr["words_today"] < 20, "relaxed spreads a unit's words out")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        cs.complete_step("u1", "learn", path=path)
        cs.complete_step("u1", "words", count=10, path=path)
        st = cs.load_state(path)
        _check(st["units"]["u1"]["words_seen"] == 10 and not st["units"]["u1"]["words"], "a part of the words doesn't finish the step")
        _check(sum(c.startswith("u1w.") for c in st["cards"]) == 10, "only the taught words get cards")
        cs.complete_step("u1", "words", count=10, path=path)
        st = cs.load_state(path)
        _check(st["units"]["u1"]["words"] and sum(c.startswith("u1w.") for c in st["cards"]) == 20, "the last part finishes it")
        cs.set_pace("relaxed", path=path)
        _check(cs.load_state(path)["pace"] == "relaxed", "pace is saved")
    low = cs._empty()
    low["log"] = [{"d": cs._today().isoformat(), "ok": i % 2 == 0} for i in range(40)]
    _check(cs.recall_slipping(low) == 50, "recall below the line is reported")
    baseline = cs.plan_today({**cs._empty(), "pace": "regular"})
    slowed = cs.plan_today({**low, "pace": "regular"})
    _check(slowed["slipping"] == 50 and len(slowed["plan"]) <= len(baseline["plan"]), "slipping recall slows new material")


def sound_diff() -> None:
    from kaiwa.course.speech_check import spot_differences
    runs = spot_differences("おはようございます", "おはございます")
    missed = "".join(str(r["text"]) for r in runs if not r["ok"])
    _check(missed == "よう", "the sounds that didn't come through are marked")
    _check(all(r["ok"] for r in spot_differences("すみません", "すみません")), "a perfect line marks nothing")
    _check(spot_differences("", "x") == [], "no target, nothing to mark")


def word_formats() -> None:
    card = srs.new_card()
    _check(cs.answer_format("word", "mean", card) == "choice", "a new word is recognised")
    known = srs.from_legacy({"box": 3, "due": "2099-01-01", "reps": 4})
    _check(cs.answer_format("word", "mean", known) == "produce", "a known word is produced on even reviews")
    _check(cs.answer_format("word", "mean", {**known, "reps": 5}) == "choice", "and understood by ear on odd ones")
    _check(cs.answer_format("kana", "read", {**known, "reps": 5}) == "produce", "kana always asks for the sound")


def main() -> None:
    sound_diff()
    word_formats()
    pacing_plans()
    kana_pictures()
    day_boundary()
    one_side_per_day()
    print("smoke_lab ok")


if __name__ == "__main__":
    main()
