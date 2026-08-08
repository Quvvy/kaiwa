# Roadmap

## Phase 0 — Scaffold (done)

- [x] Create `E:\cursor\kaiwa` git repo
- [x] Capture architecture + decisions
- [x] Ingest into llm-wiki

## Phase 1 — Turn-based MVP

- [x] Local faster-whisper Japanese transcription (`language=ja`, `large-v3-turbo`, CUDA)
- [x] DeepSeek V4 Flash chat with tutor system prompt (`deepseek-v4-flash`, thinking disabled)
- [x] Local TTS playback (VOICEVOX on `:50021`)
- [x] Minimal web UI: hold-to-talk → transcript → reply text + audio (`http://127.0.0.1:8787`)
- [x] Save session transcripts locally (`sessions/*.jsonl`)

## Phase 1.5 — Practice mode (intelligibility MVP+)

- [x] Chat | Practice tabs in UI
- [x] Phrase bank + practice last chat reply
- [x] Target TTS preview (`/api/practice/speak`)
- [x] Intelligibility score (kana-normalized vs Whisper transcript) — **not** pitch accent
- [x] Short DeepSeek tip from text mismatch
- [x] Session log `mode: practice`

## Phase 2 — Tutor quality

- [x] Correction style swap: **Gentle | Critique**
- [x] Personality editor: presets + custom notes (`data/user_prefs.json`)
- [x] Short-reply enforcement via assembled prompt (now soft/adaptive length; `max_sentences` deprecated for prompting)
- [x] Settings tab + `GET/PUT /api/prefs`
- [x] Built-ins: Anime club mate + Funny friend (loving roast → correct)
- [x] User-created named presets CRUD (`data/user_personalities.json`)
- [x] Language help: Immersion | Adaptive (brief EN corrections when struggling)
- [x] Speech register: Formal | Casual (on top of personality)
- [x] Naturalness tips toggle (textbook-stiff → more natural)
- [x] Ban stage-direction emotes in prompts + strip before TTS
- [x] VOICEVOX voice picker in Settings (`voicevox_speaker_id`, `GET /api/voices`)
- [x] Level / goal settings (`goal_level`, topic preferences)
- [x] Dynamic learner profile (`data/learner_profile.json` — heuristics + occasional Flash assess)
- [x] Flash vs Pro routing (`model_routing: auto | flash_only`)

## Phase 3 — Optional upgrades

- [x] Self-assessment Place me (stage / listening / speaking / pace → profile + goal)
- [x] Lightweight long-term memory (vocab, topics, grammar, comfort prefs)
- [x] Upgrade TTS — **AivisSpeech** default (VOICEVOX-compatible); VOICEVOX kept as Settings fallback
- [x] Evaluate realtime speech APIs — **stay turn-based** (instrument turn timing; no Realtime API)
- [x] Pitch-accent / dedicated pronunciation assessment — **deferred**; soft model-contour pitch in Practice was tried then **removed** (intelligibility + shadowing only)

## Phase 4 — Polish & daily use (done)

Core loop is usable. Prefer friction-killers and learning feedback over new product surface.

**Done**

- [x] Named user profiles — create/switch/delete/reset + JSON import/export (`data/profiles/`)
- [x] Soft phrase reuse — optional Practice warm-up from last reply / memory vocab / say-again recycle (not drill/quiz)
- [x] One-click desktop — `kaiwa-desktop` / `Kaiwa.exe` opens a window (splash → TTS+API → UI); close stops spawned services and exits (tray dropped)
- [x] Per-profile soft first-run Place me — auto-open when incomplete; Skip; expanded English self-assessment; prompt trusts placement / treats level as unknown until done
- [x] Clearer TTS / engine-down errors — soft dismissible alert + consistent engine hints
- [x] Gentle correction surfacing — optional `TRY:` line stripped before TTS; muted “Try saying…” under Chat bubble
- [x] Chat UI redesign (night studio) — readable dark conversation shell; CSS tokens ready for future themes
- [x] Settings / Practice / Place me visual polish — section rail Settings; Practice + Place me match night-studio tokens (all options kept)
- [x] Windows `Kaiwa.exe` desktop shell — PyInstaller windowed webview so taskbar is Kaiwa (API still venv)
- [x] Practice = intelligibility + shadowing (model-contour pitch % removed)
- [x] Theme switcher — Settings → Themes; six Dark/Light presets with swatch cards (`ui_theme`)

**Priority** (completed)

1. ~~First-run flow~~ **done**
2. ~~Clearer engine-down / TTS errors~~ **done**
3. ~~Stronger correction surfacing~~ **done**
4. ~~Settings / Practice / Place me visual polish~~ **done**
5. ~~Theme switcher~~ **done** (six presets; custom editors deferred)

## Phase 5 — Tutor learning quality (next)

Design input: real chat critique (`docs/TUTOR_EXCHANGE_CRITIQUE.md`). Teach under a casual conversation — not a JLPT drill.

**Constraint (all slices):** keep Kaiwa’s casual, non-textbook voice (personality / register). Do not turn replies into stiff です・ます lesson speech.

| Slice | Status | Goal |
|-------|--------|------|
| **5.1** JP-first meaning help | [ ] | When learner signals “don’t understand X”, explain in easy JP (+ one example) before English; Adaptive may add a short gloss only if still stuck (`language_policy`, `help_language`) |
| **5.2** Useful micro-corrections | [ ] | Acknowledge clear turns; for useful/recurring errors (word family, particles, です/だ), one soft fix via `TRY:` / brief JP — not every typo (`correction_style`) |
| **5.3** Topic stickiness | [ ] | Stay on the current thread 1–2 turns (reuse just-taught words) before jumping topics |
| **5.4** Difficulty governor | [ ] | Cap next-turn vocab/grammar by demonstrated level + profile; simpler follow-ups until complexity is earned (`speaking_level`, `goal_level`, memory vocab) |

**Priority**

1. 5.1 JP-first meaning help
2. 5.2 Useful micro-corrections
3. 5.3 Topic stickiness
4. 5.4 Difficulty governor

**Out of Phase 5**

- Pitch / pronunciation APIs
- Full UI i18n
- Scenario catalog / realtime speech

**Only if needed later** (from Phase 4 backlog)

- Custom / extra theme editor beyond the six presets
- Dictionary-absolute pitch accent (NHK / MARINE H–L) / OJAD-style sentence graphs
- Realtime barge-in speech APIs
- Larger scenario catalog

## Will not build (near term)

- App Store / Play Store packaging
- Multi-user accounts
- Full scenario catalog like Pingo
- Local hosting of DeepSeek V4-Pro class weights
- Claiming Whisper-based “native pronunciation accuracy”
