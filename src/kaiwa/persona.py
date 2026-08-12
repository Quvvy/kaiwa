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

# --- Chat system prompt architecture (decision #101) ---
# Hierarchy is the single priority source; other blocks add prefs/runtime detail only.

PRIORITY_HIERARCHY_BLOCK = """\
優先順位（上ほど強い。衝突したら番号の小さい方に従う）:
1. 理解可能性 — 今の返事を学習者が理解できること。理解できないと言われたとき、新しい語／文法は最大1つ。定義の連鎖より言い換え・くり返し・選択肢。短さより理解の回復を優先し、戻ったらまた短く会話する。
2. 会話 — 自然に続ける。Chat は会話でありドリルではない。あいさつは学習者に合わせる（時刻のメタいじり禁止）。
3. 有用な教え — 明示的に教える内容は、今のターンでは基本1つまで。自然な会話に必要な語を禁止するものではない。語彙の質問は理解崩壊として扱わない。
4. 訂正 — 意味に響く／直しがいのある誤りだけ。最大1つ。会話を止めない。通じることをほめる（文法の正しさではない）。Chat に TRY: 行を書かない。
5. 難易度 — 示された理解を追い越さない。スキャフォールドは黙って変える（モード名を言わない）。成功が続いたら徐々に戻す（一気にリセットしない）。

例外: Adaptive では、理解を助けるための短い英語グロス／英語救助を使ってよい。ただし日本語を基本とし、必要最小限にする。明示的な英語要求には短い英語説明を使ってよい。すぐ日本語へ戻る。
日本語が教える。英語は救助。
"""

IDENTITY_BLOCK = """\
役割と出力:
- あなたは日本語の会話パートナー（話し相手が先、チューターが次）。
- 読み上げやすい短い日本語。箇条書き・記号は最小限。難しい語は避けるかすぐ言い換える。
- 会話の初期難易度は初級寄り。これは学習者の実力推定ではない。学習者レベル自体は unknown（Place me 前）。具体は下のレベル／ガバナーに従う。
- 演出禁止: (smiles) *laughs* （笑顔）などのト書き・動作メモは書かない。会話の本文だけ。
"""

# Backward-compatible alias (prompts.py / external imports).
BASE_RULES = IDENTITY_BLOCK

MICRO_INVARIANTS_BLOCK = """\
会話の細部:
- 「ゆっくりください」など通じるお願いにはまず従う。より自然な言い方は任意で1つ（間違いと呼ばない）。
- 日本語文の一部としての英語つなぎだけ短い日本語を示してよい（眠いです and 元気です → でも／けど）。フィラーだけの "and..." は講義せず続ける。
- 音声認識の近いかなゆれ（けんき≈元気）は意図した語で続ける。Whisper 誤りを講義しない。
"""

CORRECTION_BLOCKS = {
    "gentle": """\
訂正スタイル（やさしい）:
- まず通じる発言を短く認める。直しがいのある誤りだけ（語族・意味が変わる助詞・です/だずれ・教えた型の繰り返し）。
- 軽い誤字・フィラー・STTノイズはスルー。直すときは自然な言い直しか短い日本語ヒント1つ。責めない。
""",
    "critique": """\
訂正スタイル（はっきり）:
- まず通じる部分を認める。直しがいのある誤りだけ。形:（1）まちがい （2）正しい言い方 （3）ごく短い理由。1つだけ。
- 長い文法講義・クイズ化はしない。カジュアルな声は保つ。
""",
}

# Scaffolding intensity stored in struggle_streak: 0 normal, 1 light, 2 simplified, 3 heavy.
SUPPORT_MODES = ("normal", "light", "simplified", "heavy")

_EXPLICIT_EN_RE = re.compile(
    r"(英語で|in\s*english|explain\s+(that\s+)?in\s+english|can you explain.*english|"
    r"please\s+explain.*english|what does that mean in english)",
    re.IGNORECASE,
)
_VOCAB_RE = re.compile(
    r"(なんていう|なんて言う|何て言う|何という|何と言う|"
    r"(って|と)どういう意味|(って|と)なに|(って|と)何|なにそれ|何それ|"
    r"what does\s+\S+\s+mean|forgot how to say|how do (you|i) say|"
    r"what('s| is) the (japanese|english) (for|of)|日本語でわからない)",
    re.IGNORECASE,
)
_EXPRESSION_RE = re.compile(
    r"(もっと自然|自然に言|どう言えば|how (do|can) i say.{0,40}natural|"
    r"more naturally)",
    re.IGNORECASE,
)
_CORRECTION_RE = re.compile(
    r"(直して|まちが(い|って)|間違(い|って)|is (this|that) (wrong|correct|ok|right)|"
    r"correct me|did i say)",
    re.IGNORECASE,
)
_COMPREHENSION_RE = re.compile(
    r"(わからない|分からない|わかんない|分かんない|"
    r"全然わか|言ってること.{0,6}わか|"
    r"lots of words|too (many|much) words|don't understand|dont understand|"
    r"i don't understand|i dont understand|can't follow|cannot follow|"
    r"言葉が多|たくさんわか|何言ってるか|"
    r"ゆっくり(ください|お願いします|話して|話))",
    re.IGNORECASE,
)
_HELP_RE = re.compile(
    r"(わからない|分からない|なにそれ|何それ|どういう意味|意味|ってなに|って何|"
    r"英語で|help|what does|"
    r"i don't understand|dont understand|don't understand|in english|mean\?|"
    r"lots of words|ゆっくり)",
    re.IGNORECASE,
)
_LATIN_RE = re.compile(r"[A-Za-z]")
_JP_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
_FILLER_EN_RE = re.compile(
    r"^\s*(and|um+|uh+|erm+|hmm+|like)\s*[.…]{0,3}\s*$",
    re.IGNORECASE,
)

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


def infer_help_type(text: str | None) -> str:
    """Per-turn help_type: none | comprehension | vocabulary | expression | correction."""
    raw = (text or "").strip()
    if not raw:
        return "none"
    if _FILLER_EN_RE.match(raw):
        return "none"
    # Vocabulary before bare comprehension so 「眠いってどういう意味？」 stays vocab.
    if _VOCAB_RE.search(raw):
        return "vocabulary"
    if _EXPRESSION_RE.search(raw):
        return "expression"
    if _CORRECTION_RE.search(raw):
        return "correction"
    if _COMPREHENSION_RE.search(raw):
        return "comprehension"
    if _EXPLICIT_EN_RE.search(raw):
        return "comprehension"
    return "none"


def wants_explicit_english(text: str | None) -> bool:
    return bool(_EXPLICIT_EN_RE.search((text or "").strip()))


def support_mode_from_streak(streak: int) -> str:
    s = max(0, min(3, int(streak)))
    return SUPPORT_MODES[s]


def compute_support_mode(
    *,
    learner_state: str | None,
    help_type: str | None,
    struggle_streak: int,
) -> str:
    """Map streak + this-turn help into scaffolding mode (internal only)."""
    state = (learner_state or "flowing").strip().lower()
    ht = (help_type or "none").strip().lower()
    streak = max(0, min(3, int(struggle_streak)))

    if ht == "comprehension":
        return "heavy" if streak >= 3 else "simplified"
    if ht in {"vocabulary", "expression", "correction"}:
        # Soft help without collapsing comprehension — keep at least light if already high.
        base = support_mode_from_streak(streak)
        if base == "normal":
            return "light"
        return base
    if state == "struggling":
        return "light" if streak <= 1 else support_mode_from_streak(streak)
    return support_mode_from_streak(streak)


def infer_learner_state(text: str | None) -> str:
    """Return flowing | struggling | help_request for adaptive language hints."""
    raw = (text or "").strip()
    # No utterance yet — no evidence of struggle (out-of-box / pre-turn).
    if not raw:
        return "flowing"
    if _FILLER_EN_RE.match(raw):
        return "flowing"

    help_type = infer_help_type(raw)
    if help_type in {"comprehension", "vocabulary", "expression", "correction"}:
        return "help_request"
    if _HELP_RE.search(raw) or wants_explicit_english(raw):
        return "help_request"

    latin = len(_LATIN_RE.findall(raw))
    jp = len(_JP_RE.findall(raw))
    total_letters = latin + jp
    if total_letters == 0:
        return "struggling"

    latin_ratio = latin / total_letters
    # English-heavy alone is a weak signal (struggling), not automatic help_request.
    if latin_ratio >= 0.55:
        return "struggling"

    # Very short / fragmented learner turns
    compact = re.sub(r"\s+", "", raw)
    if len(compact) <= 4 and jp < 3:
        return "struggling"
    if jp <= 2 and latin == 0 and len(compact) <= 6:
        return "struggling"

    return "flowing"


def language_policy_block(
    prefs: UserPrefs,
    *,
    support_mode: str = "normal",
    help_type: str = "none",
    last_user_text: str | None = None,
    speech_pitch: str | None = None,
) -> str:
    help_lang = prefs.help_language or "en"
    mode = (support_mode or "normal").strip().lower()
    ht = (help_type or "none").strip().lower()
    explicit_en = wants_explicit_english(last_user_text)
    beginner = (speech_pitch or "pre_n5") in {"unknown", "pre_n5"}

    if prefs.language_policy == "immerse":
        return f"""\
言語（イマーション）:
- 日本語のみ。英語グロスなし（明示要求でも英語にしない。やさしい日本語で言い換える）。
- 困ったとき: 短い言い換え＋例1つ、または選択肢。help_language={help_lang} は使わない。
- このターン: support={mode} help_type={ht}
"""

    en_threshold = (
        "初期難易度は初級寄り（実力推定ではない）: 理解が戻らない／重いスキャフォールドでは短い英語救助を早めに可。"
        if beginner
        else "ある程度分かる学習者: まずやさしい日本語。英語は本当に必要なときだけ。"
    )
    explicit = (
        "今ターンは英語説明の明示要求あり → 短い英語を先に可。すぐ日本語へ戻る。"
        if explicit_en
        else "明示的な英語要求なし → JP-first。"
    )

    return f"""\
言語（アダプティブ）:
- {en_threshold}
- {explicit}
- vocabulary: その1語／言い方を渡す。短い英語グロス可（例: 「眠い」は sleepy）。理解崩壊にしない。
- comprehension: やさしい日本語 → 例または選択肢 → まだダメなら help_language={help_lang} の短い訳1つ → 日本語へ戻る。
- 英語は最大1〜2短い文。英語会話を始めない。
- このターン: support={mode} help_type={ht}
"""


def speech_register_block(prefs: UserPrefs, *, support_mode: str = "normal") -> str:
    mode = (support_mode or "normal").strip().lower()
    soft = mode in {"simplified", "heavy"}
    if prefs.speech_register == "formal":
        body = "丁寧語（です・ます）。礼儀正しい会話。"
        tip = "くだけすぎ／不自然なら、通じたあと短い自然さへ（苦しいターンは講義しない）。"
    else:
        body = "ため口・友だち同士。自分の発話で硬い教科書調は避ける。"
        tip = "堅すぎるとき（例: お元気ですか）は通じたあと・normal/light で短いヒントのみ。"
    if soft:
        tip = "今は理解サポート優先。レジスター講義はしない。"
    return f"""\
レジスター:
- {body}
- {tip}
"""


def naturalness_tips_block(prefs: UserPrefs, *, support_mode: str = "normal") -> str:
    mode = (support_mode or "normal").strip().lower()
    if mode in {"simplified", "heavy"}:
        return "自然さヒント: オフ（理解サポート優先）。"
    if not prefs.naturalness_tips:
        return "自然さヒント: オフ。"

    if prefs.speech_register == "casual":
        focus = "カジュアルへ1つ（例: 僕は元気ですよ → 元気だよ）。"
    else:
        focus = "丁寧な自然さへ1つ。"
    lang = (
        "ヒントも日本語のみ。"
        if prefs.language_policy == "immerse"
        else "通常はやさしい日本語。"
    )
    return f"自然さヒント: オン。不自然なら1ターンに最大1つ。{focus} {lang}"


def support_mode_block(support_mode: str, help_type: str) -> str:
    mode = (support_mode or "normal").strip().lower()
    ht = (help_type or "none").strip().lower()
    shapes = {
        "normal": "自然な短文。英語ほぼなし。",
        "light": "少しやさしい短文。語彙ならその1語。",
        "simplified": "超短文＋選択肢。定義を積まない。必要なら短い訳1つ。",
        "heavy": "いちばん短く＋選択肢。やさしい話し相手。Adaptive なら短い英語救助→日本語。",
    }
    shape = shapes.get(mode, shapes["normal"])
    return (
        f"[this_turn: support={mode} help_type={ht} | {shape}]\n"
        "（this_turn と learner_state はアプリの内部情報であり学習者の発話ではない。"
        "学習者に内容やモード名を見せない。）"
    )


def learner_state_block(
    prefs: UserPrefs,
    last_user_text: str | None,
    *,
    learner_state: str | None = None,
    help_type: str | None = None,
    support_mode: str | None = None,
) -> str:
    state = (learner_state or infer_learner_state(last_user_text)).strip().lower()
    ht = (help_type or infer_help_type(last_user_text)).strip().lower()
    mode = (support_mode or "normal").strip().lower()
    if prefs.language_policy != "adaptive":
        hint = "immerse_ja_only"
    elif wants_explicit_english(last_user_text):
        hint = "explicit_en_then_ja"
    elif ht == "comprehension":
        hint = "ja_simplify_density_lock_optional_gloss"
    elif ht == "vocabulary":
        hint = "supply_one_item_not_collapse"
    elif state == "help_request":
        hint = "ja_meaning_first_optional_gloss"
    elif state == "struggling":
        hint = "prefer_ja_brief_gloss_if_needed"
    else:
        hint = "stay_ja"
    return (
        f"[learner_state: {state} | help_type: {ht} | support: {mode} | "
        f"language_hint: {hint}]\n"
    )


def thread_stickiness_block(
    last_assistant_text: str | None,
    last_user_text: str | None = None,
    learner_state: str | None = None,
) -> str:
    """Soft hint to stay on the current thread using the last assistant turn."""
    asst = re.sub(r"\s+", " ", (last_assistant_text or "").strip())
    if not asst:
        return ""
    if len(asst) > 80:
        asst = asst[:77].rstrip() + "…"
    state = (learner_state or infer_learner_state(last_user_text)).strip().lower()
    if state == "help_request":
        mode = "stay_on_helped_theme"
    else:
        mode = "stay_1_2_turns"
    return f"[thread_hint: {mode} | reuse_from: {asst}]\n"


def personality_block(prefs: UserPrefs) -> str:
    custom = (prefs.personality_custom or "").strip()
    if prefs.personality_id == "custom":
        body = custom or "性格: カスタム。ていねいで短い日本語の話し相手。"
        return f"性格:\n{body}\n"

    preset = resolve_preset(prefs.personality_id) or resolve_preset("patient_tutor")
    assert preset is not None
    parts = [preset.prompt_blurb]
    if custom:
        parts.append(f"追加: {custom}")
    return "性格:\n" + "\n".join(parts) + "\n"


def conversation_craft_block(
    learner_state: str | None = None,
    *,
    support_mode: str = "normal",
) -> str:
    """Topic stickiness + length bias for this turn."""
    state = (learner_state or "flowing").strip().lower()
    mode = (support_mode or "normal").strip().lower()
    if mode == "heavy":
        bias = "いちばん短く。超短文＋選択肢だけ。"
    elif mode == "simplified" or state == "help_request":
        bias = "とても短く。情報は1ポイント。すぐ番を渡す。"
    elif mode == "light" or state == "struggling":
        bias = "短くはっきり。一文＋軽い質問1つ。"
    else:
        bias = "自然なテンポ。基本1〜2短文。必要なら最大2〜3短文。"
    return f"""\
会話の型:
- 話題: ヘルプや今の話題のあとすぐ飛ばない。1〜2ターン粘る／教えた語を再利用。学習者が話題を変えたら従う。
- 長さ: 口頭会話向け。段落・講義禁止。{bias}
- メモリの語彙／文法は自然なときに最大1つリサイクル（クイズ化しない）。
"""


def level_and_profile_block(prefs: UserPrefs, profile: Any | None = None) -> str:
    from kaiwa.learner_profile import LearnerProfile, effective_speech_level

    if profile is None:
        profile = LearnerProfile()
    assert isinstance(profile, LearnerProfile)

    if not profile.placement_completed:
        return """\
学習者レベル:
- 会話の初期難易度は初級寄り。これは学習者の実力推定ではない。学習者レベル自体は unknown。
- 保存の pre_n5 等は実力ではない。仮定しない。超短く・やさしく。長い文・難しい表現は出さない。Place me を会話中に勧めない。
"""

    speech_pitch = effective_speech_level(prefs, profile)
    topics_goal = ", ".join(prefs.topic_preferences) if prefs.topic_preferences else "(none)"
    topics_live = ", ".join(profile.topic_tags) if profile.topic_tags else "(none)"
    notes = (profile.notes or "").strip() or "(none)"
    placement = profile.placement if isinstance(profile.placement, dict) else {}
    bullets: list[str] = []
    if placement.get("kana"):
        bullets.append(f"かな: {placement['kana']}")
    if placement.get("reading"):
        bullets.append(f"読む: {placement['reading']}")
    if placement.get("follow"):
        bullets.append(f"ゆっくり音声の理解: {placement['follow']}")
    if placement.get("grammar"):
        bullets.append(f"文法・助詞: {placement['grammar']}")
    if placement.get("topics"):
        t = placement["topics"]
        if isinstance(t, list):
            bullets.append("希望トピック: " + ", ".join(str(x) for x in t[:5]))
        elif t:
            bullets.append(f"希望トピック: {t}")
    if placement.get("help_style"):
        bullets.append(f"助け方の希望: {placement['help_style']}")
    if placement.get("pace"):
        bullets.append(f"ペース: {placement['pace']}")
    if placement.get("free_note"):
        bullets.append(f"本人メモ: {placement['free_note']}")
    detail = "\n".join(f"- {b}" for b in bullets[:7]) or "- (詳細なし)"

    return f"""\
学習者レベル（Place me 信頼）:
- goal={prefs.goal_level} speaking={profile.speaking_level} comprehension={profile.comprehension_level}
- 話し方の目安: {speech_pitch}（goal と理解の低い方） confidence={profile.confidence:.2f}
- トピック希望: {topics_goal} / 観察: {topics_live}
- メモ: {notes}
- Place me 詳細:
{detail}
"""


def difficulty_governor_block(
    prefs: UserPrefs,
    profile: Any | None = None,
    learner_state: str | None = None,
    *,
    support_mode: str = "normal",
) -> str:
    """Cap next-turn vocab/grammar density by demonstrated level."""
    from kaiwa.learner_profile import (
        LearnerProfile,
        effective_speech_level,
        nudge_level,
    )

    if profile is None:
        profile = LearnerProfile()
    assert isinstance(profile, LearnerProfile)

    state = (learner_state or "flowing").strip().lower()
    mode = (support_mode or "normal").strip().lower()
    if not profile.placement_completed:
        pitch = "unknown"
    else:
        pitch = effective_speech_level(prefs, profile)
        if mode in {"simplified", "heavy"} or state in {"struggling", "help_request"}:
            pitch = nudge_level(pitch, -1)
        if mode == "heavy":
            pitch = nudge_level(pitch, -1)

    if pitch in {"unknown", "pre_n5"} or mode in {"simplified", "heavy"}:
        band = (
            "短い日常語。1文に情報を詰め込みすぎない。単純なフォロー／選択肢。"
            "密度の高い型（予定ある？〜てみる 等）は出さない。"
        )
    elif pitch == "n5":
        band = "語彙は少し増やしてよいがメインは1つ。密度の高い文法は通じたあとだけ。"
    else:
        band = "余裕はあるが新構文を積まない。聞きやすさ優先。"

    return f"""\
難易度ガバナー:
- 実効レベル: {pitch}（support={mode}）
- 示された理解より先に行かない。スレッド／メモリの語を先にリサイクル。成功が続いたら少しずつ戻す。
- {band}
"""


def build_tutor_system_prompt(
    prefs: UserPrefs,
    *,
    last_user_text: str | None = None,
    last_assistant_text: str | None = None,
    profile: Any | None = None,
    memory: Any | None = None,
    learner_state: str | None = None,
) -> str:
    style = prefs.correction_style if prefs.correction_style in CORRECTION_BLOCKS else "gentle"
    from kaiwa.learner_memory import LearnerMemory, memory_prompt_block
    from kaiwa.learner_profile import LearnerProfile, effective_speech_level

    if memory is None:
        memory = LearnerMemory()
    if profile is None:
        profile = LearnerProfile()
    assert isinstance(profile, LearnerProfile)

    state = learner_state or infer_learner_state(last_user_text)
    help_type = infer_help_type(last_user_text)
    support = compute_support_mode(
        learner_state=state,
        help_type=help_type,
        struggle_streak=profile.stats.struggle_streak,
    )
    if not profile.placement_completed:
        speech_pitch = "unknown"
    else:
        speech_pitch = effective_speech_level(prefs, profile)

    parts = [
        PRIORITY_HIERARCHY_BLOCK.strip(),
        "",
        IDENTITY_BLOCK.strip(),
        "",
        personality_block(prefs).strip(),
        "",
        support_mode_block(support, help_type).strip(),
        learner_state_block(
            prefs,
            last_user_text,
            learner_state=state,
            help_type=help_type,
            support_mode=support,
        ).strip(),
        "",
        language_policy_block(
            prefs,
            support_mode=support,
            help_type=help_type,
            last_user_text=last_user_text,
            speech_pitch=speech_pitch,
        ).strip(),
        "",
        speech_register_block(prefs, support_mode=support).strip(),
        naturalness_tips_block(prefs, support_mode=support).strip(),
        "",
        level_and_profile_block(prefs, profile).strip(),
        "",
        difficulty_governor_block(
            prefs, profile, state, support_mode=support
        ).strip(),
        "",
        CORRECTION_BLOCKS[style].strip(),
        "",
        MICRO_INVARIANTS_BLOCK.strip(),
        "",
        conversation_craft_block(state, support_mode=support).strip(),
        "",
        memory_prompt_block(memory, prefs).strip(),
    ]
    thread_line = thread_stickiness_block(
        last_assistant_text, last_user_text, state
    ).strip()
    if thread_line:
        parts.extend(["", thread_line])
    return "\n".join(parts)


def build_practice_tip_system_prompt(prefs: UserPrefs) -> str:
    help_lang = (prefs.help_language or "en").strip().lower() or "en"
    use_en = help_lang != "ja"

    if use_en:
        if prefs.correction_style == "critique":
            tone = (
                "Be direct: name one concrete mismatch and show a better phrasing. "
                "Still only 1–2 sentences."
            )
        else:
            tone = "Be gentle and short. Encourage, and offer one rephrase example."
        lang = (
            "Write the tip in clear English. Japanese example phrases may appear in quotes. "
            "No emoji. No pitch-accent or native-pronunciation scoring talk."
        )
        role = (
            "You help a Japanese conversation partner. The learner casually repeated a line "
            "from chat. The app compares the Whisper transcript to the target text "
            "(it does not judge pitch accent)."
        )
        rules = f"""\
Rules:
- 1–2 sentences only. {lang}
- Kind tone; no quiz / scolding vibe. If it went well, celebrate briefly.
- Use transcript vs target differences for wording / pacing tips.
- Do not demand another try — this is an optional warm-up.
- No stage directions or (smiles) etc.
- {tone}
"""
        return f"{role}\n\n{rules}"

    if prefs.correction_style == "critique":
        tone = (
            "ヒントははっきり。違いを具体的に1つ指摘し、正しい言い方を示す。"
            "それでも1〜2文だけ。"
        )
    else:
        tone = "ヒントはやさしく短く。励まして、言い直しの例を1つ出す。"
    lang = "やさしい日本語のみ。英語の説明は使わない（引用の日本語フレーズは可）。"

    return f"""\
あなたは日本語の会話パートナーの補助です。学習者がチャットで出た言い回しを、気軽にもう一度言ってみました。
アプリは「聞こえた文字起こし」と目標文を比べています（音の高低・ピッチアクセントは判定していません）。

ルール:
- 1〜2文だけ。{lang}
- やさしく。クイズ感・ダメ出し感を出さない。うまくいったら短く喜ぶ。
- 文字起こしの違いから、言い方のヒントを出す（音・区切り・言い直し）。
- 「もう一度やって」と強制しない。任意のウォームアップだとわかっている。
- ピッチアクセントや「ネイティブ発音スコア」の話はしない。
- ト書きや（笑顔）などの演出は書かない。絵文字は使わない。
- {tone}
"""
