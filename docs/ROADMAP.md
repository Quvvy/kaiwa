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

## Phase 5 — Tutor learning quality (done)

Design input: real chat critique (`docs/TUTOR_EXCHANGE_CRITIQUE.md`). Teach under a casual conversation — not a JLPT drill.

**Constraint (all slices):** keep Kaiwa’s casual, non-textbook voice (personality / register). Do not turn replies into stiff です・ます lesson speech.

| Slice | Status | Goal |
|-------|--------|------|
| **5.1** JP-first meaning help | [x] | When learner signals “don’t understand X”, explain in easy JP (+ one example) before English; Adaptive may add a short gloss only if still stuck (`language_policy`, `help_language`) |
| **5.2** Useful micro-corrections | [x] | Acknowledge clear turns; for useful/recurring errors (word family, particles, です/だ), one soft fix via `TRY:` / brief JP — not every typo (`correction_style`) |
| **5.3** Topic stickiness | [x] | Stay on the current thread 1–2 turns (reuse just-taught words) before jumping topics |
| **5.4** Difficulty governor | [x] | Cap next-turn vocab/grammar by demonstrated level + profile; simpler follow-ups until complexity is earned (`speaking_level`, `goal_level`, memory vocab) |

**Priority** (completed)

1. ~~5.1 JP-first meaning help~~ **done**
2. ~~5.2 Useful micro-corrections~~ **done**
3. ~~5.3 Topic stickiness~~ **done**
4. ~~5.4 Difficulty governor~~ **done**

**Out of Phase 5**

- Pitch / pronunciation APIs
- Full UI i18n
- Scenario catalog / realtime speech

**Only if needed later** (from Phase 4 backlog)

- Custom / extra theme editor beyond the six presets
- Dictionary-absolute pitch accent (NHK / MARINE H–L) / OJAD-style sentence graphs
- Realtime barge-in speech APIs
- Larger scenario catalog

## Phase 6 — Consumer prep (→ GitHub 1.0.0) (next)

Friend-ready **Windows** release for a small non-technical share circle: install → launch → paste DeepSeek key → talk. Thin `.venv`-pointing `Kaiwa.exe` is **dev-only** after 6.4.

**Constraint:** **DeepSeek only** for 1.0.0 (no multi-LLM picker). CUDA Whisper preferred; CPU fallback required.

| Slice | Status | Goal |
|-------|--------|------|
| **6.1** Legal & version hygiene | [x] | `LICENSE`, third-party notices (Whisper / Aivis / deps), version toward `1.0.0`, start `CHANGELOG.md` |
| **6.2** DeepSeek first-run key | [ ] | Launch without repo `.env`; gate until key saved under user AppData; soft validate; Settings can update key |
| **6.3** Consumer data layout | [ ] | Profiles / prefs / sessions under `%LocalAppData%\Kaiwa\` (not repo `data/`); migrate-or-fresh for owner installs |
| **6.4** Self-contained Windows runtime | [ ] | Runnable app without a pre-made developer `.venv`; installer/bundled runtime owns Python + deps |
| **6.5** Model & voice bootstrap | [ ] | Install/first-run downloads Whisper weights + installs/locates AivisSpeech; progress UI; resume-safe |
| **6.6** Hardware path | [ ] | CUDA Whisper when available, else CPU; document “NVIDIA GPU recommended” |
| **6.7** Installer + first-launch UX | [ ] | Windows installer (Start Menu, uninstall); splash → bootstrap → API key → soft Place me; plain-English failures |
| **6.8** GitHub Release 1.0.0 | [ ] | Tag `v1.0.0`, release notes, attach installer, consumer README (“Download → Install → paste DeepSeek key”) |
| **6.9** In-app update checker | [ ] | Notify when a newer GitHub release exists; download + install without visiting the releases page (Windows) |

**Priority**

1. 6.1 Legal & version hygiene
2. 6.2 DeepSeek first-run key
3. 6.3 Consumer data layout
4. 6.4 Self-contained Windows runtime
5. 6.5 Model & voice bootstrap
6. 6.6 Hardware path
7. 6.7 Installer + first-launch UX
8. 6.8 GitHub Release 1.0.0
9. 6.9 In-app update checker

**Out of Phase 6 / 1.0.0**

- Multi-LLM providers
- macOS / Linux installers
- App Store / Play Store
- Bundling every AivisHub voice
- One giant CUDA-in-single-exe freeze

## Will not build (near term)

- App Store / Play Store packaging
- Multi-user cloud accounts
- Multi-LLM provider picker (DeepSeek-only through 1.0.0)
- Full scenario catalog like Pingo
- Local hosting of DeepSeek V4-Pro class weights
- Claiming Whisper-based “native pronunciation accuracy”

## Phase 7 — Global push-to-talk (after 1.0.0)

Hold a bindable key or mouse button from **any** app/game while Kaiwa is running (window need not be focused). Native mic → normal chat turn → TTS. Windows desktop only. Default **off**.

| Slice | Status | Goal |
|-------|--------|------|
| **7.1** Prefs + Settings bind UI | [x] | `ptt_enabled` / `ptt_binding` / `ptt_play_reply`; press-to-bind; default off |
| **7.2** Native mic turn path | [x] | Desktop records WAV → `/api/turn` → play TTS |
| **7.3** Global hook | [x] | Key + mouse hold/release while unfocused |
| **7.4** Chat UI sync | [x] | Background turns appear in transcript |

**Priority** (completed with implementation)

1. ~~7.1~~ **done**
2. ~~7.2~~ **done**
3. ~~7.3~~ **done**
4. ~~7.4~~ **done**

**Out of Phase 7**

- Always-on VAD / open-mic
- Gamepad binds
- macOS / Linux global PTT
- Tray-idle product mode
- Game audio ducking
