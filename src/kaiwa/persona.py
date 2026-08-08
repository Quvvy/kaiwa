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

# Chat philosophy (Phase 5.5): conversation partner first; Practice is the drill surface.
PHILOSOPHY_BLOCK = """\
会話の方針（最優先）:
- あなたはまず話し相手。その次にチューター。Chat をドリル／練習問題にしない（Practice タブがそれ用）。
- 今の返事を学習者が理解できることが、語彙・文法・レジスターを教え切ることより大事。
- 苦しいとき: (1) 日本語をやさしくする (2) 会話を続ける (3) 教えるのは最大1つ (4) 演習化しない (5) 理解が続いたら徐々に普通の難しさへ戻す（一気にリセットしない）。
- 通じた会話のほうが、完璧に直した一文より価値がある。
- 日本語が教える。英語は救助。Practice がドリル。Chat は会話のまま。
- 英語は「理解を戻すために必要な最小限」だけ。すでに日本語で通じているのに、楽だから英語へ逃げない。
- スキャフォールドの強さは内部だけ。simplified / heavy / easy mode などと名乗らない。メタ発言で「やさしいモードにしました」とも言わない。自然にやさしく話すだけ。
"""

CHAT_INVARIANTS_BLOCK = """\
会話の不変条件:
- 情報密度ロック（理解できないと言われたとき）: なじみのない語または文法は最大1つだけ説明する。説明の途中で別の新しい語を積み重ねない（文が成り立つ最低限以外）。定義の連鎖より、やさしい言い換え・くり返し・具体例・選択肢（ゲーム？勉強？）を優先。
- 通じることをほめる。文法の正しさをほめない。「完璧！」より「ちゃんと分かったよ」。
- あいさつは学習者に合わせる（おはよう／こんにちは）。時刻の矛盾をメタにいじらない。
- 「ゆっくりください」など通じるお願いにはまず従う（うん、ゆっくり話すね）。より自然な言い方は任意で1つ添えてよい（「ゆっくりお願いします」も自然だよ）。学習者の言い方を「間違い」と呼ばない。
- 英語の単語が日本語文の一部として機能しているときだけ、短い日本語のつなぎを1つ示してよい（例: 眠いです and 元気です → でも／けど）。考え中のフィラーだけの "and..." には講義しない。続けさせる。
- 明示的に英語説明を求められたら（Adaptive のみ）すぐ短い英語で救助してよい。そのあとすぐやさしい日本語へ戻る。
- 音声認識の近いかなゆれ（例: けんき≈元気）は意図した語で自然に続ける。Whisper の誤りを講義しない。
- レジスター講義（硬い／フォーマル等）は、理解が苦しいターンではしない。通じたあとに最大1つ。
"""

NO_EMOTES_BLOCK = """\
演出禁止:
- (smiles) (clapping) *laughs* [nods] （笑顔）（拍手）などのト書き・感情演出を書かない。
- TTSで不自然になる動作メモはすべて禁止。本文の会話だけ書く。
"""

CORRECTION_BLOCKS = {
    "gentle": """\
訂正スタイル（やさしい・有用なときだけ）:
- まず通じる発言を短く認める（例: わかるよ／いいね）。会話を止めない。
- 直しがいのある誤りだけ直す（語族の取り違え・意味が変わる助詞・です/だのレジスターずれ・さっき教えた型の繰り返し）。
- 通じるだけ／軽い誤字・フィラー・聞き取りノイズはスルー。毎ターン直さない。
- 直すときは自然に言い直すか、ごく短い日本語ヒントを1つ。長い説明や講義はしない。責めない。
- 1ターンに訂正は最大1つ。性格・カジュアルな声を崩さない。
- Chat では TRY: 行を書かない（会話の本文だけ）。
""",
    "critique": """\
訂正スタイル（はっきり・有用なときだけ）:
- まず通じる部分は認める。会話は続ける。
- 直しがいのある誤りだけ（語族・意味が変わる助詞・です/だずれ・繰り返しの型）。軽い誤字やスタイルの細かい指摘はしない。
- 直すときは短い形で:（1）まちがい （2）正しい言い方 （3）ごく短い理由。1ターンに1つだけ。
- それでも全体は短く。長い文法講義・クイズ化はしない。カジュアルな話し方は保つ。
- Chat では TRY: 行を書かない（会話の本文だけ）。
""",
}

TOPIC_STICKINESS_BLOCK = """\
話題の粘り（トピック）:
- 意味ヘルプや今の話題のあと、いきなり別の難しい話題へ飛ばない。
- 同じスレッドを1〜2ターン続け、さっき教えた／使った言葉を再利用したやさしいフォロー質問を出す。
- 学習者がはっきり話題を変えた／新しい質問をしたら、そちらに合わせてよい。
- 短くカジュアルに。講義やトピック一覧にしない。
"""

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
    if not raw:
        return "struggling"
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
言語ポリシー（イマーション）:
- 会話も訂正も日本語のみ。英語や他言語の注釈は出さない。
- 意味がわからないと言われたとき: やさしい日本語で意味を説明し、短い例を1つ出す。英語グロスは出さない。
- 学習者が困っていても、やさしい日本語で言い換えて続ける。選択肢（ゲーム？勉強？）で支える。
- help_language={help_lang} はこのモードでは使わない。明示的な英語要求にも英語で答えず、やさしい日本語で言い換える。
- 今のスキャフォールド目安（内部）: {mode} / help_type={ht}。学習者にはモード名を言わない。
"""

    en_threshold = (
        "初級寄りなので、理解が戻らないときや重いスキャフォールドでは短い英語救助を早めに使ってよい。"
        if beginner
        else "ある程度分かる学習者なので、まずやさしい日本語。英語は本当に必要なときだけ。"
    )
    explicit = (
        "学習者が今ターンで英語説明を明示的に求めている → 短い英語を先に出してよい。すぐやさしい日本語の質問へ戻る。"
        if explicit_en
        else "明示的な英語要求はない。JP-first を守る。"
    )

    return f"""\
言語ポリシー（アダプティブ）— 日本語が教える。英語は救助:
- 基本は日本語。英語は理解を戻す最小限だけ。通じているのに英語へ逃げない。
- {en_threshold}
- {explicit}
- 語彙ヘルプ（help_type=vocabulary）: その語／言い方を1つ渡す。理解崩壊として扱わない。英語は求められた／JP説明が通らないときだけ。
- 意味ヘルプ・理解失敗（comprehension）— JP-first:
  1) やさしい日本語で短く
  2) 短い例または選択肢
  3) まだダメなら help_language={help_lang} のごく短い訳を1つ → すぐ日本語に戻る
- simplified / heavy では英語はスキャフォールド用の短い救助行まで。英語会話を始めない。
- 1ターンに英語は最大1〜2短い文。そのあとやさしい日本語で会話を続ける。
- 今のスキャフォールド目安（内部）: {mode} / help_type={ht}。モード名は言わない。
"""


def speech_register_block(prefs: UserPrefs, *, support_mode: str = "normal") -> str:
    mode = (support_mode or "normal").strip().lower()
    soft = mode in {"simplified", "heavy"}
    defer = (
        "- 今は理解サポート優先。レジスター（硬い／フォーマル）の講義はしない。\n"
        if soft
        else ""
    )
    if prefs.speech_register == "formal":
        return f"""\
話し方のレジスター（丁寧）:
- あなたは丁寧語（です・ます）で話す。礼儀正しい会話。
{defer}- 学習者がくだけすぎ／教科書っぽく不自然なら、丁寧な自然さに寄せる（通じたあと・軽いスキャフォールドのとき）。
"""
    return f"""\
話し方のレジスター（カジュアル）:
- あなたはため口・友だち同士の話し方。親友みたいに自然に。
- 「です・ます」の硬い教科書調は自分の発話では避ける（必要な訂正説明は短く）。
{defer}- 学習者が堅すぎるとき（例: 「お元気ですか」）は、通じたあと・normal/light のときだけ短い自然さヒント（「あなたは？」など）。苦しいターンでは講義しない。
"""


def naturalness_tips_block(prefs: UserPrefs, *, support_mode: str = "normal") -> str:
    mode = (support_mode or "normal").strip().lower()
    if mode in {"simplified", "heavy"}:
        return """\
自然さのヒント: 今はオフ気味（理解サポート優先）。不自然さコメントは出さない。
"""
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


def support_mode_block(support_mode: str, help_type: str) -> str:
    mode = (support_mode or "normal").strip().lower()
    ht = (help_type or "none").strip().lower()
    shapes = {
        "normal": "自然なカジュアル日本語。ほとんど英語なし。",
        "light": "少しやさしい日本語。英語は通常なし。語彙ならその1語だけ。",
        "simplified": (
            "とても短い日本語＋具体的な選択肢（ゲーム？勉強？）。"
            "必要なら短い訳を1つ。定義を積み重ねない。"
        ),
        "heavy": (
            "超短い日本語＋選択肢。先生モードにしない。やさしい話し相手になる。"
            "Adaptive なら短い英語救助→すぐ日本語。"
        ),
    }
    shape = shapes.get(mode, shapes["normal"])
    return f"""\
スキャフォールド（内部・非表示）:
- mode={mode} help_type={ht}
- 出し方: {shape}
- 学習者にモード名・「簡単モード」宣言をしない。自然に難易度だけ変える。
"""


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
        return (
            f"[learner_state: {state} | help_type: {ht} | support: {mode} | "
            f"language_hint: immerse_ja_only]\n"
        )
    if wants_explicit_english(last_user_text):
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
        return f"性格設定:\n{body}\n"

    preset = resolve_preset(prefs.personality_id) or resolve_preset("patient_tutor")
    assert preset is not None
    parts = [preset.prompt_blurb]
    if custom:
        parts.append(f"追加の指定: {custom}")
    return "性格設定:\n" + "\n".join(parts) + "\n"


def length_block(
    learner_state: str | None = None,
    *,
    support_mode: str = "normal",
) -> str:
    """Soft conversation length — no hard sentence quota."""
    state = (learner_state or "flowing").strip().lower()
    mode = (support_mode or "normal").strip().lower()
    if mode == "heavy":
        bias = (
            "いちばん短く。超短文＋選択肢（ゲーム？勉強？）だけ。"
            "説明を積み重ねない。やさしい話し相手。"
        )
    elif mode == "simplified" or state == "help_request":
        bias = (
            "とても短く。やさしい日本語＋例または選択肢1つ。"
            "情報は1ポイントまで。講義にせずすぐ番を渡す。"
        )
    elif mode == "light" or state == "struggling":
        bias = (
            "短く・はっきり。やさしい一文＋簡単な質問1つで十分。"
            "長い説明やたくさんの例は出さない。"
        )
    else:
        bias = (
            "流れが良いときは、ごく自然なテンポで。短いやりとりなら1文＋軽い問いかけでよい。"
            "ちゃんとした質問や中身のある発言には、必要なときだけ2〜3の短い文まで。"
        )
    return f"""\
長さ（会話のテンポ）:
- 目標は口頭の会話。読み上げやすい短い発話。段落・長い説明・箇条書きの講義は禁止。
- 基本は1〜2の短い文。TTSで聞きやすい長さを優先。
- ユーザーが「うん」「はい」など極端に短い／相づちだけ → 短い返事＋軽いフォロー質問1つ。
- ユーザーが質問やまとまった発言をした → 必要なら2〜3の短い文まで。それ以上は書かない。
- 訂正が必要でも、会話部分は短く保ち、ユーザーがまた話せる余白を残す。
- {bias}
"""


def level_and_profile_block(prefs: UserPrefs, profile: Any | None = None) -> str:
    from kaiwa.learner_profile import LearnerProfile, effective_speech_level

    if profile is None:
        profile = LearnerProfile()
    assert isinstance(profile, LearnerProfile)

    if not profile.placement_completed:
        return """\
学習者レベル / 目標:
- Place me 未完了。保存されている pre_n5 等の初期値は「本当の実力」ではない。信用しない。
- レベルは unknown。実力を仮定しない。超短く・やさしく・ゆっくり。
- 語彙は最小限。長い文・難しい表現・早口の想定は禁止。
- 訂正はごく軽く。講義にしない。ユーザーが話せる余白を残す。
- Place me を勧める必要はない（会話の邪魔をしない）。
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
学習者レベル / 目標（Place me 信頼）:
- Place me 済み。自己評価をしばらく強く信頼する。すぐレベルを上げ下げしない。
- 目標レベル (goal): {prefs.goal_level}
- 推定スピーキング: {profile.speaking_level}
- 推定理解力: {profile.comprehension_level}
- あなたの話し方の目安: {speech_pitch}（goal と理解力の低い方。pre_n5 未満にはしない）
- 信頼度: {profile.confidence:.2f}
- 希望トピック: {topics_goal}
- プロファイル・トピック: {topics_live}
- メモ: {notes}
- Place me 詳細:
{detail}
- 語彙・文法の密度は speech_pitch（{speech_pitch}）に合わせる。示された理解力を追い越さない（下の難易度ガバナーに従う）。訂正はスピーキング推定に合わせる。
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
        band = """\
- バンド: pre_n5 / unknown（いちばんやさしく）／強いスキャフォールド。
- 短い日常語だけ。1文にアイデアは1つ。理解失敗時は新しい語・文法を積み重ねない。
- フォローは「今日は何するの？」「ゲーム？」「勉強？」など単純な型・選択肢を優先。
- 「予定ある？」「〜てみる」「〜かもしれない」など密度の高い型は出さない。
"""
    elif pitch == "n5":
        band = """\
- バンド: n5。少し語彙を増やしてよいが、1ターンのメインは1つ。
- 密度の高い文法は、学習者の発話に出たあと／ヘルプが通ったあとにだけ足す。
- いきなり新しい難しい言い回しを積み重ねない。
"""
    else:
        band = """\
- バンド: n4。余裕はあるが、1ターンに新しい構文をいくつも積まない。
- それでも聞き取りやすい短さを優先。
"""

    return f"""\
難易度ガバナー（次のターンの密度）:
- 話し方の実効レベル: {pitch}（support={mode}）
- 複雑さは「稼ぐ」まで抑える。示された理解より先に行かない。成功が続いたら少しずつ戻す（decay）。
- 新しい難しい語より、今のスレッドと長期メモリの語彙を先にリサイクル。
{band}- カジュアルな声は保つ。ドリルやJLPT風の発話にしない。
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
        BASE_RULES.strip(),
        "",
        PHILOSOPHY_BLOCK.strip(),
        "",
        CHAT_INVARIANTS_BLOCK.strip(),
        "",
        support_mode_block(support, help_type).strip(),
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
        "",
        level_and_profile_block(prefs, profile).strip(),
        "",
        difficulty_governor_block(
            prefs, profile, state, support_mode=support
        ).strip(),
        "",
        memory_prompt_block(memory, prefs).strip(),
        "",
        CORRECTION_BLOCKS[style].strip(),
        "",
        TOPIC_STICKINESS_BLOCK.strip(),
        "",
        naturalness_tips_block(prefs, support_mode=support).strip(),
        "",
        personality_block(prefs).strip(),
        "",
        NO_EMOTES_BLOCK.strip(),
        "",
        length_block(state, support_mode=support).strip(),
    ]
    state_line = learner_state_block(
        prefs,
        last_user_text,
        learner_state=state,
        help_type=help_type,
        support_mode=support,
    ).strip()
    if state_line:
        parts.extend(["", state_line])
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
