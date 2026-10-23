# Kaiwa cleanup checklist

From the October 2026 audit. Work top to bottom: each tier assumes the one above it is done.
Effort: **S** = under an hour, **M** = an afternoon, **L** = a few sessions.

## P0 — Protect what exists

- [x] **S** Commit the uncommitted Phase 9–10 work to a branch as-is (`git switch -c phase-9-10-wip`), so nothing is lost while you decide what to keep.
- [x] **S** Keep `data/tts_probe.txt` (has your AppData paths) and `data/tutor_prompt_*.txt` out of that commit. Delete them, or add `data/*.txt` to `.gitignore`.
- [x] **M** Stop the silent profile/memory wipe. Today `save_profile` / `save_memory` / `save_prefs` use plain `write_text`, background `_chat_sidework` threads read and write the same files, and any failed read returns a default that then gets saved over the real file.
  - Write to a temp file, then `os.replace` it into place.
  - Add one lock around load→modify→save.
  - On a decode error, keep a `.bak` and log it. Never return defaults that will later be saved.
  - Files: `learner_profile.py:227`, `learner_memory.py:312`, `prefs.py:256`, `app.py` `_chat_sidework`.
  - Done in `kaiwa/jsonio.py`, covered by `scripts/smoke_state_files.py`. The legacy `/api/practice` route still saves unlocked; it goes away in P1.

## P1 — Decide what Kaiwa is, then cut

- [x] **S** Write the product in one sentence at the top of the README. Every item below is judged against it.
- [x] **M** Merge Learn into Practice: one tab, one "Start", with the line picker as an option inside it.
  - The "starter leak" in `repro_bugs.py` was a wrong check (it expected a replaced, unfinished starter to count). Fixed the check; 9 known BUG lines now.
- [x] **M** Cut the Tutor settings down to the knobs a learner understands. Six of them control the same thing today: Correction style, Language help, Help language, Register, Naturalness and Personality.
  - Suggested: keep Personality, Casual/Formal and English help on/off.
  - Fold the rest into the prompt's defaults.
- [x] **S** Remove Model routing (Flash/Pro) from the UI and keep it as an env var (`MODEL_ROUTING`).
- [x] **S** Cut the themes from 15 to 3: Night, Day, Sage. Retired themes fall back to Night.
- [x] **M** Decide on Profiles: dropped. Settings → Your data keeps Export/Import/Reset, each backing up to `profiles/_backups/` first. Old extra profile folders stay on disk, hidden.
- [x] **M** Delete dead code:
  - the Phase 1.5 score routes (`/api/practice`, `/api/practice/next`), `practice/scoring.py`, `practice/phrases.py` and `practice_tip`
  - the retired `TRY:` / `better_phrase` path
  - the hardcoded `memory_updated: False`

## Course (the new core) — done and next

Kaiwa's home is now the **Learn** tab: a daily lesson (review → new phrases → listen → speak) over
10 hand-written units, with spaced review, unlimited extra listening, and a Flash speaking coach.
Chat reads the learned phrases. See `src/kaiwa/course/`.

- [x] Daily lesson, 10 units / 60 phrases, Leitner review, streak, progress.
- [x] Say-it-back check (Whisper → kana compare), speaking coach (what you said / model / one fix).
- [x] Extra listening generated from learned phrases; Chat prompt includes learned phrases.
- [x] Place me no longer hijacks first launch; Practice tab hidden; desktop boot starts TTS and API in parallel.
- [ ] **M** Try it with a real microphone for a few days and tune: pass marks (`speech_check.GOOD`), review size (20), slow speed (0.75).
- [ ] **L** Units 11–20 (adjectives/past done → counters, te-form requests, wants (〜たい), giving directions, shopping, family, plans).
- [ ] **M** Delete the hidden Practice subsystem (`practice/sitting.py`, `cards.py`, `learn.py`, its routes and UI), or fold Chat struggles into Review cards.
- [ ] **M** Kanji stage: once kana is solid, show kanji with furigana for learned phrases.
- [ ] **S** The packaged runtime takes ~20 s to answer /api/health while source takes 1.7 s — find out why (antivirus scan of the bundled Python?).

## P2 — Learning experience

- [ ] **S** Fix the skip-Place-me trap. `governor_pitch` returns `"unknown"` whenever placement isn't done (`persona.py:752`), so Easy stays at the lowest level forever. Let chat evidence (flow streaks) raise the level without the quiz.
- [ ] **S** Fix the default persona clash (also seen live: Practice sittings speak です・ます even with Casual register): "Patient tutor / やさしい先生" against the ため口 friend register. Default to Friend, or make the two agree.
- [ ] **L** Have the model judge understanding and corrections instead of regex. One structured reply per turn: the spoken text, then a short trailing tag (understood? / needs help? / one recast). This replaces:
  - the `infer_learner_state` / `infer_help_type` regexes (which misfire on 意味, help, ゆっくり and short answers like 犬)
  - the two hardcoded recast families in `wo_ga.py` (を好き→が好き and 眠り→眠い), so recasts and Practice cards work for any mistake
  - most shape and recast retries (fewer double LLM calls)
- [ ] **M** Turn streaming back on for beginners. Today `chat_stream` buffers whenever the shape lock is on or a recast is expected (`llm.py:323`), which is the default for everyone new. Do this together with the item above: stream the reply and parse the tag at the end.
- [ ] **M** Finish the prompt rewrite, starting from `data/tutor_prompt_restructured_default.txt`.
  - Target about 2 KB.
  - State each rule once, in priority order.
  - Take out app internals: tab names, Place me, `TRY:`, `mode=`/`help_type=`, Whisper.
  - Resolve the conflicts: naturalness tips vs. no register lectures vs. praise understanding over grammar.
- [ ] **M** Stop forgetting early topics. Beyond the last 16 messages, keep a 2–3 line running summary of the thread in the prompt.
- [ ] **M** Clean up memory extraction. Dedupe grammar and vocab notes on write (the panel shows 助けてください and the ない-form twice), and strip annotations like "(already known)".

## P3 — First-run and UI

- [ ] **S** Make the TTS-down message user-facing. Installer users see `.\.venv\Scripts\python.exe scripts\start_aivisspeech.py`. Show "Voice engine isn't running — Retry" and keep the dev hint in the log.
- [ ] **S** Don't show "New chat — tutor update (memory kept)" on a fresh install. `prompt_stamp` treats a missing stamp as revision 0, so new users always see it.
- [ ] **S** Show Place me (or a one-line "want Kaiwa to gauge your level?" offer) on first launch, as the README promises. Currently it only lives in Settings.
- [ ] **S** Trim the Chat empty state to a single hint line.
- [ ] **M** Hide internals in Settings: `pre_n5` → "Beginner", no raw ISO timestamps, no "confidence 83%", "Extracts: 3", "id eli" or "Flash assessments".
- [ ] **M** One save model: autosave everything, or one Save per page. Today there are four Save buttons plus a "Loaded" status line.
- [x] **S** Rename the Chat actions so they're obvious. Already done in the August WIP: "Hear that again" and "Same questions", plus Simpler.
- [ ] **S** Fix the defaults: the PTT key is F24 (most keyboards don't have it), so prompt for a bind on first enable. Blip volume defaults to 350%; set it to 100%.

## P4 — Code health

- [ ] **M** Merge the two turn pipelines (`_stream_chat_events` at `app.py:1250` and `_run_chat_turn` at `app.py:1568`) into one function that both call. Push-to-talk keeps using the non-streaming caller.
- [ ] **L** Split `app.py` (2,224 lines) into routers: chat, practice, settings, ptt, updates.
- [ ] **L** Split `static/index.html` (6,257 lines) into `app.css` plus a few JS modules (chat, practice, settings). No build step needed.
- [ ] **M** Turn the smoke scripts into pytest. They already pass and already fail loudly on a broken check. Make `repro_bugs.py` fail when a bug fires (10 known BUG lines today).
- [ ] **S** Make `KAIWA_DATA_DIR` fully isolated. It still copies the repo `.env` key and `data/profiles` into whatever folder it points at.
- [ ] **S** Stop polling `/api/ptt/events` and `/api/ptt/state` every few hundred ms when running in a plain browser, where global PTT can't work.
- [x] **M** Speed up cold start. The window now opens when the API answers (~3 s from source); the voice engine (15–25 s) finishes in the background and the page shows "Voice engine starting…". Liveness checks probe the socket first: Windows takes ~2 s to refuse a closed port over HTTP.
- [ ] **M** Shrink the docs.
  - Rewrite the README Notes section in plain English.
  - Collapse `ROADMAP.md`'s finished phases into one "Shipped" list.
  - Archive `DECISIONS.md` (about 150 entries) and keep only decisions that still constrain the code.
