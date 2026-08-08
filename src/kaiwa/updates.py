"""In-app update check against GitHub Releases (Phase 6.9)."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from kaiwa import __version__
from kaiwa.secrets_store import user_data_dir

GITHUB_REPO = "Quvvy/kaiwa"
GITHUB_LATEST_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CACHE_FILENAME = "update_check.json"
CACHE_TTL = timedelta(hours=24)
SETUP_NAME_RE = re.compile(r"^KaiwaSetup-.+\.exe$", re.IGNORECASE)
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def current_version() -> str:
    return str(__version__).strip()


def updates_dir() -> Path:
    return user_data_dir() / "downloads" / "updates"


def cache_path() -> Path:
    return user_data_dir() / CACHE_FILENAME


def parse_version(raw: str) -> tuple[int, int, int] | None:
    text = (raw or "").strip().lstrip("vV")
    match = VERSION_RE.match(text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def version_newer(latest: str, current: str) -> bool:
    left = parse_version(latest)
    right = parse_version(current)
    if left is None or right is None:
        return False
    return left > right


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(raw: str) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _load_cache() -> dict[str, Any]:
    path = cache_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}


def _save_cache(patch: dict[str, Any]) -> dict[str, Any]:
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    state = _load_cache()
    state.update(patch)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return state


def _user_agent() -> str:
    return f"Kaiwa/{current_version()} (+https://github.com/{GITHUB_REPO})"


def _pick_setup_asset(assets: list[Any], latest_version: str) -> dict[str, str] | None:
    candidates: list[dict[str, str]] = []
    for item in assets:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        url = str(item.get("browser_download_url") or "").strip()
        if not name or not url or not SETUP_NAME_RE.match(name):
            continue
        candidates.append({"name": name, "url": url})
    if not candidates:
        return None
    needle = latest_version.lstrip("vV")
    for row in candidates:
        if needle and needle in row["name"]:
            return row
    return candidates[0]


def _cache_fresh(state: dict[str, Any]) -> bool:
    checked = _parse_iso(str(state.get("checked_at") or ""))
    if checked is None:
        return False
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    return _utcnow() - checked <= CACHE_TTL


def _status_from_state(state: dict[str, Any], *, error: str | None = None) -> dict[str, Any]:
    current = current_version()
    latest = str(state.get("latest_version") or "").strip()
    update_available = bool(latest) and version_newer(latest, current)
    dismissed = str(state.get("dismissed_version") or "").strip()
    snoozed = bool(dismissed) and dismissed == latest and update_available
    return {
        "ok": error is None,
        "update_available": update_available and not snoozed,
        "current_version": current,
        "latest_version": latest or None,
        "release_name": state.get("release_name") or None,
        "asset_name": state.get("asset_name") or None,
        "asset_url": state.get("asset_url") or None,
        "html_url": state.get("html_url") or None,
        "checked_at": state.get("checked_at") or None,
        "dismissed": snoozed,
        "dismissed_version": dismissed or None,
        "error": error,
    }


def fetch_latest_release(*, timeout: float = 20.0) -> dict[str, Any]:
    """Hit GitHub Releases API; raises RuntimeError with friend-facing text on failure."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": _user_agent(),
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            res = client.get(GITHUB_LATEST_URL)
    except httpx.HTTPError as exc:
        raise RuntimeError(
            "Could not reach GitHub to check for updates. Check your internet connection."
        ) from exc

    if res.status_code == 404:
        raise RuntimeError("No GitHub release found for Kaiwa yet.")
    if res.status_code == 403:
        raise RuntimeError("GitHub rate-limited the update check. Try again later.")
    if res.status_code >= 400:
        raise RuntimeError(f"GitHub update check failed (HTTP {res.status_code}).")

    try:
        payload = res.json()
    except ValueError as exc:
        raise RuntimeError("GitHub returned an invalid update response.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub returned an invalid update response.")

    tag = str(payload.get("tag_name") or "").strip()
    latest = tag.lstrip("vV") if tag else ""
    if not latest or parse_version(latest) is None:
        raise RuntimeError("Latest GitHub release has no usable version tag.")

    asset = _pick_setup_asset(list(payload.get("assets") or []), latest)
    return {
        "latest_version": latest,
        "release_name": str(payload.get("name") or tag or latest).strip() or latest,
        "html_url": str(payload.get("html_url") or "").strip() or None,
        "asset_name": asset["name"] if asset else None,
        "asset_url": asset["url"] if asset else None,
        "checked_at": _iso(_utcnow()),
        "current_version": current_version(),
        "update_available": version_newer(latest, current_version()),
    }


def check_for_updates(*, force: bool = False) -> dict[str, Any]:
    state = _load_cache()
    if not force and _cache_fresh(state) and state.get("latest_version"):
        return _status_from_state(state)

    try:
        fresh = fetch_latest_release()
    except RuntimeError as exc:
        if state.get("latest_version"):
            out = _status_from_state(state, error=str(exc))
            out["ok"] = False
            return out
        return _status_from_state({}, error=str(exc))

    merged = _save_cache(
        {
            "checked_at": fresh["checked_at"],
            "current_version": fresh["current_version"],
            "latest_version": fresh["latest_version"],
            "release_name": fresh.get("release_name"),
            "asset_name": fresh.get("asset_name"),
            "asset_url": fresh.get("asset_url"),
            "html_url": fresh.get("html_url"),
            "update_available": fresh.get("update_available"),
        }
    )
    return _status_from_state(merged)


def dismiss_update(version: str) -> dict[str, Any]:
    ver = (version or "").strip().lstrip("vV")
    if not ver:
        raise ValueError("version is required")
    state = _save_cache({"dismissed_version": ver})
    return _status_from_state(state)


def _download_installer(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".partial")
    existing = partial.stat().st_size if partial.is_file() else 0
    headers = {"User-Agent": _user_agent()}
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"

    try:
        with httpx.stream(
            "GET",
            url,
            headers=headers,
            follow_redirects=True,
            timeout=httpx.Timeout(60.0, read=600.0),
        ) as res:
            if res.status_code == 416 and partial.is_file():
                partial.replace(dest)
                return dest
            if res.status_code not in (200, 206):
                raise RuntimeError(f"Download failed (HTTP {res.status_code})")
            mode = "ab" if res.status_code == 206 and existing else "wb"
            if mode == "wb" and partial.is_file():
                partial.unlink()
            with partial.open(mode) as out:
                for chunk in res.iter_bytes(1024 * 256):
                    out.write(chunk)
        partial.replace(dest)
        return dest
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "Could not download the Kaiwa installer. Check your internet connection "
            "and free disk space, then try again."
        ) from exc


def download_and_launch_installer(*, force_check: bool = True) -> dict[str, Any]:
    if sys.platform != "win32":
        return {
            "ok": False,
            "path": None,
            "launched": False,
            "detail": "In-app install is only supported on Windows.",
        }

    status = check_for_updates(force=force_check)
    if status.get("error") and not status.get("asset_url"):
        return {
            "ok": False,
            "path": None,
            "launched": False,
            "detail": str(status.get("error") or "Update check failed."),
        }

    asset_url = str(status.get("asset_url") or "").strip()
    asset_name = str(status.get("asset_name") or "").strip()
    latest = str(status.get("latest_version") or "").strip()
    if not asset_url or not asset_name:
        return {
            "ok": False,
            "path": None,
            "launched": False,
            "detail": "No KaiwaSetup installer is attached to the latest GitHub release.",
        }
    if not version_newer(latest, current_version()):
        return {
            "ok": False,
            "path": None,
            "launched": False,
            "detail": f"You are already on Kaiwa {current_version()}.",
        }

    dest = updates_dir() / asset_name
    try:
        if not dest.is_file():
            _download_installer(asset_url, dest)
        os.startfile(str(dest))  # noqa: S606 — intentional: launch Inno Setup
    except RuntimeError as exc:
        return {"ok": False, "path": str(dest), "launched": False, "detail": str(exc)}
    except OSError as exc:
        return {
            "ok": False,
            "path": str(dest),
            "launched": False,
            "detail": f"Could not start the installer: {exc}",
        }

    return {
        "ok": True,
        "path": str(dest),
        "launched": True,
        "detail": "Installer started — finish Setup and relaunch Kaiwa.",
        "latest_version": latest,
        "asset_name": asset_name,
    }
