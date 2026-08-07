from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kaiwa.config import ROOT, Settings
from kaiwa.learner_profile import LearnerProfile
from kaiwa.prefs import UserPrefs

MEMORY_PATH = ROOT / "data" / "learner_memory.json"
EXAMPLE_MEMORY_PATH = ROOT / "data" / "learner_memory.example.json"

MAX_VOCAB = 12
MAX_GRAMMAR = 8
MAX_TOPICS = 8
MAX_VIBE = 300
MAX_DO_DONT = 5
MAX_NAME = 40
MAX_NOTE = 120
MAX_RECYCLE = 12
MAX_RECYCLE_TEXT = 80
CLEARS_TO_EASE = 1
EXTRACT_EVERY_N = 6


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ComfortPrefs:
    preferred_name: str = ""
    vibe_notes: str = ""
    do: list[str] = field(default_factory=list)
    dont: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VocabItem:
    surface: str
    note: str = ""
    hits: int = 1
    last_seen: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GrammarNote:
    pattern: str
    hint: str = ""
    hits: int = 1
    last_seen: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecycleItem:
    """Soft “say again” line — not a fail log."""

    text: str
    reason: str = "retry"  # retry | vocab
    attempts: int = 0
    clears: int = 0
    last_seen: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryStats:
    chat_turns: int = 0
    chat_turns_since_extract: int = 0
    last_extract_turn: int = 0
    total_extracts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LearnerMemory:
    comfort: ComfortPrefs = field(default_factory=ComfortPrefs)
    topics: list[str] = field(default_factory=list)
    vocab: list[VocabItem] = field(default_factory=list)
    grammar_notes: list[GrammarNote] = field(default_factory=list)
    recycle_items: list[RecycleItem] = field(default_factory=list)
    stats: MemoryStats = field(default_factory=MemoryStats)
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "comfort": self.comfort.to_dict(),
            "topics": list(self.topics),
            "vocab": [v.to_dict() for v in self.vocab],
            "grammar_notes": [g.to_dict() for g in self.grammar_notes],
            "recycle_items": [r.to_dict() for r in self.recycle_items],
            "stats": self.stats.to_dict(),
            "updated_at": self.updated_at,
        }


def default_memory() -> LearnerMemory:
    return LearnerMemory(updated_at=_now_iso())


def _clip(text: str, n: int) -> str:
    return (text or "").strip()[:n]


def _normalize_topics(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        items = [p.strip() for p in raw.split(",")]
    elif isinstance(raw, list):
        items = [str(p).strip() for p in raw]
    else:
        return []
    out: list[str] = []
    for item in items:
        if not item:
            continue
        item = item[:40]
        if item not in out:
            out.append(item)
        if len(out) >= MAX_TOPICS:
            break
    return out


def _parse_comfort(raw: Any) -> ComfortPrefs:
    if not isinstance(raw, dict):
        return ComfortPrefs()
    do = [str(x).strip()[:80] for x in (raw.get("do") or []) if str(x).strip()][:MAX_DO_DONT]
    dont = [str(x).strip()[:80] for x in (raw.get("dont") or []) if str(x).strip()][:MAX_DO_DONT]
    return ComfortPrefs(
        preferred_name=_clip(str(raw.get("preferred_name", "")), MAX_NAME),
        vibe_notes=_clip(str(raw.get("vibe_notes", "")), MAX_VIBE),
        do=do,
        dont=dont,
    )


def _parse_vocab(raw: Any) -> list[VocabItem]:
    if not isinstance(raw, list):
        return []
    out: list[VocabItem] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        surface = _clip(str(item.get("surface", "")), 60)
        if not surface:
            continue
        try:
            hits = max(1, int(item.get("hits", 1)))
        except (TypeError, ValueError):
            hits = 1
        out.append(
            VocabItem(
                surface=surface,
                note=_clip(str(item.get("note", "")), MAX_NOTE),
                hits=hits,
                last_seen=str(item.get("last_seen") or ""),
            )
        )
        if len(out) >= MAX_VOCAB:
            break
    return out


def _parse_grammar(raw: Any) -> list[GrammarNote]:
    if not isinstance(raw, list):
        return []
    out: list[GrammarNote] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        pattern = _clip(str(item.get("pattern", "")), 80)
        if not pattern:
            continue
        try:
            hits = max(1, int(item.get("hits", 1)))
        except (TypeError, ValueError):
            hits = 1
        out.append(
            GrammarNote(
                pattern=pattern,
                hint=_clip(str(item.get("hint", "")), MAX_NOTE),
                hits=hits,
                last_seen=str(item.get("last_seen") or ""),
            )
        )
        if len(out) >= MAX_GRAMMAR:
            break
    return out


def _parse_recycle(raw: Any) -> list[RecycleItem]:
    if not isinstance(raw, list):
        return []
    out: list[RecycleItem] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = _clip(str(item.get("text", "")), MAX_RECYCLE_TEXT)
        if not text:
            continue
        reason = str(item.get("reason") or "retry").strip().lower()
        if reason not in {"retry", "vocab"}:
            reason = "retry"
        try:
            attempts = max(0, int(item.get("attempts", 0)))
        except (TypeError, ValueError):
            attempts = 0
        try:
            clears = max(0, int(item.get("clears", 0)))
        except (TypeError, ValueError):
            clears = 0
        out.append(
            RecycleItem(
                text=text,
                reason=reason,
                attempts=attempts,
                clears=clears,
                last_seen=str(item.get("last_seen") or ""),
            )
        )
        if len(out) >= MAX_RECYCLE:
            break
    return out


def _parse_stats(raw: Any) -> MemoryStats:
    if not isinstance(raw, dict):
        return MemoryStats()

    def _int(key: str) -> int:
        try:
            return max(0, int(raw.get(key, 0)))
        except (TypeError, ValueError):
            return 0

    return MemoryStats(
        chat_turns=_int("chat_turns"),
        chat_turns_since_extract=_int("chat_turns_since_extract"),
        last_extract_turn=_int("last_extract_turn"),
        total_extracts=_int("total_extracts"),
    )


def memory_from_dict(raw: dict[str, Any]) -> LearnerMemory:
    return LearnerMemory(
        comfort=_parse_comfort(raw.get("comfort")),
        topics=_normalize_topics(raw.get("topics")),
        vocab=_parse_vocab(raw.get("vocab")),
        grammar_notes=_parse_grammar(raw.get("grammar_notes")),
        recycle_items=_parse_recycle(raw.get("recycle_items")),
        stats=_parse_stats(raw.get("stats")),
        updated_at=str(raw.get("updated_at") or _now_iso()),
    )


def load_memory(path: Path | None = None) -> LearnerMemory:
    from kaiwa.profiles import memory_path as active_memory_path

    mem_file = path or active_memory_path()
    if not mem_file.exists():
        return default_memory()
    try:
        raw = json.loads(mem_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return default_memory()
    if not isinstance(raw, dict):
        return default_memory()
    try:
        return memory_from_dict(raw)
    except (ValueError, TypeError):
        return default_memory()


def save_memory(memory: LearnerMemory, path: Path | None = None) -> LearnerMemory:
    from kaiwa.profiles import memory_path as active_memory_path

    mem_file = path or active_memory_path()
    mem_file.parent.mkdir(parents=True, exist_ok=True)
    memory.updated_at = _now_iso()
    mem_file.write_text(
        json.dumps(memory.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return memory


def reset_memory(path: Path | None = None) -> LearnerMemory:
    return save_memory(default_memory(), path)


def apply_manual_memory(
    memory: LearnerMemory,
    *,
    preferred_name: str | None = None,
    vibe_notes: str | None = None,
    do: list[str] | None = None,
    dont: list[str] | None = None,
    topics: list[str] | None = None,
) -> LearnerMemory:
    if preferred_name is not None:
        memory.comfort.preferred_name = _clip(preferred_name, MAX_NAME)
    if vibe_notes is not None:
        memory.comfort.vibe_notes = _clip(vibe_notes, MAX_VIBE)
    if do is not None:
        memory.comfort.do = [str(x).strip()[:80] for x in do if str(x).strip()][:MAX_DO_DONT]
    if dont is not None:
        memory.comfort.dont = [str(x).strip()[:80] for x in dont if str(x).strip()][:MAX_DO_DONT]
    if topics is not None:
        memory.topics = _normalize_topics(topics)
    return memory


def _trim_by_hits(items: list[Any], cap: int) -> list[Any]:
    if len(items) <= cap:
        return items
    ranked = sorted(items, key=lambda x: (getattr(x, "hits", 0), getattr(x, "last_seen", "")), reverse=True)
    return ranked[:cap]


def note_chat_turn(memory: LearnerMemory) -> LearnerMemory:
    memory.stats.chat_turns += 1
    memory.stats.chat_turns_since_extract += 1
    return memory


def should_extract(memory: LearnerMemory, profile: LearnerProfile) -> bool:
    if memory.stats.total_extracts == 0 and memory.stats.chat_turns >= 2:
        return True
    if memory.stats.chat_turns_since_extract >= EXTRACT_EVERY_N:
        return True
    if profile.stats.struggle_streak >= 2 and memory.stats.chat_turns_since_extract >= 2:
        return True
    return False


def _merge_list_unique(existing: list[str], additions: list[str], cap: int) -> list[str]:
    out = list(existing)
    for item in additions:
        text = _clip(str(item), 80)
        if not text:
            continue
        if text not in out:
            out.append(text)
        if len(out) >= cap:
            break
    return out[:cap]


def merge_extract_result(memory: LearnerMemory, data: dict[str, Any]) -> LearnerMemory:
    now = _now_iso()
    comfort = data.get("comfort") if isinstance(data.get("comfort"), dict) else {}

    name = comfort.get("preferred_name")
    if isinstance(name, str) and name.strip():
        memory.comfort.preferred_name = _clip(name, MAX_NAME)

    vibe = comfort.get("vibe_notes")
    if isinstance(vibe, str) and vibe.strip():
        # Prefer newer vibe, but keep short
        memory.comfort.vibe_notes = _clip(vibe, MAX_VIBE)

    do_add = comfort.get("do_add") if isinstance(comfort.get("do_add"), list) else []
    dont_add = comfort.get("dont_add") if isinstance(comfort.get("dont_add"), list) else []
    memory.comfort.do = _merge_list_unique(memory.comfort.do, do_add, MAX_DO_DONT)
    memory.comfort.dont = _merge_list_unique(memory.comfort.dont, dont_add, MAX_DO_DONT)

    topics_add = data.get("topics_add") if isinstance(data.get("topics_add"), list) else []
    memory.topics = _merge_list_unique(memory.topics, topics_add, MAX_TOPICS)

    vocab_add = data.get("vocab_add") if isinstance(data.get("vocab_add"), list) else []
    for item in vocab_add:
        if not isinstance(item, dict):
            continue
        surface = _clip(str(item.get("surface", "")), 60)
        if not surface:
            continue
        note = _clip(str(item.get("note", "")), MAX_NOTE)
        found = None
        for row in memory.vocab:
            if row.surface == surface:
                found = row
                break
        if found:
            found.hits += 1
            found.last_seen = now
            if note:
                found.note = note
        else:
            memory.vocab.append(VocabItem(surface=surface, note=note, hits=1, last_seen=now))
    memory.vocab = _trim_by_hits(memory.vocab, MAX_VOCAB)

    grammar_add = data.get("grammar_add") if isinstance(data.get("grammar_add"), list) else []
    for item in grammar_add:
        if not isinstance(item, dict):
            continue
        pattern = _clip(str(item.get("pattern", "")), 80)
        if not pattern:
            continue
        hint = _clip(str(item.get("hint", "")), MAX_NOTE)
        found = None
        for row in memory.grammar_notes:
            if row.pattern.lower() == pattern.lower():
                found = row
                break
        if found:
            found.hits += 1
            found.last_seen = now
            if hint:
                found.hint = hint
        else:
            memory.grammar_notes.append(
                GrammarNote(pattern=pattern, hint=hint, hits=1, last_seen=now)
            )
    memory.grammar_notes = _trim_by_hits(memory.grammar_notes, MAX_GRAMMAR)

    memory.stats.total_extracts += 1
    memory.stats.last_extract_turn = memory.stats.chat_turns
    memory.stats.chat_turns_since_extract = 0
    return memory


def _extract_json(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        raw = json.loads(text)
        return raw if isinstance(raw, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            raw = json.loads(match.group(0))
            return raw if isinstance(raw, dict) else None
        except json.JSONDecodeError:
            return None


EXTRACT_SYSTEM = """\
You extract durable learner-memory facts for a Japanese conversation tutor.
Reply with JSON only (no markdown):
{
  "comfort": {
    "preferred_name": null,
    "vibe_notes": null,
    "do_add": [],
    "dont_add": []
  },
  "topics_add": [],
  "vocab_add": [{"surface": "", "note": ""}],
  "grammar_add": [{"pattern": "", "hint": ""}]
}
Rules:
- Only durable, reusable facts. Skip one-off typos and fluff.
- comfort = how Kaiwa should be with this learner (name, vibe, do/dont). Soft personality prefs on top of the selected preset.
- vocab_add: useful JP phrases/words to recycle later (surface in Japanese).
- grammar_add: recurring issues (short English pattern + hint).
- Keep notes short. Empty arrays/null when nothing new.
- Respect the speech register (casual vs formal).
"""


def run_extract(
    settings: Settings,
    memory: LearnerMemory,
    *,
    prefs: UserPrefs,
    profile: LearnerProfile,
    recent_messages: list[dict[str, str]],
    client: Any = None,
) -> LearnerMemory:
    """Occasional Flash JSON extract. Fails soft."""
    from kaiwa.llm import _completion

    recent = recent_messages[-4:]
    dialogue = "\n".join(
        f"{m.get('role', '?')}: {m.get('content', '')}" for m in recent
    )
    existing = (
        f"name={memory.comfort.preferred_name or '(none)'}; "
        f"vibe={memory.comfort.vibe_notes or '(none)'}; "
        f"topics={memory.topics}; "
        f"vocab={[v.surface for v in memory.vocab[:5]]}; "
        f"grammar={[g.pattern for g in memory.grammar_notes[:5]]}"
    )
    user = (
        f"personality_id: {prefs.personality_id}\n"
        f"speech_register: {prefs.speech_register}\n"
        f"goal_level: {prefs.goal_level}\n"
        f"speaking_level: {profile.speaking_level}\n"
        f"comprehension_level: {profile.comprehension_level}\n"
        f"existing_memory: {existing}\n"
        f"recent_dialogue:\n{dialogue}\n"
    )
    try:
        raw_text = _completion(
            settings,
            EXTRACT_SYSTEM,
            [{"role": "user", "content": user}],
            client=client,
            model=settings.deepseek_model,
        )
        data = _extract_json(raw_text)
        if data:
            memory = merge_extract_result(memory, data)
        else:
            memory.stats.chat_turns_since_extract = 0
            memory.stats.last_extract_turn = memory.stats.chat_turns
    except Exception:
        memory.stats.chat_turns_since_extract = 0
        memory.stats.last_extract_turn = memory.stats.chat_turns
    return memory


def maybe_run_extract(
    settings: Settings,
    memory: LearnerMemory,
    *,
    prefs: UserPrefs,
    profile: LearnerProfile,
    recent_messages: list[dict[str, str]],
    client: Any = None,
) -> tuple[LearnerMemory, bool]:
    if not should_extract(memory, profile):
        return memory, False
    before = memory.stats.total_extracts
    memory = run_extract(
        settings,
        memory,
        prefs=prefs,
        profile=profile,
        recent_messages=recent_messages,
        client=client,
    )
    return memory, memory.stats.total_extracts >= before


def memory_prompt_block(memory: LearnerMemory, prefs: UserPrefs) -> str:
    c = memory.comfort
    name = c.preferred_name or "(unknown)"
    vibe = c.vibe_notes or "(none yet)"
    do = "; ".join(c.do) if c.do else "(none)"
    dont = "; ".join(c.dont) if c.dont else "(none)"
    goal_topics = prefs.topic_preferences or []
    mem_topics = memory.topics or []
    topics = ", ".join(dict.fromkeys([*goal_topics, *mem_topics])) or "(none)"
    vocab_lines = [
        f"  - {v.surface}" + (f" ({v.note})" if v.note else "")
        for v in sorted(memory.vocab, key=lambda x: x.hits, reverse=True)[:6]
    ]
    grammar_lines = [
        f"  - {g.pattern}" + (f" → {g.hint}" if g.hint else "")
        for g in sorted(memory.grammar_notes, key=lambda x: x.hits, reverse=True)[:5]
    ]
    vocab_txt = "\n".join(vocab_lines) if vocab_lines else "  - (none yet)"
    grammar_txt = "\n".join(grammar_lines) if grammar_lines else "  - (none yet)"
    return f"""\
長期メモリ（学習者について知っていること。性格プリセットの上に重ねる）:
- 呼び名: {name}
- 雰囲気・好み: {vibe}
- してほしい: {do}
- しないでほしい: {dont}
- トピック（希望+観察）: {topics}
- 覚えておく語彙・言い回し:
{vocab_txt}
- 繰り返しの文法メモ:
{grammar_txt}
- 会話が止まったら覚えているトピックで自然に続ける。
- 語彙/文法は自然なときに1つだけ軽くリサイクル（クイズ化しない）。
- 親しみは増やすが、選ばれた性格プリセットは壊さない。
"""


def _text_id(prefix: str, text: str) -> str:
    import hashlib

    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}:{digest}"


def _trim_recycle(items: list[RecycleItem]) -> list[RecycleItem]:
    if len(items) <= MAX_RECYCLE:
        return items
    # Keep freshest / most attempted; drop stale cleared-ish first
    ranked = sorted(
        items,
        key=lambda r: (r.clears, r.last_seen or "", -r.attempts),
    )
    return ranked[:MAX_RECYCLE]


def _find_recycle(memory: LearnerMemory, text: str) -> RecycleItem | None:
    needle = _clip(text, MAX_RECYCLE_TEXT)
    for row in memory.recycle_items:
        if row.text == needle:
            return row
    return None


def _find_vocab(memory: LearnerMemory, text: str) -> VocabItem | None:
    needle = _clip(text, 60)
    if not needle:
        return None
    for row in memory.vocab:
        if row.surface == needle:
            return row
    for row in memory.vocab:
        if row.surface and row.surface in needle:
            return row
    return None


def next_vocab_target(
    memory: LearnerMemory,
    *,
    after_id: str = "",
) -> dict[str, str] | None:
    if not memory.vocab:
        return None
    ordered = sorted(memory.vocab, key=lambda v: (v.hits, v.last_seen or ""))
    ids = [_text_id("vocab", v.surface) for v in ordered]
    start = 0
    if after_id:
        try:
            start = (ids.index(after_id) + 1) % len(ordered)
        except ValueError:
            start = 0
    item = ordered[start]
    return {
        "phrase_id": ids[start],
        "text": item.surface,
        "source": "vocab",
        "note": item.note or "",
    }


def next_recycle_target(
    memory: LearnerMemory,
    *,
    after_id: str = "",
) -> dict[str, str] | None:
    active = [r for r in memory.recycle_items if r.clears < CLEARS_TO_EASE]
    if not active:
        return None
    # Prefer more attempts (worth another try) then oldest
    ordered = sorted(active, key=lambda r: (-r.attempts, r.last_seen or ""))
    ids = [_text_id("recycle", r.text) for r in ordered]
    start = 0
    if after_id:
        try:
            start = (ids.index(after_id) + 1) % len(ordered)
        except ValueError:
            start = 0
    item = ordered[start]
    return {
        "phrase_id": ids[start],
        "text": item.text,
        "source": "recycle",
        "note": "",
    }


def note_practice_result(
    memory: LearnerMemory,
    *,
    target: str,
    band: str,
    practice_source: str = "",
) -> LearnerMemory:
    """Soft update after a practice attempt — no shame counters exposed to UI."""
    now = _now_iso()
    text = _clip(target, MAX_RECYCLE_TEXT)
    if not text:
        return memory
    band_n = (band or "").strip().lower()
    src = (practice_source or "").strip().lower()

    vocab = _find_vocab(memory, text)
    if vocab and (src == "vocab" or vocab.surface == text):
        if band_n == "clear":
            vocab.hits += 1
            vocab.last_seen = now

    if band_n in {"unclear", "close"}:
        reason = "vocab" if src == "vocab" or (vocab and vocab.surface == text) else "retry"
        row = _find_recycle(memory, text)
        if row:
            row.attempts += 1
            row.last_seen = now
            if reason == "vocab":
                row.reason = "vocab"
        else:
            memory.recycle_items.append(
                RecycleItem(text=text, reason=reason, attempts=1, clears=0, last_seen=now)
            )
        memory.recycle_items = _trim_recycle(memory.recycle_items)
    elif band_n == "clear":
        row = _find_recycle(memory, text)
        if row:
            row.clears += 1
            row.last_seen = now
            if row.clears >= CLEARS_TO_EASE:
                memory.recycle_items = [r for r in memory.recycle_items if r.text != row.text]
            else:
                memory.recycle_items = _trim_recycle(memory.recycle_items)

    return memory
