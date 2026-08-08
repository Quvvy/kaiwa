# Kaiwa

Personal Japanese AI conversation partner — turn-based chat, Practice, and a self-assessment placement check.

**Repo:** [github.com/Quvvy/kaiwa](https://github.com/Quvvy/kaiwa) (`E:\cursor\kaiwa`)  
**Wiki:** tagged `kaiwa` in `C:\Users\elifs\Projects\llm-wiki`

## Stack

```
Chat:     Mic → faster-whisper (ja, CUDA) → DeepSeek V4 Flash → AivisSpeech (or VOICEVOX)
Practice: Target → TTS preview → Mic → Whisper → intelligibility score → tip
Quiz:     Self-assessment placement (stage / listening / speaking / pace) → profile + goal
```

| Layer | Choice |
|-------|--------|
| STT | Local `faster-whisper` `large-v3-turbo` on RTX 3090 |
| LLM | `deepseek-v4-flash` (thinking disabled by default) |
| TTS | **AivisSpeech** default (`:10101`); **VOICEVOX** fallback (`:50021`) |
| Practice score | Kana-normalized similarity (not pitch accent) |
| Tutor prefs | Goals, Immersion/Adaptive, Formal/Casual, naturalness, personalities, TTS engine/voice, Flash/Pro routing |
| Learner profile | Live speaking/comprehension estimates (auto-updating) |
| Long-term memory | Comfort prefs, topics, vocab, grammar (auto-updating) |
| App | FastAPI + Chat / Practice / Place me / Settings tabs at `/` |

## Setup

1. Copy `.env.example` → `.env` and set `DEEPSEEK_API_KEY`.
2. Create venv and install:

```powershell
cd E:\cursor\kaiwa
python -m venv .venv
.\.venv\Scripts\pip install -e .
```

3. Install/start TTS (pick one; AivisSpeech is the default in Settings):

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

4. Smoke tests (optional):

```powershell
.\.venv\Scripts\python.exe scripts\smoke_llm.py
.\.venv\Scripts\python.exe scripts\smoke_tts.py
.\.venv\Scripts\python.exe scripts\smoke_tts.py --engine voicevox
.\.venv\Scripts\python.exe scripts\smoke_stt.py
.\.venv\Scripts\python.exe scripts\smoke_practice.py
.\.venv\Scripts\python.exe scripts\eval_turn_latency.py
```

5. Run the app:

**Desktop app (recommended on Windows):**

```powershell
.\.venv\Scripts\pip install -e ".[desktop]"
.\scripts\build_desktop.ps1
# then launch:
.\dist\Kaiwa\Kaiwa.exe
```

- Builds a real **`Kaiwa.exe`** (windowed shell) so the taskbar shows Kaiwa, not Python.
- Whisper / FastAPI still run from `.venv` (see `dist\Kaiwa\Kaiwa.runtime.json`).
- Launch opens a splash, starts TTS + Kaiwa, then shows the UI.
- **Close the window** — stops Kaiwa + the TTS engine *we* started and exits (no tray).
- Unpin any old **Python 3.13** taskbar pin; pin `dist\Kaiwa\Kaiwa.exe` instead.
- Rebuild after desktop/icon changes: `.\scripts\build_desktop.ps1`

**Dev desktop (unfrozen, still shows as Python on the taskbar):**

```powershell
.\.venv\Scripts\pip install -e ".[desktop]"
.\.venv\Scripts\kaiwa-desktop
# or: .\.venv\Scripts\python.exe -m kaiwa.desktop
```

**Or run the server alone:**

```powershell
.\.venv\Scripts\python.exe -m kaiwa.app
```

Open **http://127.0.0.1:8787**

- **Chat** — hold to talk, free conversation; type a short line if Whisper misses you; **Replay** re-plays Kaiwa’s last line (status shows turn timing)
- **Practice** — optional warm-up: last reply / from our chats / say again; play model, hold to repeat (not a quiz)
- **Place me** — per-profile soft first-run (auto-open when new/reset; Skip anytime); expanded English self-ratings that shape how Kaiwa talks
- **Settings** — Profiles, Appearance, Tutor, Learning, Memory, Speech (searchable); themes, goals, corrections, TTS/PTT, learner profile, long-term memory

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

- Never commit `.env`.
- Whisper models download to the Hugging Face cache on first run.
- On Windows, `nvidia-cublas-cu12` / `nvidia-cudnn-cu12` are installed so CUDA Whisper works without a full CUDA Toolkit.
- Practice scores measure **what the app heard**, not native pitch accent.
- Phase 3 stays **turn-based** (no OpenAI Realtime); pitch-accent grading remains deferred.
- **Version:** `0.9.0` (pre-release). **Phase 4–5** done. **Phase 6 (in progress):** consumer prep → Windows GitHub **1.0.0** (slice 6.1 legal/version hygiene done). **Phase 7:** global push-to-talk shipped — see [docs/ROADMAP.md](docs/ROADMAP.md).
