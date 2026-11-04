"""Phone access: wizard states, serve + consent parsing, and what a phone may not do.

Uses a fake `tailscale` on PATH; no network, and systemd is never touched.
"""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
TMP = Path(tempfile.mkdtemp(prefix="kaiwa-phone-smoke-"))
os.environ["KAIWA_DATA_DIR"] = str(TMP / "data")
os.environ["KAIWA_TTS_WATCHDOG"] = "0"
BIN = TMP / "bin"
BIN.mkdir()
os.environ["PATH"] = f"{BIN}{os.pathsep}{os.environ['PATH']}"

FAKE = textwrap.dedent(
    f"""\
    #!{sys.executable}
    import json, os, sys, time
    base = {str(BIN)!r}
    mode = open(base + "/mode").read().strip()
    a = sys.argv[1:]
    serving = base + "/serving"
    if a[:2] == ["status", "--json"]:
        if mode == "nodaemon":
            sys.exit(1)
        d = {{"BackendState": "NeedsLogin" if mode == "login" else "Running",
             "Self": {{"DNSName": "pc.tail.ts.net."}}, "Peer": {{}}}}
        if mode == "phone":
            d["Peer"] = {{"k": {{"OS": "iOS", "Online": True, "HostName": "iphone"}}}}
        print(json.dumps(d))
    elif a[:3] == ["serve", "status", "--json"]:
        print(json.dumps({{"p": "http://127.0.0.1:8787"}}) if os.path.exists(serving) else "{{}}")
    elif a[:2] == ["serve", "--bg"]:
        if mode == "denied":
            print("Access denied: serve config denied")
            sys.exit(1)
        if mode == "consent":
            print("To enable, visit:\\n\\n   https://login.tailscale.com/f/serve?node=abc\\n", flush=True)
            time.sleep(30)
        open(serving, "w").close()
        print("https://pc.tail.ts.net/\\n|-- proxy http://127.0.0.1:8787")
    elif a[0] == "serve" and a[-1] == "off":
        if os.path.exists(serving):
            os.remove(serving)
    """
)
(BIN / "tailscale").write_text(FAKE, encoding="utf-8")
(BIN / "tailscale").chmod((BIN / "tailscale").stat().st_mode | stat.S_IEXEC)

from fastapi.testclient import TestClient  # noqa: E402

from kaiwa import phone_access  # noqa: E402
from kaiwa.app import app  # noqa: E402

# Never install a real service from a smoke test.
phone_access.service_supported = lambda: False  # type: ignore[assignment]
phone_access._open_in_browser = lambda url: None  # type: ignore[assignment]


def _check(ok: bool, label: str) -> None:
    print(("ok    " if ok else "FAIL  ") + label, flush=True)
    if not ok:
        raise SystemExit(f"smoke_phone failed: {label}")


def _mode(name: str) -> None:
    (BIN / "mode").write_text(name, encoding="utf-8")


client = TestClient(app)
PC = {"host": "127.0.0.1:8787"}
PHONE = {"host": "pc.tail.ts.net", "tailscale-user-login": "me@example.com"}

_mode("nodaemon")
_check(client.get("/api/phone/status", headers=PC).json()["step"] == "install", "daemon down → install step")
_mode("login")
_check(client.get("/api/phone/status", headers=PC).json()["step"] == "signin", "signed out → sign-in step")
_mode("running")
_check(client.get("/api/phone/status", headers=PC).json()["step"] == "enable", "signed in → enable step")

_mode("denied")
st = client.post("/api/phone/enable", headers=PC).json()
_check("operator" in st["error"], "no operator rights → says how to fix it")
_mode("consent")
st = client.post("/api/phone/enable", headers=PC).json()
_check("login.tailscale.com" in st["consent_url"] and st["step"] == "enable", "consent link handed back")
_mode("running")
st = client.post("/api/phone/enable", headers=PC).json()
_check(st["step"] == "phone" and st["url"] == "https://pc.tail.ts.net/" and not st["consent_url"], "serving → phone step")
_mode("phone")
st = client.get("/api/phone/status", headers=PC).json()
_check(st["step"] == "open" and st["phone_name"] == "iphone", "iPhone joined → open step")
for path in ("/api/phone/qr/app", "/api/phone/qr/kaiwa"):
    res = client.get(path, headers=PC)
    _check(res.status_code == 200 and b"<svg" in res.content, f"{path} is an SVG")

# Local-only guard, by header and by Host alone.
for headers, who in ((PHONE, "serve header"), ({"host": "pc.tail.ts.net"}, "Host only")):
    for method, path in (
        ("get", "/api/phone/status"),
        ("post", "/api/phone/disable"),
        ("post", "/api/updates/install"),
        ("post", "/api/data/open_folder"),
        ("put", "/api/secrets/deepseek"),
        ("post", "/api/ptt/register"),
        ("post", "/api/prefs/mic"),
    ):
        res = client.request(method.upper(), path, headers=headers, json={} if method != "get" else None)
        _check(res.status_code == 403, f"{who}: {method.upper()} {path} refused")
_check(client.get("/api/health", headers=PHONE).status_code == 200, "phone can reach the API")
_check(client.get("/", headers=PHONE).status_code == 200, "phone can load the page")
_check(client.get("/api/ptt/state", headers=PHONE).status_code == 200, "phone can read PTT state")
_check(client.get("/sw.js", headers=PHONE).status_code == 200, "service worker served from the root")
_check(client.get("/static/manifest.webmanifest", headers=PHONE).status_code == 200, "manifest served")

# A phone saving Settings keeps the PC's push-to-talk mic.
client.post("/api/prefs/mic", headers=PC, json={"label": "PC mic"})
prefs = client.get("/api/prefs", headers=PC).json()["prefs"]
client.put("/api/prefs", headers=PHONE, json={**prefs, "mic_label": ""})
_check(client.get("/api/prefs", headers=PC).json()["prefs"]["mic_label"] == "PC mic", "phone can't change the PC's mic")

st = client.post("/api/phone/disable", headers=PC).json()
_check(not st["enabled"] and st["step"] == "enable", "turned off → back to enable step")
_check(json.loads((TMP / "data" / phone_access.STATE_FILENAME).read_text())["enabled"] is False, "off is saved")
print("smoke_phone passed")
