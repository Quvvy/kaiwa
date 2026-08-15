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
- [x] Theme switcher — Settings → Themes; fifteen Dark/Light presets with swatch cards (`ui_theme`)

**Priority** (completed)

1. ~~First-run flow~~ **done**
2. ~~Clearer engine-down / TTS errors~~ **done**
3. ~~Stronger correction surfacing~~ **done**
4. ~~Settings / Practice / Place me visual polish~~ **done**
5. ~~Theme switcher~~ **done** (fifteen presets; custom editors deferred)

## Phase 5 — Tutor learning quality (done)

Design input: real chat critique (`docs/TUTOR_EXCHANGE_CRITIQUE.md`). Teach under a casual conversation — not a JLPT drill.

**Constraint (all slices):** keep Kaiwa’s casual, non-textbook voice (personality / register). Do not turn replies into stiff です・ます lesson speech.

| Slice | Status | Goal |
|-------|--------|------|
| **5.1** JP-first meaning help | [x] | When learner signals “don’t understand X”, explain in easy JP (+ one example) before English; Adaptive may add a short gloss only if still stuck (`language_policy`, `help_language`) |
| **5.2** Useful micro-corrections | [x] | Acknowledge clear turns; for useful/recurring errors (word family, particles, です/だ), one soft fix via `TRY:` / brief JP — not every typo (`correction_style`) |
| **5.3** Topic stickiness | [x] | Stay on the current thread 1–2 turns (reuse just-taught words) before jumping topics |
| **5.4** Difficulty governor | [x] | Cap next-turn vocab/grammar by demonstrated level + profile; simpler follow-ups until complexity is earned (`speaking_level`, `goal_level`, memory vocab) |
| **5.5** Comprehensibility-first Chat | [x] | Conversation partner first; internal support ladder + help_type; density lock; JP teaches / EN rescues; decay recovery; Chat `TRY:` retired (Practice stays drills) |

**Priority** (completed)

1. ~~5.1 JP-first meaning help~~ **done**
2. ~~5.2 Useful micro-corrections~~ **done**
3. ~~5.3 Topic stickiness~~ **done**
4. ~~5.4 Difficulty governor~~ **done**
5. ~~5.5 Comprehensibility-first Chat~~ **done**

**Out of Phase 5**

- Pitch / pronunciation APIs
- Full UI i18n
- Scenario catalog / realtime speech
- Surfacing support-mode names in the UI (modes stay internal)

**Only if needed later** (from Phase 4 backlog)

- Custom / extra theme editor beyond the built-in presets
- Dictionary-absolute pitch accent (NHK / MARINE H–L) / OJAD-style sentence graphs
- Realtime barge-in speech APIs
- Larger scenario catalog

## Phase 6 — Consumer prep (→ GitHub 1.0.0) (shipped)

Friend-ready **Windows** **1.0.0** for a small non-technical share circle: install → launch → paste DeepSeek key → talk. Thin `.venv`-pointing `Kaiwa.exe` is **dev-only** after 6.4. Phase 6 includes **6.9** in-app update checker.

**Constraint:** **DeepSeek only** for 1.0.0 (no multi-LLM picker). CUDA Whisper preferred; CPU fallback required.

| Slice | Status | Goal |
|-------|--------|------|
| **6.1** Legal & version hygiene | [x] | `LICENSE`, third-party notices (Whisper / Aivis / deps), version toward `1.0.0`, start `CHANGELOG.md` |
| **6.2** DeepSeek first-run key | [x] | Launch without repo `.env`; gate until key saved under user AppData; soft validate; Settings can update key |
| **6.3** Consumer data layout | [x] | Profiles / prefs / sessions under `%LocalAppData%\Kaiwa\` (not repo `data/`); migrate-or-fresh for owner installs |
| **6.4** Self-contained Windows runtime | [x] | Runnable app without a pre-made developer `.venv`; installer/bundled runtime owns Python + deps |
| **6.5** Model & voice bootstrap | [x] | Install/first-run downloads Whisper weights + installs/locates AivisSpeech; progress UI; resume-safe |
| **6.6** Hardware path | [x] | CUDA Whisper when available, else CPU; document “NVIDIA GPU recommended” |
| **6.7** Installer + first-launch UX | [x] | Windows installer (Start Menu, uninstall); splash → bootstrap → API key → soft Place me; plain-English failures |
| **6.8** GitHub Release 1.0.0 | [x] | Tag `v1.0.0`, release notes, attach installer, consumer README (“Download → Install → paste DeepSeek key”) |
| **6.9** In-app update checker | [x] | Notify when a newer GitHub release exists; download + install without visiting the releases page (Windows) |

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

## Phase 8 — Keep talking (conversation gym)

Make it almost impossible for a beginner conversation to die. Pre-N5 Chat is a **conversation gym** by default (one short, easy-to-answer idea with a next-turn hook; yes/no is Rescue only); Chat stays a conversation, not a drill. Practice stays shadowing. Success = the exchange continues.

**Constraint (all slices):** keep Phase 5.5 — Japanese teaches, English rescues, Practice drills; never name `support_mode` in the UI; no Chat `TRY:`. Rescue is a learner **action**, not a mode label.

| Slice | Status | Goal |
|-------|--------|------|
| **8.1** Pre-N5 reply shape | [x] | One idea + reuse learner words; high-load constructions (not grammar bans); one retry; silent `reply_shape` JSONL. Scaffold decays with pitch / support. |
| **8.2** Rescue | [x] | **Simpler** on the last Kaiwa bubble; `POST /api/rescue` (no fake user line); force comprehension help + bump `struggle_streak`; rewrite last assistant line one step down (shorter → yes/no → A/B); TTS + JSONL `rescue: true` |
| **8.3** Session records + New chat | [x] | Bind sessions to `profile_id`; meta (started/updated, turn count, title); hydrate RAM from JSONL; **New chat**; `GET/POST /api/sessions`; re-register PTT session id |
| **8.4** History drawer + resume | [x] | List/open past chats for the active profile; redraw bubbles; LLM context = last N turns (not the whole file) |
| **8.5** Replay | [x] | Same assistant questions again as a child session (`replay_of`); no new teaching; Rescue still allowed. Not Practice shadowing |
| **8.6** Easy vs Free + survive N | [x] | Chat **Easy** / **Free** chip (default Easy). Free turns off the 8.1 shape lock. Quiet session turn count; no XP. |
| **8.7** After-chat leftovers | [x] | On **New chat**: 3–5 unique recent learner lines from the ended thread. Optional Flash “You could have said” (1–3, no stars, no `TRY:`). Not SRS. |

**Priority** (8.1–8.7 done)

1. ~~8.1 Pre-N5 reply shape~~ **done**
2. ~~8.2 Rescue~~ **done**
3. ~~8.3 Session records + New chat~~ **done**
4. ~~8.4 History drawer + resume~~ **done**
5. ~~8.5 Replay~~ **done**
6. ~~8.7 After-chat leftovers~~ **done**
7. ~~8.6 Easy vs Free + survive N~~ **done**

**Three-PR cut** (if fewer merges): Survive today = 8.1+8.2 · Chats are durable = 8.3+8.4 · Use it twice = 8.5+8.7. Leave 8.6 out.

**Depends on**

```
8.1 ──► 8.2
 │
 ▼
8.3 ──► 8.4 ──► 8.5
 │
 ▼
8.7         8.6 (optional; after 8.1)
```

**Out of Phase 8**

- NPC / konbini / ramen scenes (after ~20 Easy turns + Rescue)
- Per-turn “did you understand?” (Rescue is that signal)
- N5 goal ledger / “today’s grammar” (Phase 10+)
- Full scenario catalog (still a non-goal)
- Rebuilding Anki / SRS in Settings

**Shipped beside 8.1 (not a Phase 8 slice):** prompt revision stamp + Chat **New chat** (keep memory) + LLM last-16 context — decision #115. 8.3 makes New chat a durable per-profile session object. 8.4 is the **Chats** drawer + resume (#118). 8.5 is **Again** (child session, not TTS Replay) (#119). 8.7 is after-chat leftovers (#120). 8.6 is Easy/Free + quiet turn count (#121).

The live Practice tab is still Phase 1.5 (intelligibility / shadowing) until **Phase 9** ships.

## Phase 9 — Practice from Chat

Guided sitting from Chat struggles and low-confidence moments — then back to Chat. Spec: [docs/PRACTICE.md](PRACTICE.md). Decision #127. **Not** in 1.0.4.

Chat’s job: talk with me. Practice’s job: get comfortable saying the kinds of things I struggled with (or lacked confidence to say) in Chat. Every activity has a path back to Chat. Cards are immutable snapshots at the Chat moment — not rebuilt from extract `grammar_add`. Home is **Today’s practice / Start**, not category tiles. Sittings are tiny guided conversations around one struggle (3–5 Easy-shaped turns), not LLM roleplay catalogs.

| Slice | Status | Goal |
|-------|--------|------|
| **9.1** Snapshot struggle cards | [ ] | Write cards when Chat shows struggle or low confidence (corrections, Simpler, help, freeze, one-word, English switch, abandoned idea). Speakable Japanese + hidden tags. Immutable snapshot. |
| **9.2** Session shell | [ ] | Today’s practice / about N minutes / **Start** / back to Chat. No phrase-bank toolbox. No intelligibility % as the product. |
| **9.3** Tiny guided conversations | [ ] | 3–5 Easy-shaped turns around one card, then stop. No new grammar. No konbini catalog. |

**Priority**

1. 9.1 Snapshot struggle cards
2. 9.2 Session shell
3. 9.3 Tiny guided conversations
4. Nothing else until cards have fuel

**Out of Phase 9**

- Conversation / shadow-recent-Kaiwa as a home peer (Again / Replay / history)
- Grammar-name navigation (Particles, Potential, …)
- Pronunciation, dictation, SRS/XP
- N5 goal ledger (Phase 10+)
- Listening / Review tiles as home navigation (hear-and-answer may happen inside a sitting)

## Phase 10+ (later)

- N5 goal ledger / “today’s grammar”
