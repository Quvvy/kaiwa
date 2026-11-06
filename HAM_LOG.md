# HAM LOG

Everything built on the `study-lab` branch, one entry per change.

## After the review (2026-11-06)

Every entry was reviewed against the code, and what passed was applied on `study-lab-apply`, branched from `phase-9-10-wip` at `2e6269f`. Nothing has been pushed or merged. `study-lab` keeps the original work, including everything held below.

**Held for real-use testing, not on this branch:**
- **H25 Speed round:** a score to beat is the closest thing here to gamification.
- **H27 Hands-free:** ungraded, adds a mode, and its voice path is untested.
- **H29 Chat steering:** in a small test neither reply asked about the recent phrases. `PROMPT_REVISION` stays 10 until a test shows it changes what Chat asks.

**Removed:** the Relaxed pace. It saved little time and stalled often, so Regular and Intensive remain.

**Decided:** the recall target stays at 87%. Go back to 90% if real recall stays under about 82% for four weeks.

**Pace numbers.** The figures in the entries below came from a simulator that planned once a day and added a 2-minute wait after each missed review, and they're kept only as a record. It now works the plan out again after every step, as the app does. Catch-up days also stay reviews-only now, which they didn't before. Medians of 5 runs over 300 days, with 15% of days skipped, while lessons last:

| | Days until lessons finish | Minutes a day | Slowest 10% of days | Reviews-only days | Words by day 30 |
|---|---|---|---|---|---|
| Regular | 124 | 11.4 | 15+ | 36 of 106 | 84 |
| Intensive | 53 | 21.3 | 30+ | 14 of 45 | 164 |

These are still estimates. The seconds per card are guesses, and nothing models overload. Other simulated runs:

| | Regular | Intensive |
|---|---|---|
| Recall target 90% instead of 87% | 157 days, 58 of 130 reviews-only, 22% more reviews | 76 days, 32 of 63 reviews-only, 30% more reviews |
| Forgets faster, recall about 83% | 178 days, 81 of 152 reviews-only | 60 days, 18 of 49 reviews-only |
| Forgets faster, recall about 78% | 295 days, 175 of 251 reviews-only | 56 days, none reviews-only, new material halved on 30 of 51 days |

The slowdown guard doesn't fire at about 83% recall, so it won't catch a moderate slip. Check real recall and session lengths after the first few weeks.

**Still untested:** a real voice, microphone or Whisper (H08, H09, H24, H45, H46), audio playback, iPhone, the desktop webview, screen readers, and any real learner.

**Needs a native speaker before any release:** 141 build sentences and their wrong tiles (`build.py`), 73 pack words (`packs.py`), 20 missions and 20 culture notes (`missions.py`). The missions for u5, u7 and u18 have openers that look odd for the scene. Kana hooks are English only and just need a read.

---

## Start here

**To try it**, use a throwaway profile and a separate checkout, because a running Kaiwa serves `static/` straight from its own folder. If your key is in `.env`, the app copies it into the throwaway folder, so delete that folder afterwards.

```bash
PORT=8799 KAIWA_DATA_DIR=/tmp/kaiwa-try .venv/bin/python -m kaiwa.app
```

**The ten that matter most, if you only look at some:**

| # | What | Why it matters |
|---|------|----------------|
| H12 | Grammar comes back as sentences you build | Grammar was taught once and never reviewed |
| H16 | A real mission at the end of each unit | Where the course turns into actually using Japanese |
| H03/H49 | Honest daily pace | "15 minutes" was really 19-27 |
| H06-H09 | Hints, typing, seeing which sounds you missed | Failing a card now teaches you something |
| H14/H15 | Course map and phrasebook | You could never go back to anything before |
| H28/H43 | Your own phrases, and keeping corrections | Learn what you actually want to say |
| H26 | Numbers by ear | Fluency practice was missing entirely |
| H45/H46 | Free recall, take a part | Recall from memory and real turn-taking |
| H17/H18 | End-of-day screen, a streak that forgives | How the day ends, and surviving a missed day |
| H10 | Words understood by ear | The cards were testing reading, not listening |

**What I couldn't test:** real speech. The browser here has no microphone, so everything marked 🎤 had its logic tested, but never with a real voice. Nothing has been tried on real learners either. Please try H24, H45 and H46 out loud first.

The numbers are stable IDs.

**How to read an entry:** what you'd notice, why it should work, how sure I am, and the commit.

**Status tags**
- ✅ tested = automated test and/or driven in the running app
- 🎤 needs a human = I can't test real speech from here; logic tested, voice path not
- 🧪 judgment call = sound reasoning, but you may disagree with the taste or the tradeoff

---

## How this branch is built

- **Base:** `phase-9-10-wip` at `2e6269f` (Kaiwa 2.1.0). Local `master` is 3 commits behind that and can fast-forward.
- **Commits:** many hold several entries, such as `[H20-H24,H26,H28]`, and some entries have later fixes (H49, H52, and the `Fix` commits). An entry can't always be cherry-picked alone.
- **Tests:** `scripts/smoke_lab.py` covers this branch's logic with no network. `smoke_course.py`, `smoke_learn.py` and `smoke_state_files.py` must keep passing. Run them with a throwaway `KAIWA_DATA_DIR`.
- **Migration:** existing `course_state.json` loads unchanged. New keys are `pace`, `mine`, `comeback` and per-day `new`/`lesson_min`; finished grammar backfills cards on load. Going back to 2.1.0 works, but its first save drops `pace` and `mine`.

---

## How far to trust the citations

I checked a few by web search and left the rest from memory. Treat them as pointers, not proof.
- **Checked, and it changed something:** Matsunaga 2003 is weaker than I first claimed. H01's wording, the in-app note and the code comment are all corrected.
- **Checked, supports the claim in general terms:** Nakata & Suzuki 2019 (paper and title), Hamada 2016 (via a review, lower-proficiency listening).
- **Searched, not found:** Krashen 2004 on narrow input. It's from memory only, so H41 rests mostly on reasoning.
- **From memory, not checked:** everything else (Roediger & Karpicke, Karpicke & Blunt, Cepeda, Logan, Barcroft & Sommers, Lyster & Saito, Swain, Ellis, Long, Nation, Gollwitzer, Dai et al., Kahneman, Deci & Ryan, Bjork, Rogers).
- **Not evidence at all:** nothing here has been tested on real learners. The simulator only models FSRS's assumptions.

---

## Changes

### Kana

**H01. Every basic kana has a picture.** ✅ `[H01,H02]`
あ, ね, ツ and the other 90 basic kana now show a one-line shape-and-sound hook when introduced and after a miss ("A NEko curling its tail around a post").
*Why:* it gives a beginner something to hang a shape on. **The evidence is mixed, so this is a 🧪:** Quackenbush et al. (1989) report fast learning, but Matsunaga (2003) found a benefit only on a self-test, only for Roman-script readers, and none on delayed recall. It's cheap and easy to ignore, so I kept it, as support for the drills and not a replacement. All hooks are newly written; please read a few and tell me which are bad.

**H02. Kana drills offer the look-alikes.** ✅ `[H01,H02]`
Wrong options now favour what a kana really gets mistaken for (ね/れ/わ, シ/ツ, ソ/ン), once those are learned. A miss also says "Don't mix it up with れ (re)".
*Why:* random wrong options can be beaten from a rough impression of the shape, so they never train the difference.

*Also in that commit:* **bug fix.** Leaving a lesson left its keyboard shortcuts active, so Space or Ctrl+Z on the home screen could jump you back into an old card.

### Pacing

**H03. Choose a daily pace; lessons fit a time budget.** ✅ 🧪 `[H03,H04,H05]`
Regular and Intensive (default since H51) under Options, with Relaxed removed after review. See "After the review" for current numbers. The Start button says how long today takes ("about 10 min").
*Why:* I built `scripts/sim_pacing.py`, which runs a virtual learner through the real planner and FSRS. It showed "about 15 minutes" was really 19-27 for weeks 2-8 and that the day-two plan stacked kana on top of three lessons. A promise that's wrong by half is a reason to quit.
*Tradeoff:* the slower paces take much longer. See H49 and H51.

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
The drill now includes up to 3 questions from the previous 3 units, then finishes with a short build-it round. *Why:* mixed grammar exercises are reported to help long-term retention (Nakata & Suzuki 2019; I confirmed the paper and its title, not its numbers).

### Seeing your progress

**H14. Course map.** ✅ `[H14-H19]`
All 20 units in one list, each with what it lets you do, a done mark, a memory-strength bar and a ★ for missions. Open any started unit to redo a step, or re-open any kana lesson. Before this, Kaiwa only ever showed the current unit, and finished lessons couldn't be revisited.

**H15. Phrasebook.** ✅ `[H14-H19]`
Everything you've learned, searchable by English, kana or romaji, with audio and a New/Growing/Strong tag. Grammar is here as a reference too. *Why:* a conversation learner constantly thinks "how did I say that again?".

**H16. Unit missions.** ✅ `[H14-H19]`
Finishing a unit now offers a small real scene written for it: order a coffee, turn down an invitation, ask the way. The partner reacts to what you actually say, and you get one fix per turn. A mission marks the unit with ★; it never blocks progress. 20 hand-written missions in `course/missions.py`. Needs the DeepSeek key.
*Why:* task-based teaching (Ellis 2003, Long 2015). It's the moment the course stops being a course. I ran one with a real typed turn and it worked.

**H17. "You can now…" and an end-of-day screen.** ✅ `[H14-H19]`
Finishing a unit says what you can now do, in plain words. Finishing the day's plan shows what you did, what's waiting tomorrow, and an easy nudge to say something in Chat. Before, the day ended on one grey line.
*Why:* people remember how something ended (peak-end rule, Kahneman et al. 1993), and feeling competent is one of the strongest drivers of sticking with things (Deci & Ryan).

**H18. A streak that forgives; a week view.** ✅ 🧪 `[H14-H19]`
Seven dots for this week. Every 7 days in a row earns a rest day: miss one and the streak holds. After 3+ days away the home screen says welcome back and the review pile isn't doubled that day. Study days also now end at 4 a.m., so a 1 a.m. session counts for the evening it started in.
*Why:* one missed day killing a long streak is a classic quitting moment. A fresh start framing helps people resume (Dai, Milkman & Riis 2014).

**H19. Real milestones; a calmer home.** ✅ 🧪 `[H14-H19]`
Quiet one-liners for abilities reached ("You can read all of hiragana", "100 words you know"). No points, levels or leagues. The Start button moved up into the first screenful, placement stays only for new users, and skip-unit, pace and romaji moved under Options.

### Fewer ways to get stuck

**H20. Leaving a lesson doesn't lose your place.** ✅ `[H20-H28]`
Exit a lesson and reopen it, and you're back where you were (per phrase, per word batch, per grammar point). Before, leaving lesson 18 of 20 meant starting over.

**H21. A dropped connection doesn't lose a lesson.** ✅ `[H20-H28]`
If saving a finished step fails, it says so and offers Try again. Before, the app froze silently. This matters most on the phone, between networks.

**H22. Quieter result bar.** ✅ 🧪 `[H20-H28]`
After an answer you see "Good · next in 3 days" with a small Change link. The four grade buttons appear only if you ask, and keys 1-4 still work. *Why:* Kaiwa grades for you, so showing Anki's four buttons on every card invites a decision that isn't needed.

**H23. Kana reading cards stay silent until you answer.** ✅ `[H20-H28]`
The Play button on a "how do you read this?" card gave the answer away.

### Listening

**H24. Slower button and shadowing.** ✅ 🎤 `[H20-H28]`
Conversations get a **Slower** toggle. After the questions, **Say it with them** walks through each line: hear it, say it straight back, see which sounds didn't come through. Optional, and it never holds up the lesson.
*Why:* shadowing helps L2 listening, especially at lower levels (Hamada 2016), and Kaiwa had no rhythm or prosody practice.

### Fluency (a missing strand)

Nation's "four strands" say a course should split time between input, output, language study and fluency. Kaiwa had the first three.

**H25. Speed round.** Held, not on `study-lab-apply`. ✅ `[H20-H28]`
One minute of known words by ear: hear it, tap the meaning, with your best score to beat. It never touches the review schedule. *Why:* fluency practice is known material under time pressure. It's also the closest thing here to a game, and the game is real recall.

**H26. Numbers by ear.** ✅ `[H20-H28]`
Hear a price or time at full speed and type it. Gets harder when you get 9/10. Unlocks with the Time and Shopping units. No LLM, works offline. *Why:* numbers are what everyone loses in a real shop, even when they "know" them.

**H27. Hands-free.** Held, not on `study-lab-apply`. ✅ `[H20-H28]`
For walking or dishes: the device reads the English, you say the Japanese aloud, it says it back in two voices. Weakest phrases first, ungraded, counts as listening time. *Why:* trying to recall before hearing makes this retrieval and not passive audio. It adds practice time that a screen can't reach.

### Your own Japanese

**H28. My phrases.** ✅ `[H20-H28]`
Phrasebook → Mine: write what you want to say ("I work in IT"), hear the simplest natural Japanese, tap Keep, and it becomes normal review cards. Chat's "Other ways to say it" also gets a Keep button. *Why:* what's about your own life is what you'll actually say and what sticks (self-reference effect, Rogers et al. 1977). The Japanese is forced to kana, retrying once if the model slips into kanji or Latin letters.

### Chat, polish and resilience

**H29. Chat aims at what you just learned.** Held, not on `study-lab-apply`. ✅ 🧪 `[H29-H34]`
The tutor now knows which phrases you learned in the last 3 days, and prefers questions you can answer with them, without saying the answer first. `PROMPT_REVISION` goes 10→11. *Why:* using a phrase soon after learning it is what makes it yours, and this keeps your "no Try saying… in Chat" rule intact because the nudge lives in the question being asked. I chose this over on-screen "try to use these" chips for that reason.

**H30. Why each step is the way it is.** ✅ 🧪 `[H29-H34]`
The first time you hit each kind of step, one short screen says what it's for: "Don't try to memorise before the test. The test is the studying." It shows once per step. A one-line note on a new learner's home says mistakes are part of how it works. *Why:* effective study feels worse than it is (Bjork's desirable difficulties), and people abandon methods that feel hard unless they know why.

**H31. Stats start with what you can do.** ✅ `[H29-H34]`
"What you can do now" comes first, from finished units and milestones. Retention tables, intervals and scheduling notes moved under More detail.

**H32. Extra listening works without a key.** ✅ `[H29-H34]`
With no key or no connection, it replays a finished unit's conversation (fresh ones first) instead of an error.

**H33. Accessibility and phones.** ✅ `[H29-H34]`
Results are announced to screen readers, focus moves to each new screen, reduced-motion is respected, key hints are hidden on touch screens, answer buttons are thumb-sized, and the phone plan list is half as tall.

**H34. Other voices and build sentences are prerendered.** ✅ `[H29-H34]`
So a replay in a new voice doesn't wait on the engine.

**H35. Bug fix in my own H03: the day's budget now remembers what's already done.** ✅ `[H35]`
The plan is worked out again after each step, so without this the lesson budget refilled every time and a day never ended. Found by reasoning, with a test added. Redoing an old step costs nothing.

**H36. "What trips you up lately."** ✅ `[H36-H39]`
The stats page now names your most common kinds of mistake across Speak, talk and Chat over 30 days, with a real example, and offers "Practise this", which builds sentences for that kind of slip. *Why:* Kaiwa has been carefully tagging every mistake into the learner log, and nothing ever showed it to the learner.

**H37. Busy day? Just two minutes.** ✅ 🧪 `[H36-H39]`
Under the Start button: eight reviews and done. It counts for the streak. *Why:* the habit dies on busy days, not on normal days, and a tiny version keeps it alive.

**H38. Study time in your calendar.** ✅ `[H36-H39]`
Options → "Study at 7:00 PM · Add to my calendar" downloads a daily repeating event. Works on the phone and needs no notification service. *Why:* naming when you'll do something makes follow-through much more likely (Gollwitzer 1999). Untested on Kaiwa's desktop webview; the link may need to open externally there.

**H39. Small fixes and copy.** ✅ `[H36-H39]`
- Stats says "remembered" not "not Again", and "Growing/Strong" not "Young/Mature".
- A right answer gets a tiny pop.
- "New things learned" counts things, not card sides.
- Redoing an old step no longer resets its date (it used to delay day two).
- Number keys change the grade after a build card.
- "Tricky cards" and "two minutes" go home when done, rather than running on into today's lesson.
- Tomorrow's count on the day-end screen never shows more than a day's share.
- Quick drills are tucked under a fold so the home screen stays at three main choices.

### Vocabulary gaps

**H40. Word packs.** ✅ `[H40]`
I checked the 324 course words against everyday N5 vocabulary and found real holes: the numbers 1-10 as words (though Time and Shopping lean on them), basic food, the body and feeling ill, colours, common verbs. Rather than reorder a course you're part-way through, nine optional packs (73 words) now live on the course map, taught with the same teach-then-test loop. Once learned, they're ordinary cards that Chat and stories can use. Units 8 and 11 point at the Numbers pack if you haven't done it.
*Why:* it fixes the gap without disturbing anyone's progress, and choosing what to learn is motivating in itself (Deci & Ryan). *For you to check:* meanings and romaji are hand-written; `course/packs.py` is short and worth a read.

### More real use

**H41. Extra listening is now one ongoing series.** ✅ 🧪 `[H41-H44]`
Stories now follow the same friends (ユキ, ケン, ハナ), carry on from the last scene, and end on a small open thread. The screen also says how much should be familiar ("about 94%"). *Why:* staying with the same people and situation makes input easier to follow ("narrow" input, Krashen 2004), and "what happens next?" is a better reason to listen than finishing an exercise. I generated one episode to check; low-level episodes are necessarily simple, but they're coherent.

**H42. The recap is mixed.** ✅ `[H41-H44]`
It used to run in teaching order (all kana, then phrases, then words). Now it's shuffled for the day, and a phrase's two sides are never adjacent. *Why:* interleaving. Telling things apart is part of remembering them.

**H43. Corrections get kept, not lost.** ✅ `[H41-H44]`
When a talk or mission ends, "Worth keeping from this talk" lists every corrected line, with audio and a Keep button that makes it a review card. Ask's examples get Keep too. *Why:* talk practice was producing perfect personalised corrections and then throwing them away.

**H44. A missed build shows the rule.** ✅ `[H41-H44]`
Getting a sentence wrong in grammar review now shows that point's one-line rule.

**H45. Free recall at the end of the day.** ✅ 🎤 `[H45-H48]`
On a day you met new phrases, the end-of-day screen offers: "Without looking, say every one you can remember." Speak or type. It tells you how many came through and plays back what got away. Matching ignores order and politeness endings and tolerates recognition slips. Offered once a day.
*Why:* unprompted recall is one of the most effective cheap study moves there is (Karpicke & Blunt 2011), and nothing else in the day asks for it.

**H46. Take a part.** ✅ 🎤 `[H45-H48]`
After a conversation's questions: the other voice speaks its lines, and you say yours from their meaning. No LLM, so it always works.
*Why:* this is the missing rung between repeating (shadowing) and a free exchange (talk practice): real turn-taking, with the words still known.

**H47. A small true thing about Japan per unit.** ✅ 🧪 `[H45-H48]`
The unit-done screen includes one "Did you know?" tied to the unit, such as why あしたは、ちょっと… is a complete polite no, or that your mother has two names depending on who's talking. Please read these (`CULTURE` in `missions.py`); I'm confident in them, but they're yours to approve.

**H48. A better finish line.** ✅ `[H45-H48]`
Finishing all 20 units now tells you what you can really do and what keeps it alive, not just "reviews continue".

**H49. Honest pace numbers, measured while lessons last.** ✅ 🧪 `[H49]`
My first labels (~12/~17/~25) came from averages that included quiet weeks after the course ended. Measured only while lessons are still coming, Regular was really 20-26 minutes, so I cut its lesson budget and relabelled every pace with minutes and months. The very first day gets a little extra so it includes real phrases and not only five vowels.
**Decided in H51.** The simulator says Intensive costs only about 4 more minutes a day than Regular and finishes in about a quarter of the time (47 vs 171 days). That looks too good, and the likely reason is that the simulator doesn't model overload: 100+ new items a week is assumed to stick as well as 40 do. I first left Regular as the default for that reason; you chose Intensive. The old fixed plan was close to Intensive.

**H50. New learners pick a pace and a time up front.** ✅ `[H50]`
The first home screen asks how much time you want to give this, with honest minutes and months, and when you'll study. After that, both move under Options. *Why:* a choice you made yourself is easier to stick to, and the pace is a promise worth seeing before you start. Also fixes Start's time estimate on day one.

**H51. Intensive is the default pace.** ✅ 🧪 `[H51]`
Your decision. New learners see Intensive already selected on the first home screen and can change it there or under Options. Anyone who already chose a pace keeps it; a save with no pace on it moves to Intensive, which is close to the old fixed plan.
*Simulated, 200 days with 15% skipped, before H52 retuned Regular:* Intensive finishes lessons in 47 days at 22.8 min a day, with 10 catch-up days across the whole 200-day run; Regular takes 171 days at 18.6 min, with 56 catch-up days across the run. Day one is 15 minutes and 20 words at Intensive, against 10 minutes and 5 words at Regular. One day in ten runs 27 minutes or more.
*Watch for:* the simulator doesn't model overload, so the real risk is 100+ new items a week not sticking. If recent recall falls under 80%, new material already halves until it recovers. Check real recall and drop-off after the first few weeks; if either looks bad, go back to Regular by changing `DEFAULT_PACE`.

**H52. Regular and Relaxed no longer crawl.** ✅ 🧪 `[H52]`
At the old settings, Relaxed taught 52 words and 18 phrases in a month, which is the "might as well not bother" pacing Kaiwa should avoid. I gave both more lesson room and more new items, and gave Regular a bigger review budget so it stalls less. Simulated medians over 5 runs, with 15% of days skipped:

| | Days until lessons finish | Minutes a day | Reviews-only days while lessons last | Words by day 30 |
|---|---|---|---|---|
| Relaxed, before | 218 | 15.1 | 53 | 52 |
| Relaxed, now | 190 | 16.7 | 78 | 84 |
| Regular, before | 153 | 18.3 | 45 | 73 |
| Regular, now | 127 | 20.8 | 27 | 100 |
| Intensive, unchanged | 49 | 22.5 | 0 | 212 |

*Tradeoff:* both cost about 2 more minutes a day, and Relaxed now has more reviews-only days: 78 of the roughly 160 days studied while lessons last, about half. Regular's fall to about a quarter. (This table first counted a whole 300-day run, including days after lessons end: 69, 96, 56, 34 and 9.) *What the scan showed:* reviews set the floor. Nothing tested stayed near 15 minutes and finished faster than about 7 months, and raising the catch-up threshold didn't help. Mid-speed settings were no bargain either: finishing in about 3 months took 24-25 minutes a day, more than Intensive. So a slower pace buys less new material at once, and only a little daily time. *Measured in the simulator only:* it can't show whether the lighter load helps real learners remember more, which is the whole case for these two paces.

*Later fix to H49:* the first-day allowance vanished once the kana lesson finished, so day one stopped before any phrases. A full first-day walkthrough caught it, and a test now covers it.

