# Kaiwa

Personal Japanese AI conversation partner — turn-based chat, Practice, and a self-assessment placement check.

**Repo:** [github.com/Quvvy/kaiwa](https://github.com/Quvvy/kaiwa) (`E:\cursor\kaiwa`)  
**Wiki:** tagged `kaiwa` in `C:\Users\elifs\Projects\llm-wiki`

## Stack

```
Chat:     Mic → faster-whisper (ja, CUDA) → DeepSeek V4 Flash → AivisSpeech (or VOICEVOX)
Practice: Target → TTS preview; Mic → Whisper → intelligibility score → tip
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

**Desktop (system tray, recommended on Windows):**

```powershell
.\.venv\Scripts\pip install -e ".[desktop]"
.\.venv\Scripts\kaiwa-desktop
# or: .\.venv\Scripts\python.exe -m kaiwa.desktop
```

- Tray icon only while idle (no Whisper / TTS / server).
- **Open Kaiwa** — starts the TTS engine from your Settings prefs (AivisSpeech or VOICEVOX), starts Kaiwa, opens a desktop window.
- **Close the window** — returns to tray and stops Kaiwa + the TTS engine *we* started.
- **Quit** (tray menu) — exits completely.

**Or run the server alone:**

```powershell
.\.venv\Scripts\python.exe -m kaiwa.app
```

Open **http://127.0.0.1:8787**

- **Chat** — hold to talk, free conversation; type a short line if Whisper misses you; **Replay** re-plays Kaiwa’s last line (status shows turn timing)
- **Practice** — optional warm-up: last reply / from our chats / say again; play model, hold to repeat (not a quiz)
- **Place me** — per-profile soft first-run (auto-open when new/reset; Skip anytime); expanded English self-ratings that shape how Kaiwa talks
- **Settings** — profiles (switch/backup), goals, corrections, language help, register, naturalness, personalities, TTS engine/voice, Flash/Pro routing, live learner profile, long-term memory

Default port is **8787** (8765 often used by Anki on this machine).

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DECISIONS.md](docs/DECISIONS.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/WIKI_SYNC.md](docs/WIKI_SYNC.md)

## Notes

- Never commit `.env`.
- Whisper models download to the Hugging Face cache on first run.
- On Windows, `nvidia-cublas-cu12` / `nvidia-cudnn-cu12` are installed so CUDA Whisper works without a full CUDA Toolkit.
- Practice scores measure **what the app heard**, not native pitch accent.
- Phase 3 stays **turn-based** (no OpenAI Realtime); pitch-accent grading remains deferred.
- **Next (Phase 4):** first-run onboarding, clearer TTS errors, gentler correction surfacing — see [docs/ROADMAP.md](docs/ROADMAP.md). Tray desktop launcher + profiles + soft phrase reuse are already in.
