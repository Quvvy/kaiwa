# Changelog

All notable changes to Kaiwa are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
