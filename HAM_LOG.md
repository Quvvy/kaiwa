# HAM LOG

Everything built on the `study-lab` branch during the 8-hour push, one entry per change.
Newest entries go at the bottom of each section's list; the numbers are stable IDs.

**How to read an entry:** what you'd notice, why it should work, how sure I am, and the commit.

**Status tags**
- ✅ tested = automated test and/or driven in the running app
- 🎤 needs a human = I can't test real speech from here; logic tested, voice path not
- 🧪 judgment call = sound reasoning, but you may disagree with the taste or the tradeoff

---

## For the agent reviewing this after the reset

- **Base:** `study-lab` branches from `phase-9-10-wip` at `2e6269f` (Kaiwa 2.1.0). Local `master` is 55 commits *behind* that, so `phase-9-10-wip` is the real trunk. Check with the owner which branch "main" means before applying anything.
- **Not pushed.** The branch is local only.
- **Each entry is its own commit** (the ID is in the commit subject, e.g. `[H12]`), so changes can be cherry-picked. Later entries may depend on earlier ones; dependencies are listed in the entry.
- **Tests:** `scripts/smoke_lab.py` covers this branch's logic with no network. Existing `scripts/smoke_course.py`, `smoke_learn.py` and `smoke_state_files.py` must keep passing. `scripts/sim_pacing.py` simulates a learner through the real scheduler.
- **Review for:** whether it fits Kaiwa's rule ("does this help them understand or speak?"), migration of existing `course_state.json`, and anything marked 🎤 or 🧪.

---

## Changes

### Kana

**H01. Every basic kana has a picture.** ✅ `[H01,H02]`
あ, ね, ツ and the other 90 basic kana now show a one-line shape-and-sound hook when introduced and after a miss ("A NEko curling its tail around a post").
*Why:* mnemonic-taught kana is learned much faster than rote (Quackenbush et al. 1989, Matsunaga 2003). All hooks are newly written; please read a few and tell me which are bad.

**H02. Kana drills offer the look-alikes.** ✅ `[H01,H02]`
Wrong options now favour what a kana really gets mistaken for (ね/れ/わ, シ/ツ, ソ/ン), once those are learned. A miss also says "Don't mix it up with れ (re)".
*Why:* random wrong options can be beaten from a rough impression of the shape, so they never train the difference.

*Also in that commit:* **bug fix.** Leaving a lesson left its keyboard shortcuts active, so Space or Ctrl+Z on the home screen could jump you back into an old card.

### Pacing

**H03. Choose a daily pace; lessons fit a time budget.** ✅ 🧪 `[H03,H04,H05]`
Relaxed (~12 min), Regular (~17 min, default), Intensive (~25 min) on the home screen. The Start button says how long today takes ("about 10 min").
*Why:* I built `scripts/sim_pacing.py`, which runs a virtual learner through the real planner and FSRS. It showed "about 15 minutes" was really 19-27 for weeks 2-8 and that the day-two plan stacked kana on top of three lessons. A promise that's wrong by half is a reason to quit.
*Tradeoff:* the course takes longer at Regular. Simulated with 15% of days skipped: all 20 units are still done inside 200 days.

**H04. A unit's words can split across days.** ✅ `[H03,H04,H05]`
If 20 words don't fit today, you get 5 or 10 now and the rest tomorrow. Existing progress isn't affected.

**H05. Recall target 87%, and a slowdown when recall slips.** ✅ 🧪 `[H03,H04,H05]`
FSRS now aims for 87% instead of 90%. If recent recall falls below 80%, new material halves and the home screen says why.
*Why:* simulated, 90→87% cuts days stuck on reviews-only by about 40% (86→52 of 200 at Regular). The higher target costs a lot of reviews for little memory, and catch-up days are where new lessons stop. *Caveat:* the simulated learner forgets exactly as FSRS's default model says; real learners vary.

### Answering

**H06. Hints before giving up.** ✅ `[H06-H11]`
Say-it and produce cards get a **Hint** (key H) that shows the first sounds and blanks: おは＿＿＿＿＿＿＿. It grades Hard rather than Again.
*Why:* before, a blank mind meant "Show me", a full fail and no retrieval attempt. A partial cue still makes you pull the answer from memory.

**H07. Type instead of speak, everywhere.** ✅ `[H06-H11]`
Say-it review cards had no typing option, so no microphone meant failing every one. They now use the same say-or-type box as other cards.

**H08. See exactly which sounds were missed.** ✅ 🎤 `[H06-H11]`
A miss shows the target with the missing sounds marked: おは<u>ようござ</u>います. Works for typed and spoken answers.
*Why:* corrective feedback that shows where the error was beats a verdict (Lyster & Saito 2010). Spoken path uses the same function but I can't test a real voice here.

**H09. After a miss, say it again.** ✅ 🎤 `[H06-H11]`
A missed say-it card prompts "Now say it once more, copying what you heard", and the mic stays live. The grade stands. *Why:* repairing straight after hearing the model is the part of correction that sticks.

**H10. Words are understood by ear; known words alternate.** ✅ 🧪 `[H06-H11]`
Word recognition cards no longer show the kana after the first exposure (a Show text button counts as help). Known words alternate between "say it" and "understand it by ear", where before they were only ever produced.
*Why:* Kaiwa's goal is understanding speech. With text on screen, the card was testing reading.

**H11. Several voices; a quick check after new phrases.** ✅ `[H06-H11]`
Each replay of a new phrase uses a different voice, and reviews rotate voices. After the phrase list, a short "What did you hear?" check runs, and it counts as those cards' first review.
*Why:* many speakers makes words easier to catch from anyone (Logan et al. 1991, Barcroft & Sommers 2005). Testing straight after exposure beats restudying (Roediger & Karpicke 2006).

### Grammar

**H12. Grammar now gets spaced reviews, as sentences you build.** ✅ 🧪 `[H12,H13]`
This was the biggest gap in the course: grammar was taught once, drilled with multiple choice, and never came back. Each grammar point is now a review card. Given the English, you put the Japanese together from tiles, one of which is a wrong particle or ending ("ユキさん は がくせい です", with が in the pile). It uses a different sentence each review, so you practise the pattern and not one line. Number keys pick tiles, Backspace undoes, H hints.
Grammar you already finished joins the schedule automatically, spread over two weeks. 140+ sentences hand-cut from the units' own examples (`course/build.py`).
*Why:* producing a form yourself (Swain), spaced (Cepeda et al. 2006). A hand-picked wrong tile makes you decide between the forms that really get confused.
*Tradeoff:* adds about 40 cards. I raised the review budget slightly so the simulated catch-up load stayed about the same.

**H13. Grammar lessons mix in older questions and end by building.** ✅ `[H12,H13]`
The drill now includes up to 3 questions from the previous 3 units, then finishes with a short build-it round. *Why:* mixed practice beat blocked practice for L2 grammar a week later (Nakata & Suzuki 2019).

