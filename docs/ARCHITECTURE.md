# Architecture

## Product scope (personal use)

| Scope | Effort | Notes |
|-------|--------|-------|
| Text chat partner | 1–3 evenings | Useful, not voice |
| Turn-based voice | ~1 weekend | Target MVP |
| Realtime barge-in voice | 1–3 weeks | Closer to Pingo feel |
| Pingo-like product | weeks–months | Scenarios, memory, pronunciation scoring — **out of scope for v0** |

v0 = turn-based speaking practice + optional **Practice** intelligibility / shadowing mode.
Skip app-store polish, accounts, 200 scenarios, and dictionary-grade pitch-accent grading.

## Pipeline (chosen)

```
Mic → local faster-whisper (ja) → DeepSeek V4 API → local JP TTS → speakers
```

Practice mode (separate):

```
Target text → VOICEVOX preview
User audio → Whisper → kana-normalized similarity vs target → optional DeepSeek tip
```

Self-assessment placement (onboarding):

```
Fixed questions → user self-ratings → speaking_level / comprehension_level / goal_level
```

### Phase 1 concrete defaults

| Piece | Default |
|-------|---------|
| App | FastAPI + Chat / Practice / Place me / Settings tabs on port **8787** |
| STT | `faster-whisper` / `large-v3-turbo` / `cuda` / `float16` |
| LLM | `deepseek-v4-flash` with `thinking: disabled` |
| TTS | **AivisSpeech** HTTP API at `http://127.0.0.1:10101` (default); VOICEVOX at `:50021` as fallback |
| Practice score | Intelligibility (`score_kind: intelligibility`) via pykakasi + Levenshtein — not pitch accent / native pronunciation |

| Tutor prefs | Active profile’s `user_prefs.json` — correction, language, register, naturalness, goals, routing, personality, voice, max sentences |
| Learner profile | Active profile’s `learner_profile.json` — live speaking/comprehension estimates |
| Long-term memory | Active profile’s `learner_memory.json` — comfort, topics, vocab, grammar, soft `recycle_items` |
| User profiles | `%LocalAppData%\Kaiwa\profiles.json` + `profiles/<id>/` (prefs, learner profile, memory, custom personalities, PTT sounds). Optional `KAIWA_DATA_DIR` override. |
| Sessions | `%LocalAppData%\Kaiwa\sessions/<id>.jsonl` with `mode: chat` or `mode: practice` (global, not per profile) |
| Secrets | `%LocalAppData%\Kaiwa\secrets.json` (DeepSeek key; Phase 6.2) |

### Phase 2 tutor prefs

Settings tab edits server-side prefs used to assemble the chat system prompt each turn:

- `correction_style`: `gentle` | `critique`
- `language_policy`: `immerse` | `adaptive` (default adaptive — brief English only when struggling)
- `speech_register`: `formal` | `casual` (applies on top of personality)
- `naturalness_tips`: bool — flag grammatical-but-stiff phrasing for the selected register
- `personality_id`: built-in id, `user_…` custom preset, or `custom`
- `personality_custom`: optional notes appended on top of the selected preset
- `max_sentences`: kept in prefs for backward compatibility; **not** used as a hard prompt cap anymore — reply length is adaptive (see length guidance in `persona.py`)
- `help_language`: currently `en` (forward-compat)
- `voicevox_speaker_id`: speaker/style id for the active engine (Settings voice picker; `GET /api/voices`)
- `tts_engine`: `aivisspeech` | `voicevox` (default `aivisspeech`)
- `goal_level`: `pre_n5` | `n5` | `n4` (pacing ceiling)
- `topic_preferences`: up to 8 short topic strings
- `model_routing`: `auto` (Flash + Pro on hard turns) | `flash_only`

Learner profile (per active user profile) tracks estimated `speaking_level` / `comprehension_level`, confidence, notes, and topic tags. Updated from chat struggle signals, practice scores, occasional Flash JSON assess, and the **self-assessment Place me** flow. Injected into the tutor prompt each turn. `GET/PUT /api/profile`.

Long-term memory (per active user profile) stores comfort/personality prefs (name, vibe, do/dont), observed topics, vocab phrases, recurring grammar notes, and soft `recycle_items` for optional “say again” Practice. Occasional Flash extract after chat turns (post-TTS). Injected into the tutor prompt on top of the selected personality. `GET/PUT /api/memory`.

Practice (`GET /api/practice/next`) sources: `bank` | `last_reply` | `vocab` (from memory) | `recycle` (soft retries; falls through to vocab → last reply). Chat is the main loop; Practice is an optional warm-up — not a quiz gate. Chat UI **Replay** re-plays the last TTS reply from a client cache (falls back to `POST /api/practice/speak` if audio was lost after refresh).

Placement APIs: `POST /api/quiz/start`, `/api/quiz/answer`, `/api/quiz/finish` (self-assessment; no `/speak`).

User-named presets live in the active profile’s `user_personalities.json` with CRUD:

- `GET /api/personalities`
- `POST /api/personalities`
- `PUT /api/personalities/{id}`
- `DELETE /api/personalities/{id}`

Also: `GET /api/prefs`, `PUT /api/prefs`.

### User profiles (named learner state)

A **profile** is one learner’s Kaiwa state (not an account): prefs, learner profile, memory, and custom personalities. Registry: `%LocalAppData%\Kaiwa\profiles.json`; files under `profiles/<id>/`. On first launch with empty AppData, Kaiwa **copies** legacy repo `data/` (+ `sessions/`) once if present; otherwise creates a fresh `default` profile. Flat legacy `*.json` at the user-data root still fold into `profiles/default/`. Sessions stay global under AppData `sessions/`; switching clears browser chat session id.

API:

- `GET /api/profiles` — list + `active_id`
- `POST /api/profiles` — create (`label`, optional `activate`)
- `POST /api/profiles/{id}/activate` — switch active; returns prefs/profile/memory for UI refresh
- `DELETE /api/profiles/{id}` — refuse if last; auto-switch if deleting active
- `POST /api/profiles/{id}/reset` — wipe four files to defaults (keep id/label)
- `GET /api/profiles/{id}/export` — versioned `kaiwa-profile` JSON download
- `POST /api/profiles/import` — JSON body or multipart file; always creates a new profile

Replies are cleaned of stage-direction emotes (`(smiles)`, `*claps*`, etc.) before chat display and TTS.

Chat turns log `timing: {stt_ms, llm_ms, tts_ms, total_ms}` in session JSONL and return it on `/api/turn`. Summarize with `scripts/eval_turn_latency.py`.

### Why hybrid

- **Local Whisper:** RTX 3090 runs `large-v3` / `large-v3-turbo` easily; accurate enough for conversation; not a pronunciation scorer.
- **DeepSeek V4 API:** V4 is **text-only** (no native audio I/O). Strong Japanese + cheap. Flash for snappy chat; Pro for deeper grammar explanations.
- **Local JP TTS:** Japanese-native voicebanks beat generic multilingual cloud voices for tutoring feel; $0 ongoing.

### Why not full local LLM

A 3090 cannot host DeepSeek V4-Pro competitively. Local 14B–32B (e.g. Qwen) can be “good enough” tutors but usually won’t beat hosted V4 quality. Owner is fine paying for DeepSeek → prefer API brain.

### Why not full realtime API first

Realtime speech-to-speech (OpenAI Realtime, Gemini Live) feels more Pingo-like but costs more and is less controllable. **Phase 3 decision: stay turn-based**; re-evaluate only if daily practice latency feels bad (`scripts/eval_turn_latency.py`).

## Latency

Turn-based stack typically **~1.5–4+ seconds** per turn (STT + LLM + TTS). Fine for practice; not phone-call natural.

Whisper on 3090: usually sub-second to a couple seconds per short utterance.

## Whisper accuracy notes

**Helps:** quiet room, headset mic, full phrases, `vad_filter=True`, larger models. Practice forces `language="ja"`. Chat auto-detects: clear English stays English; otherwise Japanese-forced (avoids Whisper “translating” English into JP).

**Hurts:** noise, mumbling, heavy code-switching, non-native pronunciation.

Whisper may “correct” learner speech toward native forms — good for conversation flow, **bad** as a pronunciation judge. Do not treat transcripts as pitch-accent ground truth.

## TTS options

### Local (preferred)

| Engine | Japanese quality | Notes |
|--------|------------------|-------|
| **AivisSpeech** | Excellent | **Phase 3 default**; VOICEVOX-compatible API on `:10101` |
| VOICEVOX | Good–great | Fallback; clear JP; anime/voicebank feel (`:50021`) |
| Style-Bert-VITS2 | Top JP prosody | More setup; expressive — not wired |
| Qwen3-TTS | Very good | Cloning; Apache-friendly — not wired |
| Fish Speech | Often top naturalness | Heavier/slower; check licenses — not wired |

### Cloud (cheap personal volume)

| Service | Price vibe | Notes |
|---------|------------|-------|
| OpenAI TTS | ~$15/1M chars | Simple; often a few $/mo at personal use |
| Google / Azure Neural | ~$4–16/1M chars | Strong JP voice catalogs |
| ElevenLabs | Much more expensive | Premium human feel; not DeepSeek-comparable thrift |

At ~10–20 min AI speech/day, OpenAI/Google neural is usually single-digit monthly dollars. Prefer local JP TTS unless setup friction wins.

## Cost ballpark (personal ~30 min practice/day)

| Stack | Monthly feel |
|-------|----------------|
| Local Whisper + DeepSeek + local TTS | mostly DeepSeek pennies–low dollars |
| Same + OpenAI/Google TTS | still usually low single digits–teens |
| OpenAI Realtime flagship | can jump to tens–hundreds |

## Prompt posture (tutor)

- Patient Japanese conversation partner
- Adapt to stated level (e.g. early beginner / JLPT target)
- Keep replies short (1–3 sentences) for TTS
- Gentle corrections; optional short English notes when asked
- Prefer spoken natural Japanese over lecture dumps

## Packaging (Windows desktop)

Two processes:

1. **Thin shell** — PyInstaller `Kaiwa.exe` (webview + PTT hook); ~tens of MB.
2. **Private runtime** — `dist/Kaiwa/runtime\` (CPython venv with FastAPI / faster-whisper **CPU** deps) + sibling `static/`. Relative `Kaiwa.runtime.json` (`app_root`, `python`). Shell sets `KAIWA_ROOT` when spawning `python -m kaiwa.app`.

**First-run bootstrap** (before TTS/API): shell runs `python -m kaiwa.bootstrap ensure` via the runtime interpreter. Downloads Whisper weights to `%LocalAppData%\Kaiwa\models\whisper\` and installs AivisSpeech Engine under `tts\aivisspeech\` if not already found (Program Files / tools / AppData). Splash shows progress; downloads resume after interrupt. STT then loads with `local_files_only` when the AppData model is present.

User data stays under `%LocalAppData%\Kaiwa\`. **Hardware:** `WHISPER_DEVICE=auto` prefers CUDA when a GPU and nvidia wheels are present, else CPU (`int8`). Owners: `pip install -e ".[cuda]"`. Friend portable runtime is CPU unless CUDA wheels are added. Dev-only: `build_desktop.ps1 -DevVenv` points the shell at the clone `.venv`.

**Installer:** `scripts/build_installer.ps1` (Inno Setup 6) packs `dist/Kaiwa/` into `dist/KaiwaSetup-1.0.0.exe` — Program Files install, Start Menu shortcut, Add/Remove Programs uninstall. Uninstall does **not** delete AppData. Friend path is the Setup.exe from the GitHub Release (portable folder remains a build intermediate).

**Updates (6.9):** UI calls `/api/updates/check` (GitHub Releases latest; 24h AppData cache). When newer, a banner + Settings → About offer **Update now**, which downloads `KaiwaSetup-*.exe` to `%LocalAppData%\Kaiwa\downloads\updates\` and launches it (`os.startfile`). Desktop log: `%LocalAppData%\Kaiwa\Kaiwa.desktop.log`.

## Out of scope (v0)

- Pronunciation dictionary / absolute pitch-accent grading (NHK / MARINE H–L)
- Mobile app stores
- Multi-user / accounts / cloud sync
- Cloning Pingo’s full scenario catalog
- Running DeepSeek V4-Pro locally
