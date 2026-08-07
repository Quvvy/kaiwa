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
- [x] Short-reply enforcement via `max_sentences` in assembled prompt
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
- [x] Pitch-accent / dedicated pronunciation assessment — **deferred past Phase 3** (Practice stays intelligibility-only)

## Phase 4 — Polish & daily use (next)

Core loop is usable. Prefer friction-killers and learning feedback over new product surface.

**Priority**

1. First-run flow — prompt Place me / basic Settings on first launch
2. One-click startup — start AivisSpeech (+ optional VOICEVOX) and Kaiwa together
3. Clearer engine-down / TTS errors in UI
4. Practice from chat weaknesses — drill last reply / memory vocab
5. Stronger correction surfacing (gentle diffs without breaking immersion)
6. Settings / tab UX cleanup (dense Settings panel)

**Only if needed later**

- Pitch accent / dedicated pronunciation scoring
- Realtime barge-in speech APIs
- Larger scenario catalog

## Will not build (near term)

- App Store / Play Store packaging
- Multi-user accounts
- Full scenario catalog like Pingo
- Local hosting of DeepSeek V4-Pro class weights
- Claiming Whisper-based “native pronunciation accuracy”
