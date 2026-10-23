"""Beginner-scenario contracts: learner-state, recast, cards, sitting, Learn.

Does not call DeepSeek or Whisper. Claimed by Testing Agent in
kaiwa-sprint/06-testing.md so Lead does not duplicate these cases.

If prompts later change, keep these as behavioral contracts
(infer_*, wo_ga, maybe_write_card, sitting wrap, Learn cluster, identity dump).
"""

from __future__ import annotations

import inspect
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaiwa.learner_profile import LearnerProfile, apply_chat_signals
from kaiwa.persona import (
    PRIORITY_HIERARCHY_BLOCK,
    PROMPT_REVISION,
    build_practice_sitting_system_prompt,
    build_tutor_system_prompt,
    compute_support_mode,
    infer_help_type,
    infer_learner_state,
    recast_hint_block,
    rescue_rewrite_block,
    support_mode_block,
    wants_explicit_english,
)
from kaiwa.prefs import UserPrefs
from kaiwa.practice.cards import (
    SPEAKABLE_AGAIN,
    SPEAKABLE_ETTO,
    english_unsolicited,
    freeze_speakable,
    is_freeze_line,
    is_natural_answer,
    is_practice_worthy,
    is_recast_family_line,
    maybe_write_card,
    meaningful_correction,
    newest_unused,
    practice_worthy_line,
    snapshot_signal,
)
from kaiwa.practice.learn import STARTER_CARDS, skip_learn_line, today_payload as learn_today
from kaiwa.practice.sitting import (
    FALLBACK_PREFIX,
    MAX_LEARNER_TURNS,
    append_learner_turn,
    consume_pending_elicit,
    finish_sitting,
    peek_pending_elicit,
    remaining_learner_turns,
    start_sitting,
    today_payload as practice_today,
)
from kaiwa.rescue import next_rescue_step
from kaiwa.reply_shape import reply_too_dense
from kaiwa.stt import empty_transcript_is_freeze, is_identity_prompt_dump, unheard_chat_payload
from kaiwa.wo_ga import (
    needs_wo_ga_recast,
    needs_word_family_recast,
    prefer_recast_reply,
    recast_phrase,
    splice_wo_ga_model,
    splice_word_family_model,
    with_recast_notices,
    wo_ga_recast_stem,
    word_family_pair,
)


RESULTS: list[tuple[str, str, bool]] = []


def _out(line: str) -> None:
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()


def _check(ok: bool, scenario: str, label: str) -> None:
    RESULTS.append((scenario, label, bool(ok)))
    status = "ok  " if ok else "FAIL"
    _out(f"{status} [{scenario}] {label}")


def _hist(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for role, content in pairs:
        out.append({"role": role, "content": content})
    return out


def _write_card(path: Path, **kwargs):
    return maybe_write_card(path=path, **kwargs)


def scenario_doesnt_understand(tmp: Path) -> None:
    s = "doesnt-understand"
    cases = [
        ("わからない", "comprehension"),
        ("分からない", "comprehension"),
        ("わかんない", "comprehension"),
        ("i don't understand", "comprehension"),
        ("don't understand", "comprehension"),
        ("ゆっくりください", "comprehension"),
        ("lots of words", "comprehension"),
        ("会話がわからない", "comprehension"),
        ("わかりません", "comprehension"),
        ("日本語でわからない", "comprehension"),
    ]
    for text, want in cases:
        _check(infer_learner_state(text) == "help_request", s, f"{text!r} is help_request")
        _check(infer_help_type(text) == want, s, f"{text!r} help_type={want}")

    _check(
        snapshot_signal(learner_state="help_request") == "help_request",
        s,
        "help_request snapshots",
    )
    _check(
        compute_support_mode(
            learner_state="help_request", help_type="comprehension", struggle_streak=0
        )
        == "simplified",
        s,
        "first comprehension miss is simplified",
    )
    _check(
        compute_support_mode(
            learner_state="help_request", help_type="comprehension", struggle_streak=3
        )
        == "heavy",
        s,
        "streak-3 comprehension is heavy",
    )

    card = _write_card(
        tmp,
        session_id="s-unk",
        history=_hist(("assistant", "眠い？"), ("user", "わからない")),
        learner_state=infer_learner_state("わからない"),
        transcript="わからない",
        reply="短く言うね。眠い？",
    )
    _check(card is not None and card["signal"] == "help_request", s, "わからない writes help card")
    _check(
        card is not None and card["help_type"] == "comprehension",
        s,
        "わからない card is comprehension",
    )
    _check(not is_practice_worthy(card), s, "help 短く言うね is not today-worthy")
    _check(
        newest_unused(cards=[card], used_ids=[]) is None,
        s,
        "junk help does not win newest_unused",
    )
    _check(not practice_worthy_line("ごめん。"), s, "ごめん is not practice-worthy")
    _check(not practice_worthy_line("そうなんだ。"), s, "そうなんだ is not practice-worthy")
    _check(
        not practice_worthy_line("「眠い」は sleepy。"),
        s,
        "gloss line is not practice-worthy",
    )
    _check(
        not practice_worthy_line("The weather is nice today"),
        s,
        "English-heavy line is not practice-worthy",
    )
    _check(practice_worthy_line("コーヒーが好きです"), s, "が好き is practice-worthy")
    _check(practice_worthy_line("眠いです"), s, "眠い is practice-worthy")
    _check(is_recast_family_line("コーヒーが好きです"), s, "が好き is recast-family")
    _check(is_recast_family_line("眠いです"), s, "眠い is recast-family")

    simp = support_mode_block("simplified", "comprehension")
    _check("選択肢" not in simp, s, "simplified collapse does not demand 選択肢")
    _check("同じ考え" in simp, s, "simplified collapse paraphrases the same idea")
    _check("二択にしない" in simp, s, "simplified collapse forbids A/B")
    heavy = support_mode_block("heavy", "comprehension")
    _check("選択肢" not in heavy, s, "heavy collapse does not demand 選択肢")
    _check("同じ考え" in heavy, s, "heavy collapse paraphrases the same idea")
    _check(
        "選択肢" not in PRIORITY_HIERARCHY_BLOCK,
        s,
        "hierarchy collapse does not demand 選択肢",
    )
    collapse_prompt = build_tutor_system_prompt(
        UserPrefs(),
        last_user_text="わからない",
        profile=LearnerProfile(placement_completed=True, speaking_level="pre_n5"),
    )
    _check("選択肢" not in collapse_prompt, s, "Chat collapse prompt has no 選択肢")
    _check("同じ考え" in collapse_prompt, s, "Chat collapse prompt paraphrases")
    _check(PROMPT_REVISION == 10, s, "Chat PROMPT_REVISION is 10")


def scenario_misunderstands(tmp: Path) -> None:
    s = "misunderstands"
    # Word-family miss: 眠り for 眠い. わからない about that word is vocab, not collapse.
    line = "すみません眠りわからない"
    _check(infer_learner_state(line) == "help_request", s, "眠りわからない is help_request")
    _check(infer_help_type(line) == "vocabulary", s, "眠りわからない is vocabulary not collapse")
    _check(wo_ga_recast_stem(line) == "", s, "眠り is not a を→が stem")
    _check(
        recast_hint_block(line) == "",
        s,
        "眠りわからない does not inject [recast]",
    )
    _check(
        recast_phrase("すみません眠りです", "眠いんだね。") == "眠いんだね。",
        s,
        "眠り vs 眠い recast caption is the model sentence",
    )
    _check(
        "眠い" in meaningful_correction("すみません眠りです", "眠いんだね。今日は？"),
        s,
        "眠り vs 眠い writes a swapped speakable",
    )

    sleepy = "今日は眠りです"
    _check(
        word_family_pair(sleepy, "眠い？") == ("眠り", "眠い"),
        s,
        "眠り vs 眠い is a word-family miss",
    )
    _check(
        needs_word_family_recast(sleepy, "いいね！", "眠い？"),
        s,
        "forgive-only 眠り still needs 眠い in speech",
    )
    sleepy_hint = recast_hint_block(sleepy, "眠い？")
    _check("[recast]" in sleepy_hint, s, "眠りです injects [recast]")
    _check("眠い" in sleepy_hint, s, "眠り hint names 眠い")
    spliced_sleepy, sleepy_landed = prefer_recast_reply(
        sleepy, "そうなんだ。", "今日だね。", last_assistant="眠い？"
    )
    _check(
        sleepy_landed is True and spliced_sleepy == "眠いんだね。",
        s,
        "both-miss 眠り splice is the model sentence only",
    )
    _check(
        not reply_too_dense(spliced_sleepy),
        s,
        "眠り splice is not two ideas",
    )
    _check(
        splice_word_family_model(sleepy, "そうなんだ。", "眠い？") == "眠いんだね。",
        s,
        "word-family splice is 眠いんだね。 only",
    )
    _check(
        word_family_pair("楽しみです", "楽しい？") is None,
        s,
        "楽しみです is not a 眠り/眠い miss",
    )
    _check(
        word_family_pair("楽しみにしてる", "楽しい？") is None,
        s,
        "楽しみにしてる is not a 眠り/眠い miss",
    )
    _check(
        not needs_word_family_recast("楽しいです", "楽しいだね。", "楽しい？"),
        s,
        "楽しいです is not a recast miss",
    )
    _check(
        recast_hint_block("楽しみです", "楽しい？") == "",
        s,
        "楽しみです does not inject [recast]",
    )

    vocab = "眠いってどういう意味？"
    _check(infer_help_type(vocab) == "vocabulary", s, "眠いってどういう意味 is vocabulary")
    _check(infer_learner_state(vocab) == "help_request", s, "vocab ask is help_request")
    _check(
        compute_support_mode(
            learner_state="help_request", help_type="vocabulary", struggle_streak=0
        )
        == "light",
        s,
        "vocab help is light not simplified",
    )
    vocab_card = _write_card(
        tmp,
        session_id="s-nemui-vocab",
        history=_hist(("assistant", "眠い？"), ("user", vocab)),
        learner_state="help_request",
        transcript=vocab,
        reply="「眠い」は sleepy。眠い？",
        better_phrase="眠いです。",
    )
    _check(
        vocab_card is not None and vocab_card["help_type"] == "vocabulary",
        s,
        "vocab ask writes vocabulary card",
    )

    # Wrong-topic but grammatical JP is flowing and not a card.
    flowing = _write_card(
        tmp,
        session_id="s-wrong-topic",
        history=_hist(("assistant", "眠い？"), ("user", "コーヒーが好きです")),
        learner_state=infer_learner_state("コーヒーが好きです"),
        transcript="コーヒーが好きです",
        reply="そうなんだ。コーヒー好き？",
    )
    _check(infer_learner_state("コーヒーが好きです") == "flowing", s, "full JP answer is flowing")
    _check(flowing is None, s, "off-topic but grammatical JP does not snapshot")


def scenario_incorrect_answer(tmp: Path) -> None:
    s = "incorrect-answer"
    pairs = [
        ("コーヒーを好きです", "好き"),
        ("日本語をすきです", "すき"),
        ("日本語をわかる", "わかる"),
        ("水をほしい", "ほしい"),
        ("料理をできる", "できる"),
        ("漢字を分かる", "分かる"),
        ("水を欲しい", "欲しい"),
        ("料理を出来る", "出来る"),
    ]
    for learner, stem in pairs:
        _check(wo_ga_recast_stem(learner) == stem, s, f"{learner} stem is {stem}")
        _check(
            needs_wo_ga_recast(learner, "いいね！"),
            s,
            f"{learner} forgive-only still needs recast",
        )
        hint = recast_hint_block(learner)
        _check("[recast]" in hint, s, f"{learner} injects [recast]")
        _check(f"が{stem}" in hint, s, f"{learner} hint names が{stem}")

    model = "コーヒーが好きなんだね。毎日飲む？"
    _check(
        not needs_wo_ga_recast("コーヒーを好きです", model),
        s,
        "spoken が好き does not retry",
    )
    _check(
        recast_phrase("コーヒーを好きです", model) == "コーヒーが好きなんだね。",
        s,
        "caption is first recast sentence",
    )
    noticed = with_recast_notices(
        _hist(("user", "コーヒーを好きです"), ("assistant", model))
    )
    _check(
        noticed[1].get("recast_phrase") == "コーヒーが好きなんだね。",
        s,
        "read-time recast_phrase on assistant",
    )

    recast_card = _write_card(
        tmp,
        session_id="s-wo-suki",
        history=_hist(("assistant", "何が好き？"), ("user", "コーヒーを好きです")),
        learner_state="flowing",
        transcript="コーヒーを好きです",
        reply=model,
    )
    _check(
        recast_card is not None and recast_card["speakable"] == "コーヒーが好きです",
        s,
        "を好き writes swapped speakable",
    )
    _check(
        recast_card is not None and recast_card["learner_line"] == "コーヒーを好きです",
        s,
        "correction keeps original learner line",
    )
    no_model = _write_card(
        tmp,
        session_id="s-wo-none",
        history=_hist(("assistant", "何が好き？"), ("user", "コーヒーを好きです")),
        learner_state="flowing",
        transcript="コーヒーを好きです",
        reply="いいね！毎日飲む？",
    )
    _check(no_model is None, s, "を好き without が好き in tutor does not write")
    already = _write_card(
        tmp,
        session_id="s-already-ga",
        history=_hist(("assistant", "何が好き？"), ("user", "コーヒーが好きです")),
        learner_state="flowing",
        transcript="コーヒーが好きです",
        reply=model,
    )
    _check(already is None, s, "already が好き does not write")

    spliced, landed = prefer_recast_reply(
        "コーヒーを好きです",
        "いいね！毎日飲む？",
        "そうなんだ。よく飲むの？",
    )
    _check(
        landed is True and spliced == "コーヒーが好きなんだね。",
        s,
        "both-miss splice speaks only コーヒーが好きなんだね。",
    )
    _check(not reply_too_dense(spliced), s, "both-miss splice is not two ideas")
    _check(
        splice_wo_ga_model("コーヒーを好きです", "いいね！毎日飲む？")
        == "コーヒーが好きなんだね。",
        s,
        "splice is the model sentence, not forgive-only leftover",
    )
    retry_ok, retry_landed = prefer_recast_reply(
        "コーヒーを好きです",
        "いいね！毎日飲む？",
        "コーヒーが好きなんだね。毎日飲む？",
    )
    _check(
        retry_landed is True and retry_ok.startswith("コーヒーが好き"),
        s,
        "retry that landed が好き is kept",
    )


def scenario_stuck_and_freeze(tmp: Path) -> None:
    s = "stuck-freeze"
    _check(infer_learner_state("") == "flowing", s, "empty transcript infer is flowing")
    _check(infer_learner_state("um") == "flowing", s, "um filler infer is flowing")
    _check(is_freeze_line("えっと…"), s, "えっと is freeze")
    _check(is_freeze_line("um"), s, "um is freeze")
    _check(is_freeze_line("..."), s, "ellipsis is freeze")
    _check(is_freeze_line("もう一回お願いします"), s, "survival again is freeze")
    _check(not is_freeze_line("はい"), s, "はい is not freeze")
    _check(freeze_speakable("um") == SPEAKABLE_ETTO, s, "um speakable is えっと…")
    _check(
        freeze_speakable("もう一度お願いします") == SPEAKABLE_AGAIN,
        s,
        "mou ichido speakable kept",
    )

    prior = _hist(("user", "こんにちは"), ("assistant", "今日は何したの？"))
    etto = _write_card(
        tmp,
        session_id="s-etto",
        history=prior + [{"role": "user", "content": "えっと…"}],
        learner_state="flowing",
        transcript="えっと…",
        reply="ゆっくりでいいよ。",
    )
    _check(
        etto is not None and etto["speakable"] == SPEAKABLE_ETTO,
        s,
        "etto freeze writes survival speakable",
    )

    empty = _write_card(
        tmp,
        session_id="s-empty",
        history=prior,
        learner_state="flowing",
        transcript="",
        reply="今日は何したの？",
    )
    _check(
        empty is not None and empty["learner_line"] == "…" and empty["speakable"] == SPEAKABLE_ETTO,
        s,
        "empty STT freeze writes ellipsis line",
    )
    _check(
        empty is not None and empty["learner_line"] != "こんにちは",
        s,
        "empty freeze does not steal previous user line",
    )
    no_asst = _write_card(
        tmp,
        session_id="s-no-asst",
        history=[],
        learner_state="flowing",
        transcript="",
        reply="今日は何したの？",
    )
    _check(no_asst is None, s, "empty freeze without prior assistant skips")

    dump = "会話 会話 会話"
    _check(is_identity_prompt_dump(dump), s, "kaiwa dump counts as unheard")
    _check(
        not empty_transcript_is_freeze({"accepted": "identity_dump"}),
        s,
        "identity dump skip freeze-card at STT gate",
    )
    heard = "" if is_identity_prompt_dump(dump) else dump
    dump_card = _write_card(
        tmp,
        session_id="s-dump-empty",
        history=prior,
        learner_state=infer_learner_state(heard),
        transcript=heard,
        reply="今日は何したの？",
    )
    _check(
        dump_card is not None and dump_card["speakable"] == SPEAKABLE_ETTO,
        s,
        "empty transcript still freeze-cards at the card layer",
    )
    _check(
        newest_unused(cards=[etto, empty, dump_card], used_ids=[]) is None,
        s,
        "freeze-only unused cards do not win today's sitting",
    )
    freeze_today = practice_today(
        cards_path=tmp,
        state_path_override=tmp.with_name("freeze-today-state.json"),
    )
    _check(freeze_today.get("fallback") is True, s, "freeze-only today uses canned fallback")
    _check(
        str(freeze_today.get("card_id") or "") == "fallback:suki",
        s,
        "default canned sitting is コーヒーが好きです not えっと",
    )


def scenario_english(tmp: Path) -> None:
    s = "uses-english"
    unsolicited = "The weather is nice today"
    _check(infer_learner_state(unsolicited) == "struggling", s, "English-heavy is struggling")
    _check(english_unsolicited(unsolicited), s, "unsolicited English flag")
    _check(not wants_explicit_english(unsolicited), s, "weather line is not an EN ask")
    en_card = _write_card(
        tmp,
        session_id="s-en",
        history=_hist(("assistant", "今日は何したの？"), ("user", unsolicited)),
        learner_state="struggling",
        transcript=unsolicited,
        reply="天気の話だね。",
    )
    _check(en_card is not None and en_card["learner_line"] == unsolicited, s, "unsolicited EN writes")
    _check(not is_practice_worthy(en_card), s, "English-heavy card is not today-worthy")

    ask = "英語で"
    _check(infer_learner_state(ask) == "help_request", s, "英語で is help_request")
    _check(wants_explicit_english(ask), s, "英語で is explicit English")
    _check(not english_unsolicited(ask), s, "explicit ask is not unsolicited EN")
    ask_card = _write_card(
        tmp,
        session_id="s-en-ask",
        history=_hist(("assistant", "今日は何したの？"), ("user", ask)),
        learner_state="help_request",
        transcript=ask,
        reply="Okay, briefly.",
    )
    _check(
        ask_card is not None and ask_card["signal"] == "help_request",
        s,
        "explicit EN ask stays help_request",
    )

    how = "how do I say movie"
    _check(infer_help_type(how) == "vocabulary", s, "how do I say is vocabulary")
    _check(infer_learner_state(how) == "help_request", s, "how do I say is help_request")


def scenario_short_answer(tmp: Path) -> None:
    s = "short-answer-not-struggle"
    _check(is_natural_answer("はい。", "元気？"), s, "はい after 元気 is natural")
    _check(is_natural_answer("うん", "コーヒー、好き？"), s, "うん after suki? is natural")
    _check(is_natural_answer("好き", "コーヒー、好き？"), s, "好き after suki? is natural")
    _check(is_natural_answer("パスタ。", "何を食べた？"), s, "パスタ after what-did-you-eat is natural")
    _check(
        not is_natural_answer("はい。", "何を食べた？"),
        s,
        "はい after WH is not a natural answer",
    )
    _check(
        infer_learner_state("はい。") == "flowing",
        s,
        "はい is flowing, not punished as a short struggle",
    )
    _check(
        infer_learner_state("はい。", "今日は何したの？") == "struggling",
        s,
        "はい after WH is struggling, not a fake yes",
    )

    flowing_profile = LearnerProfile(placement_completed=True, speaking_level="pre_n5")
    apply_chat_signals(
        flowing_profile,
        infer_learner_state("はい。", "元気？"),
        "はい。",
    )
    _check(
        flowing_profile.stats.struggle_streak == 0,
        s,
        "はい after 元気 does not bump struggle_streak",
    )
    wh_profile = LearnerProfile(placement_completed=True, speaking_level="pre_n5")
    apply_chat_signals(
        wh_profile,
        infer_learner_state("はい。", "今日は何したの？"),
        "はい。",
    )
    _check(
        wh_profile.stats.struggle_streak >= 1,
        s,
        "はい after WH bumps struggle_streak",
    )
    pasta_state = infer_learner_state("パスタ。", "何を食べた？")
    _check(pasta_state == "flowing", s, "パスタ after WH stays flowing")

    hai = _write_card(
        tmp,
        session_id="s-hai",
        history=_hist(("assistant", "元気？"), ("user", "はい。")),
        learner_state="struggling",
        transcript="はい。",
        reply="よかった。",
    )
    _check(hai is None, s, "はい after genki does not write a card")
    pasta = _write_card(
        tmp,
        session_id="s-pasta",
        history=_hist(("assistant", "何を食べた？"), ("user", "パスタ。")),
        learner_state="struggling",
        transcript="パスタ。",
        reply="おいしかった？",
    )
    _check(pasta is None, s, "pasta after what-did-you-eat does not write")

    repeated = _write_card(
        tmp,
        session_id="s-rep",
        history=_hist(
            ("user", "うん。"),
            ("assistant", "映画を見たんだ。"),
            ("user", "うん。"),
        ),
        learner_state="struggling",
        transcript="うん。",
        reply="友達とね。",
    )
    _check(
        repeated is not None and repeated["learner_line"] == "うん。",
        s,
        "two minimal non-answers still write",
    )
    _check(not is_practice_worthy(repeated), s, "fake-yes うん card is not today-worthy")
    _check(
        newest_unused(cards=[repeated], used_ids=[]) is None,
        s,
        "fake-yes うん does not win newest_unused",
    )


def scenario_rescue(tmp: Path) -> None:
    s = "simpler-rescue"
    packed = (
        "こんにちは!そうですね、日本語はむずかしいです。"
        "でも、ゆっくり話せばだいじょうぶですよ。うんどうした?"
    )
    _check(next_rescue_step(packed) == "shorter", s, "packed reply → shorter")
    _check(next_rescue_step("日本語、難しいね。") == "yes_no", s, "short statement → yes_no")
    _check(next_rescue_step("猫好き？") == "shorter", s, "short yes/no → shorter not A/B")
    block = rescue_rewrite_block("猫好き？", "shorter")
    _check("[rescue]" in block, s, "rescue block tagged")
    _check("わからない" in block, s, "rescue forbids fake わからない utterance")
    _check("学習者の発言ではない" in block, s, "Simpler is not a learner turn")

    rescued = _write_card(
        tmp,
        session_id="s-rescue",
        history=_hist(("user", "映画が好き"), ("assistant", "短い返事。")),
        learner_state="help_request",
        transcript="",
        reply="映画、好き？",
        rescue=True,
    )
    _check(rescued is not None and rescued["signal"] == "rescue", s, "rescue writes card")
    _check(
        rescued is not None and rescued["learner_line"] == "映画が好き",
        s,
        "rescue uses previous user line",
    )
    _check(
        rescued is not None and rescued["help_type"] == "comprehension",
        s,
        "rescue help_type is comprehension",
    )
    empty_rescue = _write_card(
        tmp,
        session_id="s-rescue-empty",
        history=_hist(("assistant", "こんにちは")),
        learner_state="help_request",
        transcript="",
        reply="短くするね。",
        rescue=True,
    )
    _check(empty_rescue is None, s, "rescue without learner line skips")

    rescued_hist = with_recast_notices(
        [
            {"role": "user", "content": "コーヒーを好きです"},
            {"role": "assistant", "content": "コーヒーが好き。毎日？", "rescue": True},
        ]
    )
    _check("recast_phrase" not in rescued_hist[1], s, "rescue assistant has no recast caption")


def scenario_practice_wrap(tmp: Path, state: Path) -> None:
    s = "practice-wrap"
    prefs = UserPrefs()
    card = {
        "id": "card-wrap",
        "learner_line": "コーヒーを好きです",
        "tutor_reply": "コーヒーが好きです。",
        "speakable": "コーヒーが好きです。",
    }
    opening = build_practice_sitting_system_prompt(
        prefs, card, remaining_turns=2, opening=True
    )
    mid = build_practice_sitting_system_prompt(
        prefs, card, remaining_turns=1, opening=False
    )
    wrap = build_practice_sitting_system_prompt(
        prefs, card, remaining_turns=0, opening=False, wrap=True
    )
    wrap_even_if_left = build_practice_sitting_system_prompt(
        prefs, card, remaining_turns=2, opening=False, wrap=True
    )
    _check("[practice_sitting]" in opening, s, "sitting prompt is not Chat")
    _check("会話のために教える" not in opening, s, "sitting drops Chat identity leftover")
    _check("口に出して" in opening, s, "opening is say-this")
    _check("短いやり取りを1つ" in mid, s, "second beat is one exchange")
    _check("閉じる" in wrap, s, "wrap closes")
    _check("新しい質問は出さない" in wrap, s, "wrap does not elicit a new question")
    _check("Chat へ戻るよう促さない" in wrap, s, "wrap does not tell them to go to Chat")
    _check("短いやり取りを1つ" not in wrap, s, "wrap is not another exchange")
    _check("口に出してもらう" not in wrap, s, "wrap is not another say-this")
    _check("閉じる" in wrap_even_if_left, s, "wrap flag wins over remaining_turns")
    _check("TRY: は出さない" in wrap, s, "sitting never emits TRY:")
    _check(MAX_LEARNER_TURNS == 2, s, "cap is say-this plus one exchange")

    recast = _write_card(
        tmp,
        session_id="s-wrap-recast",
        history=_hist(("assistant", "何が好き？"), ("user", "コーヒーを好きです")),
        learner_state="flowing",
        transcript="コーヒーを好きです",
        reply="コーヒーが好きなんだね。",
    )
    _check(recast is not None, s, "wrap path has a Chat recast card")
    assert recast is not None
    sitting = start_sitting(cards_path=tmp, state_path_override=state)
    _check(sitting.get("card_id") == recast["id"], s, "Start uses unused recast card")
    _check(remaining_learner_turns(sitting) == 2, s, "fresh sitting has 2 learner turns")
    append_learner_turn(sitting, "コーヒーが好きです。")
    _check(sitting["done"] is False, s, "first learner turn is not wrap yet")
    append_learner_turn(sitting, "はい。")
    _check(sitting["done"] is True, s, "second learner turn finishes sitting")
    _check(remaining_learner_turns(sitting) == 0, s, "no remaining turns after cap")
    finished = finish_sitting(state_path_override=state)
    _check(finished.get("marked_used") is True, s, "finish after wrap marks card used")
    after = practice_today(cards_path=tmp, state_path_override=state)
    _check(after.get("sitting") is None, s, "after finish there is no active sitting")
    _check(after.get("fallback") is True, s, "used recast falls back for Practice Start")
    _check(
        str(after.get("card_id") or "").startswith(FALLBACK_PREFIX),
        s,
        "next today is canned 9.8",
    )
    lines = {row.get("speakable") for row in (after.get("lines") or [])}
    _check("コーヒーが好きです" in lines, s, "finished recast appears in Things you can say")

    chat_sig = inspect.signature(build_tutor_system_prompt)
    _check(
        "elicit_line" in chat_sig.parameters,
        s,
        "Chat prompt builder has an elicit slot after Practice",
    )
    chat_prompt = build_tutor_system_prompt(
        prefs, last_user_text="はい。", elicit_line="コーヒーが好きです。"
    )
    _check(
        "[elicit]" in chat_prompt and "コーヒーが好きです。" in chat_prompt,
        s,
        "next Chat turn can invite the practiced line",
    )
    _check(
        "その全文を先に口に出さない" in chat_prompt,
        s,
        "elicit asks a hook instead of speaking the rehearsed line",
    )
    _check("口頭で先にその形を短く使ってよい" not in chat_prompt, s, "elicit does not pre-say the form")
    _check("今ターンはからかわない" in chat_prompt, s, "elicit turn forbids roast")
    _check("[practice_sitting]" not in chat_prompt, s, "Chat prompt is not a sitting prompt")
    _check(
        finished.get("pending_elicit") == "コーヒーが好きです",
        s,
        "finish queues the practiced line for one Chat elicit",
    )
    _check(
        peek_pending_elicit(state) == "コーヒーが好きです",
        s,
        "peek leaves the elicit pending",
    )
    _check(
        consume_pending_elicit(state) == "コーヒーが好きです",
        s,
        "first Chat turn consumes the elicit",
    )
    _check(peek_pending_elicit(state) == "", s, "elicit is one-shot")

    freeze_card = _write_card(
        tmp,
        session_id="s-wrap-freeze",
        history=_hist(("assistant", "ゆっくりでいいよ。"), ("user", "えっと")),
        learner_state="flowing",
        transcript="えっと",
        reply="ゆっくりでいいよ。",
    )
    _check(freeze_card is not None, s, "survival card exists for elicit skip")
    freeze_state = tmp.parent / "w-freeze-state.json"
    freeze_sitting = start_sitting(
        card_id=freeze_card["id"],
        cards_path=tmp,
        state_path_override=freeze_state,
    )
    _check(freeze_sitting.get("card_id") == freeze_card["id"], s, "survival sitting starts")
    freeze_done = finish_sitting(state_path_override=freeze_state, mark_used=True)
    _check(
        freeze_done.get("pending_elicit") == "",
        s,
        "survival えっと is not elicited in Chat",
    )


def scenario_learn_picker(tmp: Path) -> None:
    s = "learn-picker"
    empty = learn_today(cards_path=tmp)
    _check(empty.get("source") == "starter", s, "empty Learn uses starters")
    ids = [row.get("card_id") for row in (empty.get("lines") or [])]
    _check(
        ids == [card["id"] for card in STARTER_CARDS],
        s,
        "starter ids are learn:suki / iku / wakaranai",
    )
    _check(skip_learn_line(SPEAKABLE_ETTO), s, "freeze えっと is not a Learn line")
    _check(skip_learn_line(SPEAKABLE_AGAIN), s, "survival again is not a Learn line")
    _check(not skip_learn_line("コーヒーが好きです"), s, "recast speakable is Learn-eligible")
    _check(skip_learn_line("ごめん。"), s, "ごめん is not a Learn line")
    _check(skip_learn_line("そうなんだ。"), s, "そうなんだ is not a Learn line")
    _check(skip_learn_line("「眠い」は sleepy。"), s, "gloss is not a Learn line")

    freeze = _write_card(
        tmp,
        session_id="s-learn-freeze",
        history=_hist(("assistant", "ゆっくりでいいよ。"), ("user", "えっと")),
        learner_state="flowing",
        transcript="えっと",
        reply="ゆっくりでいいよ。",
    )
    _check(freeze is not None, s, "freeze card exists")
    freeze_only = learn_today(cards_path=tmp)
    _check(freeze_only.get("source") == "starter", s, "freeze-only Learn still uses starters")
    _check(
        SPEAKABLE_ETTO not in [row.get("speakable") for row in freeze_only["lines"]],
        s,
        "freeze speakable is not listed on Learn",
    )

    junk_help = _write_card(
        tmp,
        session_id="s-learn-junk",
        history=_hist(("assistant", "眠い？"), ("user", "わからない")),
        learner_state="help_request",
        transcript="わからない",
        reply="ごめん。",
    )
    _check(junk_help is not None, s, "junk help card writes")
    _check(not is_practice_worthy(junk_help), s, "Learn junk help is not practice-worthy")
    gloss = _write_card(
        tmp,
        session_id="s-learn-gloss",
        history=_hist(("assistant", "眠い？"), ("user", "眠いってどういう意味？")),
        learner_state="help_request",
        transcript="眠いってどういう意味？",
        reply="「眠い」は sleepy。",
    )
    _check(gloss is not None, s, "gloss help card writes")
    junk_only = learn_today(cards_path=tmp)
    _check(junk_only.get("source") == "starter", s, "junk-only Learn still uses starters")

    recast = _write_card(
        tmp,
        session_id="s-learn-recast",
        history=_hist(("assistant", "何が好き？"), ("user", "コーヒーを好きです")),
        learner_state="flowing",
        transcript="コーヒーを好きです",
        reply="コーヒーが好きなんだね。",
    )
    _check(recast is not None, s, "Learn recast card writes")
    mixed = learn_today(cards_path=tmp)
    _check(mixed.get("source") == "chat", s, "recast card is Learn-eligible")
    speak = [row.get("speakable") for row in mixed["lines"]]
    _check("コーヒーが好きです" in speak, s, "recast speakable is listed")
    _check(SPEAKABLE_ETTO not in speak, s, "freeze skipped when recast exists")
    _check("ごめん。" not in speak, s, "junk ごめん is not a Learn cluster winner")
    _check("「眠い」は sleepy。" not in speak, s, "gloss is not a Learn cluster winner")
    picked = newest_unused(path=tmp)
    _check(
        picked is not None and recast is not None and picked.get("id") == recast["id"],
        s,
        "recast wins newest_unused over later junk",
    )
    _check(
        all("help_type" not in row and "signal" not in row for row in mixed["lines"]),
        s,
        "Learn lines have no tags",
    )


def scenario_identity_dump() -> None:
    s = "identity-dump"
    dumps = [
        "会話",
        "会話さん",
        "会話 会話 会話",
        "Kaiwa",
        "kaiwa kaiwa",
        "カイワ",
        "Kaiwa!",
        "会話、会話、会話",
    ]
    for text in dumps:
        _check(is_identity_prompt_dump(text), s, f"{text!r} is identity dump")
    _check(
        not empty_transcript_is_freeze({"accepted": "identity_dump"}),
        s,
        "identity dump does not write a freeze card",
    )
    payload = unheard_chat_payload({"accepted": "identity_dump"})
    _check(payload.get("type_retry") is True, s, "unheard Chat asks the learner to type")
    _check(payload.get("heard") is False, s, "unheard Chat does not invent a tutor turn")
    _check(payload.get("identity_dump") is True, s, "identity dump is tagged unheard")
    empty_retry = unheard_chat_payload(None)
    _check(empty_retry.get("type_retry") is True, s, "empty Whisper still asks to type")
    _check(empty_retry.get("identity_dump") is False, s, "ordinary empty clip is not an identity dump")
    _check(
        empty_transcript_is_freeze({"accepted": "ja"}),
        s,
        "true empty Japanese still freeze-cards",
    )
    keep = [
        "音楽がわからない",
        "会話がわからない",
        "あ れーりーよー Kaiwa さーわ",
        "Hello Kaiwa",
        "私はKaiwaが好き",
        "",
    ]
    for text in keep:
        _check(not is_identity_prompt_dump(text), s, f"{text!r} is not rewritten as dump")


def main() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        scenario_doesnt_understand(root / "u.jsonl")
        scenario_misunderstands(root / "m.jsonl")
        scenario_incorrect_answer(root / "i.jsonl")
        scenario_stuck_and_freeze(root / "f.jsonl")
        scenario_english(root / "e.jsonl")
        scenario_short_answer(root / "a.jsonl")
        scenario_rescue(root / "r.jsonl")
        scenario_practice_wrap(root / "w.jsonl", root / "w-state.json")
        scenario_learn_picker(root / "l.jsonl")
        scenario_identity_dump()

    failed = [(sc, lab) for sc, lab, ok in RESULTS if not ok]
    by_sc: dict[str, list[bool]] = {}
    for sc, _lab, ok in RESULTS:
        by_sc.setdefault(sc, []).append(ok)
    _out("--- matrix ---")
    for sc, flags in by_sc.items():
        n_ok = sum(1 for x in flags if x)
        _out(f"{sc}: {n_ok}/{len(flags)} pass")
    _out(f"total {sum(1 for *_, ok in RESULTS if ok)}/{len(RESULTS)} pass")
    if failed:
        _out("FAILED:")
        for sc, lab in failed:
            _out(f"  [{sc}] {lab}")
        raise SystemExit(f"smoke_beginner failed: {len(failed)} check(s)")
    _out("smoke_beginner ok")


if __name__ == "__main__":
    main()
