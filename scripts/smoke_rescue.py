from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.learner_profile import LearnerProfile, ProfileStats, apply_chat_signals
from kaiwa.persona import rescue_rewrite_block
from kaiwa.rescue import apply_rescue_signals, next_rescue_step


def _check(ok: bool, label: str) -> None:
    status = "ok  " if ok else "FAIL"
    line = status + label
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    if not ok:
        raise SystemExit(f"smoke_rescue failed: {label}")


def main() -> None:
    packed = (
        "こんにちは!そうですね、日本語はむずかしいです。"
        "でも、ゆっくり話せばだいじょうぶですよ。うんどうした?"
    )
    _check(next_rescue_step(packed) == "shorter", "packed → shorter")
    _check(
        next_rescue_step("日本語、難しいね。") == "yes_no",
        "short statement → yes_no",
    )
    _check(next_rescue_step("猫好き？") == "ab", "short yes/no ？ → ab")
    _check(
        next_rescue_step("コーヒー、それともお茶？") == "ab",
        "soretomo → ab",
    )

    profile = LearnerProfile(
        speaking_level="n5",
        comprehension_level="n5",
        placement_completed=True,
        stats=ProfileStats(chat_turns=12, struggle_streak=0, flow_streak=4),
    )
    turns_before = profile.stats.chat_turns
    apply_rescue_signals(profile)
    _check(profile.stats.chat_turns == turns_before, "rescue does not increment chat_turns")
    _check(profile.stats.struggle_streak == 2, "streak 0 → 2")
    _check(profile.stats.flow_streak == 0, "flow_streak cleared")

    apply_rescue_signals(profile)
    _check(profile.stats.struggle_streak == 3, "streak 2 → 3")
    _check(profile.speaking_level == "pre_n5", "level nudge at 3")
    _check(profile.comprehension_level == "pre_n5", "comprehension nudge at 3")

    spoken = LearnerProfile(
        placement_completed=True,
        stats=ProfileStats(chat_turns=3, struggle_streak=2),
    )
    apply_chat_signals(spoken, "flowing", "猫が好きです")
    _check(spoken.stats.struggle_streak == 1, "later flowing turn decays streak")

    block = rescue_rewrite_block("猫好き？", "ab")
    _check("[rescue]" in block, "rescue block tagged")
    _check("わからない" in block, "rescue block forbids fake utterance")
    _check("猫好き？" in block, "original line in rescue block")


if __name__ == "__main__":
    main()
