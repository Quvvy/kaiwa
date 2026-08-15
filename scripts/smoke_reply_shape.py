from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.learner_memory import (
    LearnerMemory,
    admit_preferred_name,
    merge_extract_result,
)
from kaiwa.learner_profile import LearnerProfile
from kaiwa.persona import (
    PROMPT_REVISION,
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
    _check("はい／いいえ" not in prompt, "locked Easy is not a yes/no survey")
    _check("次の番が続く" in prompt, "locked Easy leaves next-turn affordance")
    _check("開き質問" in prompt, "locked prompt bans open narrative questions")

    free_prefs = UserPrefs(goal_level="pre_n5", chat_pace="free")
    free_prompt = build_tutor_system_prompt(
        free_prefs, last_user_text="猫好きです", profile=pre
    )
    _check("考えは1つ" not in free_prompt, "free prompt is not gym-locked")

    _check(PROMPT_REVISION == 4, "prompt revision is 4")
    empty_prompt = build_tutor_system_prompt(prefs_pre, profile=pre)
    _check("名前・身元の固定ルール" in empty_prompt, "identity names block present")
    _check("自分は「会話（Kaiwa / カイワ）」" in empty_prompt, "self name is Kaiwa")
    _check("学習者の名前は未設定" in empty_prompt, "empty name uses あなた")
    _check("身元を推測・交換しない" in empty_prompt, "no identity swap")
    _check("名前・身元は「会話を続ける」より強い" in empty_prompt, "identity beats keep-chatting")

    named = LearnerMemory()
    named.comfort.preferred_name = "Eli / イーライ"
    named_prompt = build_tutor_system_prompt(prefs_pre, profile=pre, memory=named)
    _check("学習者の名前は「Eli / イーライ」" in named_prompt, "stored name interpolated")
    _check("Kyla" in named_prompt and "STT誤認識" in named_prompt, "Kyla is STT of Kaiwa")

    kyla_mem = LearnerMemory()
    kyla_mem.comfort.preferred_name = "Kyla"
    kyla_prompt = build_tutor_system_prompt(prefs_pre, profile=pre, memory=kyla_mem)
    _check("学習者の名前は「Kyla」" in kyla_prompt, "Kyla as stored learner name")
    _check("STT誤認識" not in kyla_prompt, "stored Kyla is not treated as STT error")

    mem = LearnerMemory()
    admit_preferred_name(
        mem, "Kyla", "explicit_self_intro", user_turns=["私はKylaです"]
    )
    _check(mem.comfort.preferred_name == "", "extract rejects Kyla STT alias")
    admit_preferred_name(
        mem, "Eli", "addressed_name", user_turns=["Eliさん元気？"]
    )
    _check(mem.comfort.preferred_name == "", "extract rejects addressed name")
    admit_preferred_name(
        mem, "Eli", "explicit_self_intro", user_turns=["私はEliです"]
    )
    _check(mem.comfort.preferred_name == "Eli", "extract admits explicit self-intro")
    admit_preferred_name(
        mem, "Alex", "explicit_call_me", user_turns=["Alexって呼んで"]
    )
    _check(mem.comfort.preferred_name == "Alex", "explicit rename overwrites")
    stale = merge_extract_result(
        LearnerMemory(),
        {"comfort": {"preferred_name": "Kyla"}},
        recent_messages=[{"role": "user", "content": "Kylaさん元気？"}],
    )
    _check(stale.comfort.preferred_name == "", "legacy extract preferred_name ignored")

    print("smoke_reply_shape ok")


if __name__ == "__main__":
    main()
