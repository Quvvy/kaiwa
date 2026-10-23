# Practice (Phase 9)

Chat’s job: **talk with me.**  
Practice’s job: **help me get comfortable saying the kinds of things I struggled with — or lacked confidence to say — in Chat.**

If those blur, one disappears.

**Invariants**

1. Every Practice activity has a clear path **back to Chat**. Practice prepares the next conversation; it is not a destination.
2. **Practice reinforces existing knowledge; it does not introduce new material.**

This is the **live** Practice product (decisions #127–#134, #139, #142–#150). How cards are detected and stored: [ARCHITECTURE.md](ARCHITECTURE.md). Slice status: [ROADMAP.md](ROADMAP.md). Acquisition loop (Phase 10): [LEARNING_LOOP.md](LEARNING_LOOP.md).

## Mode, not a page

Open Practice:

- **Today’s practice**
- About N minutes
- **Start**

Kaiwa walks **one short sitting**, then Chat. No category tiles (Fixes (2) / Review (4)). Mix of card types is an implementation detail inside the sitting. No Light phrase / Last reply / From our chats / Say again toolbox. No intelligibility % as the product.

Until there are unused cards from Chat, Start still runs a short canned sitting (a line you will use in Chat). Chat cards always win. Not a phrase bank.

Under Start, **Things you can say** lists a few recently practiced speakable lines (10.5, #142). Hidden when empty. Plain text — tapping a line does not start a sitting. Tap-to-practice lives on the **Learn** tab (#143).

## Speakable Japanese, not grammar names

User sees `コーヒーが飲めます。`  
Internal tags (`particle_ga`) stay hidden. **Why?** in the sitting is a canned one-liner from the snapshot (you said を好き / this is が好き) — not a grammar-class lecture.

Do **not** organize Practice as Genki chapters (Particles, Potential, てしまう). Do **not** make Conversation/shadow-recent-Kaiwa a peer — Chat **Again**, **Replay**, and history already cover that.

## Origin

Practice content originates from the learner’s conversations with Kaiwa. Generic curriculum is fallback only, never the primary source.

## Signals (failures and low confidence)

Not corrections-only. Soft low-confidence moments are as valuable as particle fixes. Be conservative: natural short Japanese is not a card.

**Harder (explicit)**

- Meaningful correction (を好き → が好き) — not speech-recognition typos
- **Simpler**
- Help requests: わからない, “what does that mean?”, how do I say…
- Freeze / empty / I don’t know how to say…

**Softer (confidence, still from Chat)**

- Repeated **minimal** answers that look like lack of confidence, not conversational style. `はい。` or `パスタ。` when that was the question are **not** cards.
- Abandoned or rephrased an idea after an unsuccessful attempt (something Kaiwa can observe — not “wanted to use potential”)
- Switched to English without asking for help
- Needed the idea restated (not only Simpler)

Hesitation (how long they paused before speaking) is later.

## Struggle cards are immutable snapshots

A card is written **at the moment** of the Chat interaction. It preserves:

- The original prompt / learner line
- The improved example (if any)
- Enough context to run a sitting

It is **not** reconstructed later from tutor memory (vocab / grammar notes). That memory stays for Chat. It is not the Practice store.

## Sitting shape

**Rehearsal of one already-touched line** (10.3, #139): say the speakable line out loud, then one tiny exchange that uses that same form, then wrap. Cap **2** learner turns (opening tutor line does not count). About **2** minutes. Home stays **Today’s practice / Start**. Not a second Easy Chat.

Example: Chat recast 日本語を好きです → 日本語が好きです. Practice invites them to say `日本語が好きです。`, then one short follow-up that uses が好き — never “today’s particles,” never a new topic catalog.

Philosophy copy must **not** say “generated mini-scenarios” (that reads as LLM roleplay).

- Does not teach new grammar; Chat already did
- Not a konbini / ramen catalog (still a non-goal)
- Cap so Practice is not a second Chat
- After wrap TTS, the UI returns to Chat (Back to Chat is an early exit). Chat may invite the rehearsed line once.
- Hear-and-answer may happen *inside* the sitting (Kaiwa does not yet score whether they said the line)
- Survival lines (`えっと…`, `もう一回お願いします`) are cards when the learner froze — not a home tile, and they never win **today**. Help / English / fake-yes cards whose line is empty, English-heavy, ごめん / そうなんだ, a tutor fragment, or a gloss also lose Today / Learn; recast-family (が好き / 眠い) wins, else canned `コーヒーが好きです。` (#150).
- A sitting is marked used only if a learner turn overlaps the speakable line (`うん` does not burn the card)

## Non-goals

- Pronunciation / pitch tracks
- Dictation / type-what-you-heard
- SRS, XP, streaks, unlocks
- N5 can-do overlay / generated Learn lessons — not Practice tiles; a line list is not exam progress
- Listening / Review / Conversation as home navigation
- Rebuilding Anki or Bunpro inside Kaiwa

## Slices

Shipped: **9.1** cards (Simpler / help / struggling) → **9.2** Today’s practice / Start → **9.3** tiny guided sitting → **9.4** speakable line in the sitting + canned Why? → **9.5** conservative low-confidence cards → **9.6** freeze / empty (survival line, not a home tile) → **9.7** を→が (and 眠り/眠い) from this Chat turn → **9.8** empty-state fallback (canned sitting when no unused Chat card). **Phase 9 complete.**

**10.3 shipped:** rehearsal sitting (say-this + one exchange). **10.4 shipped:** wrap TTS then auto-return to Chat; next Chat turn asks a hook whose answer is the rehearsed form (does not speak it first); 9.8 stays secondary (first canned is が好き, not えっと). **10.5 shipped:** Practice-home **Things you can say** from used sittings including finished Learn starters (cap 5, no tap). **10.6 shipped:** Learn tab queues those sittings from clustered Chat lines or canned starters; a Learn tap with `card_id` replaces an in-progress sitting (Practice Start with no id still resumes). See [LEARNING_LOOP.md](LEARNING_LOOP.md) and [ROADMAP.md](ROADMAP.md).

Ships in a **later** app version, not 1.0.4. App version stays 1.0.3 until that release.
