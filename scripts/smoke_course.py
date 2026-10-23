"""Beginner course: content integrity, speech checks, spaced repetition. No network."""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("KAIWA_DATA_DIR", tempfile.mkdtemp(prefix="kaiwa-course-smoke-"))

from kaiwa.course import srs  # noqa: E402
from kaiwa.course import state as course_state  # noqa: E402
from kaiwa.course.coach import judge  # noqa: E402
from kaiwa.course.speech_check import check_phrase, matches_any, normalize  # noqa: E402
from kaiwa.course.units import ROMAJI, UNITS  # noqa: E402


def _check(ok: bool, label: str) -> None:
    line = ("ok  " if ok else "FAIL") + label
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
    if not ok:
        raise SystemExit(f"smoke_course failed: {label}")


def content() -> None:
    ids = [p["id"] for u in UNITS for p in u["phrases"]]
    _check(len(ids) == len(set(ids)), "phrase ids are unique")
    _check(set(ids) == set(ROMAJI), "every phrase has hand-written romaji")
    for unit in UNITS:
        for p in unit["phrases"]:
            r = check_phrase(p["jp"], p["jp"], p.get("accept"))
            if r.band != "good":
                _check(False, f"{p['id']} does not match itself")
        for q in unit["questions"]:
            _check(0 <= q["answer"] < len(q["choices"]), f"{unit['id']} question answer index valid")
        for i, task in enumerate(unit["speak"]):
            # Every variant of the model answer (with a sample filler) must pass its own patterns.
            for variant in task["hint"].split("／"):
                sample = variant.replace("＿", "ねこ")
                _check(matches_any(task["expect"], sample), f"{unit['id']} speak {i}: hint 「{sample}」 passes")
    _check(len(UNITS) == 20, "twenty units")
    for unit in UNITS:
        for d in unit.get("drill", []):
            _check(0 <= d["answer"] < len(d["choices"]), f"{unit['id']} drill answer index valid")
    word_ids = [w["id"] for u in UNITS for w in u.get("words", [])]
    _check(len(word_ids) == len(set(word_ids)), "word ids are unique")
    word_jp = [w["jp"] for u in UNITS for w in u.get("words", [])]
    _check(len(word_jp) == len(set(word_jp)), "no word is taught twice")
    for unit in UNITS:
        for g in unit.get("grammar", []):
            _check(bool(g.get("rule")) and len(g["examples"]) >= 3, f"{g['id']} has a rule and examples")
        for d in unit.get("drill", []):
            _check(len(set(d["choices"])) == len(d["choices"]), f"{unit['id']} drill choices differ")


def kana_track() -> None:
    from kaiwa.course.kana import KANA_LESSONS, chars_through

    for i, lesson in enumerate(KANA_LESSONS):
        known = chars_through(i)
        for w in lesson["words"]:
            missing = [c for c in w["jp"] if c not in known]
            _check(not missing, f"{lesson['id']} word {w['jp']} uses only taught kana")
            _check(w["ro"] not in w.get("confuse", []), f"{lesson['id']} {w['jp']}: near misses differ from the answer")
    chars = [ch for lesson in KANA_LESSONS for ch, _ in lesson["kana"]]
    _check(len(chars) == len(set(chars)), "each kana is taught once")


def speech() -> None:
    _check(normalize("4時です") == "よじです", "4時 reads よじ")
    _check(normalize("450円") == "よんひゃくごじゅうえん", "prices read as kana")
    _check(check_phrase("ねこがすきです。", "猫が好きです").band == "good", "kanji transcript of the phrase is good")
    _check(check_phrase("ねこがすきです。", "猫を好きです").band == "close", "を for が is only close")
    _check(check_phrase("おはようございます。", "こんばんは").band == "off", "different phrase is off")
    _check(matches_any(["わたしは*です"], "私はイーライです"), "name slot matches any name")
    _check(matches_any(["はい*"], "はい。"), "はい* matches bare はい")
    _check(not matches_any(["*がすきです"], "寿司を好きです"), "*がすきです rejects を")


def spaced_review() -> None:
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "course_state.json"
        payload = course_state.today_payload(path=path)
        _check(payload["unit"]["id"] == "u1" and payload["review_total"] == 0, "fresh learner starts at unit 1, nothing due")
        _check(payload["unit"]["phrases"][0]["ro"] == "ohayou gozaimasu.", "public phrases carry romaji")

        course_state.complete_step("u1", "learn", path=path)
        st = course_state.load_state(path)
        _check(len(st["cards"]) == 12, "learning unit 1 schedules 6 phrases × 2 skills")
        _check(course_state.stats(st)["phrases_learned"] == 6, "6 phrases learned")
        _check(course_state.stats(st)["streak"] == 1, "studying today starts a streak")
        _check(not course_state.due_cards(st), "new cards aren't reviews yet")
        recap = course_state.recap_cards(st)
        _check(len(recap) == 12, "new cards are today's recap (their second look)")

        _check(course_state.unit_steps(UNITS[0]) == ["learn", "words", "grammar", "listen", "speak"],
               "unit 1 uses the full template")
        _check(all(len(course_state.unit_steps(u)) == 5 for u in UNITS), "every unit uses the full template")
        for step in ("listen", "speak"):
            course_state.complete_step("u1", step, path=path)
        st = course_state.load_state(path)
        _check(not st["units"]["u1"].get("done_at") and course_state.next_unit(st)["id"] == "u1",
               "unit 1 isn't done until words and grammar are")
        for step in ("words", "grammar"):
            course_state.complete_step("u1", step, path=path)
        st = course_state.load_state(path)
        _check(bool(st["units"]["u1"].get("done_at")), "all five steps finish the unit")
        _check(len(st["cards"]) == 12 + len(UNITS[0]["words"]), "words step schedules a card per word")
        course_state.complete_kana("h1", path=path)
        st = course_state.load_state(path)
        _check("kana.あ:read" in st["cards"], "a kana lesson schedules its characters")
        payload = course_state.today_payload(path=path)
        _check(payload["kana"]["id"] == "h2" and payload["kana_done_today"], "next kana lesson is h2, h1 done today")
        _check(set("あいうえお") <= set(payload["kana_known"]), "known kana feed romaji fading")
        _check(course_state.next_unit(st)["id"] == "u2", "next unit is u2")

        # Learning steps: a new card comes back within minutes, two clean answers graduate it.
        first = course_state.grade("u1.ohayou:listen", correct=True, ms=3000, path=path)
        _check(first["again_soon"], "a new card comes back within the session")
        second = course_state.grade("u1.ohayou:listen", correct=True, ms=3000, path=path)
        _check(not srs.is_learning(second) and second["due"] > course_state._today().isoformat(),
               "two clean answers graduate it to a review days away")
        miss = course_state.grade("u1.ohayou:speak", correct=False, path=path)
        _check(miss["rating"] == srs.AGAIN and miss["again_soon"], "a miss is Again and comes back soon")
        after = course_state.load_state(path)
        _check(after["reviewed"] == {}, "learning steps don't spend the review budget")
        recap_kinds = {c["kind"]: c["format"] for c in course_state.recap_cards(after)}
        _check(recap_kinds.get("word") == "choice" and recap_kinds.get("kana") == "choice", "new words and kana are multiple choice")

        # Old Leitner cards convert without losing progress.
        conv = srs.from_legacy({"box": 4, "due": "2026-01-01", "reps": 5, "lapses": 1})
        _check(not srs.is_learning(conv) and srs.stability(conv) == 14 and conv["reps"] == 5, "a box-4 card becomes a 14-day memory")
        _check(srs.known(conv), "a reviewed card is answered by producing it")

        # Pretend every unit 1 card is a review due today (as converted Leitner cards would be).
        st = course_state.load_state(path)
        today_iso = course_state._today().isoformat()
        for cid in list(st["cards"]):
            st["cards"][cid] = srs.from_legacy({"box": 1, "due": today_iso, "reps": 1})
        st["reviewed"] = {}
        course_state.save_state(st, path)
        st = course_state.load_state(path)
        due = [c for c in course_state.due_cards(st, limit=100) if c["kind"] == "phrase"]
        _check(len(due) == 12, "all 12 phrase cards due")
        kinds = {c["kind"] for c in course_state.due_cards(st, limit=100)}
        _check(kinds == {"phrase", "word", "kana"}, "word and kana cards come up in review")
        pairs = [due[i]["phrase"]["id"] == due[i + 1]["phrase"]["id"] for i in range(len(due) - 1)]
        _check(not any(pairs), "a phrase's two sides are never back to back")
        todays = course_state.todays_reviews(st)
        cost = sum(course_state.card_cost(c["kind"], c["skill"]) for c in todays)
        _check(0 < cost <= course_state.DAILY_REVIEW_BUDGET, "today's reviews fit the daily budget")
        _check(len(todays) < len(course_state.due_cards(st, limit=100)), "the rest of the backlog waits")
        course_state.grade("kana.あ:read", correct=True, ms=2000, path=path)
        course_state.grade("u1.ohayou:listen", correct=True, ms=2000, path=path)
        after = course_state.load_state(path)
        _check(after["reviewed"][today_iso] == 3, "reviews spend today's budget (kana 1 + listen 2)")
        _check(course_state.streak(after) == 1, "studying today keeps the streak")
        known = course_state.known_phrases_for_chat(path=path)
        _check(known[0]["jp"] == "おはようございます。" and len(known) == 6, "Chat sees the learned phrases")
        try:
            course_state.grade("nope:listen", correct=True, path=path)
            _check(False, "unknown card rejected")
        except KeyError:
            _check(True, "unknown card rejected")


def coach_fallback() -> None:
    from kaiwa.config import get_settings

    settings = get_settings()
    object.__setattr__(settings, "deepseek_api_key", "")
    task = UNITS[3]["speak"][0]
    good = judge(settings, task=task, heard="ラーメンが好きです")
    _check(good["verdict"] == "great" and not good["coached"], "offline fallback passes a pattern match")
    bad = judge(settings, task=task, heard="hello")
    _check(bad["verdict"] == "retry" and bad["model"] == task["hint"], "offline fallback offers the model answer")


def story_checks() -> None:
    from kaiwa.course.stories import _shuffled, _valid

    good = {
        "lines": [{"who": "a", "jp": "こんばんは。"}, {"who": "b", "jp": "こんばんは。"}, {"who": "a", "jp": "じゃあ、また。"}],
        "questions": [{"q": "When?", "choices": ["Morning", "Evening", "Noon"], "answer": 1}],
    }
    _check(_valid(good), "well-formed story passes")
    _check(not _valid({**good, "lines": good["lines"][:2]}), "too-short story rejected")
    _check(not _valid({**good, "questions": [{"q": "x", "choices": ["a", "b"], "answer": 5}]}), "bad answer index rejected")
    _check(not _valid({**good, "lines": [{"who": "c", "jp": "x"}] * 4}), "unknown speaker rejected")
    for _ in range(20):
        q = _shuffled({"q": "When?", "choices": ["Right", "Wrong 1", "Wrong 2"], "answer": 0})
        if q["choices"][q["answer"]] != "Right":
            _check(False, "shuffle keeps the right answer")
    _check(True, "shuffle keeps the right answer")


def sentence_checks() -> None:
    from kaiwa.course.sentences import contains_word, only_known

    vocab = ["あさ", "いま", "せんせい", "ともだち", "おはようございます。", "おはようございます"]
    _check(only_known("せんせい、おはようございます。", vocab), "known pieces pass")
    _check(only_known("ユキさんはともだちです。", vocab), "katakana names and particles pass")
    _check(not only_known("あさはさむいです。", vocab), "an untaught word (さむい) is rejected")
    _check(not contains_word("おはようございます。", "いま", vocab), "いま inside ございます doesn't count")
    _check(contains_word("いまはあさです。", "いま", vocab), "いま on its own counts")


def auto_grades() -> None:
    usual = [3000] * 10

    def r(**kw):
        args = {"correct": True, "ms": 3000, "helped": False, "guessed": False, "band": "", "reps": 5, "times": usual}
        args.update(kw)
        return srs.rating_for(**args)

    _check(r(correct=False) == srs.AGAIN, "wrong → Again")
    _check(r(band="off") == srs.AGAIN, "speech check off → Again")
    _check(r(band="close") == srs.HARD, "speech check close → Hard")
    _check(r(guessed=True) == srs.HARD, "\"I guessed\" → Hard")
    _check(r(helped=True) == srs.HARD, "needed help → Hard")
    _check(r(ms=7000) == srs.HARD, "much slower than usual → Hard")
    _check(r(ms=3000) == srs.GOOD, "usual speed → Good")
    _check(r(ms=1500) == srs.EASY, "much faster than usual, with a track record → Easy")
    _check(r(ms=1500, reps=1) == srs.GOOD, "fast on a young card is only Good")
    _check(r(ms=40_000) == srs.GOOD, "a very long pause (looked away) doesn't count as slow")
    _check(r(ms=9000, times=[3000] * 3) == srs.GOOD, "speed is ignored until there's a baseline")


def leeches_and_retention() -> None:
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "course_state.json"
        course_state.complete_step("u1", "words", path=path)
        cid = "u1w.asa:mean"
        st = course_state.load_state(path)
        st["cards"][cid] = srs.from_legacy({"box": 3, "due": "2000-01-01", "reps": 6, "lapses": 3})
        course_state.save_state(st, path)
        _check(not course_state.is_leech(course_state.load_state(path)["cards"][cid]), "three lapses: not a leech yet")
        course_state.grade(cid, correct=False, path=path)  # a fourth lapse on a learned card
        card = course_state.load_state(path)["cards"][cid]
        _check(course_state.is_leech(card), "a fourth lapse makes it a leech")
        _check(course_state.answer_format("word", "mean", card) == "choice", "a weak leech goes back to multiple choice")
        course_state.save_hook(cid, {"hook": "Asa: a sunrise.", "parts": []}, path=path)
        course_state.grade(cid, correct=True, ms=2000, path=path)
        _check(course_state.load_state(path)["cards"][cid].get("hook", {}).get("hook") == "Asa: a sunrise.",
               "a saved hook survives the next review")

        st = course_state.load_state(path)
        _check(course_state.retention(st) is None, "no retention figure until there are enough reviews")
        today = course_state._today().isoformat()
        st["log"] = [{"d": today, "k": "word", "ok": i % 10 != 0} for i in range(30)] + [{"d": "2000-01-01", "k": "word", "ok": False}] * 50
        r = course_state.retention(st)
        _check(r is not None and r["percent"] == 90 and r["reviews"] == 30, "retention: 27 of 30 recent reviews = 90% (old ones ignored)")
        _check(r["by_kind"].get("words") == 90 and r["target"] == 90 and r["leeches"] == 1, "per-kind figures, the target, and the leech count")
        # Learning-step answers don't count toward retention.
        before = len(course_state.load_state(path)["log"])
        course_state.grade("u1w.hiru:mean", correct=False, path=path)  # still a new card
        _check(len(course_state.load_state(path)["log"]) == before, "learning-step misses don't count against retention")


def undo_and_regrade() -> None:
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "course_state.json"
        cid = "u1w.asa:mean"
        st = course_state.load_state(path)
        st["cards"][cid] = srs.from_legacy({"box": 3, "due": course_state._today().isoformat(), "reps": 3})
        course_state.save_state(st, path)
        before = course_state.load_state(path)
        r = course_state.grade(cid, correct=True, ms=2500, fmt="word:produce:type", path=path)
        _check(set(r["intervals"]) == {1, 2, 3, 4} and r["intervals"][1] < r["intervals"][3] < r["intervals"][4],
               "a grade reports the interval each button would give")
        _check(not r["learning"] and r["seconds"] > 86400, "a Good review is days away")
        mid = course_state.load_state(path)
        _check(mid["reviewed"] and mid["log"] and mid["daily"], "the answer was counted")
        u = course_state.undo(path=path)
        after = course_state.load_state(path)
        _check(u and u["card"]["card_id"] == cid, "undo hands back the card to ask again")
        _check(after["cards"][cid] == before["cards"][cid], "undo restores the card exactly")
        _check(not after["log"] and after["reviewed"].get(course_state._today().isoformat(), 0) == 0,
               "undo removes the retention row and refunds the review budget")
        _check(course_state.undo(path=path) is None, "nothing left to undo")

        course_state.grade(cid, correct=True, ms=2500, path=path)
        again = course_state.regrade(cid, srs.AGAIN, path=path)
        _check(again["rating"] == srs.AGAIN and again["learning"], "choosing Again re-applies the answer as Again")
        st = course_state.load_state(path)
        _check(len(st["log"]) == 1 and st["log"][0]["ok"] is False, "the regrade replaced the first log row")
        _check(st["overrides"][-1]["auto"] == srs.GOOD and st["overrides"][-1]["chosen"] == srs.AGAIN,
               "the correction is kept for tuning the auto-grader")

        stats = course_state.course_stats(path=path)
        _check(len(stats["forecast"]) == 30 and len(stats["activity"]) == 112 and len(stats["weeks"]) == 8,
               "stats: 30-day forecast, 16-week calendar, 8-week retention")
        _check(stats["stages"]["Words"]["learning"] == 1 and stats["today"]["answers"] == 1,
               "stats count the relearning card and today's answer")


def grader_tuning() -> None:
    import random

    from kaiwa.course import grader

    rng = random.Random(7)

    def learner(n, hard_at, fmt="word:produce:type", close_good=False):
        """Rows from someone who calls anything over `hard_at`× their usual time Hard."""
        rows = []
        for _ in range(n):
            ratio = round(rng.uniform(0.5, 3.0), 2)
            auto = srs.HARD if ratio > 2.0 else srs.GOOD
            final = srs.HARD if ratio > hard_at else srs.GOOD
            rows.append({"fmt": fmt, "ratio": ratio, "auto": auto, "final": final, "correct": True,
                         "close": False, "helped": False, "guessed": False, "seasoned": True})
        for _ in range(8):  # "close" speech checks the learner keeps at Good (or not)
            rows.append({"fmt": fmt, "ratio": None, "auto": srs.HARD, "final": srs.GOOD if close_good else srs.HARD,
                         "correct": True, "close": True, "helped": False, "guessed": False, "seasoned": True})
        return rows

    _check(not grader.tune(learner(10, 1.5))["tuned"], "too few answers: defaults stay")
    strict = grader.tune(learner(120, 1.5))
    _check(strict["tuned"] and 1.4 <= strict["hard"] < 1.9, f"a stricter learner pulls Hard down (got {strict['hard']})")
    _check(strict["close"] == srs.HARD, "close stays Hard when the learner agrees")
    lenient = grader.tune(learner(120, 2.8, close_good=True))
    _check(lenient["hard"] > 2.2, f"a lenient learner pushes Hard up (got {lenient['hard']})")
    _check(lenient["close"] == srs.GOOD, "close becomes Good when the learner keeps changing it to Good")
    _check(HARD_RANGE_OK(lenient["hard"]), "thresholds stay in bounds")
    mixed = grader.tune(learner(60, 1.5, fmt="kana:produce:type") + learner(60, 2.8, fmt="word:produce:say"))
    _check(mixed["formats"]["kana:produce:type"]["hard"] < mixed["formats"]["word:produce:say"]["hard"],
           "each answer format gets its own threshold once it has enough answers")
    used = grader.for_format(strict, "word:produce:type")
    _check(srs.rating_for(correct=True, ms=1700, helped=False, guessed=False, band="", reps=5,
                          times=[1000] * 10, **used) == srs.HARD,
           "the tuned threshold changes the grade (1.7× usual is Hard for this learner)")
    _check("Default settings" in grader.describe(None)["basis"], "stats explain the defaults")

    # Through the real path: corrections are logged, and a change refits right away.
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "course_state.json"
        st = course_state.load_state(path)
        st["grades"] = learner(60, 1.5)
        st["cards"]["u1w.asa:mean"] = srs.from_legacy({"box": 3, "due": course_state._today().isoformat(), "reps": 4})
        course_state.save_state(st, path)
        course_state.grade("u1w.asa:mean", correct=True, ms=2000, path=path)
        course_state.regrade("u1w.asa:mean", srs.HARD, path=path)
        st = course_state.load_state(path)
        _check(st["grades"][-1]["final"] == srs.HARD and st["grades"][-1]["auto"] == srs.GOOD, "a change is logged as a correction")
        _check(st["grader"] and st["grader"]["tuned"], "a grade change refits the grader")
        _check(course_state.course_stats(path=path)["grading"]["tuned"], "the stats page reports the tuned grader")


def HARD_RANGE_OK(x):
    from kaiwa.course import grader

    return grader.HARD_RANGE[0] <= x <= grader.HARD_RANGE[1]


def pacing() -> None:
    real_today = course_state._today
    day = [real_today()]
    course_state._today = lambda: day[0]

    def plan(path):
        return course_state.plan_today(course_state.load_state(path))

    try:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "course_state.json"
            _check(plan(path)["plan"] == ["kana", "learn", "words", "recap"], "day 1: a short kana lesson fits beside the unit's day one")
            course_state.complete_kana("h1", path=path)
            for s in ("learn", "words"):
                course_state.complete_step("u1", s, path=path)
            p1 = plan(path)
            _check(p1["plan"] == ["recap"] and p1["day_two_tomorrow"], "after day one: only the recap; day two waits")

            day[0] = real_today() + timedelta(days=1)
            p2 = plan(path)["plan"]
            _check(p2 == ["kana", "grammar", "listen", "speak", "recap"], "day 2: kana, day two, then the recap")
            for s in ("grammar", "listen", "speak"):
                course_state.complete_step("u1", s, path=path)
            for lid in ("h2", "h3", "h4", "h5", "h6", "h7", "h8", "h9", "h10"):
                course_state.complete_kana(lid, path=path)  # jump to h11: fifteen characters

            day[0] = real_today() + timedelta(days=2)
            st = course_state.load_state(path)
            st["reviewed"] = {}
            for cid in list(st["cards"]):
                # Nothing due and nothing learning, so only the new-item rule decides.
                st["cards"][cid] = srs.from_legacy({"box": 3, "due": "2099-01-01", "reps": 2})
            course_state.save_state(st, path)
            p3 = plan(path)["plan"]
            _check(p3 in (["kana", "recap"], ["learn", "words", "recap"]), "a long kana lesson and a unit's day one alternate")

            st = course_state.load_state(path)
            for cid in list(st["cards"]):
                st["cards"][cid] = srs.from_legacy({"box": 1, "due": "2000-01-01", "reps": 1})
            course_state.save_state(st, path)
            p4 = plan(path)
            _check(p4["catching_up"] and p4["plan"] == ["review"], "a big backlog means a reviews-only day")
            cost = sum(course_state.card_cost(c["kind"], c["skill"]) for c in course_state.todays_reviews(course_state.load_state(path)))
            _check(course_state.DAILY_REVIEW_BUDGET < cost <= course_state.DAILY_REVIEW_BUDGET * 2, "catch-up days get a bigger review budget")
    finally:
        course_state._today = real_today


def main() -> None:
    content()
    kana_track()
    speech()
    spaced_review()
    auto_grades()
    leeches_and_retention()
    undo_and_regrade()
    grader_tuning()
    pacing()
    story_checks()
    sentence_checks()
    coach_fallback()
    print("smoke_course ok")


if __name__ == "__main__":
    main()
