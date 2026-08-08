# Third-party notices

Kaiwa itself is MIT-licensed (see [LICENSE](LICENSE)). It depends on other projects. This is a plain-English summary for friends shipping or running Kaiwa — not a full dump of every transitive wheel. Prefer each package’s own metadata / upstream LICENSE for the authoritative text.

## Speech & models

| Component | Notes |
|-----------|--------|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT. Local speech-to-text wrapper around CTranslate2. |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT. Inference engine used by faster-whisper. |
| OpenAI Whisper weights (e.g. `large-v3-turbo`) | Downloaded on first run into the Hugging Face cache. Model use is subject to [OpenAI’s Whisper model license / terms](https://github.com/openai/whisper) as published upstream. |
| [Hugging Face Hub](https://huggingface.co/) | Used to fetch model files; subject to Hub and model-card terms for each artifact. |

## TTS engines (external apps)

Kaiwa talks to these over HTTP. They are **not** bundled inside Kaiwa today (installer bootstrap is Phase 6.5):

| Engine | Notes |
|--------|--------|
| [AivisSpeech Engine](https://github.com/Aivis-Project/AivisSpeech-Engine) | Separate install; see upstream license and AivisHub voice terms for any voices you download. |
| [VOICEVOX](https://voicevox.hiroshiba.jp/) / ENGINE | Optional fallback; see VOICEVOX / character licenses for commercial or redistribution use. |

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
| pywebview (desktop extra) | BSD-3-Clause |
| pynput, sounddevice (desktop extra) | LGPL-3.0 / MIT — see package metadata |
| nvidia-cublas-cu12 / nvidia-cudnn-cu12 (Windows) | NVIDIA CUDA redistributable terms |

## NVIDIA

CUDA Math libraries on Windows are distributed under NVIDIA’s CUDA EULA / redistributable terms. An NVIDIA GPU is recommended for Whisper; Kaiwa aims to fall back to CPU when CUDA is unavailable (Phase 6.6).

## DeepSeek

Chat completions go to DeepSeek’s cloud API. Use of the API is governed by [DeepSeek’s terms](https://www.deepseek.com/) and your API key account — the key is never committed to this repo.

## Questions

If you redistribute a packaged Kaiwa build, keep this file (or an equivalent notices bundle) with the installer, and include upstream licenses required by the wheels and engines you ship.
