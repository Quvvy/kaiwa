"""Clips and screenshots for mined lines, kept per profile in <profile>/mined_media/.

Names are derived from the name the mining tool used (deterministic), so
storeMediaFile("asbp_x.mp3") and a later "[sound:asbp_x.mp3]" in a note field land
on the same file without an index. Only known audio/image types are kept, audio
must be readable and short, and nothing outside the folder is ever served.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

DIRNAME = "mined_media"
MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_IMAGE_BYTES = 6 * 1024 * 1024
MAX_CLIP_S = 30.0
ORPHAN_AFTER_S = 24 * 3600

AUDIO_EXT = {"mp3": "audio/mpeg", "m4a": "audio/mp4", "mp4": "audio/mp4", "aac": "audio/aac", "ogg": "audio/ogg",
             "opus": "audio/ogg", "oga": "audio/ogg", "webm": "audio/webm", "wav": "audio/wav", "flac": "audio/flac"}
IMAGE_EXT = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp",
             "gif": "image/gif", "avif": "image/avif"}
MIME = {**AUDIO_EXT, **IMAGE_EXT}
NAME_RE = re.compile(r"^[0-9a-f]{12}-[A-Za-z0-9_-]{0,40}\.(" + "|".join(MIME) + r")$")


class MediaError(ValueError):
    pass


def media_dir(state_path: Path | None = None) -> Path:
    if state_path is None:
        from kaiwa.profiles import active_profile_dir

        base = active_profile_dir()
    else:
        base = Path(state_path).parent
    path = base / DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def ext_of(original: str) -> str:
    return Path(str(original or "")).suffix.lower().lstrip(".")


def kind_of(original: str) -> str | None:
    ext = ext_of(original)
    return "audio" if ext in AUDIO_EXT else "image" if ext in IMAGE_EXT else None


def safe_name(original: str) -> str:
    """A stable, safe file name for whatever the tool called it."""
    original = str(original or "").strip()
    ext = ext_of(original)
    if ext not in MIME:
        raise MediaError(f"Kaiwa keeps audio and images only, not .{ext or '?'} files")
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(original).stem).strip("-")[:40]
    digest = hashlib.sha1(original.encode("utf-8")).hexdigest()[:12]
    return f"{digest}-{stem}.{ext}"


def _decode(data: str) -> bytes:
    try:
        return base64.b64decode(str(data or ""), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise MediaError("media data isn't valid base64") from exc


_IMAGE_MAGIC = (b"\xff\xd8\xff", b"\x89PNG", b"GIF8")


def _image_ok(blob: bytes) -> bool:
    if blob.startswith(_IMAGE_MAGIC):
        return True
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return True
    return blob[4:12] in (b"ftypavif", b"ftypavis")


def probe_seconds(blob: bytes) -> float:
    """How long a clip plays. Raises MediaError if it can't be read as audio."""
    import av

    try:
        with av.open(io.BytesIO(blob)) as container:
            if not container.streams.audio:
                raise MediaError("that file has no sound")
            if container.duration:
                return container.duration / 1_000_000
            # MediaRecorder webm has no duration in its header: add up what decodes.
            total = 0.0
            for frame in container.decode(audio=0):
                total += frame.samples / float(frame.sample_rate or 48000)
                if total > MAX_CLIP_S:
                    break
            return total
    except MediaError:
        raise
    except Exception as exc:  # PyAV raises many kinds for junk input
        raise MediaError("Kaiwa couldn't read that audio clip") from exc


def store(base: Path, original: str, data: str) -> tuple[str, dict[str, int]]:
    """Save a base64 file under its safe name. Returns (name, {"audio_ms": …} for audio)."""
    name = safe_name(original)
    kind = kind_of(original)
    blob = _decode(data)
    if not blob:
        raise MediaError("that file is empty")
    meta: dict[str, int] = {}
    if kind == "audio":
        if len(blob) > MAX_AUDIO_BYTES:
            raise MediaError("that clip is too big for one card")
        seconds = probe_seconds(blob)
        if seconds > MAX_CLIP_S:
            raise MediaError(f"that clip is over {int(MAX_CLIP_S)} seconds: mine one or two lines at a time")
        meta["audio_ms"] = int(seconds * 1000)
    else:
        if len(blob) > MAX_IMAGE_BYTES:
            raise MediaError("that image is too big")
        if not _image_ok(blob):
            raise MediaError("that image isn't a JPEG, PNG, WebP, GIF or AVIF")
    fd, tmp = tempfile.mkstemp(dir=base, prefix=".up-", suffix="." + ext_of(original))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(blob)
        os.replace(tmp, base / name)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return name, meta


def path_for(base: Path, name: str) -> Path | None:
    """The file for a stored name, or None. Never anything outside the folder."""
    if not NAME_RE.match(str(name or "")):
        return None
    path = (base / name).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        return None
    return path


def audio_seconds_of(base: Path, name: str) -> int:
    path = path_for(base, name)
    if not path:
        return 0
    try:
        return int(probe_seconds(path.read_bytes()) * 1000)
    except MediaError:
        return 0


def delete(base: Path, names: list[str]) -> None:
    for name in names:
        path = path_for(base, name)
        if path:
            path.unlink(missing_ok=True)


def sweep_orphans(base: Path, referenced: set[str], *, older_than_s: float = ORPHAN_AFTER_S) -> int:
    """Remove uploads no line ever used (a mine that failed halfway), once they're a day old."""
    cutoff = time.time() - older_than_s
    removed = 0
    for path in base.iterdir():
        if not path.is_file() or path.name in referenced:
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed


def remove_all(profile_dir: Path) -> None:
    shutil.rmtree(Path(profile_dir) / DIRNAME, ignore_errors=True)
