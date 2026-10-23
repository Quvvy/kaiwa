"""Closed recast families (Chat hint/retry + Practice cards).

を→が for 好き/わかる/ほしい/できる is the original demo.
眠り/眠い is the original tutor-critique miss — still a string gate, not a parser.
"""

from __future__ import annotations

import re
from typing import Any

WO_GA_GROUPS = (
    ("好き", "すき"),
    ("わかる", "分かる"),
    ("ほしい", "欲しい"),
    ("できる", "出来る"),
)
WO_GA_STEMS = tuple(stem for group in WO_GA_GROUPS for stem in group)

# (wrong forms, right forms). Learner used a wrong; tutor must use a right.
# 楽しみ/楽しい is a different word — not this gate.
WORD_FAMILY_GROUPS = (
    (("眠り", "ねむり"), ("眠い", "ねむい")),
)

_SENT_RE = re.compile(r"[^。！？\n]+[。！？]?")
_SHORT_REPLY = 48
_HELPISH_RE = re.compile(
    r"(わから|分かん|わかりません|分かりません|意味|なんて|何て|how do|what does)",
    re.IGNORECASE,
)
_SPLIT_TOPIC_RE = re.compile(r"[はがも]")


def wo_ga_recast_stem(learner: str | None) -> str:
    """Stem if the learner said を好き / をわかる / … Else empty.

    Returns the learner’s exact surface so the Chat hint can say をすき.
    """
    src = learner or ""
    if not src:
        return ""
    for stem in WO_GA_STEMS:
        if f"を{stem}" in src:
            return stem
    return ""


def _group_for_stem(stem: str) -> tuple[str, ...]:
    for group in WO_GA_GROUPS:
        if stem in group:
            return group
    return (stem,) if stem else ()


def _ga_needles(learner: str | None) -> tuple[str, ...]:
    stem = wo_ga_recast_stem(learner)
    if not stem:
        return ()
    return tuple(f"が{variant}" for variant in _group_for_stem(stem))


def needs_wo_ga_recast(learner: str | None, tutor: str | None) -> bool:
    """True when the spoken reply still lacks が + any variant of the を-stem."""
    needles = _ga_needles(learner)
    if not needles:
        return False
    dst = tutor or ""
    return not any(needle in dst for needle in needles)


def word_family_pair(
    learner: str | None,
    last_assistant: str | None = None,
) -> tuple[str, str] | None:
    """(wrong, right) if the learner used the noun where the i-adj was in play."""
    src = learner or ""
    if not src:
        return None
    if _HELPISH_RE.search(src):
        return None
    asst = last_assistant or ""
    for wrongs, rights in WORD_FAMILY_GROUPS:
        if any(right in src for right in rights):
            continue
        wrong = next((item for item in wrongs if item in src), "")
        if not wrong:
            continue
        asst_has = any(right in asst for right in rights)
        rest = src[src.find(wrong) + len(wrong) :]
        pred = rest.startswith(("です", "だよ", "だね", "だ。")) or rest.startswith("だ")
        if asst_has or pred:
            return wrong, rights[0]
    return None


def _family_rights(wrong: str) -> tuple[str, ...]:
    for wrongs, rights in WORD_FAMILY_GROUPS:
        if wrong in wrongs:
            return rights
    return ()


def needs_word_family_recast(
    learner: str | None,
    tutor: str | None,
    last_assistant: str | None = None,
) -> bool:
    pair = word_family_pair(learner, last_assistant)
    if not pair:
        return False
    rights = _family_rights(pair[0])
    dst = tutor or ""
    return bool(rights) and not any(right in dst for right in rights)


def expects_recast(learner: str | None, last_assistant: str | None = None) -> bool:
    return bool(wo_ga_recast_stem(learner) or word_family_pair(learner, last_assistant))


def needs_any_recast(
    learner: str | None,
    tutor: str | None,
    last_assistant: str | None = None,
) -> bool:
    return needs_wo_ga_recast(learner, tutor) or needs_word_family_recast(
        learner, tutor, last_assistant
    )


def _object_before_wo(learner: str, stem: str) -> str:
    src = learner or ""
    needle = f"を{stem}"
    idx = src.find(needle)
    if idx <= 0:
        return ""
    start = idx
    while start > 0 and src[start - 1] not in "。！？\n、 ":
        start -= 1
        if idx - start > 16:
            break
    chunk = src[start:idx].strip()
    parts = [p.strip() for p in _SPLIT_TOPIC_RE.split(chunk) if p.strip()]
    noun = parts[-1] if parts else chunk
    noun = re.sub(r"^(私|僕|俺|自分)", "", noun).strip()
    return noun[:16]


def splice_wo_ga_model(learner: str | None, tutor: str | None) -> str:
    """Speak only the canned が+stem sentence when the LLM never said it."""
    stem = wo_ga_recast_stem(learner)
    if not stem:
        return (tutor or "").strip()
    model_stem = _group_for_stem(stem)[0]
    noun = _object_before_wo(learner or "", stem)
    model = f"{noun}が{model_stem}なんだね。" if noun else f"が{model_stem}なんだね。"
    base = (tutor or "").strip()
    if model in (base or ""):
        return base
    return model


def splice_word_family_model(
    learner: str | None,
    tutor: str | None,
    last_assistant: str | None = None,
) -> str:
    pair = word_family_pair(learner, last_assistant)
    if not pair:
        return (tutor or "").strip()
    _wrong, right = pair
    model = f"{right}んだね。"
    base = (tutor or "").strip()
    if any(item in base for item in _family_rights(_wrong)):
        return base
    return model


def recast_phrase(
    learner: str | None,
    tutor: str | None,
    last_assistant: str | None = None,
) -> str:
    """First spoken sentence that models this turn’s recast. Else empty."""
    needles = _ga_needles(learner)
    if not needles:
        pair = word_family_pair(learner, last_assistant)
        if not pair:
            return ""
        needles = _family_rights(pair[0])
    if not needles:
        return ""
    dst = (tutor or "").strip()
    needle = next((item for item in needles if item in dst), "")
    if not needle:
        return ""
    for sent in _SENT_RE.findall(dst):
        piece = sent.strip()
        if piece and any(item in piece for item in needles):
            return piece
    if len(dst) <= _SHORT_REPLY:
        return dst
    idx = dst.find(needle)
    start = idx
    while start > 0 and dst[start - 1] not in "。！？\n、 ":
        start -= 1
        if idx - start > 24:
            break
    end = idx + len(needle)
    while end < len(dst) and dst[end] not in "。！？\n":
        end += 1
        if end - (idx + len(needle)) > 24:
            break
    if end < len(dst) and dst[end] in "。！？":
        end += 1
    return dst[start:end].strip()


def prefer_recast_reply(
    learner: str | None,
    first: str,
    retry: str,
    last_assistant: str | None = None,
) -> tuple[str, bool]:
    """Prefer a reply that contains the model. If both miss, speak the canned sentence.

    Call only when the first reply needed a recast. Do not glue the forgive-only leftover.
    """
    if wo_ga_recast_stem(learner):
        if not needs_wo_ga_recast(learner, retry):
            return retry, True
        if not needs_wo_ga_recast(learner, first):
            return first, True
        spliced = splice_wo_ga_model(learner, retry or first)
        return spliced, not needs_wo_ga_recast(learner, spliced)
    if word_family_pair(learner, last_assistant):
        if not needs_word_family_recast(learner, retry, last_assistant):
            return retry, True
        if not needs_word_family_recast(learner, first, last_assistant):
            return first, True
        spliced = splice_word_family_model(learner, retry or first, last_assistant)
        return spliced, not needs_word_family_recast(
            learner, spliced, last_assistant
        )
    return retry, False


def with_recast_notices(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copy messages and attach recast_phrase on assistant turns. Read-time only."""
    out: list[dict[str, Any]] = []
    prev_user = ""
    prev_asst_before_user = ""
    last_asst = ""
    for message in messages:
        row = dict(message)
        role = str(row.get("role") or "")
        content = str(row.get("content") or "")
        if role == "assistant":
            if not row.get("rescue"):
                phrase = recast_phrase(
                    prev_user, content, last_assistant=prev_asst_before_user
                )
                if phrase:
                    row["recast_phrase"] = phrase
            last_asst = content
        elif role == "user":
            prev_asst_before_user = last_asst
            prev_user = content
        out.append(row)
    return out
