from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.persona import PROMPT_REVISION, build_practice_sitting_system_prompt
from kaiwa.prefs import UserPrefs
from kaiwa.stt import is_identity_prompt_dump
from kaiwa.practice.cards import (
    append_card,
    build_card,
    display_line,
    maybe_write_card,
    meaningful_correction,
    newest_unused,
    prior_context,
    snapshot_signal,
    unused_cards,
    why_line,
)
from kaiwa.wo_ga import (
    needs_wo_ga_recast,
    prefer_recast_reply,
    recast_phrase,
    splice_wo_ga_model,
    with_recast_notices,
    wo_ga_recast_stem,
    word_family_pair,
)
from kaiwa.practice.sitting import (
    FALLBACK_CARDS,
    LINES_CAP,
    MAX_LEARNER_TURNS,
    append_learner_turn,
    finish_sitting,
    new_sitting,
    pick_today_card,
    public_sitting,
    remaining_learner_turns,
    start_sitting,
    today_payload,
)


def _check(ok: bool, label: str) -> None:
    status = "ok  " if ok else "FAIL"
    line = f"{status} {label}"
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    if not ok:
        raise SystemExit(f"smoke_struggle_cards failed: {label}")


def main() -> None:
    _check(is_identity_prompt_dump("会話 会話 会話"), "kaiwa-kaiwa dump is empty speech")
    _check(is_identity_prompt_dump("Kaiwa"), "latin Kaiwa dump is empty speech")
    _check(is_identity_prompt_dump("会話さん"), "kaiwasan dump is empty speech")
    _check(
        not is_identity_prompt_dump("音楽がわからない"),
        "real JP line is not an identity dump",
    )
    _check(
        not is_identity_prompt_dump("会話がわからない"),
        "会話 in a real sentence is not a dump",
    )
    _check(
        not is_identity_prompt_dump("あ れーりーよー Kaiwa さーわ"),
        "mixed garbage with Kaiwa is not rewritten",
    )

    _check(snapshot_signal(learner_state="flowing") is None, "flowing skips snapshot")
    _check(
        snapshot_signal(learner_state="help_request") == "help_request",
        "help_request snapshots",
    )
    _check(
        snapshot_signal(learner_state="struggling") == "struggling",
        "struggling snapshots",
    )
    _check(
        snapshot_signal(learner_state="flowing", rescue=True) == "rescue",
        "rescue snapshots even if flowing",
    )

    history = [
        {"role": "user", "content": "昨日映画を見た"},
        {"role": "assistant", "content": "何の映画？"},
        {"role": "user", "content": "日本語を好きです"},
        {"role": "assistant", "content": "日本語が好きです、だね。何の食べ物が好き？"},
    ]
    prior_user, prior_asst = prior_context(history, skip_last=2)
    _check(prior_user == "昨日映画を見た", "prior user from history")
    _check(prior_asst == "何の映画？", "prior assistant from history")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir) / "struggle_cards.jsonl"
        skipped = maybe_write_card(
            session_id="s1",
            history=history,
            learner_state="flowing",
            transcript="元気です",
            reply="よかった。",
            path=tmp,
        )
        _check(skipped is None, "flowing does not write")

        first = maybe_write_card(
            session_id="s1",
            history=history,
            learner_state="help_request",
            transcript="わからない",
            reply="ゆっくり言うね。コーヒーが好き？",
            speakable="コーヒーが好きです。",
            path=tmp,
        )
        _check(first is not None and first["signal"] == "help_request", "help writes card")
        _check(first["learner_line"] == "わからない", "stores learner line")
        _check(first["speakable"] == "コーヒーが好きです。", "stores speakable as speakable")
        _check(first["prior_user"] == "昨日映画を見た", "stores prior user")

        dup = maybe_write_card(
            session_id="s1",
            history=history,
            learner_state="help_request",
            transcript="わからない",
            reply="もう一度。",
            path=tmp,
        )
        _check(dup is None, "same session+line is deduped")

        en_ask = maybe_write_card(
            session_id="s-en-ask",
            history=history,
            learner_state="help_request",
            transcript="英語で",
            reply="Okay, briefly.",
            path=tmp,
        )
        _check(
            en_ask is not None and en_ask["signal"] == "help_request",
            "explicit english ask stays help_request",
        )

        rescue_hist = [
            {"role": "user", "content": "映画が好き"},
            {"role": "assistant", "content": "短い返事。"},
        ]
        rescued = maybe_write_card(
            session_id="s2",
            history=rescue_hist,
            learner_state="help_request",
            transcript="",
            reply="映画、好き？",
            rescue=True,
            path=tmp,
        )
        _check(rescued is not None and rescued["signal"] == "rescue", "rescue writes card")
        _check(rescued["learner_line"] == "映画が好き", "rescue uses previous user line")
        _check(rescued["help_type"] == "comprehension", "rescue help_type is comprehension")

        empty_rescue = maybe_write_card(
            session_id="s3",
            history=[{"role": "assistant", "content": "こんにちは"}],
            learner_state="help_request",
            transcript="",
            reply="短くするね。",
            rescue=True,
            path=tmp,
        )
        _check(empty_rescue is None, "rescue without learner line skips")

        leftover = unused_cards(used_ids=[first["id"], en_ask["id"]], path=tmp)
        _check(len(leftover) == 1 and leftover[0]["id"] == rescued["id"], "unused skips used id")
        newest = newest_unused(used_ids=[first["id"], en_ask["id"]], path=tmp)
        _check(newest is None, "empty-speakable rescue does not win newest_unused")

        en_hist = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "今日は何したの？"},
            {"role": "user", "content": "The weather is nice today"},
            {"role": "assistant", "content": "天気の話だね。"},
        ]
        en_card = maybe_write_card(
            session_id="s-en",
            history=en_hist,
            learner_state="struggling",
            transcript="The weather is nice today",
            reply="天気の話だね。",
            path=tmp,
        )
        _check(
            en_card is not None and en_card["learner_line"] == "The weather is nice today",
            "unsolicited English writes",
        )

        hai_hist = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "元気？"},
            {"role": "user", "content": "はい。"},
            {"role": "assistant", "content": "よかった。"},
        ]
        hai = maybe_write_card(
            session_id="s-hai",
            history=hai_hist,
            learner_state="struggling",
            transcript="はい。",
            reply="よかった。",
            path=tmp,
        )
        _check(hai is None, "hai after genki does not write")

        pasta_hist = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "何を食べた？"},
            {"role": "user", "content": "パスタ。"},
            {"role": "assistant", "content": "おいしかった？"},
        ]
        pasta = maybe_write_card(
            session_id="s-pasta",
            history=pasta_hist,
            learner_state="struggling",
            transcript="パスタ。",
            reply="おいしかった？",
            path=tmp,
        )
        _check(pasta is None, "pasta after what-did-you-eat does not write")

        repeat_hist = [
            {"role": "user", "content": "うん。"},
            {"role": "assistant", "content": "映画を見たんだ。"},
            {"role": "user", "content": "うん。"},
            {"role": "assistant", "content": "友達とね。"},
        ]
        repeated = maybe_write_card(
            session_id="s-rep",
            history=repeat_hist,
            learner_state="struggling",
            transcript="うん。",
            reply="友達とね。",
            path=tmp,
        )
        _check(
            repeated is not None and repeated["learner_line"] == "うん。",
            "two minimal non-answers write",
        )

        abandon_hist = [
            {"role": "user", "content": "昨日…"},
            {"role": "assistant", "content": "映画を見たんだ。"},
            {"role": "user", "content": "うん。"},
            {"role": "assistant", "content": "そうなんだ。"},
        ]
        abandoned = maybe_write_card(
            session_id="s-ab",
            history=abandon_hist,
            learner_state="struggling",
            transcript="うん。",
            reply="そうなんだ。",
            path=tmp,
        )
        _check(
            abandoned is not None and abandoned["learner_line"] == "昨日…",
            "abandon writes previous fragment",
        )

        flow_hist = [
            {"role": "user", "content": "昨日…"},
            {"role": "assistant", "content": "映画を見たんだ。"},
            {"role": "user", "content": "そうだね"},
            {"role": "assistant", "content": "うん。"},
        ]
        flow_ab = maybe_write_card(
            session_id="s-ab2",
            history=flow_hist,
            learner_state="flowing",
            transcript="そうだね",
            reply="うん。",
            path=tmp,
        )
        _check(
            flow_ab is not None and flow_ab["learner_line"] == "昨日…",
            "flowing retreat still snapshots abandoned attempt",
        )

        rephrase_hist = [
            {"role": "user", "content": "映画…"},
            {"role": "assistant", "content": "映画を見たんだ。"},
            {"role": "user", "content": "映画見る"},
            {"role": "assistant", "content": "何の映画？"},
        ]
        rephrase = maybe_write_card(
            session_id="s-re",
            history=rephrase_hist,
            learner_state="flowing",
            transcript="映画見る",
            reply="何の映画？",
            path=tmp,
        )
        _check(rephrase is None, "high-overlap rephrase does not write")

        etto_hist = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "今日は何したの？"},
            {"role": "user", "content": "えっと…"},
            {"role": "assistant", "content": "ゆっくりでいいよ。"},
        ]
        etto = maybe_write_card(
            session_id="s-etto",
            history=etto_hist,
            learner_state="flowing",
            transcript="えっと…",
            reply="ゆっくりでいいよ。",
            path=tmp,
        )
        _check(
            etto is not None
            and etto["learner_line"] == "えっと…"
            and etto["speakable"] == "えっと…",
            "etto freeze writes survival speakable",
        )

        um_hist = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "今日は何したの？"},
            {"role": "user", "content": "um"},
            {"role": "assistant", "content": "ゆっくりでいいよ。"},
        ]
        um_card = maybe_write_card(
            session_id="s-um",
            history=um_hist,
            learner_state="flowing",
            transcript="um",
            reply="ゆっくりでいいよ。",
            path=tmp,
        )
        _check(
            um_card is not None and um_card["speakable"] == "えっと…",
            "um freeze writes survival speakable",
        )

        dots_hist = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "今日は何したの？"},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "ゆっくりでいいよ。"},
        ]
        dots = maybe_write_card(
            session_id="s-dots",
            history=dots_hist,
            learner_state="struggling",
            transcript="...",
            reply="ゆっくりでいいよ。",
            path=tmp,
        )
        _check(dots is not None and dots["speakable"] == "えっと…", "ellipsis freeze writes")

        again_hist = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "今日は何したの？"},
            {"role": "user", "content": "もう一回お願いします"},
            {"role": "assistant", "content": "映画を見たんだ。"},
        ]
        again = maybe_write_card(
            session_id="s-again",
            history=again_hist,
            learner_state="flowing",
            transcript="もう一回お願いします",
            reply="映画を見たんだ。",
            path=tmp,
        )
        _check(
            again is not None and again["speakable"] == "もう一回お願いします",
            "mou ichido freeze keeps that survival line",
        )

        empty_hist = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "今日は何したの？"},
        ]
        empty_fr = maybe_write_card(
            session_id="s-empty",
            history=empty_hist,
            learner_state="flowing",
            transcript="",
            reply="今日は何したの？",
            path=tmp,
        )
        _check(
            empty_fr is not None
            and empty_fr["learner_line"] == "…"
            and empty_fr["speakable"] == "えっと…",
            "empty transcript freeze writes ellipsis line",
        )
        _check(
            empty_fr["learner_line"] != "こんにちは",
            "empty freeze does not steal previous user line",
        )

        no_asst = maybe_write_card(
            session_id="s-no-asst",
            history=[],
            learner_state="flowing",
            transcript="",
            reply="今日は何したの？",
            path=tmp,
        )
        _check(no_asst is None, "empty freeze without prior assistant skips")

        how = maybe_write_card(
            session_id="s-how",
            history=etto_hist,
            learner_state="help_request",
            transcript="how do I say movie",
            reply="映画だよ。",
            path=tmp,
        )
        _check(
            how is not None and how["signal"] == "help_request",
            "how do I say stays help_request",
        )

        corr_hist = [
            {"role": "user", "content": "昨日映画を見た"},
            {"role": "assistant", "content": "何の映画？"},
            {"role": "user", "content": "日本語を好きです"},
            {"role": "assistant", "content": "日本語が好きです。何の食べ物が好き？"},
        ]
        corr = maybe_write_card(
            session_id="s-corr",
            history=corr_hist,
            learner_state="flowing",
            transcript="日本語を好きです",
            reply="日本語が好きです。何の食べ物が好き？",
            path=tmp,
        )
        _check(
            corr is not None and corr["speakable"] == "日本語が好きです",
            "wo-suki correction writes swapped speakable",
        )
        _check(corr["learner_line"] == "日本語を好きです", "correction keeps original learner line")

        no_echo = maybe_write_card(
            session_id="s-corr-none",
            history=corr_hist,
            learner_state="flowing",
            transcript="日本語を好きです",
            reply="そうなんだ。映画はよく見るの？",
            path=tmp,
        )
        _check(no_echo is None, "wo-suki without ga-suki in tutor does not write")

        already_ga = maybe_write_card(
            session_id="s-corr-ga",
            history=corr_hist,
            learner_state="flowing",
            transcript="日本語が好きです",
            reply="日本語が好きです。何の食べ物が好き？",
            path=tmp,
        )
        _check(already_ga is None, "already ga-suki does not write")

        mixed = maybe_write_card(
            session_id="s-corr-kana",
            history=corr_hist,
            learner_state="flowing",
            transcript="コーヒーをすきです",
            reply="コーヒーが好きなんだね。毎日飲む？",
            path=tmp,
        )
        _check(
            mixed is not None and mixed["speakable"] == "コーヒーがすきです",
            "kana をすき + kanji が好き writes swapped learner line",
        )
        no_mixed = maybe_write_card(
            session_id="s-corr-kana-none",
            history=corr_hist,
            learner_state="flowing",
            transcript="コーヒーをすきです",
            reply="いいね！毎日飲む？",
            path=tmp,
        )
        _check(no_mixed is None, "kana をすき without が好き/すき does not write")

        kana_only = maybe_write_card(
            session_id="s-kana",
            history=corr_hist,
            learner_state="flowing",
            transcript="わたしは学生です",
            reply="私は学生なんだ。",
            path=tmp,
        )
        _check(kana_only is None, "watashi vs kanji is not a correction card")

        empty_today = today_payload(
            cards_path=Path(tmpdir) / "missing_cards.jsonl",
            state_path_override=Path(tmpdir) / "missing_state.json",
        )
    _check(empty_today["available"] is True, "empty today is still available")
    _check(empty_today.get("fallback") is True, "empty today is fallback")
    _check(empty_today["sitting"] is None, "empty today has no sitting")
    _check(empty_today["minutes"] == 2, "today minutes is 2")
    _check(empty_today.get("lines") == [], "empty used ids has no lines")

    fallback_speakable = {card["speakable"] for card in FALLBACK_CARDS}
    with tempfile.TemporaryDirectory() as tmpdir:
        cards_file = Path(tmpdir) / "struggle_cards.jsonl"
        state_file = Path(tmpdir) / "practice_state.json"
        started = start_sitting(cards_path=cards_file, state_path_override=state_file)
        speak = display_line(started.get("card") if isinstance(started.get("card"), dict) else {})
        _check(
            str(started.get("card_id") or "").startswith("fallback:"),
            "empty start uses fallback id",
        )
        _check(speak == "コーヒーが好きです。", "empty start prefers が好き fallback")
        finish_sitting(state_path_override=state_file)

        chat_card = maybe_write_card(
            session_id="s-today",
            history=[
                {"role": "user", "content": "わからない"},
                {"role": "assistant", "content": "ゆっくり言うね。"},
            ],
            learner_state="help_request",
            transcript="わからない",
            reply="ゆっくり言うね。",
            path=cards_file,
        )
        _check(chat_card is not None, "chat card for today preference")
        assert chat_card is not None
        today_chat = today_payload(cards_path=cards_file, state_path_override=state_file)
        _check(today_chat.get("fallback") is True, "junk help does not win today")
        _check(
            str(today_chat.get("card_id") or "") == "fallback:suki",
            "junk help falls back to が好き",
        )
        _check(today_chat.get("lines") == [], "unused junk card is not in lines")

        recast_for_lines = maybe_write_card(
            session_id="s-today-recast",
            history=[
                {"role": "user", "content": "コーヒーを好きです"},
                {"role": "assistant", "content": "コーヒーが好きなんだね。"},
            ],
            learner_state="flowing",
            transcript="コーヒーを好きです",
            reply="コーヒーが好きなんだね。",
            path=cards_file,
        )
        _check(recast_for_lines is not None, "recast card for today preference")
        assert recast_for_lines is not None
        today_recast = today_payload(cards_path=cards_file, state_path_override=state_file)
        _check(today_recast.get("fallback") is False, "recast wins over junk help")
        _check(
            str(today_recast.get("card_id") or "") == recast_for_lines["id"],
            "today card_id is the recast snapshot",
        )

        used_state = Path(tmpdir) / "used_state.json"
        used_state.write_text(
            json.dumps(
                {"used_card_ids": [recast_for_lines["id"]], "sitting": None},
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        today_used = today_payload(cards_path=cards_file, state_path_override=used_state)
        _check(today_used.get("fallback") is True, "used chat cards fall back")
        _check(
            str(today_used.get("card_id") or "").startswith("fallback:"),
            "used chat does not recycle chat id",
        )
        used_lines = today_used.get("lines") or []
        _check(len(used_lines) == 1, "used chat card appears in lines")
        _check(
            used_lines[0] == {"speakable": display_line(recast_for_lines)},
            "used line is speakable only",
        )
        _check("help_type" not in used_lines[0], "line has no help_type")
        _check("signal" not in used_lines[0], "line has no signal")

    with tempfile.TemporaryDirectory() as tmpdir:
        cards_file = Path(tmpdir) / "struggle_cards.jsonl"
        state_file = Path(tmpdir) / "practice_state.json"
        recast_hist = [
            {"role": "user", "content": "コーヒーを好きです"},
            {"role": "assistant", "content": "コーヒーが好きなんだね。毎日飲む？"},
        ]
        recast_card = maybe_write_card(
            session_id="s-loop",
            history=recast_hist,
            learner_state="flowing",
            transcript="コーヒーを好きです",
            reply="コーヒーが好きなんだね。毎日飲む？",
            path=cards_file,
        )
        _check(recast_card is not None, "flowing recast writes a snapshot")
        assert recast_card is not None
        _check(
            recast_card["speakable"] == "コーヒーが好きです",
            "snapshot speakable is the swapped line",
        )
        _check(
            recast_phrase("コーヒーを好きです", "コーヒーが好きなんだね。毎日飲む？")
            == "コーヒーが好きなんだね。",
            "same pair has a recast caption",
        )
        picked, is_fallback = pick_today_card(
            used_ids=["fallback:etto", "fallback:again"],
            cards_path=cards_file,
        )
        _check(is_fallback is False, "recast card wins over used fallback ids")
        _check(picked.get("id") == recast_card["id"], "today pick is the recast snapshot")
        pub = public_sitting(new_sitting(recast_card))
        _check(
            pub is not None and pub.get("speakable") == "コーヒーが好きです",
            "sitting speakable is swapped line not んだね",
        )
        _check(
            display_line(recast_card) == "コーヒーが好きです",
            "display_line is swapped line",
        )
        started = start_sitting(cards_path=cards_file, state_path_override=state_file)
        _check(started.get("card_id") == recast_card["id"], "sitting starts on recast card")
        for i in range(MAX_LEARNER_TURNS):
            append_learner_turn(started, "コーヒーが好きです")
        finished = finish_sitting(state_path_override=state_file)
        _check(finished.get("marked_used") is True, "finish marks recast card used")
        _check(
            finished.get("pending_elicit") == "コーヒーが好きです",
            "finish queues Chat elicit",
        )
        after = today_payload(cards_path=cards_file, state_path_override=state_file)
        _check(after.get("fallback") is True, "no unused Chat card falls back")
        _check(
            str(after.get("card_id") or "").startswith("fallback:"),
            "next today is canned after recast sitting",
        )
        after_speak = {row.get("speakable") for row in (after.get("lines") or [])}
        _check("コーヒーが好きです" in after_speak, "finished recast sitting is in lines")
        extra = maybe_write_card(
            session_id="s-loop-2",
            history=[
                {"role": "user", "content": "わからない"},
                {"role": "assistant", "content": "ゆっくり言うね。"},
            ],
            learner_state="help_request",
            transcript="わからない",
            reply="ゆっくり言うね。",
            path=cards_file,
        )
        _check(extra is not None, "later Chat card still writes")
        assert extra is not None
        still_fallback = today_payload(cards_path=cards_file, state_path_override=state_file)
        _check(
            still_fallback.get("fallback") is True,
            "junk help does not steal today after recast used",
        )
        extra_recast = maybe_write_card(
            session_id="s-loop-3",
            history=[
                {"role": "user", "content": "猫を好きです"},
                {"role": "assistant", "content": "猫が好きなんだね。"},
            ],
            learner_state="flowing",
            transcript="猫を好きです",
            reply="猫が好きなんだね。",
            path=cards_file,
        )
        _check(extra_recast is not None, "later recast still writes")
        assert extra_recast is not None
        wins = today_payload(cards_path=cards_file, state_path_override=state_file)
        _check(wins.get("fallback") is False, "unused recast still wins after fallback")
        _check(str(wins.get("card_id") or "") == extra_recast["id"], "newest unused recast is today")
        win_speak = {row.get("speakable") for row in (wins.get("lines") or [])}
        _check("コーヒーが好きです" in win_speak, "used recast stays in lines")
        _check(display_line(extra) not in win_speak, "unused junk help is not in lines")

    sitting = new_sitting(
        {
            "id": "card1",
            "learner_line": "日本語を好きです",
            "tutor_reply": "日本語が好きです。",
        }
    )
    _check(remaining_learner_turns(sitting) == MAX_LEARNER_TURNS, "fresh sitting has 2 turns")
    _check(MAX_LEARNER_TURNS == 2, "sitting cap is say-this plus one exchange")
    for i in range(MAX_LEARNER_TURNS):
        append_learner_turn(sitting, f"line {i}")
    _check(sitting["done"] is True, "second learner turn finishes sitting")
    _check(remaining_learner_turns(sitting) == 0, "no remaining turns after cap")

    _check(
        display_line({"speakable": "コーヒーが飲めます。", "tutor_reply": "長い返事。"})
        == "コーヒーが飲めます。",
        "speakable wins over tutor reply",
    )
    _check(
        display_line(
            {
                "speakable": None,
                "tutor_reply": "日本語が好きです。何の食べ物が好き？",
                "learner_line": "日本語を好きです",
            }
        )
        == "日本語が好きです。",
        "first tutor sentence when speakable is empty",
    )
    _check(
        display_line({"speakable": "", "tutor_reply": "", "learner_line": "えっと…"})
        == "えっと…",
        "learner_line last resort",
    )
    _check("particle" not in display_line({"speakable": "コーヒーが飲めます。"}), "no grammar tags")
    pub = public_sitting(new_sitting({"id": "c2", "speakable": "猫が好きです。"}))
    _check(pub is not None and pub.get("speakable") == "猫が好きです。", "public sitting includes speakable")
    _check("help_type" not in (pub or {}), "public sitting hides help_type")

    with tempfile.TemporaryDirectory() as tmpdir:
        cards_file = Path(tmpdir) / "struggle_cards.jsonl"
        state_file = Path(tmpdir) / "practice_state.json"
        speakables = [
            "線1です。",
            "線2です。",
            "線3です。",
            "線4です。",
            "線5です。",
            "線6です。",
            "線2です。",
        ]
        used_ids = []
        for i, line in enumerate(speakables):
            card = append_card(
                build_card(
                    session_id=f"s-lines-{i}",
                    signal="struggling",
                    learner_line=f"miss {i}",
                    tutor_reply=line,
                    speakable=line,
                    help_type="particle",
                ),
                path=cards_file,
            )
            used_ids.append(str(card["id"]))
        state_file.write_text(
            json.dumps({"used_card_ids": used_ids, "sitting": None}, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        capped = today_payload(cards_path=cards_file, state_path_override=state_file)
        lines = capped.get("lines") or []
        _check(LINES_CAP == 5, "lines cap is 5")
        _check(len(lines) == LINES_CAP, "lines list is capped at 5")
        _check(
            [row.get("speakable") for row in lines]
            == ["線2です。", "線6です。", "線5です。", "線4です。", "線3です。"],
            "newest used first, duplicate once, cap 5",
        )
        _check(
            all(set(row.keys()) == {"speakable"} for row in lines),
            "line objects have speakable only",
        )
        started = start_sitting(cards_path=cards_file, state_path_override=state_file)
        _check(str(started.get("card_id") or "").startswith("fallback:"), "all used starts fallback")
        mid = today_payload(cards_path=cards_file, state_path_override=state_file)
        _check(mid.get("sitting") is not None, "sitting branch still returns today")
        _check(mid.get("lines") == lines, "in-progress sitting still includes lines")
        finish_sitting(state_path_override=state_file)

    _check(PROMPT_REVISION == 10, "Chat PROMPT_REVISION is 10")
    _check(wo_ga_recast_stem("コーヒーを好きです") == "好き", "wo-suki stem")
    _check(wo_ga_recast_stem("日本語がわかる") == "", "ga-wakaru is not a miss")
    _check(wo_ga_recast_stem("猫好きです") == "", "no を is not a recast stem")
    _check(
        needs_wo_ga_recast("コーヒーを好きです", "いいね！毎日飲む？"),
        "forgive-only reply still needs recast",
    )
    _check(
        not needs_wo_ga_recast("コーヒーを好きです", "コーヒーが好きなんだね。毎日飲む？"),
        "recast in speech does not retry",
    )
    _check(
        not needs_wo_ga_recast("はい。", "そうなんだ。"),
        "natural short answer is not a recast miss",
    )
    _check(
        meaningful_correction("日本語を好きです", "日本語が好きです。") == "日本語が好きです",
        "meaningful_correction swaps を→が",
    )
    _check(
        meaningful_correction("日本語を好きです", "いいね！") == "",
        "meaningful_correction empty without が好き",
    )
    _check(
        recast_phrase("コーヒーを好きです", "コーヒーが好きなんだね。毎日飲む？")
        == "コーヒーが好きなんだね。",
        "caption is first recast sentence",
    )
    _check(
        recast_phrase("コーヒーを好きです", "いいね！毎日飲む？") == "",
        "forgive-only has no caption",
    )
    _check(
        recast_phrase("コーヒーが好きです", "コーヒーが好きなんだね。") == "",
        "already-ga learner has no caption",
    )
    hist = [
        {"role": "user", "content": "コーヒーを好きです"},
        {"role": "assistant", "content": "コーヒーが好きなんだね。毎日飲む？"},
    ]
    noticed = with_recast_notices(hist)
    _check(
        noticed[1].get("recast_phrase") == "コーヒーが好きなんだね。",
        "read-time attach on assistant",
    )
    _check("recast_phrase" not in hist[1], "does not mutate LLM history")
    plain = with_recast_notices(
        [{"role": "user", "content": "はい。"}, {"role": "assistant", "content": "そうなんだ。"}]
    )
    _check("recast_phrase" not in plain[1], "ordinary turn has no caption")
    _check(wo_ga_recast_stem("コーヒーをすきです") == "すき", "kana wo-suki stem is learner surface")
    _check(
        not needs_wo_ga_recast("コーヒーをすきです", "コーヒーが好きなんだね。"),
        "kana をすき + kanji が好き does not retry",
    )
    _check(
        not needs_wo_ga_recast("コーヒーを好きです", "コーヒーがすきなんだね。"),
        "kanji を好き + kana がすき does not retry",
    )
    _check(
        needs_wo_ga_recast("コーヒーをすきです", "いいね！毎日飲む？"),
        "kana をすき without が好き/すき still needs recast",
    )
    _check(
        recast_phrase("コーヒーをすきです", "コーヒーが好きなんだね。毎日飲む？")
        == "コーヒーが好きなんだね。",
        "caption accepts kanji が好き for kana miss",
    )
    _check(
        recast_phrase("コーヒーをすきです", "いいね！毎日飲む？") == "",
        "kana miss without が好き/すき has no caption",
    )
    _check(
        meaningful_correction("コーヒーをすきです", "コーヒーが好きなんだね。")
        == "コーヒーがすきです",
        "correction swaps learner kana surface",
    )
    _check(
        meaningful_correction("コーヒーを好きです", "コーヒーがすきなんだね。")
        == "コーヒーが好きです",
        "correction swaps learner kanji when tutor used kana",
    )
    kept, landed = prefer_recast_reply(
        "コーヒーを好きです",
        "いいね！毎日飲む？",
        "そうなんだ。よく飲むの？",
    )
    _check(
        landed is True and kept == "コーヒーが好きなんだね。",
        "retry miss splices the model sentence only",
    )
    used, ok = prefer_recast_reply(
        "コーヒーを好きです",
        "いいね！毎日飲む？",
        "コーヒーが好きなんだね。毎日飲む？",
    )
    _check(ok is True and "が好き" in used, "retry with が好き is kept")
    mixed_ok, mixed_landed = prefer_recast_reply(
        "コーヒーをすきです",
        "いいね！",
        "コーヒーが好きなんだね。",
    )
    _check(mixed_landed is True and mixed_ok == "コーヒーが好きなんだね。", "retry kanji lands kana miss")
    _check(
        splice_wo_ga_model("コーヒーを好きです", "いいね！") == "コーヒーが好きなんだね。",
        "splice is the model sentence, not leftover",
    )
    _check(
        word_family_pair("今日は眠りです", "眠い？") == ("眠り", "眠い"),
        "nemuri vs nemui is a word-family miss",
    )
    _check(
        word_family_pair("すみません眠りわからない", "眠い？") is None,
        "nemuri-wakaranai is not a recast miss",
    )
    _check(
        word_family_pair("楽しみです", "楽しい？") is None,
        "tanoshimi-desu is not a nemui miss",
    )
    _check(
        word_family_pair("楽しみにしてる", "楽しい？") is None,
        "tanoshimi-ni-shiteru is not a nemui miss",
    )
    sleepy_hist = [
        {"role": "assistant", "content": "眠い？"},
        {"role": "user", "content": "今日は眠りです"},
        {"role": "assistant", "content": "眠いんだね。まだ早いよ。"},
    ]
    sleepy_noticed = with_recast_notices(sleepy_hist)
    _check(
        "眠い" in str(sleepy_noticed[2].get("recast_phrase") or ""),
        "word-family recast gets a caption",
    )
    _check(
        why_line(
            {
                "learner_line": "コーヒーを好きです",
                "speakable": "コーヒーが好きです",
            }
        ).startswith("You said を好き"),
        "Why? names the を/が pair",
    )
    rescued = with_recast_notices(
        [
            {"role": "user", "content": "コーヒーを好きです"},
            {
                "role": "assistant",
                "content": "コーヒーが好き。毎日？",
                "rescue": True,
            },
        ]
    )
    _check("recast_phrase" not in rescued[1], "rescue assistant has no caption")
    _check(
        noticed[1].get("recast_phrase") == "コーヒーが好きなんだね。",
        "normal recast still captions after rescue skip",
    )
    sitting_prompt = build_practice_sitting_system_prompt(
        UserPrefs(),
        {"learner_line": "日本語を好きです", "tutor_reply": "日本語が好きです。"},
        remaining_turns=2,
        opening=True,
    )
    _check("[practice_sitting]" in sitting_prompt, "sitting prompt is separate from Chat")
    _check("会話のために教える" not in sitting_prompt, "sitting drops Chat identity leftover")
    _check("口に出して" in sitting_prompt, "opening is say-this rehearsal")
    _check("Easy Chat の続きにしない" in sitting_prompt, "sitting is not a second Easy chat")
    _check("新しい文法" in sitting_prompt, "sitting does not teach new grammar")
    _check("TRY: は出さない" in sitting_prompt, "sitting does not emit TRY:")
    mid_prompt = build_practice_sitting_system_prompt(
        UserPrefs(),
        {
            "learner_line": "日本語を好きです",
            "tutor_reply": "日本語が好きです。",
            "speakable": "日本語が好きです。",
        },
        remaining_turns=1,
        opening=False,
    )
    _check("短いやり取りを1つ" in mid_prompt, "second beat is one tiny exchange")

    print("smoke_struggle_cards ok")


if __name__ == "__main__":
    main()
