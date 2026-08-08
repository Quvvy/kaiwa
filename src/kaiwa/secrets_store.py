"""User AppData paths: secrets + profiles/sessions layout (consumer-friendly)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

SECRETS_FILENAME = "secrets.json"
KEY_FIELD = "deepseek_api_key"
REGISTRY_FILENAME = "profiles.json"
PROFILES_SUBDIR = "profiles"
SESSIONS_SUBDIR = "sessions"


def appdata_kaiwa_dir() -> Path:
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if local:
        return Path(local) / "Kaiwa"
    return Path.home() / "AppData" / "Local" / "Kaiwa"


def user_data_dir() -> Path:
    """Durable user state root. Override with KAIWA_DATA_DIR for tests/dev."""
    override = (os.environ.get("KAIWA_DATA_DIR") or "").strip()
    if override:
        return Path(override)
    return appdata_kaiwa_dir()


def secrets_path() -> Path:
    return user_data_dir() / SECRETS_FILENAME


def registry_path() -> Path:
    return user_data_dir() / REGISTRY_FILENAME


def profiles_dir() -> Path:
    return user_data_dir() / PROFILES_SUBDIR


def sessions_dir() -> Path:
    return user_data_dir() / SESSIONS_SUBDIR


def masked_key(key: str) -> str:
    raw = (key or "").strip()
    if not raw:
        return ""
    if len(raw) <= 8:
        return "••••"
    return raw[:4] + "..." + raw[-4:]


def load_secret_key() -> str:
    path = secrets_path()
    if not path.is_file():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get(KEY_FIELD) or "").strip()


def save_secret_key(key: str) -> Path:
    cleaned = (key or "").strip()
    if not cleaned:
        raise ValueError("API key cannot be empty")
    path = secrets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                payload = existing
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            payload = {}
    payload[KEY_FIELD] = cleaned
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def maybe_migrate_from_dotenv(root: Path) -> str:
    """If AppData has no key but repo .env does, copy once into AppData."""
    if load_secret_key():
        return load_secret_key()
    env_path = root / ".env"
    if not env_path.is_file():
        return ""
    try:
        from dotenv import dotenv_values

        values = dotenv_values(env_path)
    except Exception:
        return ""
    key = str(values.get("DEEPSEEK_API_KEY") or "").strip()
    if not key:
        return ""
    try:
        save_secret_key(key)
    except ValueError:
        return ""
    return key


def resolve_deepseek_key(
    root: Path,
    *,
    process_env_key: str | None = None,
) -> tuple[str, str]:
    """Return (key, source) where source is env|appdata|dotenv|none.

    Precedence: explicit process env (pre-dotenv) → AppData (after one-time
    .env migrate) → values loaded into the environment from `.env`.
    """
    pre = (process_env_key if process_env_key is not None else "").strip()
    if pre:
        return pre, "env"

    app_key = load_secret_key()
    if not app_key:
        app_key = maybe_migrate_from_dotenv(root)
    if app_key:
        return app_key, "appdata"

    env_key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if env_key:
        return env_key, "dotenv"
    return "", "none"


def soft_validate_deepseek(key: str, base_url: str) -> dict[str, Any]:
    cleaned = (key or "").strip()
    if not cleaned:
        return {"ok": False, "detail": "API key is empty"}
    url = base_url.rstrip("/") + "/models"
    try:
        with httpx.Client(timeout=8.0) as client:
            res = client.get(url, headers={"Authorization": f"Bearer {cleaned}"})
        if res.status_code < 400:
            return {"ok": True, "detail": "Key accepted by DeepSeek"}
        return {
            "ok": False,
            "detail": f"DeepSeek returned HTTP {res.status_code}",
        }
    except Exception as exc:
        return {"ok": False, "detail": f"Could not reach DeepSeek ({exc})"}
