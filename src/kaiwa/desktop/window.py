from __future__ import annotations

import html
import json

KAIWA_URL = "http://127.0.0.1:8787"

_SPLASH_CSS = """
:root {
  --bg: #12141a;
  --fg: #e8eaef;
  --muted: #9aa3b2;
  --accent: #3d9b8f;
  --danger: #e8a0a0;
  --track: #2a2f3a;
}
* { box-sizing: border-box; }
html, body {
  margin: 0; height: 100%;
  background: var(--bg); color: var(--fg);
  font-family: "Segoe UI", system-ui, sans-serif;
}
.wrap {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
  gap: 0.75rem;
}
.brand {
  font-size: 2rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--accent);
}
.status {
  color: var(--muted);
  font-size: 1rem;
  max-width: 36rem;
  line-height: 1.45;
}
.error .status { color: var(--danger); white-space: pre-wrap; }
.hint {
  color: var(--muted);
  font-size: 0.875rem;
  max-width: 36rem;
  line-height: 1.4;
  opacity: 0.9;
}
.bar {
  width: min(22rem, 80vw);
  height: 0.45rem;
  background: var(--track);
  border-radius: 999px;
  overflow: hidden;
  margin-top: 0.35rem;
}
.bar > span {
  display: block;
  height: 100%;
  width: var(--pct, 0%);
  background: var(--accent);
  border-radius: 999px;
  transition: width 0.2s ease;
}
.bar[hidden] { display: none !important; }
"""


def splash_html(status: str = "Starting…", *, pct: int | None = None) -> str:
    safe = html.escape(status)
    show_bar = pct is not None
    clamped = 0 if pct is None else max(0, min(100, int(pct)))
    bar_attr = "" if show_bar else " hidden"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Kaiwa</title>
<style>{_SPLASH_CSS}</style></head>
<body>
  <div class="wrap">
    <div class="brand">Kaiwa</div>
    <div class="status" id="status">{safe}</div>
    <div class="bar" id="bar"{bar_attr} style="--pct: {clamped}%"><span></span></div>
  </div>
</body></html>"""


def status_js(msg: str) -> str:
    return f"var el=document.getElementById('status'); if(el) el.textContent={json.dumps(msg)};"


def friendly_boot_message(exc: BaseException) -> str:
    """Map boot failures to short friend-facing text (details stay in the log)."""
    text = str(exc).strip() or type(exc).__name__
    lower = text.lower()
    name = type(exc).__name__

    if "bootstrap" in lower or "huggingface" in lower or "download" in lower:
        return (
            "Could not finish downloading speech models or the voice engine. "
            "Check your internet connection and free disk space, then relaunch "
            "(downloads resume where they left off)."
        )
    if "aivisspeech" in lower or "voicevox" in lower or (
        "tts" in lower and ("not found" in lower or "timed out" in lower or "exited" in lower)
    ):
        return (
            "The voice engine didn’t start. Close this window and relaunch. "
            "If it keeps failing, free some disk space or check antivirus isn’t "
            "blocking Kaiwa."
        )
    if "kaiwa exited" in lower or "waiting for kaiwa" in lower or (
        "port 8787" in lower
    ):
        return (
            "Kaiwa’s server didn’t start. Close other copies of Kaiwa if they’re "
            "open, then relaunch."
        )
    if "api python" in lower or "app root unknown" in lower or "runtime" in lower:
        return (
            "This Kaiwa install looks incomplete. Reinstall with KaiwaSetup, "
            "or rebuild with scripts\\build_desktop.ps1."
        )
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)) or name in {
        "TimeoutError",
        "ConnectionError",
        "OSError",
    }:
        if "disk" in lower or "space" in lower or "errno 28" in lower:
            return "Not enough free disk space. Free some space, then relaunch Kaiwa."
        if "network" in lower or "connection" in lower or "winerror 10054" in lower:
            return (
                "A network error stopped startup. Check your internet connection, "
                "then relaunch."
            )

    # Keep short custom messages; strip long tracebacks / multi-line dumps.
    first = text.splitlines()[0].strip()
    if len(first) > 220:
        first = first[:217] + "…"
    if "traceback" in lower or first.startswith("File ") or "\\n" in first:
        return "Something went wrong while starting Kaiwa. Close and relaunch, or check Kaiwa.desktop.log."
    return first or "Something went wrong while starting Kaiwa."


def error_html(message: str) -> str:
    safe = html.escape(message.strip() or "Unknown error")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Kaiwa</title>
<style>{_SPLASH_CSS}</style></head>
<body>
  <div class="wrap error">
    <div class="brand">Kaiwa</div>
    <div class="status" id="status">Could not start</div>
    <div class="status">{safe}</div>
    <p class="hint">Check your internet connection and free disk space, then close
    this window and relaunch (downloads resume where they left off). Details are in
    Kaiwa.desktop.log next to the app (or under LocalAppData\\Kaiwa when running from source).</p>
  </div>
</body></html>"""
