"""Fail the build if a bundled module needs a Visual C++ runtime DLL that isn't bundled.

A clean Windows PC may not have the VC++ Redistributable, so every msvcp/vcruntime/
concrt DLL that a .pyd or .dll imports must ship with the app.

Usage: python packaging/check_dlls.py <folder> [<folder> ...]
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pefile

MSVC = ("msvcp", "vcruntime", "concrt", "vcomp")


def missing(folder: Path) -> dict[str, set[str]]:
    binaries = [*folder.rglob("*.pyd"), *folder.rglob("*.dll"), *folder.rglob("*.exe")]
    present = {p.name.lower() for p in binaries}
    need: dict[str, set[str]] = defaultdict(set)
    for path in binaries:
        try:
            pe = pefile.PE(str(path), fast_load=True)
            pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
        except pefile.PEFormatError:
            continue
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            name = entry.dll.decode(errors="replace").lower()
            if name.startswith(MSVC) and name not in present:
                need[name].add(str(path.relative_to(folder)))
        pe.close()
    return need


def main(folders: list[str]) -> int:
    bad = False
    for raw in folders:
        for dll, users in sorted(missing(Path(raw)).items()):
            bad = True
            print(f"{raw}: {dll} is not bundled; needed by {', '.join(sorted(users)[:4])}")
    if not bad:
        print("VC++ runtime DLLs: all bundled")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
