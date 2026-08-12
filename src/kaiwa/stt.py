from __future__ import annotations

import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

from kaiwa.bootstrap import DEFAULT_WHISPER_MODEL, whisper_model_dir, whisper_ready
from kaiwa.config import Settings

_log = logging.getLogger("kaiwa.stt")

_model: WhisperModel | None = None
_model_key: tuple[str, str, str, str] | None = None
_runtime_info: dict[str, Any] = {
    "requested": "auto",
    "active_device": "",
    "active_compute": "",
    "reason": "not_loaded",
    "local_model": False,
    "cuda_available": False,
}


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


def _nvidia_libs_present() -> bool:
    for entry in sys.path:
        root = Path(entry) / "nvidia"
        if root.is_dir() and any(root.rglob("bin")):
            return True
    return False


def probe_cuda() -> dict[str, Any]:
    """Return whether CUDA Whisper is usable on this machine/runtime."""
    _ensure_nvidia_dll_path()
    try:
        import ctranslate2
    except ImportError:
        return {
            "available": False,
            "reason": "no_ctranslate2",
            "device_count": 0,
        }

    try:
        count = int(ctranslate2.get_cuda_device_count())
    except Exception as exc:
        return {
            "available": False,
            "reason": f"cuda_probe_failed:{exc.__class__.__name__}",
            "device_count": 0,
        }

    if count <= 0:
        return {
            "available": False,
            "reason": "no_gpu",
            "device_count": 0,
        }

    # Friend portable runtime may lack nvidia-* wheels even with a GPU present.
    if sys.platform == "win32" and not _nvidia_libs_present():
        return {
            "available": False,
            "reason": "no_cuda_libs",
            "device_count": count,
        }

    gpu_name = ""
    try:
        # Optional; not all CT2 builds expose this.
        get_name = getattr(ctranslate2, "get_cuda_device_name", None)
        if callable(get_name):
            gpu_name = str(get_name(0) or "")
    except Exception:
        gpu_name = ""

    out: dict[str, Any] = {
        "available": True,
        "reason": "cuda_ok",
        "device_count": count,
    }
    if gpu_name:
        out["gpu_name"] = gpu_name
    return out


def resolve_whisper_device(settings: Settings) -> tuple[str, str, str]:
    """Return (device, compute_type, reason)."""
    requested = (settings.whisper_device or "auto").strip().lower() or "auto"
    env_compute = (settings.whisper_compute_type or "").strip().lower()

    if requested == "cpu":
        compute = (
            env_compute
            if env_compute and env_compute not in {"float16", "float32"}
            else "int8"
        )
        return "cpu", compute, "forced_cpu"

    probe = probe_cuda()
    want_cuda = requested in {"cuda", "auto"}
    if want_cuda and probe.get("available"):
        compute = env_compute or "float16"
        if compute == "int8" and requested == "auto":
            compute = "float16"
        return "cuda", compute, str(probe.get("reason") or "cuda_ok")

    reason = "forced_cpu"
    if requested == "cuda":
        reason = str(probe.get("reason") or "cuda_unavailable")
    elif requested == "auto":
        reason = str(probe.get("reason") or "cpu_fallback")
    else:
        reason = f"unknown_device:{requested}"

    compute = "int8"
    if env_compute and env_compute not in {"float16", "float32"}:
        compute = env_compute
    return "cpu", compute, reason


def get_stt_runtime_info() -> dict[str, Any]:
    """Snapshot of last resolved / loaded Whisper path (for /api/health)."""
    info = dict(_runtime_info)
    probe = probe_cuda()
    info["cuda_available"] = bool(probe.get("available"))
    info["cuda_reason"] = str(probe.get("reason") or "")
    if probe.get("gpu_name"):
        info["gpu_name"] = probe["gpu_name"]
    info["cuda_device_count"] = int(probe.get("device_count") or 0)
    return info


def _model_path_and_flags(settings: Settings) -> tuple[str, bool]:
    """Prefer AppData bootstrap cache; fall back to hub id if not bootstrapped."""
    model_id = (settings.whisper_model or DEFAULT_WHISPER_MODEL).strip() or DEFAULT_WHISPER_MODEL
    if whisper_ready(model_id):
        return str(whisper_model_dir(model_id)), True
    as_path = Path(model_id)
    if as_path.is_dir() and (as_path / "model.bin").is_file():
        return str(as_path), True
    return model_id, False


def get_model(settings: Settings) -> WhisperModel:
    global _model, _model_key, _runtime_info
    model_ref, local_only = _model_path_and_flags(settings)
    device, compute_type, reason = resolve_whisper_device(settings)
    key = (
        model_ref,
        device,
        compute_type,
        "local" if local_only else "hub",
    )
    if _model is None or _model_key != key:
        download_root = (
            None if local_only else str(whisper_model_dir(settings.whisper_model))
        )
        active_device = device
        active_compute = compute_type
        active_reason = reason
        try:
            _model = WhisperModel(
                model_ref,
                device=device,
                compute_type=compute_type,
                download_root=download_root,
                local_files_only=local_only,
            )
        except Exception as exc:
            if device != "cpu":
                _log.warning(
                    "CUDA Whisper load failed (%s); falling back to CPU",
                    exc.__class__.__name__,
                )
                _model = WhisperModel(
                    model_ref,
                    device="cpu",
                    compute_type="int8",
                    download_root=download_root,
                    local_files_only=local_only,
                )
                active_device = "cpu"
                active_compute = "int8"
                active_reason = f"cuda_load_failed:{exc.__class__.__name__}"
            else:
                raise
        _model_key = key
        _runtime_info = {
            "requested": (settings.whisper_device or "auto").strip().lower() or "auto",
            "active_device": active_device,
            "active_compute": active_compute,
            "reason": active_reason,
            "local_model": local_only,
            "cuda_available": bool(probe_cuda().get("available")),
        }
        _log.info(
            "Whisper ready device=%s compute=%s reason=%s local=%s",
            active_device,
            active_compute,
            active_reason,
            local_only,
        )
    return _model


def _join_segments(segments) -> str:
    return "".join(seg.text for seg in segments).strip()


_JP_SCRIPT_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def _jp_script_count(text: str) -> int:
    return len(_JP_SCRIPT_RE.findall(text or ""))


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


def transcribe_chat_file(
    settings: Settings, path: str | Path
) -> tuple[str, dict[str, Any]]:
    """Chat STT: keep clear English; accept first-pass JP when confident or script-rich.

    Forced ``language=ja`` alone would "translate" English speech into Japanese.
    Auto-detect first. Second pass only when the first pass is empty, not clear EN,
    and lacks Japanese script (decision #103).
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
    base_meta: dict[str, Any] = {
        "detected": detected or "",
        "prob": round(prob, 3),
    }

    if detected == "en" and prob >= 0.55 and auto_text:
        return auto_text, {**base_meta, "passes": 1, "accepted": "en"}

    if detected == "ja" and auto_text and prob >= 0.55:
        return auto_text, {**base_meta, "passes": 1, "accepted": "ja"}

    # Whisper often mis-tags learner JP as zh/ko/etc.; keep if script is clearly JP.
    if auto_text and _jp_script_count(auto_text) >= 2:
        return auto_text, {**base_meta, "passes": 1, "accepted": "jp_script"}

    forced = transcribe_file(settings, path, language="ja")
    return forced, {**base_meta, "passes": 2, "accepted": "forced_ja"}


def transcribe_audio_bytes(
    settings: Settings,
    data: bytes,
    suffix: str = ".webm",
    *,
    mode: str = "ja",
) -> tuple[str, dict[str, Any]]:
    """Write upload bytes to a temp file and transcribe.

    mode:
      - ``ja`` — force Japanese (Practice)
      - ``chat`` — auto-detect English vs Japanese (Chat)

    Returns ``(transcript, stt_meta)`` where meta includes ``passes`` / ``accepted``.
    """
    if not data or len(data) < 256:
        raise ValueError(
            "Audio clip was empty or too short — hold to talk a bit longer, then release"
        )
    if not suffix.startswith("."):
        suffix = "." + suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        if mode == "chat":
            return transcribe_chat_file(settings, tmp_path)
        text = transcribe_file(settings, tmp_path, language="ja")
        return text, {"passes": 1, "detected": "ja", "accepted": "forced_ja"}
    except Exception as exc:
        msg = str(exc)
        # PyAV / FFmpeg EOF on truncated MediaRecorder webm (common on tiny holds / WebView2)
        if "541478725" in msg or "End of file" in msg or "Invalid data" in msg:
            raise ValueError(
                "Couldn't read that recording — hold a little longer and speak clearly, then release"
            ) from exc
        raise
    finally:
        tmp_path.unlink(missing_ok=True)


def write_wav_mono(path: Path, samples: np.ndarray, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), samples, sample_rate)
