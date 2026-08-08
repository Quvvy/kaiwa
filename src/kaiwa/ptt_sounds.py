"""Custom PTT blip-in / blip-out cues stored under the active profile."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from kaiwa.desktop.icons import asset_path
from kaiwa.profiles import active_profile_dir

Which = Literal["in", "out"]

MAX_BLIP_BYTES = 1_000_000
ALLOWED_EXTS = {".ogg", ".wav", ".mp3"}
_STEM = {"in": "ptt_blip_in", "out": "ptt_blip_out"}
_DEFAULT_ASSET = {"in": "ptt_blip_in.ogg", "out": "ptt_blip_out.ogg"}


def normalize_which(raw: str) -> Which:
    w = (raw or "").strip().lower()
    if w not in ("in", "out"):
        raise ValueError("which must be 'in' or 'out'")
    return w  # type: ignore[return-value]


def sounds_dir() -> Path:
    path = active_profile_dir() / "sounds"
    path.mkdir(parents=True, exist_ok=True)
    return path


def custom_blip_path(which: Which) -> Path | None:
    """Return existing custom file for the slot, if any."""
    stem = _STEM[which]
    for path in sorted(sounds_dir().glob(f"{stem}.*")):
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTS:
            return path.resolve()
    return None


def is_custom(which: Which) -> bool:
    return custom_blip_path(which) is not None


def bundled_blip_path(which: Which) -> Path | None:
    """Return bundled default blip path, or None if assets are missing from the install."""
    try:
        return asset_path(_DEFAULT_ASSET[which]).resolve()
    except FileNotFoundError:
        return None


def resolve_blip_path(which: Which) -> Path | None:
    custom = custom_blip_path(which)
    if custom is not None:
        return custom
    return bundled_blip_path(which)


def clear_custom_blip(which: Which) -> None:
    stem = _STEM[which]
    for path in list(sounds_dir().glob(f"{stem}.*")):
        if path.is_file():
            try:
                path.unlink()
            except OSError:
                pass


def _safe_ext(filename: str | None, content_type: str | None) -> str:
    name = (filename or "").strip().lower()
    suffix = Path(name).suffix.lower() if name else ""
    if suffix in ALLOWED_EXTS:
        return suffix
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in {"audio/ogg", "application/ogg", "audio/vorbis"}:
        return ".ogg"
    if ct in {"audio/wav", "audio/x-wav", "audio/wave"}:
        return ".wav"
    if ct in {"audio/mpeg", "audio/mp3"}:
        return ".mp3"
    raise ValueError("Blip must be .ogg, .wav, or .mp3")


def save_custom_blip(
    which: Which,
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> Path:
    if not data:
        raise ValueError("Empty audio upload")
    if len(data) > MAX_BLIP_BYTES:
        raise ValueError(f"Blip too large (max {MAX_BLIP_BYTES // 1000} KB)")
    ext = _safe_ext(filename, content_type)
    clear_custom_blip(which)
    dest = sounds_dir() / f"{_STEM[which]}{ext}"
    dest.write_bytes(data)
    return dest.resolve()


def blip_state() -> dict[str, object]:
    """Fields for /api/ptt/state. Never raises if bundled defaults are missing."""
    out: dict[str, object] = {}
    for which in ("in", "out"):
        w: Which = which  # type: ignore[assignment]
        custom = is_custom(w)
        path = resolve_blip_path(w)
        out[f"blip_{which}_custom"] = custom
        out[f"blip_{which}_path"] = str(path) if path is not None else ""
        out[f"blip_{which}_label"] = "Custom" if custom else "Default"
    return out
