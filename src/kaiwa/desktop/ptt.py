"""Global push-to-talk: native hook + mic → Kaiwa /api/turn (Windows desktop)."""

from __future__ import annotations

import base64
import io
import threading
import time
import wave
from pathlib import Path
from typing import Any, Callable

import httpx

from kaiwa.desktop.icons import asset_path
from kaiwa.ptt_binding import (
    binding_from_pynput_key,
    binding_from_pynput_mouse,
    canonicalize_binding,
    format_binding_label,
)

LogFn = Callable[[str], None]

__all__ = [
    "PttController",
    "canonicalize_binding",
    "format_binding_label",
    "normalize_binding",
]


def normalize_binding(raw: str) -> str:
    return canonicalize_binding(raw)


def _noop_log(msg: str) -> None:
    pass


class PttController:
    """Hold-to-talk via global key/mouse while Kaiwa desktop runs."""

    def __init__(
        self,
        *,
        api_base: str = "http://127.0.0.1:8787",
        log: LogFn | None = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self._log = log or _noop_log
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._recording = False
        self._busy = False
        self._frames: list[Any] = []
        self._stream = None
        self._sample_rate = 16000
        self._prefs_enabled = False
        self._prefs_binding = ""
        self._prefs_play = True
        self._prefs_blips = True
        self._prefs_blip_volume = 0.6
        self._blip_in_path = ""
        self._blip_out_path = ""
        self._session_id = ""
        self._bind_capture = False
        self._lock = threading.Lock()
        self._blip_cache: dict[str, tuple[Any, int] | None] = {}

    def start(self) -> None:
        if self._threads:
            return
        self._stop.clear()
        t_poll = threading.Thread(target=self._poll_loop, name="kaiwa-ptt-poll", daemon=True)
        t_hook = threading.Thread(target=self._hook_loop, name="kaiwa-ptt-hook", daemon=True)
        self._threads = [t_poll, t_hook]
        t_poll.start()
        t_hook.start()
        self._log("ptt controller started")
        self._post_heartbeat()

    def stop(self) -> None:
        self._stop.set()
        self._stop_recording(discard=True)
        self._threads = []
        self._log("ptt controller stopped")

    def _post_heartbeat(self) -> None:
        try:
            with httpx.Client(timeout=2.0) as client:
                client.post(f"{self.api_base}/api/ptt/heartbeat")
        except Exception as exc:
            self._log(f"ptt heartbeat: {exc}")

    def _post_status(self, message: str, *, level: str = "info") -> None:
        try:
            with httpx.Client(timeout=2.0) as client:
                client.post(
                    f"{self.api_base}/api/ptt/status",
                    json={"message": message, "level": level},
                )
        except Exception as exc:
            self._log(f"ptt status post: {exc}")

    def _load_blip_from_path(self, path_str: str) -> tuple[Any, int] | None:
        key = path_str
        if key in self._blip_cache:
            return self._blip_cache[key]
        try:
            import soundfile as sf
        except ImportError:
            self._blip_cache[key] = None
            self._log("ptt blip: soundfile missing")
            return None
        try:
            path = Path(path_str)
            if not path.is_file():
                raise FileNotFoundError(path)
            data, rate = sf.read(str(path), dtype="float32", always_2d=False)
            self._blip_cache[key] = (data, int(rate))
            return self._blip_cache[key]
        except Exception as exc:
            self._blip_cache[key] = None
            self._log(f"ptt blip load {path_str}: {exc}")
            return None

    def _default_blip_path(self, which: str) -> str:
        name = "ptt_blip_in.ogg" if which == "in" else "ptt_blip_out.ogg"
        try:
            return str(asset_path(name))
        except Exception:
            return ""

    def _play_blip(self, which: str) -> None:
        with self._lock:
            enabled = self._prefs_blips
            volume = self._prefs_blip_volume
            path_str = self._blip_in_path if which == "in" else self._blip_out_path
        if not enabled or volume <= 0.0:
            return
        if not path_str:
            path_str = self._default_blip_path(which)
        if not path_str:
            return
        loaded = self._load_blip_from_path(path_str)
        if not loaded:
            # Fall back to bundled asset once if custom path failed.
            fallback = self._default_blip_path(which)
            if fallback and fallback != path_str:
                loaded = self._load_blip_from_path(fallback)
            if not loaded:
                return
        data, rate = loaded
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError:
            return
        try:
            samples = np.asarray(data, dtype="float32") * float(volume)
            sd.play(samples, rate, blocking=False)
        except Exception as exc:
            self._log(f"ptt blip play: {exc}")

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                with httpx.Client(timeout=3.0) as client:
                    try:
                        prefs_payload = client.get(f"{self.api_base}/api/prefs").json()
                        prefs = prefs_payload.get("prefs") or prefs_payload
                        state = client.get(f"{self.api_base}/api/ptt/state").json()
                        with self._lock:
                            self._prefs_enabled = bool(prefs.get("ptt_enabled"))
                            self._prefs_binding = canonicalize_binding(
                                str(prefs.get("ptt_binding") or "")
                            )
                            self._prefs_play = bool(prefs.get("ptt_play_reply", True))
                            self._prefs_blips = bool(prefs.get("ptt_blips_enabled", True))
                            try:
                                vol = float(prefs.get("ptt_blip_volume", 0.6))
                            except (TypeError, ValueError):
                                vol = 0.6
                            self._prefs_blip_volume = max(0.0, min(5.0, vol))
                            self._session_id = str(state.get("session_id") or "")
                            self._bind_capture = bool(state.get("bind_capture"))
                            new_in = str(state.get("blip_in_path") or "") or self._default_blip_path(
                                "in"
                            )
                            new_out = str(state.get("blip_out_path") or "") or self._default_blip_path(
                                "out"
                            )
                            if new_in != self._blip_in_path or new_out != self._blip_out_path:
                                self._blip_cache.clear()
                            self._blip_in_path = new_in
                            self._blip_out_path = new_out
                    except Exception as exc:
                        self._log(f"ptt poll: {exc}")
                    finally:
                        # Keep hook_alive even if prefs/state fail (e.g. missing blip assets).
                        try:
                            client.post(f"{self.api_base}/api/ptt/heartbeat")
                        except Exception as exc:
                            self._log(f"ptt heartbeat: {exc}")
            except Exception as exc:
                self._log(f"ptt poll client: {exc}")
            self._stop.wait(1.5)

    def _hook_loop(self) -> None:
        try:
            from pynput import keyboard, mouse
        except ImportError:
            self._log("ptt: pynput missing — pip install pynput (desktop extra)")
            self._post_status(
                "Global PTT unavailable — install desktop deps (pynput).",
                level="error",
            )
            return

        def on_press(key: Any) -> None:
            self._maybe_start(binding_from_pynput_key(key))

        def on_release(key: Any) -> None:
            self._maybe_stop(binding_from_pynput_key(key))

        def on_click(x: float, y: float, button: Any, pressed: bool) -> None:
            name = binding_from_pynput_mouse(button)
            if pressed:
                self._maybe_start(name)
            else:
                self._maybe_stop(name)

        kb_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        ms_listener = mouse.Listener(on_click=on_click)
        kb_listener.start()
        ms_listener.start()
        self._log("ptt hooks listening")
        try:
            while not self._stop.is_set():
                time.sleep(0.2)
        finally:
            kb_listener.stop()
            ms_listener.stop()

    def _active_binding(self) -> str:
        with self._lock:
            if not self._prefs_enabled or self._bind_capture:
                return ""
            return self._prefs_binding

    def _maybe_start(self, binding: str) -> None:
        want = self._active_binding()
        got = canonicalize_binding(binding)
        if not want or got != want:
            return
        with self._lock:
            if self._recording or self._busy:
                return
        self._start_recording()

    def _maybe_stop(self, binding: str) -> None:
        want = self._active_binding()
        got = canonicalize_binding(binding)
        if not want or got != want:
            return
        if not self._recording:
            return
        threading.Thread(target=self._finish_turn, name="kaiwa-ptt-turn", daemon=True).start()

    def _start_recording(self) -> None:
        try:
            import sounddevice as sd
        except ImportError:
            self._log("ptt: sounddevice missing — pip install sounddevice")
            self._post_status(
                "Global PTT mic unavailable — install sounddevice.",
                level="error",
            )
            return

        self._frames = []

        def callback(indata, frames, time_info, status) -> None:  # noqa: ANN001
            if status:
                self._log(f"ptt mic status: {status}")
            self._frames.append(indata.copy())

        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                callback=callback,
            )
            # Cue before opening the mic to avoid PortAudio duplex glitches.
            self._play_blip("in")
            self._stream.start()
            self._recording = True
            self._log("ptt recording…")
            self._post_status("PTT listening — hold, then release to send")
        except Exception as exc:
            self._log(f"ptt mic start failed: {exc}")
            self._stream = None
            self._recording = False
            self._post_status(f"PTT mic failed: {exc}", level="error")

    def _stop_recording(self, *, discard: bool = False) -> bytes | None:
        was_recording = self._recording
        self._recording = False
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        if was_recording:
            self._play_blip("out")
        if discard:
            self._frames = []
            return None
        if not self._frames:
            return None
        try:
            import numpy as np
        except ImportError:
            return None
        audio = np.concatenate(self._frames, axis=0).reshape(-1)
        self._frames = []
        pcm = np.clip(audio, -1.0, 1.0)
        pcm_i16 = (pcm * 32767.0).astype("<i2")
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self._sample_rate)
            wf.writeframes(pcm_i16.tobytes())
        return buf.getvalue()

    def _finish_turn(self) -> None:
        with self._lock:
            if self._busy:
                self._stop_recording(discard=True)
                return
            self._busy = True
            session_id = self._session_id
            play = self._prefs_play
        try:
            wav = self._stop_recording(discard=False)
            if not wav or len(wav) < 1600:
                self._log("ptt: clip too short")
                self._post_status(
                    "Hold the PTT key longer, then release (don’t just click).",
                    level="warn",
                )
                return
            self._log("ptt: sending turn…")
            self._post_status("PTT sending…")
            files = {"audio": ("ptt.wav", wav, "audio/wav")}
            data = {
                "session_id": session_id,
                "client_source": "ptt",
            }
            with httpx.Client(timeout=180.0) as client:
                res = client.post(f"{self.api_base}/api/turn", files=files, data=data)
            if res.status_code >= 400:
                self._log(f"ptt turn failed: {res.status_code} {res.text[:200]}")
                self._post_status(
                    f"PTT turn failed ({res.status_code}).",
                    level="error",
                )
                return
            payload = res.json()
            self._log("ptt turn ok")
            self._post_status("Ready · push-to-talk")
            if play and payload.get("audio_base64"):
                self._play_wav_b64(str(payload["audio_base64"]))
        except Exception as exc:
            self._log(f"ptt turn error: {exc}")
            self._post_status(f"PTT error: {exc}", level="error")
        finally:
            with self._lock:
                self._busy = False

    def _play_wav_b64(self, b64: str) -> None:
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError:
            self._log("ptt: cannot play — sounddevice/numpy missing")
            return
        try:
            raw = base64.b64decode(b64)
            with wave.open(io.BytesIO(raw), "rb") as wf:
                rate = wf.getframerate()
                channels = wf.getnchannels()
                frames = wf.readframes(wf.getnframes())
                width = wf.getsampwidth()
            if width == 2:
                data = np.frombuffer(frames, dtype="<i2").astype("float32") / 32768.0
            else:
                self._log(f"ptt: unsupported sample width {width}")
                return
            if channels > 1:
                data = data.reshape(-1, channels)
            sd.play(data, rate)
            sd.wait()
        except Exception as exc:
            self._log(f"ptt play failed: {exc}")
