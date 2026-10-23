# Architecture

## Product scope (personal use)

| Scope | Effort | Notes |
|-------|--------|-------|
| Text chat partner | 1–3 evenings | Useful, not voice |
| Turn-based voice | ~1 weekend | Target MVP |
| Realtime barge-in voice | 1–3 weeks | Closer to Pingo feel |
| Pingo-like product | weeks–months | Scenarios, memory, pronunciation scoring — **out of scope for v0** |

v0 = turn-based speaking practice + **Practice** sittings from Chat struggle snapshots (Phase 9, #127–#129).
Skip app-store polish, accounts, 200 scenarios, and dictionary-grade pitch-accent grading.

## Pipeline (chosen)

```
Mic → local faster-whisper (ja) → DeepSeek V4 API → local JP TTS → speakers
```

Practice (Phase 9 + 10.3): Chat writes immutable struggle cards → **Today’s practice / Start** → say the speakable line, one tiny exchange, then Chat. Spec: [PRACTICE.md](PRACTICE.md). Phase 10 acquisition loop: [LEARNING_LOOP.md](LEARNING_LOOP.md) (#136) — recasts first; Learn is a picker tab that queues those sittings (#143).

```
Chat struggle/help/Simpler → profiles/<id>/struggle_cards.jsonl
Start → rehearsal sitting (RAM + practice_state.json, not Chats) → back to Chat
```

Leftover Phase 1.5 routes (`GET /api/practice/next`, `POST /api/practice` score) are unused by the UI. `POST /api/practice/speak` remains for Chat **Replay**.

Self-assessment placement (onboarding):

```
Fixed questions → user self-ratings → speaking_level / comprehension_level / goal_level
Optional last question: preferred name (memory.comfort.preferred_name)
```

### Phase 1 concrete defaults

| Piece | Default |
|-------|---------|
| App | FastAPI + Chat / Practice / Settings tabs on port **8787** (Place me is a Settings section) |
| STT | `faster-whisper` / `large-v3-turbo` / `cuda` / `float16`. Chat auto-detects EN/JP with **no** identity `initial_prompt` / `hotwords`. Practice sittings force Japanese, also with no identity hint. Transcripts that are only `会話` / `会話さん` / `Kaiwa` / `カイワ` count as unheard (#135) and do **not** write a freeze card. Displayed transcript is never rewritten. |
| LLM | `deepseek-v4-flash` with `thinking: disabled` |
| TTS | **AivisSpeech** HTTP API at `http://127.0.0.1:10101` (default); VOICEVOX at `:50021` as fallback |
| Practice | Chat struggle cards → `GET /api/practice/today` + sitting start/turn/finish (Easy lock, max 2 learner turns). Leftover intelligibility score routes unused by UI. |

| Tutor prefs | Active profile’s `user_prefs.json` — correction, language, register, naturalness, goals, routing, personality, voice, max sentences |
| Learner profile | Active profile’s `learner_profile.json` — live speaking/comprehension estimates |
| Long-term memory | Active profile’s `learner_memory.json` — comfort, topics, vocab, grammar, soft `recycle_items` |
| User profiles | `%LocalAppData%\Kaiwa\profiles.json` + `profiles/<id>/` (prefs, learner profile, memory, custom personalities, PTT sounds, `struggle_cards.jsonl`, `practice_state.json`). Optional `KAIWA_DATA_DIR` override. |
| Sessions | `%LocalAppData%\Kaiwa\sessions/<id>.jsonl` plus `<id>.meta.json` (`profile_id`, title, turn_count, `prompt_revision`, optional `replay_of` + `replay_questions`). Still a global folder (not under `profiles/<id>/`). Chat UI redraws bubbles from `GET /api/sessions/{id}` on load and from the **Chats** drawer (#118). **Again** forks a child session (`POST /api/sessions/{id}/replay`, #119). After **New chat**, `GET /api/sessions/{id}/leftovers` surfaces learner lines from the ended thread (#120). LLM hydrates from JSONL on RAM miss; context is the last **16** messages. `PROMPT_REVISION` bump starts a **new session per profile** (UI New chat / `chat_reset`) and keeps old JSONL; a stale revision does **not** mint a new id mid-turn (#115/#118). |
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

Long-term memory (per active user profile) stores comfort/personality prefs (name, vibe, do/dont), observed topics, vocab phrases, recurring grammar notes, and soft `recycle_items` (unused by the live Practice tab). Occasional Flash extract after chat turns (post-TTS). **`preferred_name` is gated:** Settings `PUT /api/memory` and Place me write it; extract returns `name.candidate` + `evidence` and app code admits only `explicit_self_intro` / `explicit_call_me` with a first-person user turn. Product self-name (会話 / Kaiwa) is rejected as a learner name. The tutor prompt has hard identity slots (self = 会話 / Kaiwa; learner = stored name or あなた; other names are third parties). Tutor prompt `PROMPT_REVISION` **10** (#144/#147/#148/#149/#150). Injected into the tutor prompt on top of the selected personality. `GET/PUT /api/memory`.

Practice is a **Start** sitting from Chat struggle cards (`GET /api/practice/today`, `POST /api/practice/sitting/start|turn|finish`). Product spec: [PRACTICE.md](PRACTICE.md) (#127–#134, #139–#140, #142–#143, #148, #150). Detection and storage stay here. Phase 10: Chat recast is live (**10.1**, #137/#145/#148 — splice if retry still misses; を→が plus 眠り/眠い; `[this_turn]` keep-form); recast notice is live (**10.2**, #138); sittings are rehearsal of the snapshot pair (**10.3**, #139 — say-this + one exchange, cap 2); wrap TTS then auto-return to Chat with a one-shot Chat elicit (**10.4**, #140/#146); Practice home lists recently practiced speakable lines (**10.5**, #142/#148); Learn tab queues a sitting from clustered Chat lines or canned starters (**10.6**, #143/#148).

**Live write gate (9.1 + 9.5–9.7):** after a Chat or Simpler turn, snapshot when rescue / `help_request` (unconditional), a conservative `struggling` filter, a freeze, or a meaning-changing recast restatement (`maybe_write_card` in `practice/cards.py`). Natural short answers (`はい。` / `パスタ。` when that was the question) are flowing in Chat too (#147). Struggling writes only for unsolicited English-heavy turns, repeated minimal answers that are not natural replies, or an abandoned JP attempt (one turn late: previous fragment, current retreat, low overlap). Freeze: transcribed fillers (`えっと` / `um`), punctuation-only, survival they already said (`もう一回お願いします`), or empty Whisper on a real-length clip (not too-short tap, not identity dumps). Empty Chat STT returns `{heard:false, type_retry:true}` (HTTP 200) so the type row can take over — no fake tutor turn, no dead 400 (#148). Skip if there is no prior assistant. Survival cards exist but never win `newest_unused` / today. Help / English / fake-yes / freeze cards whose `display_line` is empty, English-heavy, ごめん / そうなんだ, a tutor-only fragment, or a gloss like 「眠い」は sleepy。 also lose Today / Learn (`practice_worthy_line` / `is_practice_worthy`); recast-family (`is_recast_family_line`) wins when present, else canned が好き (#150). Correction: learner `を好き` (also わかる / ほしい / できる) and this-turn tutor reply contains `が` + the same stem **or its kana/kanji variant**, or a closed word-family miss (`眠り`/`眠い`) — speakable is the swapped learner line. Not STT typos (`お好き`, `わたし`/`私`). Never rebuild from extract `grammar_add`. Simpler looks back for the learner line. Light dedupe: same session + learner line. Cards are append-only (`profiles/<id>/struggle_cards.jsonl`); used ids live in `practice_state.json` — never mutate the card body. Sittings are RAM + that sidecar, not `sessions/*.jsonl`, not the Chats drawer.

**APIs:** `GET /api/practice/today`, sitting start / turn / finish. Sitting payloads include resolved `speakable` (`display_line`: stored speakable, else first `。` sentence of tutor reply, else learner line). Sitting UI shows that line; Why? is a canned one-liner from the snapshot. Home omits today’s unused line. `today` also returns `lines` — recently practiced speakable from `used_card_ids` (newest first, deduped, cap 5; `{ "speakable" }` only; includes finished Learn starters). `GET /api/learn/today` returns clustered Chat lines or canned starters (`source` + `{ "speakable", "card_id" }`). `POST /api/practice/sitting/start` may include `{ "card_id" }` (Chat snapshot or `learn:…` starter) — that **replaces** an in-progress sitting; empty body **resumes** today’s sitting if one is mid-flight, else today’s pick. Leftover `GET /api/practice/next` and `POST /api/practice` score are unused by the UI. `POST /api/practice/speak` remains for Chat **Replay**.

**Empty today (9.8 / #148 / #150):** unused practice-worthy Chat card always wins (recast-family first). Freeze/survival leftover and speakable junk do **not** win today. If none, a canned sitting from `FALLBACK_CARDS` in `practice/sitting.py` — first unused is `fallback:suki` (`コーヒーが好きです。` / tutor `コーヒーが好き？`), then again, then `えっと…`. Fallbacks are **not** appended to `struggle_cards.jsonl` and are not the old phrase-bank catalog. Recycle fallbacks only — never auto-replay used Chat cards. `available` is true whenever a sitting can start; `fallback: true` is home copy only (do not expose `signal` / tags). `POST /api/practice/sitting/start` does not 404 on empty JSONL. Never the primary source (#134).

Do not infer “avoided a structure.” Survival is not a Practice home tile.

Chat UI **Replay** re-plays the last TTS reply from a client cache (falls back to `POST /api/practice/speak` if audio was lost after refresh). Chat **Again** is a different control: it starts a child session that re-asks the same Kaiwa questions (`replay_of`).

Placement APIs: `POST /api/quiz/start`, `/api/quiz/answer`, `/api/quiz/finish` (self-assessment; no `/speak`). Last Place me item is optional preferred name (reading allowed, e.g. `Eli / イーライ`); blank does not clear an existing Settings name.

User-named presets live in the active profile’s `user_personalities.json` with CRUD:

- `GET /api/personalities`
- `POST /api/personalities`
- `PUT /api/personalities/{id}`
- `DELETE /api/personalities/{id}`

Also: `GET /api/prefs`, `PUT /api/prefs`.

### User profiles (named learner state)

A **profile** is one learner’s Kaiwa state (not an account): prefs, learner profile, memory, and custom personalities. Registry: `%LocalAppData%\Kaiwa\profiles.json`; files under `profiles/<id>/`. On first launch with empty AppData, Kaiwa **copies** legacy repo `data/` (+ `sessions/`) once if present; otherwise creates a fresh `default` profile. Flat legacy `*.json` at the user-data root still fold into `profiles/default/`. Chat sessions stay in the global AppData `sessions/` folder with `profile_id` in `.meta.json` (export still omits transcripts). Switching clears the browser chat session id; the **Chats** list is per active profile.

API:

- `GET /api/profiles` — list + `active_id`
- `POST /api/profiles` — create (`label`, optional `activate`)
- `POST /api/profiles/{id}/activate` — switch active; returns prefs/profile/memory for UI refresh
- `DELETE /api/profiles/{id}` — refuse if last; auto-switch if deleting active
- `POST /api/profiles/{id}/reset` — wipe four files to defaults (keep id/label)
- `GET /api/profiles/{id}/export` — versioned `kaiwa-profile` JSON download
- `POST /api/profiles/import` — JSON body or multipart file; always creates a new profile
- `GET /api/sessions` — Chat session metas for the active profile
- `POST /api/sessions` — same as `POST /api/chat/new` (durable new id; keeps old JSONL)
- `GET /api/sessions/{id}` — meta + hydrated messages (409 if another profile); Chat UI redraws bubbles from this on load and from the **Chats** drawer
- `POST /api/sessions/{id}/replay` — child session (`replay_of`) that re-asks stored Kaiwa questions; seeds the first question + TTS
- `GET /api/sessions/{id}/leftovers` — unique recent learner lines from a hydrated thread (cap 5); optional Flash alternatives (soft-fail → empty). Does not write SRS / recycle / memory.

Replies are cleaned of stage-direction emotes (`(smiles)`, `*claps*`, etc.) before chat display and TTS.

Chat turns log `timing: {stt_ms, llm_ms, tts_ms, total_ms}` in session JSONL and return it on `/api/turn`. Summarize with `scripts/eval_turn_latency.py`.

### Phase 8 — Keep talking

See `docs/ROADMAP.md`.

- **8.1 shipped:** pre-N5 reply shape — one idea (not one `。`); high-load constructions; one retry; JSONL `reply_shape`. Easy is easy-to-answer conversation with a next-turn hook, not a yes/no survey (#126). Lock decays with pitch / support (`flow_streak`). Shape-locked Chat finishes LLM before sentence TTS.
- **8.2 shipped:** **Simpler** on the last Kaiwa bubble (`POST /api/rescue`). No fake user line. Comprehension scaffolding bump; rewrite last assistant one step down (packed → shorter; already-short yes/no stays shorter, not A/B; #147); TTS; JSONL `rescue: true`. PTT has no Rescue hotkey.
- **8.3 shipped:** sessions bound to `profile_id` via `<id>.meta.json`; hydrate RAM from JSONL (rescue replaces last assistant); `GET/POST /api/sessions` + durable **New chat** (keeps old JSONL). Prompt-revision starts a new session per profile (New chat / `chat_reset`).
- **8.4 shipped:** **Chats** drawer lists the active profile; open or refresh redraws You/Kaiwa bubbles from `GET /api/sessions/{id}`. Stale `prompt_revision` no longer mints on a turn — opening an old chat continues that id with the current prompt + last-16 (#118).
- **8.5 shipped:** **Again** forks a child session (`replay_of`) that re-asks the parent’s Kaiwa questions (no new teaching; Simpler still allowed). Distinct from TTS **Replay** and Practice shadowing (#119). Does not bump `PROMPT_REVISION`.
- **8.7 shipped:** after **New chat**, **From this chat** shows 3–5 unique recent learner lines from the ended thread. Optional Flash **You could have said** (1–3, no stars, no `TRY:`) is a follow-up GET and soft-fails empty. Never live in Chat bubbles. Not SRS (#120). Does not bump `PROMPT_REVISION`.
- **8.6 shipped:** Chat **Easy** / **Free** chip (`prefs.chat_pace`, default Easy). Easy keeps the 8.1 shape lock (conversation, not yes/no gym; #126). Free turns off `shape_lock_active` (no gym retry); **Simpler** and internal support still run. Quiet session `turn_count` by the composer. No XP. Does not bump `PROMPT_REVISION` (#121).
- **Prompt revision (#115):** `PROMPT_REVISION` + AppData stamp; new empty chat on bump (memory kept). LLM sees last **16 messages** (not 16 turns).
- **10.1 shipped:** Chat recast-in-speech (`PROMPT_REVISION` **10**, #137/#144/#145/#147/#148/#149/#150/#151). を→が and 眠り/眠い hint + one retry; if retry still misses, speak **only** the canned model sentence (no leftover). `[this_turn]` keeps recast stems (not the elicit speakable). Recast/elicit turns do not roast. Stream buffers those turns. Rescue / Practice sittings do not recast-retry. Collapse is paraphrase of the same idea (no 選択肢); A/B stays last-resort Simpler. 楽しみ is not 眠い. No live `TRY:`.
- **10.2 shipped:** tiny **Notice this** caption of the same spoken recast sentence under the Kaiwa bubble (`recast_phrase`, #138/#145). Not TTS, not LLM history; session GET attaches at read time. Rescue / Practice sittings have no caption.
- **10.3 shipped:** Practice sitting is rehearsal — say the speakable line, one tiny exchange, then wrap (`MAX_LEARNER_TURNS` 2, #139/#149). Same home. Why? is a canned one-liner. Sitting prompt does not prepend Chat `IDENTITY_BLOCK`. Does not bump Chat `PROMPT_REVISION` by itself.
- **10.4 shipped:** sitting finishes after wrap TTS and returns to Chat (#140/#146/#149/#150). Next Chat turn `[elicit]`s a hook whose answer is the rehearsed form — does not speak that line first. Recast snapshot is today’s sitting; freeze leftover and speakable junk never win today; 9.8 starts with が好き.
- **10.5 shipped:** Practice home **Things you can say** from used sittings (`lines` on today payload, cap 5, #142/#148). Includes finished Learn starters. No tap.
- **10.6 shipped:** Learn tab (`GET /api/learn/today`) queues existing sittings from clustered Chat lines or canned starters (#143/#148/#150). Skip freeze/survival and speakable junk; recast-family ranks first. Explicit `card_id` replaces an in-progress sitting. ~20-min generated lessons / N5 overlay still later.

Silent freeze can raise `struggle_streak` via Simpler. A following `rescue: true` JSONL line is the live assistant text when hydrating. Hydrate always tags that row so recast captions skip Simpler (#149).

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

User data stays under `%LocalAppData%\Kaiwa\`. **Hardware:** `WHISPER_DEVICE=auto` prefers CUDA when a GPU and nvidia wheels are present, else CPU (`int8`). Owners: `pip install -e ".[cuda]"`. The portable runtime is CPU unless CUDA wheels are added. Dev-only: `build_desktop.ps1 -DevVenv` points the shell at the clone `.venv`.

**Installer:** `scripts/build_installer.ps1` (Inno Setup 6) packs `dist/Kaiwa/` into `dist/KaiwaSetup-*.exe` — Program Files install, Start Menu shortcut, Add/Remove Programs uninstall. Uninstall does **not** delete AppData. The GitHub Release Setup.exe is the install path (portable folder remains a build intermediate).

**Updates (6.9):** UI calls `/api/updates/check` (GitHub Releases latest; 24h AppData cache). When newer, a banner + Settings → About offer **Update now**, which downloads `KaiwaSetup-*.exe` to `%LocalAppData%\Kaiwa\downloads\updates\` and launches it (`os.startfile`). Desktop log: `%LocalAppData%\Kaiwa\Kaiwa.desktop.log`.

## Out of scope (v0)

- Pronunciation dictionary / absolute pitch-accent grading (NHK / MARINE H–L)
- Mobile app stores
- Multi-user / accounts / cloud sync
- Cloning Pingo’s full scenario catalog
- Running DeepSeek V4-Pro locally
