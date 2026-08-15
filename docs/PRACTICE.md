# Practice (Phase 9)

Chat’s job: **talk with me.**  
Practice’s job: **help me get comfortable saying the kinds of things I struggled with — or lacked confidence to say — in Chat.**

If those blur, one disappears.

**Invariant:** every Practice activity has a clear path **back to Chat**. Practice prepares the next conversation; it is not a destination.

This is the **next** Practice product (decision #127). Until Phase 9 ships, the live tab is still the Phase 1.5 intelligibility warm-up (phrase bank / last reply / vocab / recycle + score). See [ARCHITECTURE.md](ARCHITECTURE.md).

## Mode, not a page

Open Practice:

- **Today’s practice**
- About N minutes
- **Start**

Kaiwa walks **one short sitting**, then Chat. No category tiles (Fixes (2) / Review (4)). Mix of card types is an implementation detail inside the sitting. No Light phrase / Last reply / From our chats / Say again toolbox. No intelligibility % as the product.

## Speakable Japanese, not grammar names

User sees `コーヒーが飲めます。`  
Internal tags (`particle_ga`) stay hidden unless they tap Why?.

Do **not** organize Practice as Genki chapters (Particles, Potential, てしまう). Do **not** make Conversation/shadow-recent-Kaiwa a peer — Chat **Again**, **Replay**, and history already cover that.

## Every card traces to Chat

If it could have existed before any conversation, it does not belong. Phrase bank is fallback or gone.

## Signals (failures and low confidence)

Not corrections-only. Soft low-confidence moments are as valuable as particle fixes.

**Harder (explicit)**

- Meaningful correction (を好き → が好き) — not STT typos
- **Simpler** / rescue
- Help: わからない, “what does that mean?”, `help_type` comprehension / vocabulary / expression
- Freeze / empty / I don’t know how to say…

**Softer (confidence, still Chat-grounded)**

- One-word answers repeatedly
- Avoided a structure / abandoned an idea halfway
- Switched to English without asking for help
- Needed the idea restated (not only Simpler)

Hesitation wall-clock (e.g. 15s) is nice-to-have later; session JSONL does not store it today.

Existing Chat hooks (not the Practice store): `infer_learner_state` / `infer_help_type` in `persona.py`, rescue JSONL `kind: rescue`, `struggle_streak`. English switch is partly covered. One-word / abandoned-idea need new heuristics or a turn-time note when 9.1 is built — spec them here; do not claim they are already logged as cards.

## Struggle cards are immutable snapshots

A card is written **at the moment** of the Chat interaction. It preserves:

- The original prompt / learner line
- The improved example (if any)
- Enough context to run a sitting

It is **not** reconstructed later from extract `grammar_add` / vocab metadata. Extract stays tutor-memory (`learner_memory.json`). It is not the Practice store.

## Sitting shape

A **tiny guided conversation around one specific struggle**: 3–5 Easy-shaped turns, then stop.

Example: Chat corrected 日本語を好きです → 日本語が好きです. Practice asks 何の食べ物が好きですか？ — never “today’s particles.”

Philosophy copy must **not** say “generated mini-scenarios” (that reads as LLM roleplay). If an LLM writes the three prompts, that is an implementation note only.

- Does not teach new grammar; Chat already did
- Not a konbini / ramen catalog (still a non-goal)
- Cap so Practice is not a second Chat
- Hear-and-answer may happen *inside* the sitting
- Survival lines (`えっと…`, `もう一回お願いします`) are cards when the learner froze — not a home tile

## Non-goals

- Pronunciation / pitch tracks
- Dictation / type-what-you-heard
- SRS, XP, streaks, unlocks
- N5 goal ledger (Phase 10+)
- Listening / Review / Conversation as home navigation
- Rebuilding Anki or Bunpro inside Kaiwa

## Build order (when implementing)

1. Snapshot struggle cards from Chat
2. Session shell — Today’s practice / Start / back to Chat
3. Tiny guided conversations from those snapshots
4. Nothing else until cards have fuel

Ships in a **later** app version, not 1.0.4.
