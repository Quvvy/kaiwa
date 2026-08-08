"""Canonical PTT binding strings shared by desktop hook matching.

Forms:
  key:v, key:f24, key:space, mouse:x1, mouse:middle, …
"""

from __future__ import annotations

import re
from typing import Any

# Windows VK_F1=0x70 … VK_F24=0x87
_VK_F1 = 0x70
_VK_TO_KEY: dict[int, str] = { _VK_F1 + i: f"f{i + 1}" for i in range(24) }

_KEY_ALIASES = {
    " ": "space",
    "spacebar": "space",
    "esc": "esc",
    "escape": "esc",
    "arrowup": "up",
    "arrowdown": "down",
    "arrowleft": "left",
    "arrowright": "right",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "return": "enter",
    "enter": "enter",
    "page_up": "pageup",
    "page_down": "pagedown",
    "pageup": "pageup",
    "pagedown": "pagedown",
}

_ANGLE_VK_RE = re.compile(r"^<(\d+)>$")
_CODE_KEY_RE = re.compile(r"^key([a-z0-9])$", re.I)
_CODE_F_RE = re.compile(r"^f(\d{1,2})$", re.I)
_CODE_DIGIT_RE = re.compile(r"^digit([0-9])$", re.I)
_CODE_NUMPAD_RE = re.compile(r"^numpad([0-9])$", re.I)


def canonicalize_binding(raw: str) -> str:
    """Normalize a stored or live binding to `key:…` or `mouse:…`."""
    s = (raw or "").strip().lower()
    if not s:
        return ""
    if s.startswith("mouse:"):
        btn = s[6:].strip()
        return f"mouse:{btn}" if btn else ""
    if s.startswith("key:"):
        name = s[4:].strip()
    else:
        name = s

    m = _ANGLE_VK_RE.match(name)
    if m:
        vk = int(m.group(1))
        mapped = _VK_TO_KEY.get(vk)
        if mapped:
            return f"key:{mapped}"
        return f"key:vk{vk}"

    if name.startswith("vk") and name[2:].isdigit():
        vk = int(name[2:])
        mapped = _VK_TO_KEY.get(vk)
        if mapped:
            return f"key:{mapped}"
        return f"key:vk{vk}"

    # KeyboardEvent.code forms: KeyV, F24, Digit1, Numpad0
    cm = _CODE_KEY_RE.match(name)
    if cm:
        return f"key:{cm.group(1).lower()}"
    fm = _CODE_F_RE.match(name)
    if fm:
        return f"key:f{int(fm.group(1))}"
    dm = _CODE_DIGIT_RE.match(name)
    if dm:
        return f"key:{dm.group(1)}"
    nm = _CODE_NUMPAD_RE.match(name)
    if nm:
        return f"key:numpad{nm.group(1)}"

    name = _KEY_ALIASES.get(name, name)
    # Strip accidental "key." prefix from pynput Key.f24 already handled
    if name.startswith("key."):
        name = name[4:]
    return f"key:{name}" if name else ""


def binding_from_pynput_key(key: Any) -> str:
    """Map a pynput keyboard key object to a canonical binding."""
    try:
        from pynput.keyboard import Key, KeyCode
    except ImportError:
        return canonicalize_binding(str(key))

    vk = getattr(key, "vk", None)
    if isinstance(vk, int) and vk in _VK_TO_KEY:
        return f"key:{_VK_TO_KEY[vk]}"

    if isinstance(key, KeyCode):
        ch = key.char
        if ch:
            return canonicalize_binding(f"key:{ch}")
        if isinstance(vk, int):
            mapped = _VK_TO_KEY.get(vk)
            if mapped:
                return f"key:{mapped}"
            return f"key:vk{vk}"

    if isinstance(key, Key):
        name = getattr(key, "name", None) or str(key)
        if str(name).startswith("Key."):
            name = str(name)[4:]
        return canonicalize_binding(f"key:{name}")

    return canonicalize_binding(f"key:{key}")


def binding_from_pynput_mouse(button: Any) -> str:
    name = str(button).split(".")[-1].lower()
    return canonicalize_binding(f"mouse:{name}")


def format_binding_label(binding: str) -> str:
    b = canonicalize_binding(binding)
    if not b:
        return "(not set)"
    if b.startswith("key:"):
        return b[4:].upper()
    if b.startswith("mouse:"):
        return f"Mouse {b[6:]}"
    return b
