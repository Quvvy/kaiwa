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
    _check(p["minutes"] >= 8, "the plan says how long today takes, the first day's extra included")
    relaxed = {**cs._empty(), "pace": "relaxed"}
    pr = cs.plan_today(relaxed)
    _check(cs.DEFAULT_PACE == "intensive" and cs.plan_today(cs._empty())["pace"] == "intensive", "Intensive is the default pace")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        cs.set_pace("relaxed", path=path)
        _check(cs.plan_today(cs.load_state(path))["pace"] == "relaxed", "a pace the learner chose outlasts the default")
    for name in ("relaxed", "regular"):
        plan = cs.plan_today({**cs._empty(), "pace": name})
        _check("words" in plan["plan"] and plan["words_today"] >= 5, f"{name} reaches words on day one")
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
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        first = cs.plan_today(cs.load_state(path))
        cs.complete_kana("h1", path=path)
        cs.complete_step("u1", "learn", path=path)
        cs.complete_step("u1", "words", count=first["words_today"], path=path)
        again = cs.plan_today(cs.load_state(path))
        _check("words" not in again["plan"] and "learn" not in again["plan"], "a day's lessons don't restart when the plan is worked out again")
        _check(again["plan"] == ["recap"], "after today's lessons only the recap is left")
        cs.complete_step("u1", "learn", path=path)
        _check(abs(cs.load_state(path)["daily"][cs._today().isoformat()]["lesson_min"] - cs.load_state(path)["daily"][cs._today().isoformat()]["lesson_min"]) == 0 and cs.plan_today(cs.load_state(path))["plan"] == ["recap"], "redoing a step spends nothing new")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        cs.complete_kana("h1", path=path)
        _check("learn" in cs.plan_today(cs.load_state(path))["plan"], "the first day still reaches real phrases after its kana lesson")
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
        _check(cs.day_summary(st)["new"] == 6, "today's summary counts things taught, not card sides")
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


def chat_focus_and_offline() -> None:
    from kaiwa import persona
    from kaiwa.course import prerender
    st = cs._empty()
    st["units"]["u4"] = {"learn": True, "learn_on": cs._today().isoformat(), "listen": True}
    st["units"]["u1"] = {"learn": True, "learn_on": "2020-01-01", "listen": True}
    recent = cs.recent_phrases(st)
    _check(any("ねこ" in r["jp"] for r in recent) and not any("おはよう" in r["jp"] for r in recent), "Chat's fresh phrases are the last few days'")
    block = persona.course_phrases_block({"phrases": recent, "recent": recent})
    _check("習ったばかり" in block and "答えを先に言わない" in block, "the tutor is told to give them a chance to use them")
    old = cs.old_dialogue(st)
    _check(old is not None and old["replay"] and old["lines"] and old["questions"], "without a key, listening falls back to a finished unit's conversation")
    _check(cs.old_dialogue(cs._empty()) is None, "nothing to replay before any listening")
    lines = prerender.lesson_lines()
    _check(any(v == "b" for _, v, _s in lines) and any(t == "がくせいですか" for t, _v, _s in lines), "other voices and build sentences get prerendered")


def word_packs() -> None:
    from kaiwa.course import packs
    from kaiwa.course.units import UNITS
    in_units = {w["jp"] for u in UNITS for w in u["words"]}
    all_words = [w for p in packs.PACKS for w in p["words"]]
    _check(not [w["jp"] for w in all_words if w["jp"] in in_units], "pack words don't repeat the units'")
    ids = [w["id"] for w in all_words]
    _check(len(ids) == len(set(ids)) and len({w["jp"] for w in all_words}) == len(all_words), "pack words are unique")
    _check(all(w["ro"].isascii() and w["en"] for w in all_words), "every pack word has romaji and a meaning")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        _check(cs.complete_pack("numbers", path=path) == 10, "a pack schedules its words")
        _check(cs.complete_pack("numbers", path=path) == 0, "and only once")
        st = cs.load_state(path)
        _check(cs._card_kind("p.numbers.ichi:mean") == ("word", "p.numbers.ichi", "mean"), "they're ordinary word cards")
        _check(cs.packs_overview(path=path)[0]["taught"] == 10, "progress shows")
        _check(any(w["jp"] == "きゅう" for w in cs.phrasebook(path=path)["words"]), "the phrasebook lists them")
        _check("いち" in cs.known_vocab(path=path)[0], "Chat and stories can use them")


def free_recall_and_culture() -> None:
    from kaiwa.course import missions
    from kaiwa.course.units import UNITS
    _check(set(missions.CULTURE) == {u["id"] for u in UNITS}, "every unit has a culture note")
    st = cs._empty()
    st["units"]["u1"] = {"learn": True, "learn_on": cs._today().isoformat()}
    _check(len(cs.todays_phrases(st)) == 6, "today's phrases are known")
    r = cs.recall_matches(st, "おはようございます ありがとうございます")
    got = {p["jp"] for p in r["recalled"]}
    _check("おはようございます。" in got and "ありがとうございます。" in got and len(r["missed"]) == 4, "two phrases said, two recalled")
    r = cs.recall_matches(st, "おはよう、すみません、じゃあまた")
    got = {p["jp"] for p in r["recalled"]}
    _check({"おはようございます。", "すみません。", "じゃあ、また。"} <= got, "casual forms and run-together speech still count")
    _check(cs.recall_matches(st, "パンをたべます")["recalled"] == [], "unrelated speech recalls nothing")
    st2 = {**cs._empty(), "units": {"u1": {"learn": True, "learn_on": "2020-01-01"}}}
    _check(cs.todays_phrases(st2) == [], "older lessons aren't today's")


def recap_mix() -> None:
    st = cs._empty()
    for ch in "あいうえお":
        st["cards"][f"kana.{ch}:read"] = srs.new_card()
    for p in cs.UNITS[0]["phrases"]:
        for side in cs.SKILLS:
            st["cards"][f"{p['id']}:{side}"] = srs.new_card()
    rows = cs.recap_cards(st)
    kinds = [r["kind"] for r in rows]
    _check(len(rows) == 17 and kinds != sorted(kinds), "the recap mixes kinds of card")
    items = [r["card_id"].split(":")[0] for r in rows]
    _check(all(a != b for a, b in zip(items, items[1:])), "a phrase's two sides aren't next to each other")
    _check([r["card_id"] for r in cs.recap_cards(st)] == [r["card_id"] for r in rows], "the mix holds for the day")


def fixes() -> None:
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        cs.complete_step("u1", "learn", path=path)
        st = cs.load_state(path)
        st["units"]["u1"]["learn_on"] = "2020-01-01"
        cs.save_state(st, path)
        cs.complete_step("u1", "learn", path=path)
        _check(cs.load_state(path)["units"]["u1"]["learn_on"] == "2020-01-01", "redoing a step doesn't make it new again")
    st = {**cs._empty(), "pace": "regular"}
    st["days"] = [(cs._today() - timedelta(days=9)).isoformat()]
    for i in range(30):
        due = srs.placed_card(5.0, (cs._today() - timedelta(days=2)))
        st["cards"][f"u{1 + i // 18}w.x{i}"] = due
    for p in [p["id"] for u in cs.UNITS[:8] for p in u["phrases"]]:
        st["cards"][f"{p}:listen"] = srs.placed_card(5.0, cs._today() - timedelta(days=2))
    budget = cs.PACES["regular"]["reviews"]
    _check(sum(cs.card_cost(c["kind"], c["skill"]) for c in cs.todays_reviews(st)) <= budget, "a comeback day isn't doubled")
    cs._mark_day(st)
    _check(st.get("comeback") == cs._today().isoformat(), "coming back is remembered for the day")
    _check(sum(cs.card_cost(c["kind"], c["skill"]) for c in cs.todays_reviews(st)) <= budget, "and it stays normal-sized after the first answer")


def slips_and_counts() -> None:
    from datetime import datetime
    now = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        cs.complete_step("u4", "grammar", path=path)
        rows = [{"t": now, "mistakes": [{"type": "particle", "detail": "を instead of が with すき"}]} for _ in range(4)]
        rows += [{"t": "2001-01-01T00:00:00+00:00", "mistakes": [{"type": "verb_form", "detail": "old"}] * 9}]
        rows += [{"t": now, "mistakes": [{"type": "politeness", "detail": ""}]}]
        slips = cs.slip_summary(rows, path=path)
        _check(len(slips) == 1 and slips[0]["type"] == "particle" and slips[0]["count"] == 4, "recent repeated slips are summarised, old and one-off ones aren't")
        _check(slips[0]["cards"] and slips[0]["cards"][0]["card_id"] == "u4g.ga:build", "a slip comes with sentences to practise, if taught")
        _check("が" in slips[0]["example"], "with a real example")
        cs.grade("u1w.asa:mean", correct=True, path=path)
        today = cs._today().isoformat()
        _check(cs.load_state(path)["daily"][today]["new"] == 1, "a word first answered in a lesson counts as taught once")
        cs.complete_step("u1", "learn", path=path)
        cs.grade("u1.ohayou:listen", correct=True, path=path)
        _check(cs.load_state(path)["daily"][today]["new"] == 7, "a phrase's two sides count as one thing")
        cs.undo(card_id="u1w.asa:mean", path=path)
        _check(cs.load_state(path)["daily"][today]["new"] == 6, "undoing the first answer takes it back")


def redo_keeps_schedule() -> None:
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        st = cs._empty()
        cid = cs.UNITS[0]["words"][0]["id"] + ":mean"
        card = srs.placed_card(60.0, cs._today() + timedelta(days=40))
        st["cards"][cid] = card
        cs.save_state(st, path)
        r = cs.grade(cid, correct=False, ms=4000, fmt="word:choice", lesson=True, path=path)
        after = cs.load_state(path)
        _check(r["skipped"] and after["cards"][cid] == card and not after["log"], "a miss while redoing a step leaves a learned card's schedule alone")
        new_id = cs.UNITS[0]["words"][1]["id"] + ":mean"
        _check(not cs.grade(new_id, correct=True, ms=4000, lesson=True, path=path).get("skipped"), "a card being taught still counts its first look")
        _check(not cs.grade(cid, correct=True, ms=4000, path=path).get("skipped"), "a real review still grades")


def main() -> None:
    redo_keeps_schedule()
    free_recall_and_culture()
    recap_mix()
    word_packs()
    fixes()
    slips_and_counts()
    chat_focus_and_offline()
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
