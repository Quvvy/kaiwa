"""Immutable Chat struggle snapshots for Phase 9 Practice.

Cards are written at the Chat moment. They are never rebuilt from extract
`grammar_add` / vocab. Used-card ids live in practice_state.json, not here.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kaiwa import profiles
from kaiwa.persona import (
    _FILLER_EN_RE,
    _JP_RE,
    _LATIN_RE,
    infer_help_type,
    infer_learner_state,
    wants_explicit_english,
)
from kaiwa.wo_ga import (
    needs_wo_ga_recast,
    needs_word_family_recast,
    wo_ga_recast_stem,
    word_family_pair,
)

CARDS_FILE = "struggle_cards.jsonl"
SIGNALS = frozenset({"rescue", "help_request", "struggling"})
_AFFIRM_SHORT = frozenset(
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
    }
)
_PARTICLE_RE = re.compile(r"[はがをにでとへも]")
_YES_NO_RE = re.compile(
    r"(ですか|ますか|でしたか|ましたか|の[？?]|かな[？?]|か[？?]|好き[？?]|元気[？?]|大丈夫[？?])"
)
_WH_RE = re.compile(r"(何|なに|どれ|誰|だれ|どこ|いつ)")
_JP_RUN_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]{2,}")
_JP_FILLERS = frozenset({"えっと", "えーと", "あの", "あのう", "うーん"})
_AGAIN_RE = re.compile(r"^(もう一回(お願いします)?|もう一度(お願いします)?)$")
FREEZE_EMPTY_LINE = "…"
SPEAKABLE_ETTO = "えっと…"
SPEAKABLE_AGAIN = "もう一回お願いします"
SURVIVAL_LINES = frozenset({SPEAKABLE_ETTO, SPEAKABLE_AGAIN})
_JUNK_SPEAKABLE = frozenset(
    {
        "ごめん",
        "ごめんなさい",
        "ごめんね",
        "そうなんだ",
        "そうなんだね",
        "そっか",
        "うん",
        "うんうん",
        "ゆっくり言うね",
        "短く言うね",
        "もう一回言うね",
        "大丈夫",
        "大丈夫だよ",
        "いいよ",
        "ごめん。",
        "そうなんだ。",
    }
)
_GLOSS_RE = re.compile(r"」は\s*[A-Za-z]|は\s*[A-Za-z]{3,}")
_RECAST_FAMILY_RE = re.compile(
    r"が好き|がすき|がわかる|が分かる|がほしい|が欲しい|ができる|が出来る|眠い"
)


def is_survival_card(card: dict[str, Any] | None) -> bool:
    """Freeze/survival speakable — rehearse if asked, never today's default."""
    return display_line(card) in SURVIVAL_LINES


def is_recast_family_line(line: str | None) -> bool:
    """Closed を→が / 眠い family the learner can actually reuse in Chat."""
    return bool(_RECAST_FAMILY_RE.search(line or ""))


def practice_worthy_line(line: str | None) -> bool:
    """True if this Japanese is worth Today's sitting / Learn (not gloss or backchannel)."""
    raw = (line or "").strip()
    if not raw or raw in SURVIVAL_LINES:
        return False
    compact = _normalize_short(raw)
    if not compact or compact in SURVIVAL_LINES:
        return False
    if compact in _JUNK_SPEAKABLE or raw in _JUNK_SPEAKABLE:
        return False
    if english_unsolicited(raw) or _latin_ratio(raw) >= 0.45:
        return False
    if _GLOSS_RE.search(raw):
        return False
    if not _JP_RUN_RE.search(raw):
        return False
    return True


def is_practice_worthy(card: dict[str, Any] | None) -> bool:
    """Today / Learn pick: stored recast/help line, not tutor fragments or English essays."""
    if not isinstance(card, dict) or is_survival_card(card):
        return False
    stored = str(card.get("speakable") or "").strip()
    if stored:
        return practice_worthy_line(stored)
    line = display_line(card)
    return practice_worthy_line(line) and is_recast_family_line(line)


def cards_path(profile_dir: Path | None = None) -> Path:
    return (profile_dir or profiles.active_profile_dir()) / CARDS_FILE


def snapshot_signal(*, learner_state: str, rescue: bool = False) -> str | None:
    """Return a card signal, or None when this turn should not snapshot."""
    if rescue:
        return "rescue"
    state = (learner_state or "").strip().lower()
    if state in {"help_request", "struggling"}:
        return state
    return None


def prior_context(
    history: list[dict[str, str]] | None,
    *,
    skip_last: int = 2,
) -> tuple[str, str]:
    """One user/assistant pair before the current turn."""
    rows = list(history or [])
    if skip_last > 0:
        rows = rows[:-skip_last] if len(rows) > skip_last else []
    prior_user = ""
    prior_assistant = ""
    for message in reversed(rows):
        role = str(message.get("role") or "")
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        if not prior_assistant and role == "assistant":
            prior_assistant = content
        elif not prior_user and role == "user":
            prior_user = content
        if prior_user and prior_assistant:
            break
    return prior_user, prior_assistant


def last_user_line(history: list[dict[str, str]] | None) -> str:
    for message in reversed(history or []):
        if message.get("role") == "user":
            text = str(message.get("content") or "").strip()
            if text:
                return text
    return ""


def last_assistant_line(history: list[dict[str, str]] | None) -> str:
    for message in reversed(history or []):
        if message.get("role") == "assistant":
            text = str(message.get("content") or "").strip()
            if text:
                return text
    return ""


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


def _normalize_short(text: str) -> str:
    return re.sub(r"[。．.、,！!？?…・\s]+", "", text or "").strip()


def _letter_counts(text: str) -> tuple[int, int]:
    raw = text or ""
    return len(_LATIN_RE.findall(raw)), len(_JP_RE.findall(raw))


def _empty_letters(text: str) -> bool:
    latin, jp = _letter_counts(text)
    return (latin + jp) == 0


def _latin_ratio(text: str) -> float:
    latin, jp = _letter_counts(text)
    total = latin + jp
    if total == 0:
        return 0.0
    return latin / total


def english_unsolicited(text: str) -> bool:
    raw = (text or "").strip()
    if not raw or wants_explicit_english(raw):
        return False
    return _latin_ratio(raw) >= 0.55


def is_minimal(text: str) -> bool:
    """Same short/fragment heuristic as infer_learner_state."""
    raw = (text or "").strip()
    if not raw or _empty_letters(raw):
        return False
    latin, jp = _letter_counts(raw)
    compact = _compact(raw)
    if len(compact) <= 4 and jp < 3:
        return True
    return jp <= 2 and latin == 0 and len(compact) <= 6


def freeze_speakable(text: str) -> str:
    """Survival line for a freeze card. Not a grammar lecture."""
    compact = _normalize_short(text)
    if compact and _AGAIN_RE.match(compact):
        return SPEAKABLE_AGAIN
    return SPEAKABLE_ETTO


def is_freeze_line(text: str) -> bool:
    """Transcribed freeze: filler, punctuation-only, or survival they already said."""
    raw = (text or "").strip()
    if not raw:
        return False
    if _empty_letters(raw):
        return True
    if _FILLER_EN_RE.match(raw):
        return True
    compact = _normalize_short(raw)
    if not compact or compact == "ん":
        return False
    if compact in _JP_FILLERS:
        return True
    return bool(_AGAIN_RE.match(compact))


def _is_question(assistant: str) -> bool:
    raw = (assistant or "").strip()
    if not raw:
        return False
    if "？" in raw or "?" in raw:
        return True
    last = raw.split("。")[-1].strip()
    return bool(re.search(r"か\s*$", last))


def _is_yes_no_question(assistant: str) -> bool:
    return _is_question(assistant) and bool(_YES_NO_RE.search(assistant or ""))


def _is_wh_question(assistant: str) -> bool:
    return bool(_WH_RE.search(assistant or ""))


def _is_noun_only(text: str) -> bool:
    compact = _normalize_short(text)
    if not compact or len(compact) > 12:
        return False
    if _PARTICLE_RE.search(compact):
        return False
    latin, jp = _letter_counts(compact)
    return jp >= 1 and latin == 0 and jp == len(compact)


def is_natural_answer(learner: str, assistant: str) -> bool:
    """はい／パスタ when that was the question — not a confidence hole."""
    if not (learner or "").strip() or not _is_question(assistant):
        return False
    compact = _normalize_short(learner)
    if not compact:
        return False
    if compact in _AFFIRM_SHORT:
        if _is_wh_question(assistant):
            return False
        return _is_yes_no_question(assistant) or _is_question(assistant)
    return _is_wh_question(assistant) and _is_noun_only(learner)


def _previous_user_line(
    history: list[dict[str, str]] | None, current: str
) -> str:
    seen_current = False
    current = (current or "").strip()
    for message in reversed(history or []):
        if message.get("role") != "user":
            continue
        text = str(message.get("content") or "").strip()
        if not text:
            continue
        if not seen_current and current and text == current:
            seen_current = True
            continue
        return text
    return ""


def _prompt_for_line(history: list[dict[str, str]] | None, learner_line: str) -> str:
    """Assistant turn immediately before this learner line."""
    rows = list(history or [])
    target = (learner_line or "").strip()
    if target:
        for i in range(len(rows) - 1, -1, -1):
            if rows[i].get("role") != "user":
                continue
            if str(rows[i].get("content") or "").strip() != target:
                continue
            for j in range(i - 1, -1, -1):
                if rows[j].get("role") == "assistant":
                    return str(rows[j].get("content") or "").strip()
            return ""
    for message in reversed(rows):
        if message.get("role") == "assistant":
            text = str(message.get("content") or "").strip()
            if text:
                return text
    return ""


def _jp_runs(text: str) -> set[str]:
    return set(_JP_RUN_RE.findall(text or ""))


def _is_jp_attempt(text: str) -> bool:
    latin, jp = _letter_counts(text)
    return jp >= 1 and jp >= latin


def _is_retreat(current: str, prompt: str) -> bool:
    if is_natural_answer(current, prompt):
        return False
    if english_unsolicited(current):
        return True
    if _normalize_short(current) in _AFFIRM_SHORT:
        return True
    return is_minimal(current)


def struggling_is_cardable(learner_line: str, history: list[dict[str, str]] | None) -> bool:
    """English-without-asking or repeated minimal (not natural answers)."""
    line = (learner_line or "").strip()
    if not line or _empty_letters(line):
        return False
    if english_unsolicited(line):
        return True
    prev = _previous_user_line(history, line)
    if not prev or _empty_letters(prev):
        return False
    if not (is_minimal(line) and is_minimal(prev)):
        return False
    if is_natural_answer(line, _prompt_for_line(history, line)):
        return False
    if is_natural_answer(prev, _prompt_for_line(history, prev)):
        return False
    return True


def abandoned_attempt(
    history: list[dict[str, str]] | None, current: str
) -> str:
    """Previous JP attempt they left. Empty if not observable."""
    line = (current or "").strip()
    prev = _previous_user_line(history, line)
    if not line or not prev:
        return ""
    if infer_learner_state(prev) == "help_request":
        return ""
    if not _is_jp_attempt(prev) or not is_minimal(prev):
        return ""
    prev_prompt = _prompt_for_line(history, prev)
    if is_natural_answer(prev, prev_prompt):
        return ""
    if _jp_runs(prev) & _jp_runs(line):
        return ""
    if not _is_retreat(line, _prompt_for_line(history, line)):
        return ""
    return prev


def meaningful_correction(
    learner: str,
    tutor: str,
    last_assistant: str = "",
) -> str:
    """Learner miss + tutor model → swapped speakable. Empty if tutor never modeled it."""
    stem = wo_ga_recast_stem(learner)
    if stem:
        if needs_wo_ga_recast(learner, tutor):
            return ""
        return (learner or "").replace(f"を{stem}", f"が{stem}", 1)
    pair = word_family_pair(learner, last_assistant or tutor)
    if not pair:
        return ""
    if needs_word_family_recast(learner, tutor, last_assistant or tutor):
        return ""
    wrong, right = pair
    return (learner or "").replace(wrong, right, 1)


def _help_type_for(*, signal: str, transcript: str) -> str:
    if signal == "rescue":
        return "comprehension"
    ht = infer_help_type(transcript)
    return ht if ht else "none"


def load_cards(path: Path | None = None) -> list[dict[str, Any]]:
    file = path or cards_path()
    if not file.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        raw = file.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("id"):
            out.append(row)
    return out


def _is_duplicate(
    cards: list[dict[str, Any]],
    *,
    session_id: str,
    learner_line: str,
) -> bool:
    if not cards:
        return False
    last = cards[-1]
    return (
        str(last.get("session_id") or "") == session_id
        and str(last.get("learner_line") or "").strip() == learner_line
    )


def append_card(card: dict[str, Any], *, path: Path | None = None) -> dict[str, Any]:
    file = path or cards_path()
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(card, ensure_ascii=False) + "\n")
    return card


def build_card(
    *,
    session_id: str,
    signal: str,
    learner_line: str,
    tutor_reply: str,
    speakable: str | None = None,
    help_type: str = "none",
    prior_user: str = "",
    prior_assistant: str = "",
) -> dict[str, Any]:
    return {
        "id": uuid.uuid4().hex,
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "signal": signal,
        "help_type": help_type,
        "learner_line": learner_line,
        "tutor_reply": tutor_reply,
        "speakable": (speakable or "").strip() or None,
        "prior_user": prior_user,
        "prior_assistant": prior_assistant,
    }


def maybe_write_card(
    *,
    session_id: str,
    history: list[dict[str, str]] | None,
    learner_state: str,
    transcript: str,
    reply: str,
    speakable: str | None = None,
    rescue: bool = False,
    path: Path | None = None,
) -> dict[str, Any] | None:
    """Append a snapshot when Chat shows struggle / help / Simpler. Never raises."""
    try:
        signal = snapshot_signal(learner_state=learner_state, rescue=rescue)
        current = (transcript or "").strip()
        learner_line = last_user_line(history) if rescue else current
        tutor_reply = (reply or "").strip()
        if not tutor_reply:
            return None
        prior_user, prior_assistant = prior_context(history, skip_last=2)
        phrase = speakable

        if signal in {"rescue", "help_request"}:
            pass
        elif not rescue and not current:
            last_asst = last_assistant_line(history)
            if not last_asst:
                return None
            signal = "struggling"
            learner_line = FREEZE_EMPTY_LINE
            tutor_reply = last_asst
            phrase = phrase or SPEAKABLE_ETTO
            prior_user, prior_assistant = prior_context(history, skip_last=0)
        elif is_freeze_line(current):
            signal = "struggling"
            learner_line = current
            phrase = freeze_speakable(current)
        elif signal == "struggling" and learner_line and english_unsolicited(
            learner_line
        ):
            pass
        else:
            abandoned = abandoned_attempt(history, current or learner_line)
            if abandoned:
                signal = "struggling"
                learner_line = abandoned
                prior_assistant = _prompt_for_line(history, abandoned)
                prior_user = _previous_user_line(history, abandoned)
            elif signal == "struggling" and struggling_is_cardable(
                learner_line, history
            ):
                pass
            else:
                swapped = meaningful_correction(
                    learner_line,
                    tutor_reply,
                    last_assistant=_prompt_for_line(history, learner_line),
                )
                if not swapped:
                    return None
                signal = "struggling"
                if not phrase:
                    phrase = swapped

        if not learner_line:
            return None
        cards = load_cards(path)
        if _is_duplicate(cards, session_id=session_id, learner_line=learner_line):
            return None
        card = build_card(
            session_id=session_id,
            signal=signal,
            learner_line=learner_line,
            tutor_reply=tutor_reply,
            speakable=phrase,
            help_type=_help_type_for(signal=signal, transcript=learner_line),
            prior_user=prior_user,
            prior_assistant=prior_assistant,
        )
        return append_card(card, path=path)
    except Exception:
        return None


def unused_cards(
    cards: list[dict[str, Any]] | None = None,
    used_ids: list[str] | None = None,
    *,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    rows = cards if cards is not None else load_cards(path)
    used = {str(i) for i in (used_ids or []) if i}
    return [row for row in rows if str(row.get("id") or "") not in used]


def newest_unused(
    cards: list[dict[str, Any]] | None = None,
    used_ids: list[str] | None = None,
    *,
    path: Path | None = None,
) -> dict[str, Any] | None:
    leftover = unused_cards(cards, used_ids, path=path)
    if not leftover:
        return None
    worthy = [row for row in leftover if is_practice_worthy(row)]
    if not worthy:
        return None
    family = [row for row in worthy if is_recast_family_line(display_line(row))]
    pool = family or worthy
    return pool[-1]


def _first_sentence(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    if "。" in raw:
        head = raw.split("。", 1)[0].strip()
        return f"{head}。" if head else ""
    return raw


def display_line(card: dict[str, Any] | None) -> str:
    """Japanese the learner should see in a sitting. No grammar tags."""
    if not isinstance(card, dict):
        return ""
    speakable = str(card.get("speakable") or "").strip()
    if speakable:
        return speakable
    first = _first_sentence(str(card.get("tutor_reply") or ""))
    if first:
        return first
    return str(card.get("learner_line") or "").strip()


def why_line(card: dict[str, Any] | None) -> str:
    """One Practice-only noticing sentence. No grammar-class names."""
    if not isinstance(card, dict):
        return ""
    learner = str(card.get("learner_line") or "").strip()
    speakable = display_line(card)
    if speakable in SURVIVAL_LINES:
        return "A line you can use when you freeze in Chat."
    stem = wo_ga_recast_stem(learner)
    if stem and speakable:
        return f"You said を{stem} — this line uses が{stem}."
    pair = word_family_pair(learner, str(card.get("prior_assistant") or ""))
    if pair and speakable:
        wrong, right = pair
        if wrong in {"眠り", "ねむり"}:
            return "眠り is sleep; 眠い is sleepy. Say this line."
        return f"{wrong} vs {right} — say 「{speakable}」."
    if speakable:
        return f"Say 「{speakable}」 — a line from your chat."
    return ""
