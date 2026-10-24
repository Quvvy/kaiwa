# Changelog

All notable changes to Kaiwa are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [2.0.1] — 2026-10-24

### Changed

- **Calmer default voice.** Kaiwa now uses 凛音エル instead of AivisSpeech's built-in まお (median pitch about 280 Hz instead of 430 Hz), and it's also the clearest female voice measured. Anyone still on the old default is moved over once; a voice you picked yourself is kept.
- **Voices ship with Kaiwa.** First run downloads 凛音エル, ほのか (the lowest female voice), 阿井田 茂 (male) and にせ (the clearest for single words) from AivisHub, with progress on the splash screen. Existing installs fetch them on the next launch. Before, a fresh install only had まお.
- Dialogues pair 凛音エル with 阿井田 茂, then ほのか. The high voices (まお, コハク, 桜音, 花音) are no longer cast, and まお and コハク, which the engine can't uninstall, are hidden from Settings → Voice unless selected.
- Settings → Voice lists Kaiwa's voices under **Recommended**, with short names.

## [2.0.0] — 2026-10-24

Kaiwa is now a lesson-first course: a daily plan teaches, checks and reviews real phrases out loud, and the AI parts are built from what you have learned.

### Added

- **Daily lesson** as home: due reviews, a few new words and grammar points, a listening thread, and speak-it-back checks with one concrete fix. Kana track; units 1–20 in the full template; paced plan with two-day units, a new-item cap and catch-up days.
- **FSRS reviews** with automatic grades you can change or undo, produce-the-answer cards, leech handling, a same-day recap and a stats page.
- **Placement test** (adaptive, no multiple choice): separate by-ear and in-kana levels, imitation items, graduated hints; checks on placed units reopen lessons, and units can be skipped.
- **Extra listening**: stories and dialogues built from known words, checked for unknown grammar, the next one ready instantly; listening minutes counted.
- **Talk practice**: short spoken role-plays with a goal, one fix per turn, at your level.
- **Learner log**: a per-profile record of answers, typed mistakes, listening, help and sessions (stays on this PC; Settings → Data → Open the folder).
- **Voice engine watchdog**: restarts the voice engine if it stops, plus a **Restart voice** button.
- **Portable zip** (`Kaiwa-2.0.0-portable.zip`): no install; all data in `Data\` next to Kaiwa.exe.
- Kana model judges say-it-back attempts alongside Whisper; microphone picker.

### Changed

- The bundled runtime is the python.org embeddable Python, so Kaiwa runs on PCs without Python installed (1.x needed the build PC's Python).
- One Kaiwa window at a time: opening it again brings the open window forward, and a pinned Kaiwa no longer gets a second taskbar button.
- Installer: LZMA2 ultra compression, asks to close a running Kaiwa before updating, cleans out old 1.x files, starts Kaiwa as you rather than as administrator, offers a desktop icon, and on uninstall asks whether to delete your data (default: keep).
- Window opens about 3 s after launch instead of about 19 s; lesson audio cached on disk and pre-rendered a lesson ahead.
- Plainer UI and wording, grouped Settings with tooltips, Light/Dark theme setting; the first-run key screen explains what needs DeepSeek and can be skipped.
- One learner per profile, with backup export / import / reset (the learner log included).

## [1.0.3] — 2026-08-13

### Changed

- Phase **8.1**: pre-N5 Chat reply shape — one idea, reuse learner words, high-load constructions (not grammar bans), one retry, silent `reply_shape` session log (decision #114).
- Tutor prompt updates start a **new chat** (memory kept): `PROMPT_REVISION` stamp, last-16 LLM context, Chat **New chat** (decision #115).
- Phase **8.2**: **Simpler** on the last Kaiwa line — rewrite one step easier, keep memory, no fake “I don’t understand” turn (decision #116).
- Phase **8.3**: Chat sessions belong to a profile (meta + JSONL hydrate); **New chat** keeps the old file; `GET/POST /api/sessions` (decision #117).
- Phase **8.4**: **Chats** drawer lists this profile’s threads and redraws bubbles on load/open; stale prompt revision no longer mints a new id mid-turn (decision #118).
- Phase **8.5**: **Again** starts a child chat that re-asks this thread’s Kaiwa questions (`replay_of`); TTS **Replay** is unchanged (decision #119).
- Phase **8.7**: after **New chat**, **From this chat** shows phrases actually used in that thread; optional **You could have said** is Flash, soft-fail, and never live in Chat (decision #120).
- Phase **8.6**: Chat **Easy** / **Free** chip (default Easy) can turn off the pre-N5 gym lock; quiet turn count, no XP (decision #121).
- Chat UI flatten: one desk sheet on the dark room for Chat, Practice, and Settings; composer/save as a raised floor (decision #122).
- **Place me** moved from a top-level tab into Settings (decision #123).
- Themes: Dusk, Sage, Blush, Matcha, Paper, Ink, Indigo, Amber, Wisteria beside Night, Slate, Graphite, Day, Cloud, Frost (decision #79).

## [1.0.2] — 2026-08-11

### Changed

- Chat tutor system prompt restructured: numbered priority hierarchy with less duplication (behavior preserved; decision #101). Polish: broader Adaptive EN glosses; pitch ≠ ability; density/teach-one wording; internal-state disclaimer.
- Chat turn latency: reply returns after TTS without waiting for assess/extract; Auto→Pro only for heavier comprehension / critique streak (vocab stays Flash); status shows model used (decision #102).
- Chat STT: accept first-pass Japanese via lower confidence + kana/kanji heuristic (avoid double Whisper when possible); status shows `stt …×2` when a second pass ran (decision #103).
- Chat streams LLM text + sentence-by-sentence TTS over SSE (UI); status shows `ttfa`; PTT stays blocking full-turn JSON (decision #104).
- Chat shows a scrollable disclaimer that the first reply after launch may be slower and that replies can be wrong.

## [1.0.1] — 2026-08-08

### Changed

- Phase **5.5**: Chat is comprehensibility-first (conversation partner before tutor). Internal support ladder + help_type; density lock on incomprehension; JP teaches / EN rescues; scaffolding decays on success. Chat no longer shows “Try saying…” (`TRY:` retired from chat prompts; Practice remains the drill surface).

## [1.0.0] — 2026-08-08

### Added

- Phase **6.1**: MIT `LICENSE`, `NOTICE.md`, changelog; version path to **1.0.0**.
- Phase **6.2**: DeepSeek first-run API key gate; AppData `secrets.json`; Settings update; soft validate.
- Phase **6.3**: Profiles, prefs, and sessions under `%LocalAppData%\Kaiwa\`; one-time migrate-or-fresh from repo `data/` / `sessions/`; optional `KAIWA_DATA_DIR`.
- Phase **6.4**: Portable `dist/Kaiwa/` with private CPU `runtime\` + `static\`; relative `Kaiwa.runtime.json`; optional `[cuda]` extra; `-DevVenv` for shell-only rebuilds.
- Phase **6.5**: First-run bootstrap downloads Whisper weights + AivisSpeech Engine (AppData); splash progress; resume-safe.
- Phase **6.6**: Auto CUDA/CPU Whisper path; health reports device; NVIDIA GPU recommended.
- Phase **6.7**: Windows Inno Setup installer (`KaiwaSetup-1.0.0.exe`); Start Menu + uninstall (keeps AppData); plain-English splash errors; Place me after API key gate.
- Phase **6.8**: Tagged GitHub Release `v1.0.0` with Setup.exe attached; consumer README (Download → Install → paste DeepSeek key).
- Phase **6.9**: in-app update checker (GitHub Releases) with soft banner, Settings → About, and Windows download + launch of `KaiwaSetup-*.exe`.
- Phase 7 global push-to-talk (Windows desktop): bindable key/mouse, hold-to-talk, custom blip cues, hook heartbeat.
- Phase 5 tutor learning quality (prompt layers): JP-first help, micro-corrections, topic stickiness, difficulty governor.
- Settings IA: Profiles / Appearance / Tutor / Learning / Memory / Speech / About + search; themed blip volume slider.

### Changed

- Friends no longer need a repo `.env` for the DeepSeek key (AppData / first-run UI).
- Profiles and chat session logs live under AppData (not the repo `data/` / `sessions/` folders).
- Release desktop build no longer requires a developer `.venv` on the friend machine (bundled runtime).
- Windows CUDA Whisper packages moved to optional extra `[cuda]`.
- Default `WHISPER_DEVICE=auto` picks CUDA when available, else CPU; `/api/health` reports the active path.
- Friend install path is `KaiwaSetup-1.0.0.exe` from the GitHub Release (Start Menu); portable `dist/Kaiwa/` remains the build input.
- Frozen desktop log writes to `%LocalAppData%\Kaiwa\Kaiwa.desktop.log` (Program Files next to the exe is not writable).
- Desktop shell starts AivisSpeech using bootstrap.json `aivis_path` when filesystem probes miss the AppData engine.
- Bootstrap subprocess returns `aivis_path` over stdout JSON; frozen shell `Popen`s it without AppData `exists()` checks.
- Runtime package ships desktop `assets/*.ogg` (PTT blips); `/api/ptt/state` soft-fails if blips are missing; desktop PTT poll always heartbeats so `hook_alive` stays true.

## [0.9.0] — 2026-08-07

### Added

- Legal & version hygiene for consumer prep (LICENSE, NOTICE, changelog).
- Package / desktop metadata version set to `0.9.0` (pre-1.0.0 staging).
