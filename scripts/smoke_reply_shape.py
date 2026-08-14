from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.learner_profile import LearnerProfile
from kaiwa.persona import (
    build_tutor_system_prompt,
    governor_pitch,
    shape_lock_active,
)
from kaiwa.prefs import UserPrefs, validate_prefs_dict
from kaiwa.reply_shape import (
    analyze_reply_shape,
    has_high_load,
    reply_too_dense,
    reused_user_vocab,
)


def _check(ok: bool, label: str) -> None:
    status = "ok  " if ok else "FAIL"
    line = status + label
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    if not ok:
        raise SystemExit(f"smoke_reply_shape failed: {label}")


def main() -> None:
    packed = (
        "こんにちは!そうですね、日本語はむずかしいです。"
        "でも、ゆっくり話せばだいじょうぶですよ。うんどうした?"
    )
    extra = "日本語は難しいね。でもゆっくり話せば大丈夫だよ。"
    _check(reply_too_dense(packed), "packed hanaseba transcript is dense")
    _check(reply_too_dense(extra), "demo + ba extra-idea reply is dense")
    _check(has_high_load("ゆっくり話せばだいじょうぶですよ"), "hanaseba is high-load")
    _check(not has_high_load("ならない"), "naranai is not high-load")
    _check(not has_high_load("こんばんは"), "konbanwa is not high-load")

    _check(not reply_too_dense("こんにちは！元気？"), "konnichiwa genki is one idea")
    _check(not reply_too_dense("そうなんだ。猫好き？"), "sou-nanda neko-suki is one idea")
    _check(not reply_too_dense("元気だよ!あなたは?"), "genki da yo anata wa is not dense")

    _check(
        reused_user_vocab("猫好きです", "そうなんだ。猫好き？"),
        "reuses neko-suki from learner",
    )

    shape = analyze_reply_shape(
        reply="そうなんだ。猫好き？",
        user_text="猫好きです",
        locked=True,
        retry=False,
    )
    _check(shape["locked"] is True, "metric locked")
    _check(shape["sentence_count"] == 2, "metric sentence_count=2")
    _check(shape["conditional"] is False, "metric conditional false")
    _check(shape["open_question"] is False, "metric open_question false")
    _check(shape["reused_user_vocab"] is True, "metric reused_user_vocab")
    _check(shape["retry"] is False, "metric retry false")
    _check(shape["extra_idea"] is False, "metric extra_idea false")

    unknown = LearnerProfile(placement_completed=False)
    prefs_pre = UserPrefs(goal_level="pre_n5")
    pitch_u = governor_pitch(prefs_pre, unknown, "flowing", support_mode="normal")
    _check(pitch_u == "unknown", "unplaced pitch is unknown")
    _check(shape_lock_active(pitch_u, "normal"), "unknown locks")

    pre = LearnerProfile(
        speaking_level="pre_n5",
        comprehension_level="pre_n5",
        placement_completed=True,
    )
    pitch_pre = governor_pitch(prefs_pre, pre, "flowing", support_mode="normal")
    _check(pitch_pre == "pre_n5", "placed pre_n5 pitch")
    _check(shape_lock_active(pitch_pre, "normal"), "pre_n5 locks")

    prefs_n5 = UserPrefs(goal_level="n5")
    n5 = LearnerProfile(
        speaking_level="n5",
        comprehension_level="n5",
        placement_completed=True,
    )
    pitch_n5 = governor_pitch(prefs_n5, n5, "flowing", support_mode="normal")
    _check(pitch_n5 == "n5", "n5+normal pitch")
    _check(not shape_lock_active(pitch_n5, "normal"), "n5+normal unlocked")
    _check(shape_lock_active(pitch_n5, "simplified"), "simplified still locks")
    _check(shape_lock_active(pitch_pre, "normal", chat_pace="easy"), "easy keeps pre_n5 lock")
    _check(
        not shape_lock_active(pitch_pre, "normal", chat_pace="free"),
        "free unlocks pre_n5",
    )
    _check(
        shape_lock_active(pitch_n5, "simplified", chat_pace="easy"),
        "easy + simplified still locks",
    )
    _check(
        not shape_lock_active(pitch_n5, "simplified", chat_pace="free"),
        "free unlocks even simplified",
    )
    _check(validate_prefs_dict({}).chat_pace == "easy", "missing pref defaults easy")

    prompt = build_tutor_system_prompt(
        prefs_pre, last_user_text="猫好きです", profile=pre
    )
    _check("考えは1つ" in prompt, "locked prompt says one idea")
    _check("負荷の高い型" in prompt, "locked prompt names high-load constructions")
    _check("禁止文法" in prompt, "locked prompt is scaffold not a ban")

    free_prefs = UserPrefs(goal_level="pre_n5", chat_pace="free")
    free_prompt = build_tutor_system_prompt(
        free_prefs, last_user_text="猫好きです", profile=pre
    )
    _check("考えは1つ" not in free_prompt, "free prompt is not gym-locked")

    print("smoke_reply_shape ok")


if __name__ == "__main__":
    main()
