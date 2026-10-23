"""Global push-to-talk: native hook + mic → Kaiwa /api/turn (Windows desktop)."""

from __future__ import annotations

import base64
import collections
import io
import json
import queue
import threading
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


def resolve_input_device(label: str) -> int | None:
    """PortAudio input index for a Windows mic name, or None for the system default.

    The page stores the name the browser shows ("use THIS (VB-Audio Voicemeeter VAIO)",
    sometimes prefixed "Default - "). MME device names are cut to 31 characters, so a
    prefix match in either direction counts. MME is preferred: it resamples to 16 kHz.
    """
    want = (label or "").strip()
    for prefix in ("Default - ", "Communications - "):
        if want.startswith(prefix):
            want = want[len(prefix):]
    want = want.casefold()
    if not want:
        return None
    try:
        import sounddevice as sd

        apis = sd.query_hostapis()
        devices = sd.query_devices()
    except Exception:
        return None
    best: tuple[int, int] | None = None
    for index, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) <= 0:
            continue
        name = str(dev.get("name") or "").casefold()
        if not name:
            continue
        exact = name == want
        prefix = want.startswith(name) or name.startswith(want)
        if not (exact or prefix):
            continue
        api = str(apis[dev["hostapi"]].get("name") or "")
        rank = (0 if exact else 1) * 10 + (0 if api == "MME" else 1 if "DirectSound" in api else 2)
        if best is None or rank < best[0]:
            best = (rank, index)
    return best[1] if best else None


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
        self._prefs_mic = ""
        # Warm input stream while PTT is on: pressing starts instantly, and a short
        # rolling pre-roll keeps the first syllable said while the key goes down.
        self._mic_stream = None
        self._mic_key: tuple[str, int | None] | None = None
        self._preroll: collections.deque = collections.deque(maxlen=8)  # ~0.3 s at 16 kHz/40 ms blocks

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
        self._close_mic()
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
                            self._prefs_mic = str(prefs.get("mic_label") or "")
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
            try:
                self._sync_mic()
            except Exception as exc:
                self._log(f"ptt mic sync: {exc}")
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

        # Low-level hooks route every click and keypress on the whole system
        # through this Python process; while the GIL is busy, input everywhere
        # lags. So the hooks exist only while PTT is on (or a key is being bound).
        listeners: list[Any] = []

        def want_hooks() -> bool:
            with self._lock:
                return self._prefs_enabled or self._bind_capture

        def install() -> None:
            kb = keyboard.Listener(on_press=on_press, on_release=on_release)
            ms = mouse.Listener(on_click=on_click)
            kb.start()
            ms.start()
            listeners.extend([kb, ms])
            self._log("ptt hooks listening")

        def remove() -> None:
            for listener in listeners:
                listener.stop()
            listeners.clear()
            self._log("ptt hooks removed (PTT off)")

        try:
            while not self._stop.is_set():
                wanted = want_hooks()
                if wanted and not listeners:
                    install()
                elif not wanted and listeners:
                    remove()
                self._stop.wait(0.3)
        finally:
            if listeners:
                remove()

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

    def _sync_mic(self) -> None:
        if self._stop.is_set():
            return  # shutting down: don't reopen the mic stop() just closed
        with self._lock:
            enabled = self._prefs_enabled
            label = self._prefs_mic
        if not enabled:
            if not self._recording:
                self._close_mic()
            return
        device = resolve_input_device(label)
        if self._mic_stream is not None and self._mic_key == (label, device):
            return
        if self._recording:
            return
        self._open_mic(label, device)

    def _open_mic(self, label: str, device: int | None) -> bool:
        try:
            import sounddevice as sd
        except ImportError:
            self._log("ptt: sounddevice missing — pip install sounddevice")
            self._post_status("Push-to-talk can't record: the sounddevice package is missing.", level="error")
            return False
        self._close_mic()

        def callback(indata, frames, time_info, status) -> None:  # noqa: ANN001
            block = indata.copy()
            if self._recording:
                self._frames.append(block)
            else:
                self._preroll.append(block)

        try:
            stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                blocksize=640,
                device=device,
                callback=callback,
            )
            stream.start()
        except Exception as exc:
            self._log(f"ptt mic open failed ({label or 'default'}): {exc}")
            self._post_status(f"Push-to-talk couldn't open {label or 'the default microphone'}: {exc}", level="error")
            return False
        self._mic_stream = stream
        self._mic_key = (label, device)
        self._log(f"ptt mic open: {label or 'system default'} (device {device})")
        return True

    def _close_mic(self) -> None:
        stream = self._mic_stream
        self._mic_stream = None
        self._mic_key = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    def _start_recording(self) -> None:
        if self._mic_stream is None:
            with self._lock:
                label = self._prefs_mic
            if not self._open_mic(label, resolve_input_device(label)):
                return
        self._frames = list(self._preroll)
        self._recording = True
        self._play_blip("in")
        self._log("ptt recording…")
        self._post_status("Listening — let go to send")
    def _stop_recording(self, *, discard: bool = False) -> bytes | None:
        was_recording = self._recording
        self._recording = False
        if was_recording:
            self._play_blip("out")
        frames, self._frames = self._frames, []
        if discard or not frames:
            return None
        try:
            import numpy as np
        except ImportError:
            return None
        audio = np.concatenate(frames, axis=0).reshape(-1)
        if float(np.max(np.abs(audio))) < 0.01:
            self._log("ptt: silent clip")
            self._post_status(
                "Push-to-talk heard silence. Pick your microphone in Settings → Speech.",
                level="warn",
            )
            return None
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
            if wav is None:
                return
            if len(wav) < 1600 * 2 * 4:  # < ~0.4 s of audio
                self._log("ptt: clip too short")
                self._post_status("That was too short. Hold the key the whole time you speak.", level="warn")
                return
            self._log("ptt: sending turn…")
            self._post_status("Thinking…")
            files = {"audio": ("ptt.wav", wav, "audio/wav")}
            data = {"session_id": session_id, "client_source": "ptt"}
            player = _SequentialPlayer(self._log) if play else None
            # Streamed: each sentence's audio plays as soon as it is ready.
            with httpx.Client(timeout=180.0) as client:
                with client.stream("POST", f"{self.api_base}/api/turn/stream", files=files, data=data) as res:
                    if res.status_code >= 400:
                        self._log(f"ptt turn failed: {res.status_code}")
                        self._post_status(f"Push-to-talk turn failed ({res.status_code}).", level="error")
                        return
                    if "text/event-stream" not in res.headers.get("content-type", ""):
                        payload = json.loads(res.read() or b"{}")
                        self._log("ptt: no speech")
                        self._post_status(
                            str(payload.get("detail") or "Couldn't catch that. Try again or type it in Chat."),
                            level="warn",
                        )
                        return
                    event = ""
                    for line in res.iter_lines():
                        if line.startswith("event:"):
                            event = line[6:].strip()
                        elif line.startswith("data:"):
                            body = json.loads(line[5:].strip() or "{}")
                            if event == "audio" and player is not None:
                                player.add(str(body.get("audio_base64") or ""))
                            elif event == "error":
                                self._post_status(f"Push-to-talk: {body.get('detail')}", level="error")
            if player is not None:
                player.finish()
            self._log("ptt turn ok")
            self._post_status("Ready · push-to-talk")
        except Exception as exc:
            self._log(f"ptt turn error: {exc}")
            self._post_status(f"Push-to-talk error: {exc}", level="error")
        finally:
            with self._lock:
                self._busy = False


class _SequentialPlayer:
    """Plays WAV chunks in order on a background thread as they arrive."""

    def __init__(self, log: LogFn) -> None:
        self._log = log
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="kaiwa-ptt-play", daemon=True)
        self._thread.start()

    def add(self, b64: str) -> None:
        if b64:
            self._queue.put(b64)

    def finish(self) -> None:
        self._queue.put(None)
        self._thread.join(timeout=120)

    def _run(self) -> None:
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError:
            self._log("ptt: cannot play — sounddevice/numpy missing")
            return
        while True:
            b64 = self._queue.get()
            if b64 is None:
                return
            try:
                with wave.open(io.BytesIO(base64.b64decode(b64)), "rb") as wf:
                    rate = wf.getframerate()
                    channels = wf.getnchannels()
                    frames = wf.readframes(wf.getnframes())
                data = np.frombuffer(frames, dtype="<i2").astype("float32") / 32768.0
                if channels > 1:
                    data = data.reshape(-1, channels)
                sd.play(data, rate)
                sd.wait()
            except Exception as exc:
                self._log(f"ptt play failed: {exc}")
