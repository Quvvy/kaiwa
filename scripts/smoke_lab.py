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


def grammar_cards() -> None:
    from kaiwa.course import build
    from kaiwa.course.speech_check import normalize
    from kaiwa.course.units import UNITS
    examples = {u["id"]: [normalize(e["jp"]) for g in u["grammar"] for e in g["examples"]] for u in UNITS}
    points = {g["id"]: u["id"] for u in UNITS for g in u["grammar"]}
    _check(set(build.BUILD) <= set(points), "build items belong to real grammar points")
    thin = [g["id"] for u in UNITS for g in u["grammar"] if g["id"] not in build.BUILD]
    _check(thin == ["u1g.polite"], "every grammar point but polite-vs-casual has sentences to build")
    for pid, items in build.BUILD.items():
        for it in items:
            if it["decoy"] and it["decoy"] in it["tiles"]:
                _check(False, f"{pid}: decoy {it['decoy']} is needed in {it['jp']}")
            if not any(normalize(it["jp"]) in ex for ex in examples[points[pid]]) and pid != "u1g.desu":
                _check(False, f"{pid}: {it['jp']} isn't one of the unit's examples")
            for alt in it["also"]:
                if sorted(alt) != sorted(it["jp"]):
                    _check(False, f"{pid}: other order of {it['jp']} has different tiles")
    _check(True, "build sentences match the unit's examples, decoys are spare, other orders use the same tiles")
    _check(sum(len(v) for v in build.BUILD.values()) >= 120, "plenty of sentences")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        cs.complete_step("u4", "grammar", path=path)
        st = cs.load_state(path)
        _check("u4g.ga:build" in st["cards"] and "u4g.janai:build" in st["cards"], "finishing the grammar step schedules its cards")
        kind = cs._card_kind("u4g.ga:build")
        _check(kind == ("grammar", "u4g.ga", "build"), "grammar cards are a real card kind")
        row = cs._card_row("u4g.ga:build", kind, st["cards"]["u4g.ga:build"])
        _check(row["format"] == "build" and row["grammar"]["items"], "a review row carries its sentences")
        cs.grade("u4g.ga:build", correct=True, path=path)
        _check(cs.course_stats(path=path)["stages"]["Grammar"], "the stats page counts grammar cards")
        _check(cs.undo(path=path) is not None, "a grammar answer can be undone")
        old = {**cs._empty(), "units": {"u1": {"grammar": True}, "u2": {"grammar": True}}}
        cs.save_state(old, path)
        st = cs.load_state(path)
        added = [c for c in st["cards"] if c.endswith(":build")]
        _check(len(added) == 3 and not any(srs.is_learning(st["cards"][c]) for c in added),
               "grammar done before this update joins the schedule as reviews")


def habit_and_map() -> None:
    from datetime import date
    from kaiwa.course import missions
    from kaiwa.course.units import UNITS
    real = cs._today
    cs._today = lambda: date(2027, 5, 31)
    try:
        run = [(date(2027, 5, 31) - timedelta(days=x)).isoformat() for x in range(1, 9)]
        st = {**cs._empty(), "days": sorted(run)}
        _check(cs.streak(st) == 8, "eight days in a row, ending yesterday")
        gap = [d for d in run if d != run[1]]  # one day missed, after a full week
        st2 = {**cs._empty(), "days": sorted(gap)}
        info = cs.streak_info(st2)
        _check(info["days"] == 1, "a miss before a week's study resets")
        week = [(date(2027, 5, 31) - timedelta(days=x)).isoformat() for x in range(2, 10)]
        st3 = {**cs._empty(), "days": sorted(week)}
        _check(cs.streak(st3) == 8 and cs.streak_info(st3)["rests"] == 0, "a rest day earned by a week covers one missed day")
        far = {**cs._empty(), "days": sorted((date(2027, 5, 31) - timedelta(days=x)).isoformat() for x in range(5, 10))}
        _check(cs.streak(far) == 0 and cs.days_away(far) == 4, "a long gap ends it, and days away are counted")
        dots = cs.week_dots(st)
        _check(len(dots) == 7 and dots[0]["today"], "this week's dots start on Monday")
    finally:
        cs._today = real
    _check(set(missions.MISSIONS) == {u["id"] for u in UNITS}, "every unit has a mission")
    _check(all(m["goal"] and m["opener"] and m["suggest"] and m["scene"] for m in missions.MISSIONS.values()), "missions are complete")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        m = cs.course_map(path=path)
        _check(len(m["units"]) == 20 and m["units"][0]["status"] == "current" and m["units"][1]["status"] == "later", "course map shows where you are")
        cs.complete_step("u1", "learn", path=path)
        cs.complete_mission("u1", path=path)
        m = cs.course_map(path=path)
        _check(m["units"][0]["steps"] == 1 and m["units"][0]["mission"], "the map tracks steps and missions")
        _check(cs.unit_payload("u3", path=path)["unit"]["number"] == 3 and cs.unit_payload("nope", path=path) is None, "any unit opens by id")
        book = cs.phrasebook(path=path)
        _check(len(book["phrases"]) == 6 and not book["words"] and book["phrases"][0]["strength"] == "new", "phrasebook lists only what's been taught")
        st = cs.load_state(path)
        _check(cs.day_summary(st)["new"] == 12, "today's summary counts what was taught")
        _check(cs.milestones({**cs._empty()}) == [], "no milestones on day one")
        st4 = cs.load_state(path)
        for p in [p["id"] for u in UNITS[:2] for p in u["phrases"]]:
            st4["cards"][f"{p}:listen"] = srs.new_card()
        _check(any(x["id"] == "phrases10" for x in cs.milestones(st4)), "ten phrases is a milestone")


def fluency_and_mine() -> None:
    from kaiwa.course import drills, my_phrases
    prices = drills.round_items("price", 1, seed=4)
    _check(len(prices) == 10 and all(p["say"].endswith("えん") and int(p["answer"]) % 100 == 0 for p in prices), "a price round is ten spoken prices")
    three = next(p for s in range(40) for p in drills.round_items("price", 1, seed=s) if p["answer"] == "300")
    _check(three["say"] == "さんびゃくえん", "300 is さんびゃく, not さんひゃく")
    times = drills.round_items("time", 2, seed=4)
    _check(all(":" in t["answer"] and t["say"].endswith("です") for t in times), "time rounds answer in h:mm")
    four = next(t for s in range(40) for t in drills.round_items("time", 1, seed=s) if t["answer"] == "4:00")
    _check(four["say"] == "よじです", "4 o'clock is よじ")
    _check(drills.available({"u8": {"learn": True}}) == {"time": True, "price": False}, "drills unlock with their units")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        row = cs.keep_my_phrase("わたしのいぬはレックスです。", "My dog is called Rex.", path=path)
        st = cs.load_state(path)
        _check(row["id"].startswith("my.") and f"{row['id']}:speak" in st["cards"] and f"{row['id']}:listen" in st["cards"], "a kept phrase gets both cards")
        _check(cs._card_kind(f"{row['id']}:speak") == ("phrase", row["id"], "speak"), "its cards are ordinary phrase cards")
        _check(cs.stats(st)["phrases_learned"] == 0 and cs.stats(st)["phrases_total"] == cs.COURSE_PHRASES, "own phrases don't distort course progress")
        _check(cs.phrasebook(path=path)["mine"][0]["jp"] == row["jp"], "the phrasebook lists it")
        _check(row["ro"] and row["ro"].isascii(), "it has romaji")
        cs.keep_my_phrase("わたしのいぬはレックスです。", "again", path=path)
        _check(len(cs.load_state(path)["mine"]) == 1, "keeping it twice keeps one")
        _check(cs.grade(f"{row['id']}:speak", correct=True, path=path)["card_id"], "it can be reviewed")
        _check(cs.remove_my_phrase(row["id"], path=path) and not cs.load_state(path)["mine"], "it can be removed")
        _check(not any(c.startswith("my.") for c in cs.load_state(path)["cards"]), "removing it removes its cards")
        _check(cs.record_best("speed", 12, path=path) == {"best": 12, "previous": 0}, "a first score is the best")
        _check(cs.record_best("speed", 9, path=path) == {"best": 12, "previous": 12}, "a lower score doesn't replace it")
    _check(my_phrases.clean_kept([{"id": "x", "jp": "a"}, {"id": "my.1", "jp": "b"}, "junk"])[0]["id"] == "my.1" and len(my_phrases.clean_kept([{"id": "x", "jp": "a"}, "junk"])) == 0, "bad saved rows are dropped")


def main() -> None:
    fluency_and_mine()
    habit_and_map()
    grammar_cards()
    sound_diff()
    word_formats()
    pacing_plans()
    kana_pictures()
    day_boundary()
    one_side_per_day()
    print("smoke_lab ok")


if __name__ == "__main__":
    main()
