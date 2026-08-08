# Tutor exchange critique (2026-08-07)

Design input from a real Kaiwa chat critique. Used to define **Phase 5 — Tutor learning quality** (see `docs/ROADMAP.md`). Not a transcript dump of private sessions — summarized teaching goals only.

## Sample exchange (paraphrased)

- Learner greeted casually; Kaiwa asked if they were 眠い.
- Learner: roughly「すみません眠りわからない」(meant: don’t understand 眠い).
- Kaiwa glossed 眠い in English and moved on (“how do you feel?”).
- Learner:「今日は眠いですでも元気だよ」— understandable; Kaiwa stayed conversational without a micro-fix.
- Kaiwa then jumped to「楽しいことする予定ある？」— several new items at once for a beginner.

## What worked

- Casual, non-textbook voice (e.g.「お、いいね!眠いけど元気か。それ、わかるよ。」).
- Natural handling of a believable learner mistake without quiz energy.

## What to improve (→ Phase 5 slices)

1. **JP-first meaning help (5.1)** — Prefer easy Japanese + one example before English when the learner signals unknown vocab; Adaptive may add a short gloss only if still stuck.
2. **Useful micro-corrections (5.2)** — Acknowledge clear turns; for useful/recurring errors (word family 眠り vs 眠い, particles, です/だ), one soft fix (`TRY:` / brief JP) — not every typo.
3. **Topic stickiness (5.3)** — Stay on the thread 1–2 turns reusing just-taught words (起きる / 寝る / 何時) before jumping topics.
4. **Difficulty governor (5.4)** — Cap next-turn complexity by demonstrated level; prefer「今日は何するの？」until denser patterns are earned.
5. **Constraint** — Keep casual personality; teaching sits *under* conversation, not as JLPT-style speech.

## Target shape (illustrative)

Conversation layer stays warm and short. Micro-teaching clarifies 眠い vs 眠り and offers one natural rephrase. Follow-ups stay on sleep/wake until the learner shows they can follow, then widen.

## Related

- Roadmap Phase 5.1–5.5
- Decision #80 (tutor learning layers), #99 (comprehensibility-first Chat)
- Existing hooks: `language_policy`, learner profile levels, Practice tab (drills)

---

# Tutor exchange critique — round 2 (2026-08-08)

Second critique: Kaiwa felt like a chatbot that teaches, not a tutor that converses. Core failure: responding to comprehension collapse by teaching many new items at once.

## Failure modes (paraphrased)

- After “lots of words I don’t understand,” Kaiwa explained 硬い / カジュアル / フォーマル / … in one turn.
- Lone filler `and...` treated as trouble, or connector lectures when the learner was only thinking.
- Greeting flip (こんにちは → おはよう) got a meta “you feel like morning” joke instead of following the learner.
- Successful communication (`お元気ですか` turn-back) got premature register lectures.
- Chat `TRY:` / “Try saying… Practice this” blurred Chat vs Practice.

## What to improve (→ Phase 5.5)

1. **One-item density lock** on incomprehension — simpler JP / choices over definition stacks.
2. **Internal support ladder** with decay (not sticky simplified; not one-shot reset to normal).
3. **help_type** — vocabulary/expression ≠ comprehension collapse.
4. **English as rescue scaffolding**, not the conversation language; weak signal alone.
5. **Retire Chat TRY:** — Practice stays the drill surface.
6. **Invisible scaffolding** — never announce “simplified mode.”

## Philosophy (short)

Japanese teaches. English rescues. Practice drills. Conversation stays a conversation. Comprehensibility > correction > teaching density.
