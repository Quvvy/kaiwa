"""Print one version's section of CHANGELOG.md. Usage: release_notes.py 2.1.0"""

from __future__ import annotations

import re
import sys
from pathlib import Path

text = (Path(__file__).resolve().parents[1] / "CHANGELOG.md").read_text(encoding="utf-8")
match = re.search(rf"^## \[{re.escape(sys.argv[1])}\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.M | re.S)
if not match or not match.group(1).strip():
    raise SystemExit(f"No changelog section for {sys.argv[1]}")
sys.stdout.buffer.write(match.group(1).strip().encode("utf-8") + b"\n")
