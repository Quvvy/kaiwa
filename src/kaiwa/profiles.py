"""One learner per install, stored under profiles/<active id>/.

The registry and per-id folders predate the single-learner cut: older installs
may hold extra profile folders, which are left on disk untouched (not shown).
Folders starting with "_" (backups) are never treated as profiles.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kaiwa import jsonio
from kaiwa import secrets_store
from kaiwa.config import ROOT

PREFS_FILE = "user_prefs.json"
PROFILE_FILE = "learner_profile.json"
MEMORY_FILE = "learner_memory.json"
PERSONALITIES_FILE = "user_personalities.json"
STRUGGLE_CARDS_FILE = "struggle_cards.jsonl"
PRACTICE_STATE_FILE = "practice_state.json"

BUNDLE_FORMAT = "kaiwa-profile"
BUNDLE_VERSION = 1

_FLAT_FILES = (PREFS_FILE, PROFILE_FILE, MEMORY_FILE, PERSONALITIES_FILE)
BACKUPS_SUBDIR = "_backups"
_migrated = False


def data_dir() -> Path:
    return secrets_store.user_data_dir()


def registry_path() -> Path:
    return secrets_store.registry_path()


def profiles_dir() -> Path:
    return secrets_store.profiles_dir()


@dataclass
class ProfileMeta:
    id: str
    label: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class ProfileRegistry:
    active: str = "default"
    profiles: list[ProfileMeta] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "profiles": [p.to_dict() for p in self.profiles],
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: Any) -> None:
    with jsonio.STATE_LOCK:
        jsonio.write_json_atomic(path, data)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_prefs_dict() -> dict[str, Any]:
    from kaiwa.prefs import default_prefs

    return default_prefs().to_dict()


def _default_profile_dict() -> dict[str, Any]:
    from kaiwa.learner_profile import default_profile

    return default_profile().to_dict()


def _default_memory_dict() -> dict[str, Any]:
    from kaiwa.learner_memory import default_memory

    return default_memory().to_dict()


def _write_fresh_profile_files(profile_dir: Path) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    _write_json(profile_dir / PREFS_FILE, _default_prefs_dict())
    _write_json(profile_dir / PROFILE_FILE, _default_profile_dict())
    _write_json(profile_dir / MEMORY_FILE, _default_memory_dict())
    _write_json(profile_dir / PERSONALITIES_FILE, {"presets": []})


def _repo_has_user_data(src_data: Path) -> bool:
    if (src_data / "profiles.json").is_file():
        return True
    src_profiles = src_data / "profiles"
    if src_profiles.is_dir() and any(src_profiles.iterdir()):
        return True
    return any((src_data / name).is_file() for name in _FLAT_FILES)


def _maybe_copy_from_repo() -> None:
    """One-time: if user data has no registry, copy from repo data/ (+ sessions)."""
    dest_reg = registry_path()
    if dest_reg.is_file():
        return

    src_data = ROOT / "data"
    if not _repo_has_user_data(src_data):
        return

    dest_root = data_dir()
    dest_root.mkdir(parents=True, exist_ok=True)

    src_reg = src_data / "profiles.json"
    if src_reg.is_file():
        shutil.copy2(src_reg, dest_reg)

    src_profiles = src_data / "profiles"
    dest_profiles = profiles_dir()
    if src_profiles.is_dir() and not dest_profiles.exists():
        shutil.copytree(src_profiles, dest_profiles)

    for name in _FLAT_FILES:
        src = src_data / name
        dest = dest_root / name
        if src.is_file() and not dest.is_file():
            shutil.copy2(src, dest)

    src_sess = ROOT / "sessions"
    dest_sess = secrets_store.sessions_dir()
    if src_sess.is_dir():
        jsonls = list(src_sess.glob("*.jsonl"))
        if jsonls:
            dest_sess.mkdir(parents=True, exist_ok=True)
            if not any(dest_sess.glob("*.jsonl")):
                for f in jsonls:
                    shutil.copy2(f, dest_sess / f.name)


def _load_registry_raw() -> ProfileRegistry:
    path = registry_path()
    if not path.exists():
        return ProfileRegistry(active="default", profiles=[])
    try:
        raw = _read_json(path)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return ProfileRegistry(active="default", profiles=[])
    if not isinstance(raw, dict):
        return ProfileRegistry(active="default", profiles=[])
    profiles: list[ProfileMeta] = []
    for item in raw.get("profiles") or []:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip()
        if not pid:
            continue
        profiles.append(
            ProfileMeta(
                id=pid,
                label=str(item.get("label") or pid).strip() or pid,
                created_at=str(item.get("created_at") or _now_iso()),
                updated_at=str(item.get("updated_at") or _now_iso()),
            )
        )
    active = str(raw.get("active") or "default").strip() or "default"
    return ProfileRegistry(active=active, profiles=profiles)


def _save_registry(reg: ProfileRegistry) -> ProfileRegistry:
    data_dir().mkdir(parents=True, exist_ok=True)
    _write_json(registry_path(), reg.to_dict())
    return reg


def _touch_meta(reg: ProfileRegistry, profile_id: str) -> None:
    now = _now_iso()
    for meta in reg.profiles:
        if meta.id == profile_id:
            meta.updated_at = now
            break


def ensure_migrated() -> None:
    """Copy repo data once if needed; flatten legacy files; ensure registry exists."""
    global _migrated
    if _migrated:
        return
    _migrated = True

    _maybe_copy_from_repo()

    root = data_dir()
    pdir = profiles_dir()
    pdir.mkdir(parents=True, exist_ok=True)
    default_dir = pdir / "default"
    flat_existing = [root / name for name in _FLAT_FILES if (root / name).exists()]

    if not default_dir.exists():
        default_dir.mkdir(parents=True, exist_ok=True)
        if flat_existing:
            for src in flat_existing:
                dest = default_dir / src.name
                if not dest.exists():
                    shutil.move(str(src), str(dest))
        if not (default_dir / PREFS_FILE).exists():
            _write_json(default_dir / PREFS_FILE, _default_prefs_dict())
        if not (default_dir / PROFILE_FILE).exists():
            _write_json(default_dir / PROFILE_FILE, _default_profile_dict())
        if not (default_dir / MEMORY_FILE).exists():
            _write_json(default_dir / MEMORY_FILE, _default_memory_dict())
        if not (default_dir / PERSONALITIES_FILE).exists():
            _write_json(default_dir / PERSONALITIES_FILE, {"presets": []})
    else:
        if not (default_dir / PREFS_FILE).exists():
            _write_json(default_dir / PREFS_FILE, _default_prefs_dict())
        if not (default_dir / PROFILE_FILE).exists():
            _write_json(default_dir / PROFILE_FILE, _default_profile_dict())
        if not (default_dir / MEMORY_FILE).exists():
            _write_json(default_dir / MEMORY_FILE, _default_memory_dict())
        if not (default_dir / PERSONALITIES_FILE).exists():
            _write_json(default_dir / PERSONALITIES_FILE, {"presets": []})

    reg = _load_registry_raw()
    ids = {p.id for p in reg.profiles}
    if "default" not in ids:
        now = _now_iso()
        reg.profiles.insert(
            0,
            ProfileMeta(id="default", label="Default", created_at=now, updated_at=now),
        )
    if not any(p.id == reg.active for p in reg.profiles):
        reg.active = reg.profiles[0].id if reg.profiles else "default"
    for child in pdir.iterdir():
        if not child.is_dir() or child.name.startswith("_"):
            continue
        if child.name not in {p.id for p in reg.profiles}:
            now = _now_iso()
            reg.profiles.append(
                ProfileMeta(
                    id=child.name,
                    label=child.name,
                    created_at=now,
                    updated_at=now,
                )
            )
    _save_registry(reg)


def active_profile_id() -> str:
    ensure_migrated()
    return _load_registry_raw().active


def active_profile_dir() -> Path:
    ensure_migrated()
    pid = active_profile_id()
    path = profiles_dir() / pid
    path.mkdir(parents=True, exist_ok=True)
    return path


def prefs_path() -> Path:
    return active_profile_dir() / PREFS_FILE


def learner_profile_path() -> Path:
    return active_profile_dir() / PROFILE_FILE


def memory_path() -> Path:
    return active_profile_dir() / MEMORY_FILE


def personalities_path() -> Path:
    return active_profile_dir() / PERSONALITIES_FILE


def struggle_cards_path() -> Path:
    return active_profile_dir() / STRUGGLE_CARDS_FILE


def practice_state_path() -> Path:
    return active_profile_dir() / PRACTICE_STATE_FILE


def profile_dir(profile_id: str) -> Path:
    ensure_migrated()
    return profiles_dir() / profile_id


def get_meta(profile_id: str) -> ProfileMeta | None:
    ensure_migrated()
    for meta in _load_registry_raw().profiles:
        if meta.id == profile_id:
            return meta
    return None


def list_profiles() -> dict[str, Any]:
    """The one active learner (kept as a list for older clients)."""
    ensure_migrated()
    reg = _load_registry_raw()
    active = next((p for p in reg.profiles if p.id == reg.active), None)
    return {
        "active_id": reg.active,
        "profiles": [active.to_dict()] if active else [],
    }


def backup_active(reason: str) -> Path:
    """Copy the active profile folder to profiles/_backups/ before overwriting it."""
    ensure_migrated()
    pid = active_profile_id()
    src = profiles_dir() / pid
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = profiles_dir() / BACKUPS_SUBDIR / f"{pid}-{reason}-{stamp}"
    with jsonio.STATE_LOCK:
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            dest.mkdir(parents=True, exist_ok=True)
    return dest


def reset_active() -> tuple[ProfileMeta, Path]:
    """Back up, then reset prefs, level, memory, and custom personalities."""
    ensure_migrated()
    backup = backup_active("reset")
    reg = _load_registry_raw()
    with jsonio.STATE_LOCK:
        _write_fresh_profile_files(profiles_dir() / reg.active)
    _touch_meta(reg, reg.active)
    _save_registry(reg)
    meta = get_meta(reg.active)
    assert meta is not None
    return meta, backup


def _load_bundle_file(profile_id: str, filename: str) -> dict[str, Any]:
    path = profiles_dir() / profile_id / filename
    if not path.exists():
        if filename == PREFS_FILE:
            return _default_prefs_dict()
        if filename == PROFILE_FILE:
            return _default_profile_dict()
        if filename == MEMORY_FILE:
            return _default_memory_dict()
        if filename == PERSONALITIES_FILE:
            return {"presets": []}
    try:
        raw = _read_json(path)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        raw = {}
    return raw if isinstance(raw, dict) else {}


def export_bundle() -> dict[str, Any]:
    """Backup bundle of the active learner."""
    ensure_migrated()
    profile_id = active_profile_id()
    meta = get_meta(profile_id)
    if meta is None:
        raise KeyError(f"profile not found: {profile_id}")
    return {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "exported_at": _now_iso(),
        "label": meta.label,
        "prefs": _load_bundle_file(profile_id, PREFS_FILE),
        "learner_profile": _load_bundle_file(profile_id, PROFILE_FILE),
        "learner_memory": _load_bundle_file(profile_id, MEMORY_FILE),
        "user_personalities": _load_bundle_file(profile_id, PERSONALITIES_FILE),
    }


def import_bundle(bundle: dict[str, Any]) -> tuple[ProfileMeta, Path]:
    """Validate a backup bundle, back up the current learner, then restore over it."""
    ensure_migrated()
    if not isinstance(bundle, dict):
        raise ValueError("bundle must be a JSON object")
    fmt = str(bundle.get("format") or "").strip()
    if fmt and fmt != BUNDLE_FORMAT:
        raise ValueError(f"unsupported format: {fmt}")
    version = bundle.get("version", 1)
    try:
        version_i = int(version)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid bundle version") from exc
    if version_i != BUNDLE_VERSION:
        raise ValueError(f"unsupported bundle version: {version_i}")

    from kaiwa.learner_memory import memory_from_dict, save_memory
    from kaiwa.learner_profile import profile_from_dict, save_profile
    from kaiwa.personalities_store import _save_raw
    from kaiwa.prefs import save_prefs, validate_prefs_dict

    prefs_raw = bundle.get("prefs") or {}
    if not isinstance(prefs_raw, dict):
        raise ValueError("prefs must be an object")
    try:
        prefs = validate_prefs_dict(prefs_raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid prefs: {exc}") from exc

    profile_raw = bundle.get("learner_profile") or {}
    if not isinstance(profile_raw, dict):
        raise ValueError("learner_profile must be an object")
    try:
        learner = profile_from_dict(profile_raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid learner_profile: {exc}") from exc

    memory_raw = bundle.get("learner_memory") or {}
    if not isinstance(memory_raw, dict):
        raise ValueError("learner_memory must be an object")
    try:
        memory = memory_from_dict(memory_raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid learner_memory: {exc}") from exc

    personalities_raw = bundle.get("user_personalities") or {"presets": []}
    if not isinstance(personalities_raw, dict):
        personalities_raw = {"presets": []}
    presets_in = personalities_raw.get("presets") or []
    if not isinstance(presets_in, list):
        presets_in = []

    valid_presets: list[dict[str, Any]] = []
    for item in presets_in:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id", "")).strip()
        if not pid.startswith("user_"):
            continue
        label_p = str(item.get("label", "")).strip()
        desc = str(item.get("description", "")).strip()
        blurb = str(item.get("prompt_blurb", "")).strip()
        if not label_p or not blurb:
            continue
        if len(label_p) > 60 or len(desc) > 200 or len(blurb) > 2000:
            continue
        valid_presets.append(
            {
                "id": pid,
                "label": label_p,
                "description": desc,
                "prompt_blurb": blurb,
            }
        )

    # Everything validated — only now touch the active learner.
    backup = backup_active("import")
    reg = _load_registry_raw()
    dest = profiles_dir() / reg.active
    with jsonio.STATE_LOCK:
        save_prefs(prefs, dest / PREFS_FILE)
        save_profile(learner, dest / PROFILE_FILE)
        save_memory(memory, dest / MEMORY_FILE)
        _save_raw(valid_presets, dest / PERSONALITIES_FILE)
    _touch_meta(reg, reg.active)
    _save_registry(reg)
    meta = get_meta(reg.active)
    assert meta is not None
    return meta, backup
