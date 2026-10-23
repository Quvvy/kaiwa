"""Unit proofs for Kaiwa bug hunt. No network. Exit 0 even when bugs fire."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.learner_profile import LearnerProfile, apply_chat_signals  # noqa: E402
from kaiwa.llm import _complete_with_retry  # noqa: E402
from kaiwa.persona import infer_help_type, infer_learner_state  # noqa: E402
from kaiwa.practice.cards import maybe_write_card  # noqa: E402
from kaiwa.practice.learn import STARTER_CARDS  # noqa: E402
from kaiwa.practice.sitting import (  # noqa: E402
    finish_sitting,
    recent_practiced_lines,
    start_sitting,
)
from kaiwa.reply_shape import (  # noqa: E402
    has_high_load,
    has_open_question,
    reply_too_dense,
)
from kaiwa.session_store import (  # noqa: E402
    append_record,
    create_session,
    hydrate,
)
from kaiwa.stt import is_identity_prompt_dump  # noqa: E402
from kaiwa.wo_ga import (  # noqa: E402
    needs_wo_ga_recast,
    prefer_recast_reply,
    recast_phrase,
    with_recast_notices,
)


def emit(line: str) -> None:
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()


def show(ok: bool, label: str, detail: str = "") -> None:
    tag = "BUG " if not ok else "ok  "
    line = f"{tag} {label}"
    if detail:
        line += f" :: {detail}"
    emit(line)


def main() -> None:
    emit("=== 1. prefer_recast_reply / recast retry ===")
    kept, landed = prefer_recast_reply(
        "コーヒーを好きです",
        "いいね！毎日飲む？",
        "そうなんだ。よく飲むの？",
    )
    show(
        not (kept == "いいね！毎日飲む？" and landed is False),
        "retry miss keeps uncorrected first",
        f"chosen={kept!r} landed={landed}",
    )

    queue = ["いいね！毎日飲む？", "そうなんだ。よく飲むの？"]

    def fake_completion(*_a, **_k):
        return queue.pop(0)

    import kaiwa.llm as llm_mod

    orig = llm_mod._completion
    llm_mod._completion = fake_completion
    try:
        chosen, retry_flag = _complete_with_retry(
            SimpleNamespace(),
            "sys",
            [{"role": "user", "content": "コーヒーを好きです"}],
            locked=False,
            last_user="コーヒーを好きです",
        )
    finally:
        llm_mod._completion = orig
    show(
        "が好き" in chosen,
        "_complete_with_retry miss still speaks uncorrected first",
        f"chosen={chosen!r} retry_flag={retry_flag}",
    )

    queue = [
        "コーヒーが好きなんだね。でも毎日飲むの？それから映画も好き？",
        "いいね！毎日飲む？",
    ]
    llm_mod._completion = lambda *_a, **_k: queue.pop(0)
    try:
        chosen2, flag2 = _complete_with_retry(
            SimpleNamespace(),
            "sys",
            [{"role": "user", "content": "コーヒーを好きです"}],
            locked=True,
            last_user="コーヒーを好きです",
        )
    finally:
        llm_mod._completion = orig
    show(
        "が好き" in chosen2,
        "shape retry can drop an already-landed recast",
        f"chosen={chosen2!r} flag={flag2} need_recast_first={needs_wo_ga_recast('コーヒーを好きです', 'コーヒーが好きなんだね。でも毎日飲むの？それから映画も好き？')}",
    )

    queue = ["いいね！毎日飲む？"]
    def boom(*_a, **_k):
        if len(queue) == 1:
            return queue.pop(0)
        raise RuntimeError("retry failed")

    llm_mod._completion = boom
    try:
        chosen3, flag3 = _complete_with_retry(
            SimpleNamespace(),
            "sys",
            [{"role": "user", "content": "コーヒーを好きです"}],
            locked=False,
            last_user="コーヒーを好きです",
        )
    finally:
        llm_mod._completion = orig
    show(
        "が好き" in chosen3,
        "retry exception swallows and returns uncorrected first",
        f"chosen={chosen3!r} flag={flag3}",
    )

    emit("=== 2. infer_learner_state / cards ===")
    for text, expect_state in [
        ("はい", "struggling"),
        ("はい。", "struggling"),
        ("パスタ", "struggling"),
        ("パスタ。", "struggling"),
        ("猫", "struggling"),
        ("元気です", "flowing"),
        ("わかりません", "help_request"),
        ("わからない", "help_request"),
    ]:
        actual = infer_learner_state(text)
        show(
            actual == expect_state,
            f"infer_learner_state({text!r})",
            f"expected={expect_state} actual={actual}",
        )

    profile = LearnerProfile(placement_completed=True, speaking_level="pre_n5")
    before = profile.stats.struggle_streak
    apply_chat_signals(profile, infer_learner_state("はい。"), "はい。")
    show(
        profile.stats.struggle_streak == before,
        "はい after yes/no does not bump struggle_streak",
        f"streak {before} -> {profile.stats.struggle_streak} flow={profile.stats.flow_streak}",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "cards.jsonl"
        hai_hist = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "元気？"},
            {"role": "user", "content": "はい。"},
            {"role": "assistant", "content": "よかった。"},
        ]
        hai = maybe_write_card(
            session_id="s-hai",
            history=hai_hist,
            learner_state=infer_learner_state("はい。"),
            transcript="はい。",
            reply="よかった。",
            path=path,
        )
        show(hai is None, "はい after 元気？ does not write a card", f"card={hai}")

        pasta_hist = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "何を食べた？"},
            {"role": "user", "content": "パスタ。"},
            {"role": "assistant", "content": "おいしかった？"},
        ]
        pasta = maybe_write_card(
            session_id="s-pasta",
            history=pasta_hist,
            learner_state=infer_learner_state("パスタ。"),
            transcript="パスタ。",
            reply="おいしかった？",
            path=path,
        )
        show(
            pasta is None,
            "パスタ after WH-question does not write a card",
            f"state={infer_learner_state('パスタ。')} card={pasta}",
        )

        lone_hai = maybe_write_card(
            session_id="s-hai2",
            history=[
                {"role": "assistant", "content": "今日は何したの？"},
                {"role": "user", "content": "はい。"},
                {"role": "assistant", "content": "映画？"},
            ],
            learner_state="struggling",
            transcript="はい。",
            reply="映画？",
            path=path,
        )
        show(
            lone_hai is None,
            "single はい to open question is not carded (needs repeat)",
            f"card={lone_hai}",
        )

    emit("=== 3. wakaranai help_type ===")
    cases = [
        ("わからない", "comprehension"),
        ("分からない", "comprehension"),
        ("わかんない", "comprehension"),
        ("わかりません", "comprehension"),
        ("日本語でわからない", "vocabulary"),
        ("眠いってどういう意味？", "vocabulary"),
        ("音楽がわからない", "comprehension"),
        ("どういう意味", "vocabulary"),
        ("意味がわからない", "comprehension"),
    ]
    for text, expect in cases:
        actual = infer_help_type(text)
        show(
            actual == expect,
            f"infer_help_type({text!r})",
            f"expected={expect} actual={actual} state={infer_learner_state(text)}",
        )

    emit("=== 4. identity dump false drops ===")
    dumps = [
        ("会話さん", True),
        ("会話", True),
        ("Kaiwa", True),
        ("カイワ", True),
        ("会話 会話 会話", True),
        ("Kaiwa?", True),
        ("会話。", True),
        ("会話さん？", True),
        ("会話、Kaiwa", True),
        ("会話です", False),
        ("こんにちは、会話さん", False),
        ("音楽がわからない", False),
        ("会話がわからない", False),
        ("Kaiwaです", False),
        ("あ れーりーよー Kaiwa さーわ", False),
    ]
    for text, expect_drop in dumps:
        actual = is_identity_prompt_dump(text)
        show(
            actual == expect_drop,
            f"identity_dump({text!r})",
            f"dropped={actual} expect_drop={expect_drop}",
        )
    show(
        not is_identity_prompt_dump("会話さん"),
        "addressing 会話さん is kept as real speech (decision #135 is only-token dumps)",
        "actual dump=True so Chat 400s as unheard",
    )

    emit("=== 5. shape-lock false positives ===")
    shape_cases = [
        ("こんばんは", False, "greeting ば"),
        ("ば？", False, "bare ば"),
        ("来たら", True, "来たら is a real たら-conditional"),
        ("あたらしい", False, "あたらしい contains たら"),
        ("新しい", False, "kanji 新しい"),
        ("さようなら", False, "さようなら contains なら"),
        ("さよなら", False, "さよなら contains なら"),
        ("映画の予定だね。", False, "予定 in a statement"),
        ("予定ないよ。", False, "予定ない statement"),
        ("今日の予定は？", True, "予定 question is an open pivot"),
        ("ならない", False, "ならない excluded"),
        ("ゆっくり話せばだいじょうぶですよ", True, "real ば-conditional"),
    ]
    for text, expect_dense, note in shape_cases:
        dense = reply_too_dense(text)
        show(
            dense == expect_dense,
            f"reply_too_dense({text!r}) [{note}]",
            f"dense={dense} high_load={has_high_load(text)} open={has_open_question(text)} expect={expect_dense}",
        )

    emit("=== 6. rescue vs recast_phrase on hydrate ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        meta = create_session(root, "alice")
        append_record(
            root,
            meta.id,
            {
                "ts": "2026-09-17T00:00:00+00:00",
                "mode": "chat",
                "transcript": "コーヒーを好きです",
                "reply": "コーヒーが好きなんだね。毎日飲む？",
            },
            profile_id="alice",
            bump_turns=True,
        )
        tagged = hydrate(root, meta.id, mark_rescue=True)
        noticed = with_recast_notices(tagged)
        show(
            noticed[1].get("recast_phrase") == "コーヒーが好きなんだね。",
            "hydrate recast caption before Simpler",
            f"phrase={noticed[1].get('recast_phrase')!r}",
        )
        append_record(
            root,
            meta.id,
            {
                "ts": "2026-09-17T00:00:01+00:00",
                "mode": "chat",
                "rescue": True,
                "transcript": "",
                "reply": "コーヒー、好き？",
            },
            profile_id="alice",
        )
        tagged2 = hydrate(root, meta.id, mark_rescue=True)
        noticed2 = with_recast_notices(tagged2)
        show(
            tagged2[-1].get("rescue") is True,
            "GET hydrate tags rescue on last assistant",
            f"row={tagged2[-1]}",
        )
        show(
            "recast_phrase" not in noticed2[-1],
            "rescue assistant has no recast caption",
            f"row={noticed2[-1]}",
        )
        ram = hydrate(root, meta.id, mark_rescue=False)
        ram_noticed = with_recast_notices(ram)
        show(
            "recast_phrase" not in ram_noticed[-1],
            "RAM hydrate (no rescue tag) still skips caption because content lost が好き",
            f"content={ram_noticed[-1].get('content')!r} phrase={ram_noticed[-1].get('recast_phrase')}",
        )

        append_record(
            root,
            meta.id,
            {
                "ts": "2026-09-17T00:00:02+00:00",
                "mode": "chat",
                "rescue": True,
                "transcript": "",
                "reply": "コーヒーが好き。毎日？",
            },
            profile_id="alice",
        )
        ram3 = hydrate(root, meta.id, mark_rescue=False)
        ram3_n = with_recast_notices(ram3)
        show(
            "recast_phrase" not in ram3_n[-1],
            "RAM hydrate without rescue tag must not recaption a simpler line that still has が好き",
            f"rescue_flag={ram3[-1].get('rescue')} phrase={ram3_n[-1].get('recast_phrase')!r} content={ram3[-1].get('content')!r}",
        )

    emit("=== 7. Learn vs Practice card_id ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        cards = Path(tmpdir) / "struggle_cards.jsonl"
        state = Path(tmpdir) / "practice_state.json"
        first = start_sitting(
            card_id=STARTER_CARDS[0]["id"],
            cards_path=cards,
            state_path_override=state,
        )
        show(
            first.get("card_id") == STARTER_CARDS[0]["id"],
            "Learn starter id starts that sitting",
            f"id={first.get('card_id')}",
        )
        second = start_sitting(
            card_id=STARTER_CARDS[1]["id"],
            cards_path=cards,
            state_path_override=state,
        )
        show(
            second.get("card_id") == STARTER_CARDS[1]["id"],
            "Learn tap replaces in-progress sitting with the tapped card",
            f"wanted={STARTER_CARDS[1]['id']} got={second.get('card_id')} same_sitting={second.get('id')==first.get('id')}",
        )
        finish_sitting(state_path_override=state, mark_used=True)
        used_state = json.loads(state.read_text(encoding="utf-8"))
        lines = recent_practiced_lines(
            used_state.get("used_card_ids"),
            cards_path=cards,
        )
        show(
            any(row.get("speakable") == STARTER_CARDS[0]["speakable"] for row in lines),
            "practiced Learn starter appears in Things you can say",
            f"used={used_state.get('used_card_ids')} lines={lines}",
        )
        try:
            start_sitting(
                card_id="missing-card",
                cards_path=cards,
                state_path_override=state,
            )
            show(False, "unknown card_id raises LookupError")
        except LookupError:
            show(True, "unknown card_id raises LookupError")

        today = start_sitting(cards_path=cards, state_path_override=state)
        show(
            not str(today.get("card_id") or "").startswith("learn:"),
            "Practice Start without id is not a Learn starter",
            f"id={today.get('card_id')}",
        )
        finish_sitting(state_path_override=state)

    emit("=== 8. last-16 vs on-screen ===")
    chat_llm_history = 16

    def llm_messages(history):
        slim = [
            {
                "role": str(message.get("role") or ""),
                "content": str(message.get("content") or ""),
            }
            for message in history
        ]
        if len(slim) <= chat_llm_history:
            return slim
        return slim[-chat_llm_history:]

    history = []
    for i in range(12):
        history.append({"role": "user", "content": f"topic-{i} を好きです", "rescue": True})
        history.append({"role": "assistant", "content": f"reply-{i}"})
    slim = llm_messages(history)
    show(
        len(slim) == chat_llm_history,
        f"LLM history capped at {chat_llm_history}",
        f"on_screen={len(history)} llm={len(slim)} first_llm={slim[0]['content']!r}",
    )
    show(
        slim[0]["content"] == "topic-0 を好きです",
        "last-16 still includes the first topic",
        f"first_llm={slim[0]['content']!r} (dropped topic-0 after 8+ exchanges)",
    )
    show(
        "rescue" not in slim[0],
        "hydrate flags stripped before LLM",
        f"keys={list(slim[0].keys())}",
    )
    show(
        any("topic-0" in m["content"] for m in slim),
        "early topic survives in LLM tail after 12 exchanges (24 msgs)",
        "topic-0 is gone from last-16 once history exceeds 16 messages",
    )

    emit("=== 9. empty-reply fallback / identity freeze path notes ===")
    show(
        True,
        "see report for stream dangling-user and うん。 fallback (code inspection)",
    )
    emit("repro_bugs done")


if __name__ == "__main__":
    main()
