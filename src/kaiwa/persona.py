from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from kaiwa.personalities_store import get_user_preset, list_user_presets
from kaiwa.prefs import UserPrefs


@dataclass(frozen=True)
class PersonalityPreset:
    id: str
    label: str
    description: str
    prompt_blurb: str
    source: str = "builtin"


PERSONALITY_PRESETS: list[PersonalityPreset] = [
    PersonalityPreset(
        id="friend",
        label="Friend",
        description="Casual peer, light joking, relaxed.",
        prompt_blurb=(
            "性格: 友だちみたいな話し相手。"
            "カジュアルで少し冗談もOK。くだけた日本語で。"
        ),
    ),
    PersonalityPreset(
        id="patient_tutor",
        label="Patient tutor",
        description="Calm teacher; clear and supportive.",
        prompt_blurb=(
            "性格: やさしい先生。"
            "落ち着いて、わかりやすく、焦らせない。"
        ),
    ),
    PersonalityPreset(
        id="genki_peer",
        label="Genki peer",
        description="Energetic and encouraging.",
        prompt_blurb=(
            "性格: 元気な同世代の友だち。"
            "明るく励ます。短くテンポよく。"
        ),
    ),
    PersonalityPreset(
        id="stoic_coach",
        label="Stoic coach",
        description="Concise and serious.",
        prompt_blurb=(
            "性格: ストイックなコーチ。"
            "無駄話は少ない。はっきり、短く、真剣に。"
        ),
    ),
    PersonalityPreset(
        id="anime_club",
        label="Anime club mate",
        description="Hobby chat, excited but still beginner JP.",
        prompt_blurb=(
            "性格: アニメ部の友だち。"
            "アニメや趣味の話が好きで元気。でも学習者向けにやさしい日本語で。"
            "専門用語はすぐ言い換える。短くテンポよく。"
        ),
    ),
    PersonalityPreset(
        id="funny_friend",
        label="Funny friend",
        description="Loving roast when you're hilariously wrong — then corrects you.",
        prompt_blurb=(
            "性格: 大好きな友だち。あたたかくて少しおちゃめ。"
            "学習者がすごくおかしな言い間違いをしたときだけ、優しくからかっていい"
            "（いじわる・バカにする・積み重ねない）。1ターンにからかいの一文は最大1つ。"
            "からかったあとは必ず短い正しい言い方で直す。学習を止めない。"
            "はずかしめない。やさしい日本語。短く。"
        ),
    ),
]

BASE_RULES = """\
あなたは日本語の会話パートナーです。学習者の話し相手になってください。

基本ルール:
- やさしい日本語で話す。レベルは初級寄り（pre-N5〜N5）。
- 難しい語は避けるか、すぐ言い換える。
- 返事は読み上げやすい日本語（箇条書きや記号は最小限）。
- 演技・ト書き・効果音は禁止。括弧の動作描写や *笑い* や （笑顔） などは絶対に書かない。会話の言葉だけ。
"""

NO_EMOTES_BLOCK = """\
演出禁止:
- (smiles) (clapping) *laughs* [nods] （笑顔）（拍手）などのト書き・感情演出を書かない。
- TTSで不自然になる動作メモはすべて禁止。本文の会話だけ書く。
"""

CORRECTION_BLOCKS = {
    "gentle": """\
訂正スタイル（やさしい）:
- 会話を止めない。自然に続けながら直す。
- 誤りがあれば、正しい言い方を短く言い直す程度。
- 長い説明や講義はしない。責めない。
""",
    "critique": """\
訂正スタイル（はっきり）:
- 会話は続けるが、誤りははっきり示す。
- 短い形で:（1）まちがい （2）正しい言い方 （3）ごく短い理由。
- それでも全体は短く。長い文法講義はしない。
""",
}

_HELP_RE = re.compile(
    r"(わからない|分からない|なにそれ|何それ|どういう意味|英語で|help|what does|"
    r"i don't understand|dont understand|don't understand|in english|mean\?)",
    re.IGNORECASE,
)
_LATIN_RE = re.compile(r"[A-Za-z]")
_JP_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def builtin_preset_ids() -> set[str]:
    return {p.id for p in PERSONALITY_PRESETS}


def resolve_preset(preset_id: str) -> PersonalityPreset | None:
    for preset in PERSONALITY_PRESETS:
        if preset.id == preset_id:
            return preset
    user = get_user_preset(preset_id)
    if user is None:
        return None
    return PersonalityPreset(
        id=user.id,
        label=user.label,
        description=user.description,
        prompt_blurb=user.prompt_blurb,
        source="user",
    )


def all_presets() -> list[PersonalityPreset]:
    out = list(PERSONALITY_PRESETS)
    for user in list_user_presets():
        out.append(
            PersonalityPreset(
                id=user.id,
                label=user.label,
                description=user.description,
                prompt_blurb=user.prompt_blurb,
                source="user",
            )
        )
    return out


def preset_public_list() -> list[dict[str, str]]:
    return [
        {
            "id": p.id,
            "label": p.label,
            "description": p.description,
            "source": p.source,
        }
        for p in all_presets()
    ]


def valid_personality_ids() -> set[str]:
    ids = builtin_preset_ids() | {"custom"}
    ids |= {p.id for p in list_user_presets()}
    return ids


def infer_learner_state(text: str | None) -> str:
    """Return flowing | struggling | help_request for adaptive language hints."""
    raw = (text or "").strip()
    if not raw:
        return "struggling"

    if _HELP_RE.search(raw):
        return "help_request"

    latin = len(_LATIN_RE.findall(raw))
    jp = len(_JP_RE.findall(raw))
    total_letters = latin + jp
    if total_letters == 0:
        return "struggling"

    latin_ratio = latin / total_letters
    if latin_ratio >= 0.55:
        return "struggling"

    # Very short / fragmented learner turns
    compact = re.sub(r"\s+", "", raw)
    if len(compact) <= 4 and jp < 3:
        return "struggling"
    if jp <= 2 and latin == 0 and len(compact) <= 6:
        return "struggling"

    return "flowing"


def language_policy_block(prefs: UserPrefs) -> str:
    help_lang = prefs.help_language or "en"
    if prefs.language_policy == "immerse":
        return f"""\
言語ポリシー（イマーション）:
- 会話も訂正も日本語のみ。英語や他言語の注釈は出さない。
- 学習者が困っていても、やさしい日本語で言い換えて続ける。
- help_language={help_lang} はこのモードでは使わない。
"""

    return f"""\
言語ポリシー（アダプティブ）:
- 基本は日本語イマーション。英語は最小限。
- 学習者が明らかに苦しい（英語だらけ・極端に短い・壊れた日本語・助け求め）ときだけ、
  ごく短い英語で訂正・説明してよい（help_language={help_lang}）。そのあとすぐやさしい日本語の質問で会話に戻る。
- 助けを明示的に求めたときも短い英語メモOK。
- 英語だけの長い会話にはしない。1ターンに英語は最大1〜2短い文。
"""


def speech_register_block(prefs: UserPrefs) -> str:
    if prefs.speech_register == "formal":
        return """\
話し方のレジスター（丁寧）:
- あなたは丁寧語（です・ます）で話す。礼儀正しい会話。
- 学習者がくだけすぎ／教科書っぽく不自然なら、丁寧な自然さに寄せる。
"""
    return """\
話し方のレジスター（カジュアル）:
- あなたはため口・友だち同士の話し方。親友みたいに自然に。
- 「です・ます」の硬い教科書調は自分の発話では避ける（必要な訂正説明は短く）。
- 学習者が堅すぎるとき（例: 「僕は元気ですよ」）は、もっと自然なカジュアルへ誘導してよい。
"""


def naturalness_tips_block(prefs: UserPrefs) -> str:
    if not prefs.naturalness_tips:
        return """\
自然さのヒント: オフ。文法的に通じる言い方への「不自然さ」コメントはしない。
"""

    register = prefs.speech_register
    lang_note = (
        "イマーション中はヒントも日本語のみ。"
        if prefs.language_policy == "immerse"
        else "苦しいときは短い英語ヒントでもよい。それ以外はやさしい日本語。"
    )
    if register == "casual":
        focus = (
            "カジュアルな自然さ。例: 「僕は元気ですよ」→「元気だよ」のように、"
            "硬すぎる・教科書っぽい部分を1つだけ指摘。"
        )
    else:
        focus = (
            "丁寧な会話としての自然さ。くだけすぎや不自然な教科書調を1つだけ指摘。"
        )

    return f"""\
自然さのヒント: オン。
- 文法的には合っていても、選んだレジスターとして不自然なら、1ターンに最大1つの短いヒント。
- {focus}
- 責めない。言い換え例を1つ出す。{lang_note}
"""


def learner_state_block(prefs: UserPrefs, last_user_text: str | None) -> str:
    if prefs.language_policy != "adaptive":
        return ""
    state = infer_learner_state(last_user_text)
    if state == "flowing":
        hint = "stay_ja"
    elif state == "help_request":
        hint = "brief_en_ok_then_ja"
    else:
        hint = "brief_en_correction_then_ja"
    return f"[learner_state: {state} | language_hint: {hint}]\n"


def personality_block(prefs: UserPrefs) -> str:
    custom = (prefs.personality_custom or "").strip()
    if prefs.personality_id == "custom":
        body = custom or "性格: カスタム。ていねいで短い日本語の話し相手。"
        return f"性格設定:\n{body}\n"

    preset = resolve_preset(prefs.personality_id) or resolve_preset("patient_tutor")
    assert preset is not None
    parts = [preset.prompt_blurb]
    if custom:
        parts.append(f"追加の指定: {custom}")
    return "性格設定:\n" + "\n".join(parts) + "\n"


def length_block(max_sentences: int) -> str:
    n = max(1, min(6, int(max_sentences)))
    return f"長さ: 返事は最大{n}文。それ以上は書かない。\n"


def level_and_profile_block(prefs: UserPrefs, profile: Any | None = None) -> str:
    from kaiwa.learner_profile import LearnerProfile, effective_speech_level

    if profile is None:
        profile = LearnerProfile()
    assert isinstance(profile, LearnerProfile)
    speech_pitch = effective_speech_level(prefs, profile)
    topics_goal = ", ".join(prefs.topic_preferences) if prefs.topic_preferences else "(none)"
    topics_live = ", ".join(profile.topic_tags) if profile.topic_tags else "(none)"
    notes = (profile.notes or "").strip() or "(none)"
    return f"""\
学習者レベル / 目標:
- 目標レベル (goal): {prefs.goal_level}
- 推定スピーキング: {profile.speaking_level}
- 推定理解力: {profile.comprehension_level}
- あなたの話し方の目安: {speech_pitch}（goal と理解力の低い方。pre_n5 未満にはしない）
- 信頼度: {profile.confidence:.2f}
- 希望トピック: {topics_goal}
- プロファイル・トピック: {topics_live}
- メモ: {notes}
- 語彙・テンポは推定理解力に合わせる。訂正はスピーキング推定に合わせる。難しすぎる表現は避ける。
"""


def build_tutor_system_prompt(
    prefs: UserPrefs,
    *,
    last_user_text: str | None = None,
    profile: Any | None = None,
    memory: Any | None = None,
) -> str:
    style = prefs.correction_style if prefs.correction_style in CORRECTION_BLOCKS else "gentle"
    from kaiwa.learner_memory import LearnerMemory, memory_prompt_block

    if memory is None:
        memory = LearnerMemory()
    parts = [
        BASE_RULES.strip(),
        "",
        language_policy_block(prefs).strip(),
        "",
        speech_register_block(prefs).strip(),
        "",
        level_and_profile_block(prefs, profile).strip(),
        "",
        memory_prompt_block(memory, prefs).strip(),
        "",
        CORRECTION_BLOCKS[style].strip(),
        "",
        naturalness_tips_block(prefs).strip(),
        "",
        personality_block(prefs).strip(),
        "",
        NO_EMOTES_BLOCK.strip(),
        "",
        length_block(prefs.max_sentences).strip(),
    ]
    state = learner_state_block(prefs, last_user_text).strip()
    if state:
        parts.extend(["", state])
    return "\n".join(parts)


def build_practice_tip_system_prompt(prefs: UserPrefs) -> str:
    if prefs.correction_style == "critique":
        tone = (
            "ヒントははっきり。違いを具体的に1つ指摘し、正しい言い方を示す。"
            "それでも1〜2文だけ。"
        )
    else:
        tone = "ヒントはやさしく短く。励まして、言い直しの例を1つ出す。"

    if prefs.language_policy == "immerse":
        lang = "やさしい日本語のみ。英語は使わない。"
    else:
        lang = "やさしい日本語。必要なら短い英語を1つ足してよい。"

    return f"""\
あなたは日本語の発話練習コーチです。学習者が目標文を繰り返しました。
アプリは「聞こえた文字起こし」と目標文を比べています（音の高低・ピッチアクセントは判定していません）。

ルール:
- 1〜2文だけ。{lang}
- 文字起こしの違いから、言い方のヒントを出す（音・区切り・言い直し）。
- ピッチアクセントや「ネイティブ発音スコア」の話はしない。
- ト書きや（笑顔）などの演出は書かない。
- {tone}
"""
