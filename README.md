# Kaiwa

Personal Japanese AI conversation partner — turn-based chat, Practice, and a self-assessment placement check.

**Repo:** [github.com/Quvvy/kaiwa](https://github.com/Quvvy/kaiwa)  
**Version:** **1.0.3**

## For installation (Windows)

1. Download **`KaiwaSetup-1.0.3.exe`** from the [latest GitHub Release](https://github.com/Quvvy/kaiwa/releases/latest).
2. Run the installer → open **Kaiwa** from the Start Menu.
3. First launch may download a speech model (~1.5 GB) and voice engine (~200 MB) into `%LocalAppData%\Kaiwa\` (progress on the splash; relaunch resumes).
4. When asked, paste a [DeepSeek](https://platform.deepseek.com/) API key (saved under AppData, not in the install folder).
5. Optional soft **Place me** quiz; then talk in Chat. **NVIDIA GPU recommended** for faster speech recognition; CPU works.

If Kaiwa fails to start, details are in `%LocalAppData%\Kaiwa\Kaiwa.desktop.log`. When a newer release exists, Kaiwa can notify you and download/run the Windows Setup from Settings → About (or the update banner). Uninstall via Windows Apps keeps your key and models in `%LocalAppData%\Kaiwa\`.

## Stack

```
Chat:     Mic → faster-whisper (ja, CUDA) → DeepSeek V4 Flash → AivisSpeech (or VOICEVOX)
Practice: Target → TTS preview → Mic → Whisper → intelligibility score → tip
Quiz:     Self-assessment placement (stage / listening / speaking / pace) → profile + goal
```

| Layer | Choice |
|-------|--------|
| STT | Local `faster-whisper` `large-v3-turbo` (CUDA when available, else CPU) |
| LLM | `deepseek-v4-flash` (thinking disabled by default) |
| TTS | **AivisSpeech** default (`:10101`); **VOICEVOX** fallback (`:50021`) |
| Practice score | Kana-normalized similarity (not pitch accent) |
| Tutor prefs | Goals, Immersion/Adaptive, Formal/Casual, naturalness, personalities, TTS engine/voice, Flash/Pro routing |
| Learner profile | Live speaking/comprehension estimates (auto-updating) |
| Long-term memory | Comfort prefs, topics, vocab, grammar (auto-updating) |
| App | FastAPI + Chat / Practice / Settings tabs at `/` |

## Setup (developers / owners)

1. **API key:** On first launch Kaiwa asks for a DeepSeek API key (AppData `secrets.json`). Optional for owners: copy `.env.example` → `.env` and set `DEEPSEEK_API_KEY` (migrates once into AppData). Process env overrides.
2. **User data:** Profiles, prefs, memory, and session logs live under `%LocalAppData%\Kaiwa\`. Optional `KAIWA_DATA_DIR`. First launch also bootstraps Whisper + AivisSpeech into that folder.
3. Create venv and install:

```powershell
cd E:\cursor\kaiwa
python -m venv .venv
.\.venv\Scripts\pip install -e ".[desktop,cuda]"
```

4. Install/start TTS (pick one; AivisSpeech is the default in Settings):

```powershell
# AivisSpeech Engine (already under tools/aivisspeech if installed via agent)
.\.venv\Scripts\python.exe scripts\start_aivisspeech.py

# Or download Engine yourself from:
# https://github.com/Aivis-Project/AivisSpeech-Engine/releases
# Extract to tools/aivisspeech/engine/Windows-x64/ then run the start script.

# Or VOICEVOX fallback
winget install --id HiroshibaKazuyuki.VOICEVOX
.\.venv\Scripts\python.exe scripts\start_voicevox.py
```

In **Settings → TTS engine**, choose AivisSpeech or VOICEVOX to match what’s running.

Extra AivisSpeech voices (from AivisHub):

```powershell
.\.venv\Scripts\python.exe scripts\start_aivisspeech.py
.\.venv\Scripts\python.exe scripts\install_aivis_voices.py
```

5. Smoke tests (optional):

```powershell
.\.venv\Scripts\python.exe scripts\smoke_llm.py
.\.venv\Scripts\python.exe scripts\smoke_tts.py
.\.venv\Scripts\python.exe scripts\smoke_tts.py --engine voicevox
.\.venv\Scripts\python.exe scripts\smoke_stt.py
.\.venv\Scripts\python.exe scripts\smoke_practice.py
.\.venv\Scripts\python.exe scripts\smoke_reply_shape.py
.\.venv\Scripts\python.exe scripts\eval_turn_latency.py
```

6. Build desktop / installer:

```powershell
.\.venv\Scripts\pip install -e ".[desktop,desktop-build,cuda]"
.\scripts\build_desktop.ps1
# Installer (needs Inno Setup 6 — winget install JRSoftware.InnoSetup):
.\scripts\build_installer.ps1
# or portable without Setup:
.\dist\Kaiwa\Kaiwa.exe
```

- Builds a portable folder: thin **`Kaiwa.exe`** + private `runtime\` (CPU Python + deps) + `static\`.
- `build_installer.ps1` wraps that folder into `dist\KaiwaSetup-1.0.3.exe` (Start Menu + uninstall).
- Relative `Kaiwa.runtime.json` points at `runtime\Scripts\python.exe`. Shell sets `KAIWA_ROOT` for the API child.
- Dev shell-only rebuild (points at clone `.venv`): `.\scripts\build_desktop.ps1 -DevVenv`
- **Close the window** — stops Kaiwa + the TTS engine *we* started and exits (no tray).

**Dev desktop (unfrozen, still shows as Python on the taskbar):**

```powershell
.\.venv\Scripts\pip install -e ".[desktop,cuda]"
.\.venv\Scripts\kaiwa-desktop
# or: .\.venv\Scripts\python.exe -m kaiwa.desktop
```

**Or run the server alone:**

```powershell
.\.venv\Scripts\python.exe -m kaiwa.app
```

Open **http://127.0.0.1:8787**

- **Chat** — hold to talk, free conversation; type a short line if Whisper misses you; **Replay** re-plays Kaiwa’s last line; **Simpler** on Kaiwa’s last bubble says it more easily; **Easy** / **Free** picks the gym lock (Easy is the default); a quiet turn count sits by the status; **New chat** starts a fresh thread (keeps memory; past chats stay on disk) and may show **From this chat** leftovers; **Chats** lists and reopens this profile’s threads; **Again** re-asks this thread’s questions as a new chat
- **Practice** — optional warm-up: last reply / from our chats / say again; play model, hold to repeat (not a quiz)
- **Place me** — Settings section; per-profile soft first-run (auto-open when new/reset; Skip anytime); expanded English self-ratings that shape how Kaiwa talks
- **Settings** — Profiles, Appearance, Tutor, Learning, Place me, Memory, Speech (searchable); themes, goals, corrections, TTS/PTT, learner profile, long-term memory

Default port is **8787** (8765 often used by Anki on this machine).

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DECISIONS.md](docs/DECISIONS.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/WIKI_SYNC.md](docs/WIKI_SYNC.md)
- [CHANGELOG.md](CHANGELOG.md)
- [NOTICE.md](NOTICE.md)

## License

Kaiwa is **MIT** — see [LICENSE](LICENSE). Third-party speech engines, models, and Python deps are summarized in [NOTICE.md](NOTICE.md).

## Notes

- Never commit `.env` or AppData `secrets.json` / profile data.
- Whisper weights download on first launch into `%LocalAppData%\Kaiwa\models\whisper\` (splash progress).
- **NVIDIA GPU recommended** for faster speech recognition. Kaiwa defaults to `WHISPER_DEVICE=auto` (CUDA when a GPU and `.[cuda]` wheels are available, otherwise CPU). Owners: `pip install -e ".[desktop,cuda]"`. The portable runtime is **CPU-only** unless CUDA wheels are added.
- Practice scores measure **what the app heard**, not native pitch accent.
- Phase 3 stays **turn-based** (no OpenAI Realtime); pitch-accent grading remains deferred.
- **Version:** `1.0.3`. **Phase 4–5** done (incl. 5.5 comprehensibility-first Chat). **Phase 6:** 6.1–6.9 done (Windows GitHub release + in-app update checker). **Phase 7:** global push-to-talk shipped. **Phase 8.1–8.7** shipped (reply shape, Simpler, durable sessions, Chats drawer, Again, leftovers, Easy/Free). Chat / Practice / Settings share one desk; Place me is a Settings section; fifteen themes — see [docs/ROADMAP.md](docs/ROADMAP.md).
