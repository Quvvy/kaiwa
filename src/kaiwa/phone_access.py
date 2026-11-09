"""Reach Kaiwa from a phone: `tailscale serve` in front of the local server.

Kaiwa stays on 127.0.0.1; Tailscale gives it a private HTTPS address only the
learner's own devices can open. Never Funnel: the API has no login. On Linux a
systemd user service keeps Kaiwa running with no window open (desktop.background).
"""

from __future__ import annotations

import io
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

from kaiwa import jsonio
from kaiwa.secrets_store import user_data_dir

KAIWA_PORT = 8787
SERVICE_NAME = "kaiwa-phone.service"
STATE_FILENAME = "phone_access.json"
IOS_APP_URL = "https://apps.apple.com/app/tailscale/id1470499037"

IS_WINDOWS = sys.platform == "win32"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "Kaiwa"
TAILSCALE_DOWNLOAD_URL = "https://tailscale.com/download"

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "testserver"}  # testserver: FastAPI's TestClient
_LOCAL_ONLY_PREFIXES = ("/api/phone/", "/api/ptt/")
_LOCAL_ONLY_PATHS = {
    "/api/updates/install",
    "/api/updates/dismiss",
    "/api/secrets/deepseek",
    "/api/data/open_folder",
    "/api/prefs/mic",
    "/ankiconnect",  # mining tools run on the PC; ankiconnect.py checks this itself too
    "/ankiconnect/",
}
_PHONE_OSES = {"ios", "android"}
_URL = re.compile(r"https://\S+")
_CONSENT_WAIT_S = 6.0
_SERVE_WAIT_S = 600.0  # `tailscale serve` waits this long for the consent page

_last_phone_seen = 0.0
_serve_proc: subprocess.Popen | None = None
_serve_lock = threading.Lock()
_login_url = ""
_install_state = {"running": False, "error": ""}


# --- which requests came from the phone ---

def is_remote(host: str | None, tailscale_login: str | None = None) -> bool:
    """Serve sets Tailscale-User-Login (and strips any sent to it); tagged devices don't
    get one, so a Host that isn't this machine counts too."""
    if tailscale_login:
        return True
    name = (host or "").strip().lower()
    if name.startswith("["):
        name = name.split("]")[0] + "]"
    else:
        name = name.split(":")[0]
    return name not in _LOCAL_HOSTS


def refuses_remote(path: str, method: str) -> bool:
    """Anything that acts on the PC itself stays on the PC."""
    if path in _LOCAL_ONLY_PATHS or path.startswith("/api/phone/"):
        return True
    return method not in {"GET", "HEAD"} and any(path.startswith(p) for p in _LOCAL_ONLY_PREFIXES)


def note_phone_request() -> None:
    global _last_phone_seen
    _last_phone_seen = time.time()


# --- saved state ---

def _state_path() -> Path:
    return user_data_dir() / STATE_FILENAME


def _load_state() -> dict[str, Any]:
    return jsonio.read_json_dict(_state_path()) or {}


def _save_state(state: dict[str, Any]) -> None:
    jsonio.write_json_atomic(_state_path(), state)


def is_enabled() -> bool:
    return bool(_load_state().get("enabled"))


# --- requests to the desktop app, which is a separate process (desktop.keeper) ---

def _signal_path(name: str) -> Path:
    return user_data_dir() / f"kaiwa-{name}.signal"


def request_signal(name: str) -> None:
    try:
        path = _signal_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    except OSError:
        pass


def take_signal(name: str) -> bool:
    try:
        _signal_path(name).unlink()
    except OSError:
        return False
    return True


# --- power (Windows) ---

def _power_status() -> tuple[int, int] | None:
    """(AC line status, battery flag), or None where that can't be read."""
    if not IS_WINDOWS:
        return None
    import ctypes

    class SystemPowerStatus(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte),
            ("BatteryFlag", ctypes.c_ubyte),
            ("BatteryLifePercent", ctypes.c_ubyte),
            ("SystemStatusFlag", ctypes.c_ubyte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    status = SystemPowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return None
    return status.ACLineStatus, status.BatteryFlag


def on_battery() -> bool:
    power = _power_status()
    return power is not None and power[0] == 0


def has_battery() -> bool:
    """Decides the laptop warning. 128 is Windows' "no system battery"."""
    power = _power_status()
    return power is not None and power[1] != 128


# --- tailscale ---

def tailscale_cli() -> str | None:
    found = shutil.which("tailscale")
    if found:
        return found
    if sys.platform == "win32":
        program_files = os.environ.get("ProgramFiles") or r"C:\Program Files"
        candidate = Path(program_files) / "Tailscale" / "tailscale.exe"
        if candidate.is_file():
            return str(candidate)
    return None


def _creationflags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _tailscale(*args: str, timeout: float = 8.0) -> subprocess.CompletedProcess[str] | None:
    cli = tailscale_cli()
    if not cli:
        return None
    try:
        return subprocess.run(
            [cli, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=_creationflags(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _read_tailscale() -> dict[str, Any] | None:
    """`tailscale status --json`, or None when the daemon isn't answering."""
    done = _tailscale("status", "--json")
    if done is None or done.returncode != 0:
        return None
    try:
        data = json.loads(done.stdout)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _serve_active() -> bool:
    done = _tailscale("serve", "status", "--json")
    return bool(done and done.returncode == 0 and f":{KAIWA_PORT}" in done.stdout)


def _setup_commands() -> list[str]:
    """What to paste into a terminal for the step Kaiwa can't do itself (Linux)."""
    if IS_WINDOWS:
        return []
    if shutil.which("pacman"):
        install = "sudo pacman -S tailscale"
    elif shutil.which("apt"):
        install = "sudo apt install tailscale"
    elif shutil.which("dnf"):
        install = "sudo dnf install tailscale"
    else:
        install = "curl -fsSL https://tailscale.com/install.sh | sh"
    return [install, "sudo systemctl enable --now tailscaled", "sudo tailscale up --operator=$USER"]


def _phone_peer(data: dict[str, Any]) -> dict[str, Any] | None:
    """The learner's phone on their tailnet; an online one wins over an offline one."""
    peers = data.get("Peer") or {}
    phones = [
        p for p in (peers.values() if isinstance(peers, dict) else [])
        if str(p.get("OS") or "").lower() in _PHONE_OSES
    ]
    if not phones:
        return None
    return sorted(phones, key=lambda p: not p.get("Online"))[0]


def status() -> dict[str, Any]:
    """Where the setup wizard is, worked out fresh from Tailscale each time."""
    state = _load_state()
    result: dict[str, Any] = {
        "step": "install",
        "enabled": bool(state.get("enabled")),
        "installed": tailscale_cli() is not None,
        "commands": _setup_commands(),
        "ios_app_url": IOS_APP_URL,
        "buttons": IS_WINDOWS,  # Windows can install and sign in from the wizard; Linux needs sudo
        "download_url": TAILSCALE_DOWNLOAD_URL,
        "installing": _install_state["running"],
        "install_error": _install_state["error"],
        "login_url": _login_url,
        "daemon_up": False,
        "https_ready": False,
        "phone_steps": "",
        "keeps_running": IS_WINDOWS or service_supported(),
        "starts_with_pc": bool(state.get("linger") or state.get("autostart")),
        "has_battery": has_battery(),
        "url": "",
        "phone_name": "",
        "phone_online": False,
        "phone_last_used": _last_phone_seen,
        "service_supported": service_supported(),
        "service_active": service_active(),
        "starts_before_sign_in": bool(state.get("linger")),
        "consent_url": state.get("consent_url") or "",
        "error": state.get("error") or "",
    }
    data = _read_tailscale() if result["installed"] else None
    if data is None:
        return result
    result["daemon_up"] = True
    if data.get("BackendState") != "Running":
        result["step"] = "signin"
        return result
    result["login_url"] = ""
    result["https_ready"] = bool(data.get("CertDomains"))
    dns = str((data.get("Self") or {}).get("DNSName") or "").rstrip(".")
    if dns:
        result["url"] = f"https://{dns}/"
        result["phone_steps"] = phone_steps_text(result["url"])
    phone = _phone_peer(data)
    if phone:
        # iPhones report their hostname as "localhost"; the wizard says "Your phone" instead.
        name = str(phone.get("HostName") or "")
        result["phone_name"] = "" if name == "localhost" else name
        result["phone_online"] = bool(phone.get("Online"))
    if not (result["enabled"] and _serve_active()):
        result["step"] = "enable"
        return result
    result["consent_url"] = ""  # approved: serving now
    if not phone:
        result["step"] = "phone"
    else:
        result["step"] = "open"
    return result


# --- turning it on and off ---

def _run_until_link(cli: str, *args: str) -> tuple[subprocess.Popen, str, str]:
    """Run a Tailscale command that may stop to ask for approval in a browser: it prints a
    link and keeps waiting, so hand back the link and let it finish in the background.
    Returns (process, link or "", everything printed so far)."""
    global _serve_proc
    with _serve_lock:
        if _serve_proc is not None and _serve_proc.poll() is None:
            _serve_proc.kill()
        proc = subprocess.Popen(
            [cli, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            encoding="utf-8",
            errors="replace",
            creationflags=_creationflags(),
        )
        _serve_proc = proc

    lines: queue.Queue[str | None] = queue.Queue()

    def pump() -> None:
        for line in proc.stdout or io.StringIO():
            lines.put(line)
        lines.put(None)

    threading.Thread(target=pump, name="kaiwa-tailscale-serve", daemon=True).start()
    threading.Timer(_SERVE_WAIT_S, lambda: proc.poll() is None and proc.kill()).start()

    seen: list[str] = []
    deadline = time.monotonic() + _CONSENT_WAIT_S
    while True:
        try:
            line = lines.get(timeout=max(0.0, deadline - time.monotonic()))
        except queue.Empty:
            break
        if line is None:
            break
        seen.append(line)
        match = _URL.search(line)
        # Serve's success text also prints the https address it now answers on.
        if match and "tailscale.com" in match.group(0):
            return proc, match.group(0), "".join(seen)
    return proc, "", "".join(seen)


def _start_serve() -> dict[str, str]:
    cli = tailscale_cli()
    if not cli:
        return {"error": "Tailscale isn't installed."}
    proc, link, output = _run_until_link(cli, "serve", "--bg", str(KAIWA_PORT))
    if link:
        return {"consent_url": link}
    if proc.poll() not in (None, 0):
        if "access denied" in output.lower() or "operator" in output.lower():
            return {"error": "Tailscale needs permission first. Run: sudo tailscale set --operator=$USER"}
        first = next((ln.strip() for ln in output.splitlines() if ln.strip()), "tailscale serve failed")
        return {"error": first[:300]}
    return {}


def enable() -> dict[str, Any]:
    state = _load_state()
    state["enabled"] = True
    state.pop("error", None)
    state.pop("consent_url", None)
    outcome = _start_serve()
    state.update(outcome)
    if service_supported() and "error" not in outcome:
        state.update(_install_service())
    if IS_WINDOWS and "error" not in outcome:
        state["autostart"] = _set_autostart(True)
    if outcome.get("consent_url"):
        _open_in_browser(outcome["consent_url"])
    _save_state(state)
    return status()


def disable() -> dict[str, Any]:
    """Cut the phone off now. With a window open the service stays until it closes, since
    the window may be using that server (desktop.app hands over in on_closed)."""
    with _serve_lock:
        if _serve_proc is not None and _serve_proc.poll() is None:
            _serve_proc.kill()
    _tailscale("serve", "--https=443", "off")
    state = _load_state()
    state["enabled"] = False
    state.pop("consent_url", None)
    state.pop("error", None)
    if service_supported():
        _systemctl("disable", SERVICE_NAME)
        if state.pop("linger", False):
            _run_quiet("loginctl", "disable-linger")
    if IS_WINDOWS:
        _set_autostart(False)
        state.pop("autostart", None)
    _save_state(state)
    if service_supported() and not _window_open():
        # This request is probably being served by that service: answer first.
        threading.Timer(0.5, remove_service).start()
    return status()


def _finish_install(proc: subprocess.Popen) -> None:
    code = proc.wait()
    _install_state["running"] = False
    if code != 0 and tailscale_cli() is None:
        _install_state["error"] = "Tailscale didn't install. Use the download link instead."


def install_tailscale() -> dict[str, Any]:
    """One button instead of a download page. Windows asks for permission once."""
    if _install_state["running"] or tailscale_cli():
        return status()
    _install_state["error"] = ""
    winget = shutil.which("winget")
    if winget:
        try:
            proc = subprocess.Popen(
                [
                    winget, "install", "--exact", "--id", "Tailscale.Tailscale", "--silent",
                    "--accept-package-agreements", "--accept-source-agreements",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=_creationflags(),
            )
        except OSError:
            winget = None
        else:
            _install_state["running"] = True
            threading.Thread(target=_finish_install, args=(proc,), name="kaiwa-tailscale-install", daemon=True).start()
    if not winget:
        _open_in_browser(TAILSCALE_DOWNLOAD_URL)
    return status()


def sign_in() -> dict[str, Any]:
    """Start Tailscale's sign-in and open its page."""
    global _login_url
    cli = tailscale_cli()
    if cli:
        _proc, link, _output = _run_until_link(cli, "up")
        if link:
            _login_url = link
            _open_in_browser(link)
    return status()


def phone_steps_text(url: str) -> str:
    return (
        "Kaiwa on your iPhone\n\n"
        f"1. Install Tailscale: {IOS_APP_URL}\n"
        "2. Open it and sign in with the same account as your PC.\n"
        "3. When your iPhone asks to add a VPN, tap Allow. This is how your phone reaches "
        "your PC privately. It doesn't change your other browsing.\n"
        f"4. Open Kaiwa in Safari: {url}\n"
        "5. Tap Share, then Add to Home Screen. Open Kaiwa from that icon from now on.\n"
    )


def email_steps() -> dict[str, Any]:
    """Open a draft in the learner's own mail app. Kaiwa sends nothing itself."""
    current = status()
    if current["phone_steps"]:
        subject = quote("Kaiwa on your iPhone")
        _open_in_browser(f"mailto:?subject={subject}&body={quote(current['phone_steps'])}")
    return current


def _open_in_browser(url: str) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(url)  # type: ignore[attr-defined]  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass  # the wizard shows the same link to click


def qr_svg(text: str) -> bytes:
    import segno

    out = io.BytesIO()
    # Always dark on white, whatever the theme: phone cameras need the contrast.
    segno.make(text, error="m").save(out, kind="svg", scale=6, border=2, dark="#000", light="#fff")
    return out.getvalue()


# --- starting with Windows ---

def _set_autostart(on: bool) -> bool:
    """A per-user Run entry: no admin rights, and Kaiwa starts hidden when they sign in.
    KAIWA_DESKTOP_CMD comes from the desktop app that started this server."""
    command = (os.environ.get("KAIWA_DESKTOP_CMD") or "").strip()
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if on:
                if not command:
                    return False
                winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE)
                except FileNotFoundError:
                    pass
    except (ImportError, OSError):
        return False
    return on


# --- the background service (Linux) ---

def service_supported() -> bool:
    return sys.platform.startswith("linux") and shutil.which("systemctl") is not None


def _unit_path() -> Path:
    xdg = (os.environ.get("XDG_CONFIG_HOME") or "").strip()
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "systemd" / "user" / SERVICE_NAME


def _run_quiet(*cmd: str, timeout: float = 15.0) -> bool:
    try:
        done = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def _systemctl(*args: str) -> bool:
    return _run_quiet("systemctl", "--user", *args)


def _unit_text() -> str:
    root = Path(__file__).resolve().parents[2]
    command = [sys.executable, "-m", "kaiwa.desktop.background"]
    inhibit = shutil.which("systemd-inhibit")
    if inhibit:
        # Idle only: the PC stays up on its own, but choosing Sleep still sleeps.
        command = [inhibit, "--what=idle", "--who=Kaiwa", "--why=Phone access", *command]
    exec_start = " ".join(f'"{part}"' for part in command)
    env = [f'Environment="KAIWA_ROOT={root}"']
    override = (os.environ.get("KAIWA_DATA_DIR") or "").strip()
    if override:
        env.append(f'Environment="KAIWA_DATA_DIR={override}"')
    env_lines = "\n".join(env)
    return f"""[Unit]
Description=Kaiwa, reachable from your phone

[Service]
ExecStart={exec_start}
WorkingDirectory={root}
{env_lines}
Restart=on-failure
RestartSec=5
TimeoutStopSec=20

[Install]
WantedBy=default.target
"""


def _install_service() -> dict[str, Any]:
    """Enable it for next boot. Not started now: the server answering this request is
    already running, and the service takes over when that one closes."""
    path = _unit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_unit_text(), encoding="utf-8")
    _systemctl("daemon-reload")
    _systemctl("enable", SERVICE_NAME)
    return {"linger": _run_quiet("loginctl", "enable-linger")}


def service_active() -> bool:
    return service_supported() and _systemctl("is-active", "--quiet", SERVICE_NAME)


def start_service() -> bool:
    return _systemctl("start", SERVICE_NAME)


def remove_service() -> None:
    _systemctl("stop", SERVICE_NAME)
    _unit_path().unlink(missing_ok=True)
    _systemctl("daemon-reload")


def after_window_closed() -> None:
    """Hand the server back: phone access on → the service runs it; off → nothing should."""
    if not service_supported():
        return
    if is_enabled():
        start_service()
    elif _unit_path().exists():
        remove_service()


def _window_open() -> bool:
    """desktop.instance holds an flock on this file while a window is open."""
    try:
        import fcntl
    except ImportError:
        return False
    try:
        with open(user_data_dir() / "kaiwa-desktop.lock", "a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle, fcntl.LOCK_UN)
    except BlockingIOError:
        return True
    except OSError:
        return False
    return False
