from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

from kaiwa.config import Settings

_model: WhisperModel | None = None
_model_key: tuple[str, str, str] | None = None


def _ensure_nvidia_dll_path() -> None:
    """Make pip-installed CUDA DLLs (cublas, etc.) visible on Windows."""
    if sys.platform != "win32":
        return
    candidates: list[Path] = []
    for entry in sys.path:
        root = Path(entry) / "nvidia"
        if root.is_dir():
            candidates.append(root)
    for nvidia_root in candidates:
        for bin_dir in nvidia_root.rglob("bin"):
            if not bin_dir.is_dir():
                continue
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(str(bin_dir))
                except OSError:
                    pass


_ensure_nvidia_dll_path()


def get_model(settings: Settings) -> WhisperModel:
    global _model, _model_key
    key = (settings.whisper_model, settings.whisper_device, settings.whisper_compute_type)
    if _model is None or _model_key != key:
        device = settings.whisper_device
        compute_type = settings.whisper_compute_type
        try:
            _model = WhisperModel(
                settings.whisper_model,
                device=device,
                compute_type=compute_type,
            )
        except Exception:
            # Fall back to CPU if CUDA stack is unavailable.
            _model = WhisperModel(
                settings.whisper_model,
                device="cpu",
                compute_type="int8",
            )
        _model_key = key
    return _model


def _join_segments(segments) -> str:
    return "".join(seg.text for seg in segments).strip()


def transcribe_file(
    settings: Settings,
    path: str | Path,
    *,
    language: str | None = "ja",
) -> str:
    """Transcribe audio. Pass language=None to auto-detect."""
    model = get_model(settings)
    kwargs: dict = {
        "vad_filter": True,
        "beam_size": 1,
    }
    if language:
        kwargs["language"] = language
    segments, _info = model.transcribe(str(path), **kwargs)
    return _join_segments(segments)


def transcribe_chat_file(settings: Settings, path: str | Path) -> str:
    """Chat STT: keep clear English as English; otherwise force Japanese.

    Forced ``language=ja`` alone would "translate" English speech into Japanese.
    Auto-detect first; if English with decent confidence, keep that transcript.
    Otherwise re-run with Japanese for better learner JP accuracy.
    """
    model = get_model(settings)
    segments, info = model.transcribe(
        str(path),
        vad_filter=True,
        beam_size=1,
    )
    auto_text = _join_segments(segments)
    detected = (getattr(info, "language", None) or "").lower()
    prob = float(getattr(info, "language_probability", 0.0) or 0.0)

    if detected == "en" and prob >= 0.55 and auto_text:
        return auto_text

    # Japanese or uncertain → force ja (accented learner speech)
    if detected == "ja" and auto_text and prob >= 0.7:
        return auto_text

    return transcribe_file(settings, path, language="ja")


def transcribe_audio_bytes(
    settings: Settings,
    data: bytes,
    suffix: str = ".webm",
    *,
    mode: str = "ja",
) -> str:
    """Write upload bytes to a temp file and transcribe.

    mode:
      - ``ja`` — force Japanese (Practice)
      - ``chat`` — auto-detect English vs Japanese (Chat)
    """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        if mode == "chat":
            return transcribe_chat_file(settings, tmp_path)
        return transcribe_file(settings, tmp_path, language="ja")
    finally:
        tmp_path.unlink(missing_ok=True)


def write_wav_mono(path: Path, samples: np.ndarray, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), samples, sample_rate)
