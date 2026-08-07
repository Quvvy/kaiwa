from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kaiwa.config import ROOT

USER_PERSONALITIES_PATH = ROOT / "data" / "user_personalities.json"
MAX_USER_PRESETS = 20
_SLUG_RE = re.compile(r"[^a-z0-9_]+")


@dataclass
class UserPersonality:
    id: str
    label: str
    description: str
    prompt_blurb: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def public_dict(self) -> dict[str, str]:
        d = self.to_dict()
        d["source"] = "user"
        return d


def _slugify(label: str) -> str:
    base = label.strip().lower().replace(" ", "_").replace("-", "_")
    base = _SLUG_RE.sub("", base)
    base = base.strip("_") or "preset"
    return f"user_{base[:40]}"


def _load_raw(path: Path | None = None) -> list[dict[str, Any]]:
    from kaiwa.profiles import personalities_path

    prefs_path = path or personalities_path()
    if not prefs_path.exists():
        return []
    try:
        raw = json.loads(prefs_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, dict):
        return []
    presets = raw.get("presets", [])
    return presets if isinstance(presets, list) else []


def _save_raw(presets: list[dict[str, Any]], path: Path | None = None) -> None:
    from kaiwa.profiles import personalities_path

    prefs_path = path or personalities_path()
    prefs_path.parent.mkdir(parents=True, exist_ok=True)
    prefs_path.write_text(
        json.dumps({"presets": presets}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _validate_fields(
    *,
    label: str,
    description: str,
    prompt_blurb: str,
) -> tuple[str, str, str]:
    label = (label or "").strip()
    description = (description or "").strip()
    prompt_blurb = (prompt_blurb or "").strip()
    if not label:
        raise ValueError("label is required")
    if len(label) > 60:
        raise ValueError("label must be ≤ 60 characters")
    if len(description) > 200:
        raise ValueError("description must be ≤ 200 characters")
    if not prompt_blurb:
        raise ValueError("prompt_blurb is required")
    if len(prompt_blurb) > 2000:
        raise ValueError("prompt_blurb must be ≤ 2000 characters")
    return label, description, prompt_blurb


def list_user_presets(path: Path | None = None) -> list[UserPersonality]:
    out: list[UserPersonality] = []
    for item in _load_raw(path):
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id", "")).strip()
        if not pid.startswith("user_"):
            continue
        try:
            label, description, prompt_blurb = _validate_fields(
                label=str(item.get("label", "")),
                description=str(item.get("description", "")),
                prompt_blurb=str(item.get("prompt_blurb", "")),
            )
        except ValueError:
            continue
        out.append(
            UserPersonality(
                id=pid,
                label=label,
                description=description,
                prompt_blurb=prompt_blurb,
            )
        )
    return out


def get_user_preset(preset_id: str, path: Path | None = None) -> UserPersonality | None:
    for preset in list_user_presets(path):
        if preset.id == preset_id:
            return preset
    return None


def create_user_preset(
    *,
    label: str,
    description: str,
    prompt_blurb: str,
    path: Path | None = None,
) -> UserPersonality:
    label, description, prompt_blurb = _validate_fields(
        label=label, description=description, prompt_blurb=prompt_blurb
    )
    existing = list_user_presets(path)
    if len(existing) >= MAX_USER_PRESETS:
        raise ValueError(f"at most {MAX_USER_PRESETS} user presets allowed")

    base_id = _slugify(label)
    preset_id = base_id
    n = 2
    used = {p.id for p in existing}
    while preset_id in used:
        preset_id = f"{base_id}_{n}"
        n += 1

    preset = UserPersonality(
        id=preset_id,
        label=label,
        description=description,
        prompt_blurb=prompt_blurb,
    )
    raw = [p.to_dict() for p in existing] + [preset.to_dict()]
    _save_raw(raw, path)
    return preset


def update_user_preset(
    preset_id: str,
    *,
    label: str,
    description: str,
    prompt_blurb: str,
    path: Path | None = None,
) -> UserPersonality:
    if not preset_id.startswith("user_"):
        raise ValueError("only user_ presets can be updated")
    label, description, prompt_blurb = _validate_fields(
        label=label, description=description, prompt_blurb=prompt_blurb
    )
    existing = list_user_presets(path)
    found = False
    updated: list[UserPersonality] = []
    for preset in existing:
        if preset.id == preset_id:
            updated.append(
                UserPersonality(
                    id=preset_id,
                    label=label,
                    description=description,
                    prompt_blurb=prompt_blurb,
                )
            )
            found = True
        else:
            updated.append(preset)
    if not found:
        raise KeyError(f"preset not found: {preset_id}")
    _save_raw([p.to_dict() for p in updated], path)
    return updated[[p.id for p in updated].index(preset_id)]


def delete_user_preset(preset_id: str, path: Path | None = None) -> bool:
    if not preset_id.startswith("user_"):
        raise ValueError("only user_ presets can be deleted")
    existing = list_user_presets(path)
    remaining = [p for p in existing if p.id != preset_id]
    if len(remaining) == len(existing):
        return False
    _save_raw([p.to_dict() for p in remaining], path)
    return True
