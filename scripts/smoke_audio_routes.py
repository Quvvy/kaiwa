"""Voice uploads end to end: a browser-style webm/opus clip through the HTTP routes.

Catches dependency drift in the audio stack (PyAV 19 broke faster-whisper's
decoding, so every speech route answered 500). Loads Whisper; no network.
Run it with the bundled runtime too: dist\\Kaiwa\\runtime\\python.exe scripts\\smoke_audio_routes.py
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("KAIWA_DATA_DIR", tempfile.mkdtemp(prefix="kaiwa-audio-smoke-"))

import av  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from kaiwa import bootstrap  # noqa: E402
from kaiwa.app import app  # noqa: E402
from kaiwa.course import state as course_state  # noqa: E402
from kaiwa.secrets_store import appdata_kaiwa_dir  # noqa: E402

# State goes to the temp folder, but reuse the installed Whisper model (1.6 GB).
bootstrap.models_dir = lambda: appdata_kaiwa_dir() / "models"


def _check(ok: bool, label: str) -> None:
    line = ("ok    " if ok else "FAIL  ") + label
    sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
    sys.stdout.flush()
    if not ok:
        raise SystemExit(f"smoke_audio_routes failed: {label}")


def _webm(wav: Path) -> bytes:
    """Re-encode a wav as webm/opus, the format MediaRecorder uploads."""
    out = io.BytesIO()
    with av.open(str(wav)) as src, av.open(out, "w", format="webm") as dst:
        stream = dst.add_stream("libopus", rate=48000)
        resampler = av.AudioResampler(format="s16", layout="mono", rate=48000)
        for frame in src.decode(audio=0):
            for f in resampler.resample(frame):
                for packet in stream.encode(f):
                    dst.mux(packet)
        for packet in stream.encode(None):
            dst.mux(packet)
    return out.getvalue()


def main() -> None:
    wav = ROOT / "recordings" / "smoke_tts.wav"
    if not wav.is_file():
        raise SystemExit(f"missing {wav} - run scripts/smoke_tts.py first")
    clip = _webm(wav)
    _check(len(clip) > 1000, f"encoded a webm clip ({len(clip)} bytes)")

    from faster_whisper.audio import decode_audio

    samples = decode_audio(io.BytesIO(clip), sampling_rate=16000)
    _check(len(samples) > 8000, "faster-whisper decodes the webm (kana judge path)")

    client = TestClient(app)
    files = {"audio": ("utterance.webm", clip, "audio/webm")}

    r = client.post("/api/course/check_text", files=files, data={"target": "こんにちは", "strict": "true"})
    _check(r.status_code != 500, f"placement repeat-after-me: {r.status_code} {r.text[:200]}")
    _check(r.status_code != 200 or "credit" in r.json(), "placement repeat returns a credit")

    r = client.post("/api/course/check_text", files=files, data={"target": "あ"})
    _check(r.status_code == 200, f"single-kana say-it: {r.status_code} {r.text[:200]}")

    phrase_id = next(iter(course_state._PHRASES))
    r = client.post("/api/course/check", files=files, data={"phrase_id": phrase_id})
    _check(r.status_code != 500, f"lesson say-it-back: {r.status_code} {r.text[:200]}")

    print("smoke_audio_routes: all ok")


if __name__ == "__main__":
    main()
