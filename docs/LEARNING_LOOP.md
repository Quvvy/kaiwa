# Learning loop (Phase 10)

Kaiwa teaches the smallest useful thing that helps the learner communicate, then returns them to communication.

**Feature test:** does this help them communicate something they could not comfortably communicate before? If it is primarily a neat way to teach Japanese grammar, it is probably not Kaiwa.

Conversation-first is the **reason**, not a Chat-gated **door**. Comprehensibility-first (#99) does **not** mean skip the recast. Forgiving-without-a-model is the bug.

Spec for Phase 10. Slice status: [ROADMAP.md](ROADMAP.md). Practice product (Phase 9, live): [PRACTICE.md](PRACTICE.md). Detection/store: [ARCHITECTURE.md](ARCHITECTURE.md). Decision #136.

## Two paths

Learn is **not** a prerequisite for Practice and not a higher stage of the same pipeline. Both converge on Chat.

**Reactive:** Chat → recast → notice → Practice → Chat  
**Proactive (10.6 only):** Learn → Practice → Chat

**Hard constraint:** do **10.1–10.4** (model, notice, rehearse, return to conversation) before any Learn tab.

### Chat

Keep talking. On a useful miss, the spoken reply **uses** the corrected form (`コーヒーが好きなんだね`). No lecture. No live `TRY:` / “Try saying… Practice this.”

**10.1 shipped:** `PROMPT_REVISION` **10**. を好き (etc.) and 眠り/眠い turns get a recast hint and one retry; if the spoken reply still lacks the model, speak **only** the canned sentence (no forgive-only leftover). Density retry keeps a positive `[this_turn]` item (recast stem). Recast turns do not roast. Collapse after わからない／Simpler is the same idea shorter — no new items, no 選択肢. Forgiving-without-a-model is the bug. 楽しみ/楽しい is not this family (#151).

**10.2 shipped:** a tiny **Notice this** caption of the **same** spoken sentence (`コーヒーが好きなんだね。` / `眠いんだね。`). Not “Try saying…”, not Practice this, not 助詞.

### Practice

Immediate rep of **that pair** (you said を好き / say が好き), then back. Not a second Easy chat. Not Bunpro. Not the main menu. Fed by Chat **or** by Learn.

**10.3 shipped:** say the speakable line, one tiny exchange that uses it, then wrap. Cap 2 learner turns. Home stays **Today’s practice / Start**. Not a Chat clone.

**10.4 shipped:** after the wrap line and its TTS, Practice finishes and returns to Chat. The next Chat turn asks a hook whose natural answer is the rehearsed form (`[elicit]`, no `TRY:`, do not speak the line first). Recast snapshot is today’s sitting; unused practice-worthy Chat cards win (recast-family first); freeze/survival leftover and speakable junk never win today; canned 9.8 starts with が好き. Back to Chat stays an early exit. Survival sittings do not elicit.

**10.5 shipped:** Practice home, under Start, lists **Things you can say** — a few recently practiced speakable lines (cap 5, no tap). Hidden when empty.

### Learn (10.6)

**10.6 shipped:** Learn tab. Pick one of **your** clustered Chat lines (skip freeze/survival and speakable junk; recast-family first), or a canned Chat-shaped starter if none are eligible. Tap starts the existing Practice sitting (replaces an in-progress sitting), then Chat. Not Genki. Not a 20-minute generated lesson. N5 overlay and longer intentional blocks are still later.

## Speakable repertoire

A line is not “N5 progress.” Memorizing 50 lines is not the product.

A line becomes meaningful when the learner can, over time:

1. Recognize it
2. Produce it with support
3. Produce it independently
4. Use it appropriately in Chat
5. Adapt it to a similar situation

Phase 10 does **not** need all five states in the UI. Keep the distinction so Kaiwa does not become phrase memorization with an AI wrapper.

A quiet N5 can-do overlay, if any, lives with Learn — never equate a stack of lines with exam progress.

## 10.5 is lightweight

Not a giant My Progress system. Answer only: **what did Kaiwa actually help me learn?**

**10.5 shipped:** **Things you can say** on Practice home — a few recently practiced speakable lines (`コーヒーが好きです。` / `学校に行きます。`) from finished sittings. Cap 5. No tap-to-drill. Not N5 progress. The data model can mature later.

## Recast notice (10.2)

A tiny caption of the **same** model phrase Kaiwa just said. Not grammar names. Not a second product under the bubble.

**10.2 shipped:** muted **Notice this** caption under the Kaiwa bubble when this turn restated a closed recast family (を→が or 眠り/眠い). First spoken sentence that contains the model.

## Non-goals

- Practice as the main menu
- Genki / Bunpro / category tiles (Particles, て-form, …)
- Live Chat `TRY:`
- XP / SRS
- Rebuilding cards from extract `grammar_add`
- A predetermined lesson catalog as the primary source
- Treating a line list as N5 progress
