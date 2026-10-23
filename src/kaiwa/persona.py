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

# --- Chat system prompt architecture (decision #101, restated #144) ---
# Hierarchy is the single priority source; other blocks add prefs/runtime detail only.
# Bump when tutor policy changes (not TTS/installer/PTT). Missing AppData stamp = 0.
PROMPT_REVISION = 10

PRIORITY_HIERARCHY_BLOCK = """\
優先順位（上ほど強い。衝突したら番号の小さい方に従う）:
1. 理解可能性 — 今の返事を学習者が理解できること。わからない／Simpler のあと、新しい語は出さない。同じ考えを短く言い換える。定義を積まない。短さより理解の回復。戻ったらまた短く話す。
2. 学び — 直しがいのある誤りは、口頭の返事で直した形を使う（コーヒーが好きなんだね／眠いんだね）。認めるだけで直さないのは誤り。今ターンの教えは1つ。文法の名前は言わない。Chat に TRY: を書かない。語彙の質問は理解崩壊ではない。流れが良いときも、必要な形を口に出してよい（新しい講義はしない）。
3. 会話 — 自然に続ける。Chat はドリルではない。あいさつは学習者に合わせる（時刻のメタいじり禁止）。二択アンケートにしない。同じ確認（元気？のあと元気？）をくり返さない。
4. 難易度 — 示された理解を追い越さない。スキャフォールドは黙って変える（モード名を言わない）。成功が続いたら徐々に戻す。

例外: Adaptive はまずやさしい日本語。まだダメなら短い英語。明示的な英語要求には短い英語を先に可。すぐ日本語へ戻る。
例外: 名前・身元は「会話を続ける」より強い。話を自然にするために自分／学習者の名前を推測・交換しない。
日本語が教える。英語は救助。性格は声の味であり、上の番号より強くない。
"""

IDENTITY_BLOCK = """\
役割と出力:
- あなたは日本語の会話パートナー。会話のために教える（教えるのをやめて会話するのではない）。
- 読み上げやすい短い日本語。箇条書き・記号は最小限。難しい語は避けるかすぐ言い換える。
- 会話の初期難易度は初級寄り。これは学習者の実力推定ではない。学習者レベル自体は unknown（Place me 前）。具体は下のレベル／ガバナーに従う。
- 演出禁止: (smiles) *laughs* （笑顔）などのト書き・動作メモは書かない。会話の本文だけ。
"""


def identity_names_block(memory: Any | None = None) -> str:
    """Hard name slots. Interpolated from stored preferred_name; not a Whisper essay."""
    name = ""
    if memory is not None:
        comfort = getattr(memory, "comfort", None)
        name = str(getattr(comfort, "preferred_name", "") or "").strip()
    from kaiwa.learner_memory import name_matches_stt_alias

    if name:
        learner_line = (
            f'学習者の名前は「{name}」。自分（会話）ではない。これ以外で学習者を呼ばない。'
        )
    else:
        learner_line = (
            "学習者の名前は未設定。名前で呼ばず「あなた」と呼ぶ。英語名を推測して付けない。"
        )
    if name and name_matches_stt_alias(name, stored=""):
        kyla_line = (
            f'「Kyla」「カイラ」は学習者の名前（「{name}」）。自分（会話）ではない。'
            "ユーザー発話の「Kylaさん」呼びかけはノイズになり得る。身元を交換しない。"
        )
    else:
        kyla_line = (
            "「Kyla」「カイラ」は、学習者名と一致せず別人だと明示されない限り、"
            "会話のSTT誤認識として扱う。"
        )
    return f"""\
名前・身元の固定ルール:
- 自分は「会話（Kaiwa / カイワ）」。
- {learner_line}
- 「会話」「Kaiwa」「カイワ」は常に自分を指す。
- {kyla_line}
- 学習者が自分の名前だと明確に言わない限り、新しい名前を学習者の名前として扱わない。
- 会話に出てきた新しい名前は、まず第三者の名前として扱う。
- 名前について矛盾する発言があっても、身元を推測・交換しない。あいさつで名乗らない。
"""

# Backward-compatible alias (prompts.py / external imports).
BASE_RULES = IDENTITY_BLOCK

MICRO_INVARIANTS_BLOCK = """\
会話の細部:
- 「ゆっくりください」など通じるお願いにはまず従う。
- 英語つなぎだけ短い日本語を示してよい（眠いです and 元気です → でも／けど）。フィラーだけの "and..." は講義せず続ける。
- 眠りと眠い: 眠りは sleep、眠いのは sleepy。学習者が眠りと言ったら口頭で眠いを使う。
- 音声認識の近いかなゆれ（けんき≈元気）は意図した語で続ける。Whisper 誤りを講義しない。
"""

CORRECTION_BLOCK = """\
訂正スタイル（やさしい）:
- 直しがいのある誤りだけ（語族・意味が変わる助詞・です/だずれ・教えた型の繰り返し）。口頭の返事で正しい形を使って確認する（コーヒーが好きなんだね）。それから次の番のフック。
- 通じることを認めるのは、正しい形を口に出したあとで短くてよい。認めるだけで直さないのは誤り。
- 軽い誤字・フィラー・STTノイズはスルー。文法の名前は言わない。TRY: は出さない。責めない。
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
    r"どういう意味|(って|と)なに|(って|と)何|なにそれ|何それ|"
    r"what does\s+\S+\s+mean|forgot how to say|how do (you|i) say|"
    r"what('s| is) the (japanese|english) (for|of))",
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
_COMPREHENSION_COLLAPSE_RE = re.compile(
    r"(全然わか|言ってること.{0,6}わか|"
    r"lots of words|too (many|much) words|don't understand|dont understand|"
    r"i don't understand|i dont understand|can't follow|cannot follow|"
    r"言葉が多|たくさんわか|何言ってるか)",
    re.IGNORECASE,
)
_COMPREHENSION_RE = re.compile(
    r"(わからない|分からない|わかんない|分かんない|"
    r"わかりません|分かりません|わかんないです|分かんないです|"
    r"全然わか|言ってること.{0,6}わか|"
    r"lots of words|too (many|much) words|don't understand|dont understand|"
    r"i don't understand|i dont understand|can't follow|cannot follow|"
    r"言葉が多|たくさんわか|何言ってるか|"
    r"ゆっくり(ください|お願いします|話して|話))",
    re.IGNORECASE,
)
_TARGETED_UNKNOWN_RE = re.compile(
    r"([\u3040-\u30ff\u3400-\u9fff]{2,8}?)"
    r"(?:って|が|は|を|の|で)?"
    r"(?:わからない|分からない|わかんない|分かんない|"
    r"わかりません|分かりません)"
)
_LEXEME_TAIL_RE = re.compile(r"(って|[がはをにので])$")
_NOT_LEXEME = frozenset(
    {
        "全然",
        "ちょっと",
        "あまり",
        "よく",
        "まだ",
        "もう",
        "ほんと",
        "本当",
        "何言",
        "会話",
        "日本語",
        "こと",
        "それ",
        "これ",
        "あれ",
        "意味",
    }
)
_FLOWING_SHORT = frozenset(
    {
        "はい",
        "うん",
        "ええ",
        "いいえ",
        "ううん",
        "そう",
        "そうだね",
        "そうです",
        "好き",
        "元気",
        "大丈夫",
        "うんうん",
        "わかる",
        "わかった",
        "おはよう",
        "こんにちは",
        "ありがとう",
    }
)
_YES_NO_Q_RE = re.compile(
    r"(ですか|ますか|でしたか|ましたか|の[？?]|かな[？?]|か[？?]|好き[？?]|元気[？?]|大丈夫[？?])"
)
_WH_Q_RE = re.compile(r"(何|なに|どれ|誰|だれ|どこ|いつ)")
_PARTICLE_CHAR_RE = re.compile(r"[はがをにでとへも]")
_HELP_RE = re.compile(
    r"(わからない|分からない|わかりません|分かりません|"
    r"なにそれ|何それ|どういう意味|意味|ってなに|って何|"
    r"英語で|help|what does|"
    r"i don't understand|dont understand|don't understand|in english|mean\?|"
    r"lots of words|ゆっくり)",
    re.IGNORECASE,
)
_FAKE_YES = frozenset({"はい", "うん", "ええ", "そう", "そうだね", "そうです"})
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


def _normalize_short(text: str) -> str:
    return re.sub(r"[。．.、,！!？?…・\s]+", "", text or "").strip()


def _is_question_line(assistant: str | None) -> bool:
    raw = (assistant or "").strip()
    if not raw:
        return False
    if "？" in raw or "?" in raw:
        return True
    last = raw.split("。")[-1].strip()
    return bool(re.search(r"か\s*$", last))


def _is_noun_only_reply(text: str) -> bool:
    compact = _normalize_short(text)
    if not compact or len(compact) > 12:
        return False
    if _PARTICLE_CHAR_RE.search(compact):
        return False
    latin = len(_LATIN_RE.findall(compact))
    jp = len(_JP_RE.findall(compact))
    return jp >= 1 and latin == 0 and jp == len(compact)


def is_natural_short_reply(learner: str | None, assistant: str | None = None) -> bool:
    """はい／パスタ when that was the question — not struggle."""
    raw = (learner or "").strip()
    if not raw:
        return False
    compact = _normalize_short(raw)
    asst = assistant or ""
    if compact in _FLOWING_SHORT:
        if compact in _FAKE_YES and _WH_Q_RE.search(asst):
            return False
        return True
    if not _is_question_line(asst):
        return False
    if _WH_Q_RE.search(asst) and _is_noun_only_reply(raw):
        return True
    return False


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
    if _COMPREHENSION_COLLAPSE_RE.search(raw):
        return "comprehension"
    targeted = _TARGETED_UNKNOWN_RE.search(raw)
    if targeted:
        lexeme = _LEXEME_TAIL_RE.sub("", targeted.group(1) or "")
        if lexeme not in _NOT_LEXEME and not lexeme.startswith("何言"):
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


def infer_learner_state(
    text: str | None,
    last_assistant: str | None = None,
) -> str:
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

    if is_natural_short_reply(raw, last_assistant):
        return "flowing"

    latin = len(_LATIN_RE.findall(raw))
    jp = len(_JP_RE.findall(raw))
    total_letters = latin + jp
    if total_letters == 0:
        return "struggling"

    latin_ratio = latin / total_letters
    # English-heavy alone is a weak signal (struggling), not automatic help_request.
    if latin_ratio >= 0.55:
        return "struggling"

    # Very short / fragmented learner turns — not はい／好き／パスタ.
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
    mode = (support_mode or "normal").strip().lower()
    ht = (help_type or "none").strip().lower()
    explicit_en = wants_explicit_english(last_user_text)
    beginner = (speech_pitch or "pre_n5") in {"unknown", "pre_n5"}

    if prefs.language_policy == "immerse":
        return f"""\
言語（イマーション）:
- 日本語のみ。英語グロスなし（明示要求でも英語にしない。やさしい日本語で言い換える）。
- 困ったとき: 短い言い換え＋例1つ。英語は使わない。
- このターン: support={mode} help_type={ht}
"""

    en_threshold = (
        "初期難易度は初級寄り（実力推定ではない）: まずやさしい日本語で1つ言い換える。まだダメなら短い英語救助。"
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
- vocabulary: その1語をやさしい日本語＋短い例で渡す。まだダメなら短い英語グロス（例: 「眠い」は sleepy）。理解崩壊にしない。
- comprehension: やさしい日本語で言い換え → まだダメなら英語の短い訳1つ → 日本語へ戻る。二択で逃げない。
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
        "simplified": "同じ考えの超短文。言い換え。新しい語は出さない。二択にしない。",
        "heavy": "いちばん短く同じ考え。言い換え。新しい語は出さない。二択にしない。Adaptive なら短い英語救助→日本語。",
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
    shape_lock: bool = False,
) -> str:
    """Topic stickiness + length bias for this turn."""
    state = (learner_state or "flowing").strip().lower()
    mode = (support_mode or "normal").strip().lower()
    if shape_lock:
        topic = (
            "学習者の言葉を再利用。今の考えに粘る。学習者が話題を変えたら従う。"
        )
        bias = (
            "難易度ガバナーの1考えルールに従う。短く答えやすい会話。"
            "同じ確認をくり返さない。次の番が続くフックを残す。"
        )
    else:
        topic = (
            "ヘルプや今の話題のあとすぐ飛ばない。1〜2ターン粘る／教えた語を再利用。"
            "学習者が話題を変えたら従う。"
        )
        if mode == "heavy":
            bias = "いちばん短く。同じ考えの言い換えだけ。二択にしない。"
        elif mode == "simplified" or state == "help_request":
            bias = "とても短く。情報は1ポイント。すぐ番を渡す。"
        elif mode == "light" or state == "struggling":
            bias = "短くはっきり。一文＋軽い質問1つ。"
        else:
            bias = "自然なテンポ。基本1〜2短文。必要なら最大2〜3短文。"
    return f"""\
会話の型:
- 話題: {topic}
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


def governor_pitch(
    prefs: UserPrefs,
    profile: Any | None = None,
    learner_state: str | None = None,
    *,
    support_mode: str = "normal",
) -> str:
    """Effective speech pitch after support/struggle nudge. Shared by prompt + retry."""
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
        return "unknown"
    pitch = effective_speech_level(prefs, profile)
    if mode in {"simplified", "heavy"} or state in {"struggling", "help_request"}:
        pitch = nudge_level(pitch, -1)
    if mode == "heavy":
        pitch = nudge_level(pitch, -1)
    return pitch


def shape_lock_active(
    pitch: str,
    support_mode: str = "normal",
    *,
    chat_pace: str = "easy",
) -> bool:
    """Temporary scaffold: pre-N5 / unknown, or simplified/heavy support.

    Turns off when pitch leaves pre_n5 (flow_streak / level nudge) or support
    decays. Free pace opts out of the gym lock. Not a permanent speaking style.
    """
    if (chat_pace or "easy").strip().lower() == "free":
        return False
    mode = (support_mode or "normal").strip().lower()
    p = (pitch or "").strip().lower()
    return p in {"unknown", "pre_n5"} or mode in {"simplified", "heavy"}


SHAPE_RETRY_BLOCK = """\
[shape_retry]
直前の返事は考えが多すぎた。新しい考えは最大1つ。
学習者の言葉を再利用し、同じ話題で短く答えやすい会話にする。二択アンケートにしない。
次の番が続くフックを残す。同じ確認のくり返しはしない。
今教えている形（が好き／眠いなど）は落とさない。
この難易度では負荷の高い型（〜れば／たら／なら など）は出さない（禁止ではなく今の負荷）。
助言・励ましの追加や話題のジャンプはしない。モード名は言わない。
（shape_retry は内部指示。学習者に見せない。）
"""

RECAST_RETRY_BLOCK = """\
[recast_retry]
直前の返事は直した形を口に出していない。学習者の意味が変わる誤りを、口頭の返事で正しい形を使って確認してから続ける。
文法の名前は言わない。TRY: は出さない。講義しない。
（recast_retry は内部指示。学習者に見せない。）
"""


def recast_hint_block(
    last_user_text: str | None,
    last_assistant_text: str | None = None,
) -> str:
    """This-turn hint when the learner said を好き / 眠り for 眠い / …"""
    from kaiwa.wo_ga import wo_ga_recast_stem, word_family_pair

    stem = wo_ga_recast_stem(last_user_text)
    if stem:
        return f"""\
[recast]
学習者は「を{stem}」。口頭の返事で「が{stem}」を使って確認してから続ける。今ターンはからかわない。文法の名前は言わない。TRY: は出さない。
（recast は内部指示。学習者に見せない。）
"""
    pair = word_family_pair(last_user_text, last_assistant_text)
    if not pair:
        return ""
    wrong, right = pair
    return f"""\
[recast]
学習者は「{wrong}」。口頭の返事で「{right}」を使って確認してから続ける。今ターンはからかわない。文法の名前は言わない。TRY: は出さない。
（recast は内部指示。学習者に見せない。）
"""


def elicit_hint_block(speakable: str | None) -> str:
    """After Practice wrap: ask a hook whose natural answer is the rehearsed form."""
    line = (speakable or "").strip()
    if not line:
        return ""
    return f"""\
[elicit]
学習者は今「{line}」を口にした。同じ話題で、その言い方が自然な答えになる短い質問を1つ（何が好き？／毎日飲む？）。
その全文を先に口に出さない。好き？だけにしない。今ターンはからかわない。
答えが名詞だけなら、口頭の返事でその言い方を使って確認してから続ける。
講義しない。TRY: は出さない。Practice / 文法の名前は言わない。新しい文法は足さない。
（elicit は内部指示。学習者に見せない。）
"""


def this_turn_keep_form_block(
    last_user_text: str | None,
    last_assistant_text: str | None = None,
    elicit_line: str | None = None,
) -> str:
    """Positive this-turn item so Easy density retry cannot drop the form in play.

    Elicit turns must not list the rehearsed speakable here — that made Kaiwa
    say the line instead of asking. Recast stems still belong.
    """
    from kaiwa.wo_ga import wo_ga_recast_stem, word_family_pair

    del elicit_line  # kept for callers; elicit is ask-not-say (#149)
    items: list[str] = []
    stem = wo_ga_recast_stem(last_user_text)
    if stem:
        items.append(f"が{stem}")
    pair = word_family_pair(last_user_text, last_assistant_text)
    if pair:
        items.append(pair[1])
    if not items:
        return ""
    listed = "／".join(dict.fromkeys(items))
    return f"""\
[this_turn]
今ターンの必須の形: {listed}。口頭の返事にそれを入れる。落とさない。からかわない。TRY: は出さない。
（this_turn は内部指示。学習者に見せない。）
"""


def rescue_rewrite_block(original: str, step: str) -> str:
    """Rescue-only system addendum. Not used on ordinary Chat turns."""
    key = (step or "shorter").strip().lower()
    if key == "yes_no":
        target = "はい／いいえで答えられる短い確認"
    elif key == "ab":
        target = "A と B の短い選択肢（それとも）"
    else:
        target = "同じ話題で考えは1つの短い言い直し"
        key = "shorter"
    orig = (original or "").strip()
    return f"""\
[rescue]
学習者は直前の発話がわからなかった（ボタン。学習者の発言ではない）。
元の発話: 「{orig}」
一段やさしく書き直す。目標: {target}（{key}）。
同じ話題。新しい考えは足さない。TRY: は出さない。モード名は言わない。
学習者が「わからない」と言った体にしない。
（rescue は内部指示。学習者に見せない。）
"""


def replay_block(questions: list[str] | None) -> str:
    """Child-session only. None means not a replay thread."""
    if questions is None:
        return ""
    if not questions:
        return """\
[replay]
これはやり直しの会話。用意した質問には答え終わった。
短い温かい一言だけ。新しい質問は出さない。新しい話題・文法は出さない。
TRY: は出さない。モード名は言わない。
（replay は内部指示。学習者に見せない。）
"""
    numbered = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
    return f"""\
[replay]
これはやり直しの会話。新しい教え・新しい話題・新しい文法は出さない。
用意した質問をこの順で出す（今の質問を含む）:
{numbered}
学習者が答えたら、短いあいづちのあと、次の質問を出す（ほぼ同じ聞き方）。
最後の質問の答えのあとは短い温かい一言だけ。新しい質問は出さない。
TRY: は出さない。モード名は言わない。
（replay は内部指示。学習者に見せない。）
"""


def difficulty_governor_block(
    prefs: UserPrefs,
    profile: Any | None = None,
    learner_state: str | None = None,
    *,
    support_mode: str = "normal",
) -> str:
    """Cap next-turn vocab/grammar density by demonstrated level."""
    mode = (support_mode or "normal").strip().lower()
    pitch = governor_pitch(
        prefs, profile, learner_state, support_mode=mode
    )
    lock = shape_lock_active(pitch, mode, chat_pace=prefs.chat_pace)

    if lock:
        band = (
            "考えは1つ（句点の数ではない。今、ひま？ は一つの流れ）。"
            "学習者の言葉を再利用。短く答えやすい会話。二択アンケートにしない。"
            "同じ確認をくり返さない。学習者の返事から次の番が続くフックを残す。"
            "第二の考え（励まし・助言・話題ジャンプ）は足さない。"
            "この難易度では負荷の高い型（〜れば／たら／なら など）は出さない。"
            "禁止文法ではなく今の負荷。余裕が出たら戻す。"
            "開き質問（どうした／何をしました／何したの／今日は何した／予定）は出さない。"
            "あいさつにはすぐ答えられるフック（元気？／今、ひま？）。"
            "今教えている形の が／を／に は落とさない（コーヒーが好き？は可。コーヒー、好き？ばかりにしない）。"
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
    help_type: str | None = None,
    replay_questions: list[str] | None = None,
    elicit_line: str | None = None,
) -> str:
    from kaiwa.learner_memory import LearnerMemory, memory_prompt_block
    from kaiwa.learner_profile import LearnerProfile, effective_speech_level

    if memory is None:
        memory = LearnerMemory()
    if profile is None:
        profile = LearnerProfile()
    assert isinstance(profile, LearnerProfile)

    state = learner_state or infer_learner_state(
        last_user_text, last_assistant_text
    )
    ht = (help_type or infer_help_type(last_user_text)).strip().lower()
    if ht not in {"none", "comprehension", "vocabulary", "expression", "correction"}:
        ht = infer_help_type(last_user_text)
    help_type = ht
    support = compute_support_mode(
        learner_state=state,
        help_type=help_type,
        struggle_streak=profile.stats.struggle_streak,
    )
    if not profile.placement_completed:
        speech_pitch = "unknown"
    else:
        speech_pitch = effective_speech_level(prefs, profile)
    lock = shape_lock_active(
        governor_pitch(prefs, profile, state, support_mode=support),
        support,
        chat_pace=prefs.chat_pace,
    )

    parts = [
        PRIORITY_HIERARCHY_BLOCK.strip(),
        "",
        IDENTITY_BLOCK.strip(),
        "",
        identity_names_block(memory).strip(),
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
        CORRECTION_BLOCK.strip(),
        "",
        MICRO_INVARIANTS_BLOCK.strip(),
        "",
        conversation_craft_block(
            state, support_mode=support, shape_lock=lock
        ).strip(),
        "",
        memory_prompt_block(memory, prefs).strip(),
    ]
    thread_line = thread_stickiness_block(
        last_assistant_text, last_user_text, state
    ).strip()
    if thread_line:
        parts.extend(["", thread_line])
    replay_line = replay_block(replay_questions).strip()
    if replay_line:
        parts.extend(["", replay_line])
    elicit = elicit_hint_block(elicit_line).strip()
    if elicit:
        parts.extend(["", elicit])
    recast_line = recast_hint_block(
        last_user_text, last_assistant_text
    ).strip()
    if recast_line:
        parts.extend(["", recast_line])
    keep = this_turn_keep_form_block(
        last_user_text, last_assistant_text, elicit_line
    ).strip()
    if keep:
        parts.extend(["", keep])
    return "\n".join(parts)


def build_practice_sitting_system_prompt(
    prefs: UserPrefs,
    card: dict[str, Any],
    *,
    remaining_turns: int,
    opening: bool = False,
    wrap: bool = False,
    memory: Any | None = None,
) -> str:
    """Practice sitting only. Does not change Chat tutor policy / PROMPT_REVISION."""
    learner_line = str(card.get("learner_line") or "").strip()
    tutor_reply = str(card.get("tutor_reply") or "").strip()
    speakable = str(card.get("speakable") or "").strip()
    prior_user = str(card.get("prior_user") or "").strip()
    prior_assistant = str(card.get("prior_assistant") or "").strip()
    example = speakable or tutor_reply
    left = max(0, int(remaining_turns))

    if wrap or left <= 0:
        close = (
            "これが最後の番。短い温かい一言で閉じる。新しい質問は出さない。"
            "Chat へ戻るよう促さない（UI が戻す）。モード名は言わない。"
        )
    elif opening:
        close = (
            "まだ学習者の番はない。「"
            + example
            + "」を口に出してもらう短い誘いだけ。新しい話題は出さない。"
            "Chat の原文を講義し直さない。文法の名前は言わない。"
        )
    else:
        close = (
            "その同じ言い方を使う短いやり取りを1つだけ出す。新しい話題カタログは出さない。"
            "新しい文法は教えない。"
        )

    snapshot = f"""\
[practice_sitting]
これは短いリハーサル（Chat ではない）。Chat ですでに触れた1つの言い方を口に出して慣れる。
学習者の発話: 「{learner_line}」
会話の返事: 「{tutor_reply}」
口に出す日本語: 「{example}」
直前の学習者: 「{prior_user}」
直前の会話: 「{prior_assistant}」
ルール:
- 言い方を口に出す → それを使う短いやり取り1つ → 終わり。Easy Chat の続きにしない。
- この1つの言い方だけ。新しい文法・新しい話題は出さない。
- 性格は声だけ。からかい・新しい話題はしない。
- 学習者に見えるのは話せる日本語。タグ名は出さない。
- TRY: は出さない。モード名は言わない。
- {close}
（practice_sitting は内部指示。学習者に見せない。）
"""
    parts = [
        identity_names_block(memory).strip(),
        "",
        personality_block(prefs).strip(),
        "",
        "会話の型:\n- これは短いリハーサル。Chat の続きにしない。口頭は短く。新しい話題は出さない。",
        "",
        snapshot.strip(),
    ]
    return "\n".join(parts)
