# Third-party notices

Kaiwa itself is MIT-licensed (see [LICENSE](LICENSE)). It depends on other projects. This is a plain-English summary for shipping or running Kaiwa — not a full dump of every transitive wheel. Prefer each package’s own metadata / upstream LICENSE for the authoritative text.

## Speech & models

| Component | Notes |
|-----------|--------|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT. Local speech-to-text wrapper around CTranslate2. |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT. Inference engine used by faster-whisper. |
| OpenAI Whisper weights (e.g. `large-v3-turbo`) | First-run bootstrap downloads into `%LocalAppData%\Kaiwa\models\whisper\`. Model use is subject to [OpenAI’s Whisper model license / terms](https://github.com/openai/whisper) as published upstream. |
| [Hugging Face Hub](https://huggingface.co/) | Used to fetch model files; subject to Hub and model-card terms for each artifact. |

## TTS engines (external apps)

Kaiwa talks to these over HTTP. The desktop bootstrap can **download AivisSpeech Engine 1.2.0** from GitHub into `%LocalAppData%\Kaiwa\tts\aivisspeech\` when no existing install is found:

| Engine | Notes |
|--------|--------|
| [AivisSpeech Engine](https://github.com/Aivis-Project/AivisSpeech-Engine) | Pinned asset: `AivisSpeech-Engine-Windows-x64-1.2.0.7z.001` from [release 1.2.0](https://github.com/Aivis-Project/AivisSpeech-Engine/releases/tag/1.2.0). See upstream license and AivisHub voice terms for any extra voices. |
| [VOICEVOX](https://voicevox.hiroshiba.jp/) / ENGINE | Optional fallback; not auto-installed; see VOICEVOX / character licenses. |

## Python libraries (runtime)

Installed via `pyproject.toml`. Typical licenses (confirm on PyPI / GitHub if redistributing):

| Package | Common license |
|---------|----------------|
| FastAPI, Starlette, Uvicorn | MIT / BSD-style |
| openai (API client) | Apache-2.0 |
| httpx, httpcore | BSD-3-Clause |
| numpy | BSD-3-Clause |
| soundfile | BSD-3-Clause |
| python-dotenv, python-multipart | BSD / Apache-style |
| pykakasi | GPL-3.0 (used for kana helpers — check if your redistribution needs care) |
| py7zr | LGPL-2.1+ (AivisSpeech Engine archive extract on first run) |
| pywebview (desktop extra) | BSD-3-Clause |
| pynput, sounddevice (desktop extra) | LGPL-3.0 / MIT — see package metadata |
| nvidia-cublas-cu12 / nvidia-cudnn-cu12 (Windows, optional `[cuda]`) | NVIDIA CUDA redistributable terms |

## NVIDIA

CUDA Math libraries on Windows are distributed under NVIDIA’s CUDA EULA / redistributable terms. An NVIDIA GPU is recommended for Whisper; Kaiwa aims to fall back to CPU when CUDA is unavailable (Phase 6.6).

## DeepSeek

Chat completions go to DeepSeek’s cloud API. Use of the API is governed by [DeepSeek’s terms](https://www.deepseek.com/) and your API key account — the key is never committed to this repo.

## UI assets

| Component | Notes |
|-----------|--------|
| [Fluent UI System Icons](https://github.com/microsoft/fluentui-system-icons) | MIT. Header **New chat** (`chat_add_20_regular`) and **Chats** (`chat_multiple_20_regular`) only. Vendored under `static/icons/fluent/`. |

## Questions

If you redistribute a packaged Kaiwa build, keep this file (or an equivalent notices bundle) with the installer, and include upstream licenses required by the wheels and engines you ship.
