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
"""


def splash_html(status: str = "Starting…") -> str:
    safe = html.escape(status)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Kaiwa</title>
<style>{_SPLASH_CSS}</style></head>
<body>
  <div class="wrap">
    <div class="brand">Kaiwa</div>
    <div class="status" id="status">{safe}</div>
  </div>
</body></html>"""


def status_js(msg: str) -> str:
    return f"var el=document.getElementById('status'); if(el) el.textContent={json.dumps(msg)};"


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
    <p class="hint">Check that your preferred TTS engine is installed and that
    <code>.venv</code> can run <code>python -m kaiwa.app</code>. Close this window and relaunch.</p>
  </div>
</body></html>"""
