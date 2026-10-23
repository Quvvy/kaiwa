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
    _check(len(UNITS) == 10, "ten units")
    for unit in UNITS:
        for d in unit.get("drill", []):
            _check(0 <= d["answer"] < len(d["choices"]), f"{unit['id']} drill answer index valid")
    word_ids = [w["id"] for u in UNITS for w in u.get("words", [])]
    _check(len(word_ids) == len(set(word_ids)), "word ids are unique")


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


def srs() -> None:
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
        _check(not course_state.due_cards(st), "new cards wait until tomorrow")

        _check(course_state.unit_steps(UNITS[0]) == ["learn", "words", "grammar", "listen", "speak"],
               "unit 1 uses the full template")
        _check(course_state.unit_steps(UNITS[1]) == ["learn", "listen", "speak"], "older units keep three steps")
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

        # Pretend it's tomorrow: everything from unit 1 is due.
        real_today = course_state._today
        course_state._today = lambda: real_today() + timedelta(days=1)
        try:
            st = course_state.load_state(path)
            due = [c for c in course_state.due_cards(st, limit=100) if c["kind"] == "phrase"]
            _check(len(due) == 12, "all 12 phrase cards due the next day")
            kinds = {c["kind"] for c in course_state.due_cards(st, limit=100)}
            _check(kinds == {"phrase", "word", "kana"}, "word and kana cards come up in review")
            pairs = [due[i]["phrase"]["id"] == due[i + 1]["phrase"]["id"] for i in range(len(due) - 1)]
            _check(not any(pairs), "a phrase's two sides are never back to back")
            good = course_state.grade("u1.ohayou:listen", True, path=path)
            _check(good["box"] == 2 and good["due"] == (real_today() + timedelta(days=1 + 3)).isoformat(),
                   "good answer → box 2, due in 3 days")
            _check(course_state.grade("kana.あ:read", True, path=path)["box"] == 2, "kana cards grade")
            _check(course_state.grade("u1w.asa:mean", True, path=path)["box"] == 2, "word cards grade")
            bad = course_state.grade("u1.ohayou:speak", False, path=path)
            _check(bad["box"] == 1 and bad["lapses"] == 1, "miss → box 1 with a lapse")
            _check(course_state.streak(course_state.load_state(path)) == 2, "two days in a row")
        finally:
            course_state._today = real_today

        known = course_state.known_phrases_for_chat(path=path)
        _check(known[0]["jp"] == "おはようございます。" and len(known) == 6, "Chat sees the learned phrases")
        try:
            course_state.grade("nope:listen", True, path=path)
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


def main() -> None:
    content()
    kana_track()
    speech()
    srs()
    story_checks()
    coach_fallback()
    print("smoke_course ok")


if __name__ == "__main__":
    main()
